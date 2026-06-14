# -*- coding: utf-8 -*-
"""
장기(1년/3년) 수익률 adj오차 원인 진단.
가설: (A)분배락 보정 결함  (B)기간시작일 매칭(거래일 캘린더) 차이  (C)데이터 결함.
방법: 오차 상위 펀드의 분배락 내역 + 시작일 ±N일 NAV 민감도 분해.
"""
import csv, json, bisect
import pandas as pd

D = pd.Timestamp("2026-05-07")
CSV = "(20260508)_과기공제회_연금_실적배당형상품.csv"
COLS = {"1년": 14, "3년": 15, "YTD": 13, "6개월": 12}
OFF = {"1년": pd.DateOffset(years=1), "3년": pd.DateOffset(years=3),
       "6개월": pd.DateOffset(months=6)}
DIST = json.load(open("adjusted_nav/_distributions.json", encoding="utf-8"))

# CSV 공시값
csvd = {}
for r in list(csv.reader(open(CSV, encoding="utf-8")))[2:]:
    if not r or not r[0].strip():
        continue
    def fnum(s):
        s = (s or "").strip().replace(",", "")
        try: return float(s)
        except: return None
    csvd[r[0].strip()] = {k: fnum(r[i]) for k, i in COLS.items()}

TARGETS = ["K55209CT1721", "K55301B43371", "KR5223A95821", "K55301DD0305", "KR5105AI0048"]

def load(code):
    rows = [r for r in list(csv.reader(open("adjusted_nav/%s.csv" % code, encoding="utf-8")))[1:] if r]
    dates = [pd.Timestamp(r[0]) for r in rows]
    adj = [float(r[2]) for r in rows]
    return dates, adj

def idx_le(dates, t):  # 직전 거래일
    i = bisect.bisect_right(dates, t) - 1
    return i if i >= 0 else None

def idx_ge(dates, t):  # 직후 거래일
    i = bisect.bisect_left(dates, t)
    return i if i < len(dates) else None

print("기준일 D=%s\n" % D.date())
for code in TARGETS:
    dates, adj = load(code)
    iD = idx_le(dates, D)
    nD = DIST.get(code, [])
    print("=== %s | 분배락 %d건 | 데이터 %s~%s (%d일) ===" %
          (code, len(nD), dates[0].date(), dates[-1].date(), len(dates)))
    for k in ["6개월", "1년", "3년"]:
        cv = csvd.get(code, {}).get(k)
        if cv is None:
            continue
        tgt = D - OFF[k]
        iS = idx_ge(dates, tgt)        # verify가 쓰는 규칙(직후)
        iSb = idx_le(dates, tgt)       # 대안 규칙(직전)
        if iS is None:
            print("  %-4s CSV=%.2f | 시작일 데이터밖(신생)" % (k, cv)); continue
        ca = (adj[iD] / adj[iS] - 1) * 100
        cab = (adj[iD] / adj[iSb] - 1) * 100 if iSb is not None else float("nan")
        # 시작일 ±3거래일 민감도
        lo = max(0, iS - 3); hi = min(len(dates) - 1, iS + 3)
        ca_lo = (adj[iD] / adj[hi] - 1) * 100   # 더 늦은 시작 → 짧은 구간
        ca_hi = (adj[iD] / adj[lo] - 1) * 100   # 더 이른 시작 → 긴 구간
        gap_days = (dates[iS] - tgt).days
        print("  %-4s CSV=%6.2f | 직후매칭 calc=%6.2f(오차%5.2f, 시작%s %+dd) | 직전매칭 calc=%6.2f | ±3일밴드[%.1f~%.1f]" %
              (k, cv, ca, abs(ca - cv), dates[iS].date(), gap_days, cab, ca_lo, ca_hi))
    # 분배락 계수곱 (3년 누적 영향)
    if nD:
        prod = 1.0
        for d in nD:
            prod *= d["factor"]
        print("  분배락 누적계수곱=%.4f (보정 총효과 %.1f%%)" % (prod, (1/prod - 1) * 100))
    print()
