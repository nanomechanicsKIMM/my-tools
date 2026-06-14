# -*- coding: utf-8 -*-
"""
백테스트 자격(eligibility) 레이어 — 개별 시작일 정책.
공통구간 클리핑(신생펀드 배제) 대신, 각 펀드를 실제 데이터 존재 구간에만 유니버스에 편입.
백테스터 규칙: 시점 t에서 data_start <= t <= data_end 이고 그날 NAV가 존재하는 펀드만 매매 대상.
(룩어헤드 방지: 펀드는 설정/데이터 시작 이전에 선택 불가)

출력:
  eligibility.csv         — 펀드별 자격 메타(code,name,type,set_date,data_start,data_end,n_days,full_5y,has_gap,gap_ranges)
  universe_timeline.csv   — 월말별 매매가능 펀드 수(유니버스 성장 추이)
"""
import csv, glob, os, json
from datetime import datetime, timedelta

SRC = "nav_history"
START = "20210613"
GAP_DAYS = 25          # 연속 거래일 간격이 이보다 크면 데이터 공백으로 간주

def load_dates(path):
    return [r[0] for r in list(csv.reader(open(path, encoding="utf-8")))[1:] if r]

def find_gaps(dates):
    gaps = []
    for a, b in zip(dates, dates[1:]):
        da = datetime.strptime(a, "%Y%m%d"); db = datetime.strptime(b, "%Y%m%d")
        if (db - da).days > GAP_DAYS:
            gaps.append("%s~%s(%dd)" % (a, b, (db - da).days))
    return gaps

def month_ends(start, end):
    d = datetime.strptime(start[:6] + "01", "%Y%m%d")
    last = datetime.strptime(end, "%Y%m%d")
    outs = []
    while d <= last:
        nd = (d.replace(day=28) + timedelta(days=4)).replace(day=1)  # 다음달 1일
        outs.append((nd - timedelta(days=1)).strftime("%Y%m%d"))     # 이번달 말일
        d = nd
    return outs

def main():
    meta = json.load(open(os.path.join(SRC, "_metadata.json"), encoding="utf-8"))
    files = {os.path.basename(f)[:-4]: f for f in glob.glob(os.path.join(SRC, "*.csv"))
             if os.path.basename(f)[0] == "K" and "_" not in os.path.basename(f)}
    rows = []
    intervals = []   # (code, data_start, data_end, set(active dates))  유니버스 추이용
    for code, m in meta.items():
        dates = load_dates(files[code])
        gaps = find_gaps(dates)
        full = m["set_date"] <= START and not gaps and dates[0] <= "20210701"
        rows.append({"code": code, "name": m["name"], "type": m["type"],
                     "set_date": m["set_date"], "data_start": dates[0], "data_end": dates[-1],
                     "n_days": len(dates), "full_5y": "Y" if full else "N",
                     "has_gap": "Y" if gaps else "N", "gap_ranges": ";".join(gaps)})
        intervals.append((dates[0], dates[-1], set(dates)))
    rows.sort(key=lambda r: r["data_start"])
    with open("eligibility.csv", "w", newline="", encoding="utf-8") as w:
        cw = csv.DictWriter(w, fieldnames=list(rows[0].keys())); cw.writeheader(); cw.writerows(rows)

    # 유니버스 추이: 각 월말에 매매가능(구간 내) 펀드 수. 마지막 월말은 데이터 최종일로 클램프.
    gmax = max(r["data_end"] for r in rows)
    me = month_ends(START, gmax)
    with open("universe_timeline.csv", "w", newline="", encoding="utf-8") as w:
        cw = csv.writer(w); cw.writerow(["month_end", "tradeable_funds"])
        tl = []
        for d in me:
            dd = min(d, gmax)
            n = sum(1 for s, e, _ in intervals if s <= dd <= e)
            cw.writerow([dd, n]); tl.append((dd, n))

    full_n = sum(1 for r in rows if r["full_5y"] == "Y")
    gap_n = sum(1 for r in rows if r["has_gap"] == "Y")
    print("펀드:%d | 5년풀(공백無):%d | 신생/단축:%d | 내부공백:%d" %
          (len(rows), full_n, len(rows) - full_n, gap_n))
    print("유니버스 추이(반기):")
    for d, n in tl:
        if d[4:6] in ("06", "12"):
            print("  %s-%s : %d개 매매가능" % (d[:4], d[4:6], n))
    if gap_n:
        print("내부공백 펀드:")
        for r in rows:
            if r["has_gap"] == "Y":
                print("  %s %s : %s" % (r["code"], r["name"][:24], r["gap_ranges"]))

if __name__ == "__main__":
    main()
