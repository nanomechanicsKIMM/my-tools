# -*- coding: utf-8 -*-
"""5년 분기별 최고 수익률 섹터 변천 — bar chart + 데이터.
섹터 = region(미국/한국/중국/인도/...) + 강한 테마(반도체/바이오/금) 분리.
섹터 수익률 = 섹터 펀드들의 3개월(분기) 수익률 평균 ± 표준편차.
단일펀드 섹터(대표성·신뢰성 부족, 분배락 과탐 위험)는 제외(MIN_N=2)."""
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

MIN_N = 2
cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))
meta = json.load(open("nav_history/_metadata.json", encoding="utf-8"))


EXCLUDE = {"브라질"}  # 단일펀드 + 분배락 과탐(K55301B43371) → 명시 제외


def sector(c):
    nm = meta.get(c, {}).get("name", "")
    info = cls.get(nm, {})
    th = info.get("themes", [])
    rg = info.get("region")
    if "semiconductor" in th or any(k in nm for k in ["반도체", "필라델피아"]):
        return "반도체"
    if "healthcare" in th or any(k in nm for k in ["바이오", "헬스", "제약", "의료"]):
        return "바이오/의료"
    if "space" in th or any(k in nm for k in ["방산", "국방", "우주", "항공", "디펜스"]):
        return "국방/우주"
    if "energy" in th or "ev" in th or any(
            k in nm for k in ["2차전지", "이차전지", "배터리", "전기차", "친환경",
                              "신재생", "그린", "클린테크", "클린에너지", "에너지"]):
        return "에너지/이차전지"
    if "골드" in nm or "금광" in nm:
        return "금"
    m = {"us": "미국", "korea": "한국", "china": "중국", "india": "인도", "vietnam": "베트남",
         "brazil": "브라질", "japan": "일본", "europe": "유럽", "global": "글로벌",
         "emerging": "신흥국", "asean": "아세안", "asia": "아시아"}
    return m.get(rg, "기타")


def qlabel(d):
    return "%dQ%d" % (d.year, (d.month - 1) // 3 + 1)


def main():
    nav = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    sectors = {}
    for c in nav.columns:
        sectors.setdefault(sector(c), []).append(c)
    sectors = {s: f for s, f in sectors.items()
               if len(f) >= MIN_N and s not in EXCLUDE}  # 단일펀드 + 명시 제외(브라질)
    q = nav.resample("QE").last()
    qret = q.pct_change(fill_method=None) * 100

    results = []  # (label, sector, mean, std, n, runner_up, ru_val)
    for qi, date in enumerate(qret.index):
        if qi == 0:
            continue
        sv = {}
        for s, funds in sectors.items():
            vals = qret.loc[date, funds].dropna()
            if len(vals) >= MIN_N:
                sv[s] = (vals.mean(), vals.std(), len(vals))
        if not sv:
            continue
        rank = sorted(sv, key=lambda s: -sv[s][0])
        best = rank[0]
        results.append((qlabel(date), best, sv[best][0], sv[best][1], sv[best][2],
                        rank[1] if len(rank) > 1 else "-", sv[rank[1]][0] if len(rank) > 1 else 0))

    # 출력
    print("분기별 최고 수익률 섹터 (MIN_N=%d):" % MIN_N)
    for r in results:
        print("  %-7s %-6s %+6.1f%% (std%5.1f n%d) | 2위 %s %+.1f%%" %
              (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))

    # ---- Bar chart ----
    labels = [r[0] for r in results]
    sects = [r[1] for r in results]
    vals = [r[2] for r in results]
    stds = [r[3] for r in results]
    uniq = list(dict.fromkeys(sects))
    cmap = plt.cm.tab20
    colors = {s: cmap(i % 20) for i, s in enumerate(uniq)}

    fig, ax = plt.subplots(figsize=(16, 7.5))
    bars = ax.bar(range(len(labels)), vals, yerr=stds, capsize=3,
                  color=[colors[s] for s in sects], edgecolor="white", linewidth=0.7,
                  error_kw=dict(ecolor="#555", lw=1))
    for i, (b, s, v) in enumerate(zip(bars, sects, vals)):
        ax.text(i, v + stds[i] + 1.2, s, ha="center", va="bottom", fontsize=9, fontweight="bold",
                color=colors[s])
        ax.text(i, v / 2, "%.0f" % v, ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_ylabel("분기 수익률 (%)", fontsize=12)
    ax.set_title("5년 분기별 최고 수익률 섹터 변천 (2021Q3~2026Q2)\n섹터 = 과기공제회 펀드 3개월 평균수익률 ± 표준편차, 단일펀드 섹터 제외",
                 fontsize=13)
    ax.axhline(0, color="k", lw=0.6)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(handles=[Patch(color=colors[s], label=s) for s in uniq],
              ncol=len(uniq), loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=10, frameon=False)
    fig.tight_layout()
    fig.savefig("sector_rotation.png", dpi=120, bbox_inches="tight")
    print("\n저장: sector_rotation.png")
    # 섹터 출현 빈도(변천 분석용)
    from collections import Counter
    print("최고섹터 출현 빈도:", dict(Counter(sects).most_common()))
    return results


if __name__ == "__main__":
    main()
