# -*- coding: utf-8 -*-
"""
수정기준가(분배 재투자 후방조정) 생성기.
배경: 한국 펀드는 결산 시 분배금 지급 후 기준가를 1000 근처로 리셋 -> 원기준가엔 가짜 폭락.
조정: 분배락일 d의 계수 = raw[d]/raw[d-1] (=P_after/P_before)를 d 이전 전구간에 누적 곱(후방조정).
      -> 결산일 수익률 0, 일일수익률(비율) 보존, 최신 기준가는 raw 그대로 유지(백테스트 표준).

분배락 식별(데이터 검증 규칙):
  |raw[d] - 1000| <= BAND  AND  raw[d-1]/raw[d] >= DROP
  - BAND=1.5 : 분배 직후 999.9x~1000.0x 착지 포착(당일 운용손익 ±소액)
  - DROP=1.003: 999.04->1000.01 같은 자연통과(상승) 제외, 진짜 분배락(하락)만
  - 시장 폭락(nav가 1000과 무관)은 BAND가 자동 배제

출력: adjusted_nav/{code}.csv (date,raw_nav,adj_nav,ret)
      adjusted_nav/_distributions.json (펀드별 분배락 내역)
"""
import csv, os, glob, json

SRC_DIR = "nav_history"
OUT_DIR = "adjusted_nav"
BAND = 1.5      # 1000 근처 밴드
DROP = 1.003    # 직전/직후 최소 하락비율

def is_ex(prev, cur):
    return abs(cur - 1000.0) <= BAND and prev / cur >= DROP

def load(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))[1:]
    return [(r[0], float(r[1])) for r in rows if r and r[1]]

def adjust(navs):
    """navs: 오름차순 float 리스트. 반환: adj 리스트, ex-date 인덱스/계수 리스트."""
    n = len(navs)
    adj = [0.0] * n
    exs = []
    cum = 1.0
    adj[n - 1] = navs[n - 1]
    for i in range(n - 1, 0, -1):
        if is_ex(navs[i - 1], navs[i]):
            factor = navs[i] / navs[i - 1]
            cum *= factor
            exs.append((i, factor))
        adj[i - 1] = navs[i - 1] * cum
    return adj, exs

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(set(f for f in glob.glob(os.path.join(SRC_DIR, "*.csv"))
                       if os.path.basename(f)[0] == "K" and "_" not in os.path.basename(f)))
    dist = {}
    n_ex_total = 0
    affected = 0
    for f in files:
        code = os.path.basename(f)[:-4]
        series = load(f)
        dates = [d for d, _ in series]
        navs = [v for _, v in series]
        adj, exs = adjust(navs)
        if exs:
            affected += 1
            n_ex_total += len(exs)
            dist[code] = [{"date": dates[i], "p_before": round(navs[i - 1], 2),
                           "p_after": round(navs[i], 2), "factor": round(fac, 6)}
                          for i, fac in sorted(exs)]
        with open(os.path.join(OUT_DIR, code + ".csv"), "w", newline="", encoding="utf-8") as w:
            cw = csv.writer(w)
            cw.writerow(["date", "raw_nav", "adj_nav", "ret"])
            prev = None
            for k in range(len(dates)):
                ret = "" if prev is None else round(adj[k] / prev - 1, 6)
                cw.writerow([dates[k], navs[k], round(adj[k], 4), ret])
                prev = adj[k]
    json.dump(dist, open(os.path.join(OUT_DIR, "_distributions.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("펀드:%d | 분배락 발생 펀드:%d | 총 분배락:%d건" % (len(files), affected, n_ex_total))

if __name__ == "__main__":
    main()
