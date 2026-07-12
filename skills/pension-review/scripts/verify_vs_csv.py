# -*- coding: utf-8 -*-
"""
수집 NAV(KOFIA) vs 원본 CSV 수익률 전수 교차검증.
- 기본: data_raw/ 최신 CSV 자동 선택, 기준일 D = 파일명 날짜의 직전 영업일(포털 '전영업일 결제기준')
  한국 공휴일이 낀 경우 --date로 명시 오버라이드.
- 공시 수익률은 분배 재투자 기준 -> adj_nav 계산값이 일치, raw_nav는 분배락 펀드서 어긋나야 정상
- 기간시작 = 캘린더 역산 후 직전거래일(asof). CSV 공란이면 스킵.
"""
import argparse, csv, glob, os, re, bisect
import pandas as pd

_ap = argparse.ArgumentParser()
_ap.add_argument("--csv", default=None, help="원본 CSV 경로 (기본: data_raw/ 최신)")
_ap.add_argument("--date", default=None, help="기준일 YYYY-MM-DD (기본: 파일명 날짜의 직전 영업일)")
_a = _ap.parse_args()

if _a.csv:
    CSV = _a.csv
else:
    _cands = glob.glob("data_raw/*_과기공제회_연금_실적배당형상품.csv")
    if not _cands:
        raise SystemExit("data_raw/에 원본 CSV가 없습니다")
    CSV = max(_cands, key=lambda p: re.search(r"(20\d{6})", os.path.basename(p)).group(1))
_m = re.search(r"(20\d{6})", os.path.basename(CSV))
if _a.date:
    D = pd.Timestamp(_a.date)
else:
    D = pd.Timestamp(_m.group(1)) - pd.tseries.offsets.BDay(1)
print("CSV=%s | 기준일 D=%s (직전영업일 자동유도%s)" %
      (CSV, D.date(), "" if not _a.date else "; 수동지정"))
COLS = {"1주": 9, "1개월": 10, "3개월": 11, "6개월": 12, "YTD": 13, "1년": 14, "3년": 15}
OFF = {"1주": pd.DateOffset(weeks=1), "1개월": pd.DateOffset(months=1),
       "3개월": pd.DateOffset(months=3), "6개월": pd.DateOffset(months=6),
       "1년": pd.DateOffset(years=1), "3년": pd.DateOffset(years=3)}

def fnum(s):
    s = (s or "").strip().replace(",", "")
    try: return float(s)
    except: return None

# CSV 로드
csvd = {}
for r in list(csv.reader(open(CSV, encoding="utf-8")))[2:]:
    if not r or not r[0].strip(): continue
    csvd[r[0].strip()] = {"price": fnum(r[6]), "rets": {k: fnum(r[i]) for k, i in COLS.items()}}

def asof_b(dates, target):   # 직전 거래일(이하 최대) — 기준일/YTD용
    i = bisect.bisect_right(dates, target) - 1
    return i if i >= 0 else None

def asof_a(dates, target):   # 직후 거래일(이상 최소) — CSV 기간시작 규칙
    i = bisect.bisect_left(dates, target)
    return i if i < len(dates) else None

# 펀드별 검증
err_adj = {k: [] for k in COLS}   # (code, calc, csv, abserr)
err_raw = {k: [] for k in COLS}
price_err = []
missing = []
for f in sorted(glob.glob("adjusted_nav/*.csv")):
    code = os.path.basename(f)[:-4]
    if code not in csvd or "_" in code or code[0] != "K": continue
    rows = [r for r in list(csv.reader(open(f, encoding="utf-8")))[1:] if r]
    dates = [pd.Timestamp(r[0]) for r in rows]
    raw = [float(r[1]) for r in rows]
    adj = [float(r[2]) for r in rows]
    iD = asof_b(dates, D)
    if iD is None or dates[iD] != D:
        missing.append(code); continue
    # 기준가 검증
    cp = csvd[code]["price"]
    if cp: price_err.append((code, abs(raw[iD] - cp) / cp))
    # 수익률 검증
    for k in COLS:
        cv = csvd[code]["rets"][k]
        if cv is None: continue
        if k == "YTD":
            iS = asof_b(dates, pd.Timestamp(str(D.year - 1) + "-12-31"))
        else:
            iS = asof_a(dates, D - OFF[k])
        if iS is None or iS == iD: continue
        ca = (adj[iD] / adj[iS] - 1) * 100
        cr = (raw[iD] / raw[iS] - 1) * 100
        err_adj[k].append((code, ca, cv, abs(ca - cv)))
        err_raw[k].append((code, cr, cv, abs(cr - cv)))

# 리포트
import statistics as st
print("기준일 D=%s | 검증펀드=%d | D 미존재=%d" % (D.date(), len(csvd) - len(missing), len(missing)))
pe = sorted(e for _, e in price_err)
print("기준가 일치: 중앙 %.4f%% / 최대 %.4f%% / >0.1%% 펀드수 %d" %
      (pe[len(pe)//2]*100, pe[-1]*100, sum(1 for e in pe if e > 0.001)))
print("\n기간별 수익률 오차(%p) — adj(공시기준) vs raw(미보정)")
print("%-6s %5s | %8s %8s %8s | %8s  (adj오차<0.5%%p 비율)" % ("기간","n","adj중앙","adj_p95","adj최대","raw중앙"))
for k in ["1주","1개월","3개월","6개월","YTD","1년","3년"]:
    ea = sorted(e[3] for e in err_adj[k]); er = sorted(e[3] for e in err_raw[k])
    if not ea: continue
    p95 = ea[int(len(ea)*0.95)] if len(ea) > 1 else ea[0]
    pas = sum(1 for e in ea if e < 0.5) / len(ea) * 100
    print("%-6s %5d | %8.3f %8.3f %8.3f | %8.3f  (%.0f%%)" %
          (k, len(ea), ea[len(ea)//2], p95, ea[-1], er[len(er)//2], pas))

# 분배락 펀드 집중: 1년/3년에서 adj vs raw 극명 차이
print("\n분배락 펀드 raw 어긋남 입증 (1년 수익률, raw오차 상위5):")
big = sorted(err_raw["1년"], key=lambda x: -x[3])[:5]
for code, cr, cv, e in big:
    ca = next(a[1] for a in err_adj["1년"] if a[0] == code)
    print("  %s CSV=%.1f adj=%.1f(오차%.2f) raw=%.1f(오차%.2f)" % (code, cv, ca, abs(ca-cv), cr, e))

# 최종 판정
print("\n=== 최악 adj 오차 펀드(1년 기준) ===")
for code, ca, cv, e in sorted(err_adj["1년"], key=lambda x:-x[3])[:5]:
    print("  %s CSV=%.2f calc=%.2f 오차%.3f%%p" % (code, cv, ca, e))
