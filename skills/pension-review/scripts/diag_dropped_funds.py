# -*- coding: utf-8 -*-
"""
탈락 펀드 2종 원인 추정 — 수익률 추이·순자산·데이터종료일·동종 상대성과 종합.
탈락: K55205B20547 미래에셋글로벌EMP(채권혼합-재간접), K55102BT6570 하나글로벌리츠(P2E)
주: 공제회 라인업 제외는 내부 결정 → 데이터 기반 '추측'. 단정 금지.
"""
import csv, glob, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

MAY = "(20260508)_과기공제회_연금_실적배당형상품.csv"
DROP = {"K55205B20547": "미래에셋글로벌EMP(채권혼합)", "K55102BT6570": "하나글로벌리츠(P2E)"}
COLS = {"위험등급": 5, "기준가": 6, "1주": 9, "1개월": 10, "3개월": 11, "6개월": 12,
        "연초후": 13, "1년": 14, "3년": 15, "운용사": 16, "운용규모억": 17,
        "클래스설정액억": 18, "총보수": 19, "설정일": 21, "대유형": 2, "소유형": 3}


def fn(s):
    s = (s or "").replace(",", "").strip()
    try: return float(s)
    except: return None


def load_may():
    rows = list(csv.reader(open(MAY, encoding="utf-8-sig")))[2:]
    return {r[0].strip(): r for r in rows if r and r[0].strip()}


def nav_stats(code):
    rows = [r for r in list(csv.reader(open("adjusted_nav/%s.csv" % code, encoding="utf-8")))[1:] if r]
    dates = [pd.Timestamp(r[0]) for r in rows]
    adj = pd.Series([float(r[2]) for r in rows], index=dates)
    raw_end = float(rows[-1][1])
    ret = adj.pct_change().dropna()
    eq = adj / adj.iloc[0]
    yrs = len(adj) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    vol = ret.std() * np.sqrt(252)
    # 최근 1년 추세
    one_yr_ago = dates[-1] - pd.DateOffset(years=1)
    recent = adj[adj.index >= one_yr_ago]
    r1y = recent.iloc[-1] / recent.iloc[0] - 1 if len(recent) > 1 else np.nan
    return {"start": dates[0], "end": dates[-1], "n": len(adj),
            "cagr": cagr * 100, "mdd": mdd * 100, "vol": vol * 100, "r1y": r1y * 100,
            "adj": adj}


def main():
    may = load_may()
    print("데이터 최신 종료일 기준: 살아있으면 end≈2026-06-12 (청산 아님=라인업 제외)\n")

    # 동종 대유형 통계(5월 전체)
    by_type = {}
    for code, r in may.items():
        t = r[COLS["대유형"]]
        by_type.setdefault(t, []).append(code)

    series_for_plot = {}
    for code, label in DROP.items():
        r = may.get(code)
        st = nav_stats(code)
        series_for_plot[label] = st["adj"]
        typ = r[COLS["대유형"]]; sub = r[COLS["소유형"]]
        print("=" * 90)
        print("【%s】 %s" % (label, code))
        print("  유형: %s / %s | 운용사: %s | 위험등급: %s | 설정일: %s" %
              (typ, sub, r[COLS["운용사"]], r[COLS["위험등급"]], r[COLS["설정일"]]))
        print("  순자산(운용규모): %s억 | 클래스설정액: %s억 | 총보수: %s%%" %
              (r[COLS["운용규모억"]], r[COLS["클래스설정액억"]], r[COLS["총보수"]]))
        print("  공시수익률(5/8): 1개월 %s / 3개월 %s / 6개월 %s / 1년 %s / 3년 %s" %
              (r[COLS["1개월"]], r[COLS["3개월"]], r[COLS["6개월"]], r[COLS["1년"]], r[COLS["3년"]]))
        print("  NAV추이: %s~%s | CAGR %.2f%% | 변동성 %.2f%% | MDD %.2f%% | 최근1년 %.2f%%" %
              (st["start"].date(), st["end"].date(), st["cagr"], st["vol"], st["mdd"], st["r1y"]))
        # 동종 상대 위치 (1년 수익률, 순자산)
        peers = by_type[typ]
        peer_r1y = sorted(v for v in (fn(may[c][COLS["1년"]]) for c in peers) if v is not None)
        peer_aum = sorted(v for v in (fn(may[c][COLS["운용규모억"]]) for c in peers) if v is not None)
        my_r1y = fn(r[COLS["1년"]]); my_aum = fn(r[COLS["운용규모억"]])
        def pct_rank(arr, v):
            return sum(1 for x in arr if x < v) / len(arr) * 100 if arr and v is not None else None
        print("  동종('%s' %d개) 상대위치: 1년수익률 하위%.0f%%ile | 순자산 하위%.0f%%ile (중앙 %.0f억)" %
              (typ, len(peers), pct_rank(peer_r1y, my_r1y) or 0,
               pct_rank(peer_aum, my_aum) or 0, peer_aum[len(peer_aum) // 2]))
        print()

    # 그래프: 탈락 2펀드 누적수익률 추이 + KOSPI200 + 동종 평균
    fig, ax = plt.subplots(figsize=(11, 5.5))
    cols = ["#d62728", "#1f77b4"]
    for (label, s), c in zip(series_for_plot.items(), cols):
        ax.plot(s.index, (s / s.iloc[0] - 1) * 100, label=label, lw=2, color=c)
    # KOSPI200 (삼성KOSPI200) 비교선
    k = nav_stats("K55105BU5980")["adj"]
    ax.plot(k.index, (k / k.iloc[0] - 1) * 100, label="KOSPI200(참고)", lw=1.2,
            color="#999999", ls="--")
    ax.set_title("탈락 펀드 5년 누적수익률 추이", fontsize=13)
    ax.set_ylabel("누적수익률 (%)"); ax.axhline(0, color="k", lw=0.5)
    ax.legend(loc="upper left", fontsize=10); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("dropped_funds_trend.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("저장: dropped_funds_trend.png")


if __name__ == "__main__":
    main()
