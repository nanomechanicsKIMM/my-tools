# -*- coding: utf-8 -*-
"""
10개 퀀트 알고리즘 백테스트 + 추천65/35 비교.
- 유니버스: 전체 283펀드(알고리즘이 모멘텀 상위20 후보풀에서 배분). 추천은 proxy 6종+예금.
- 공통 조건: 분기 리밸(QE), warmup=252, execution_lag=1, cost 20bp, DC제약(위험70/단일40).
- 산출: 성과표(콘솔) + algos_equity_curve.png + algos_riskreturn.png
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

from backtester import Backtester
from constraints import load_riskmap, dc_constrained
from backtest_portfolio import add_deposit, fixed, REC_PROXY
from algos import ALGOS

COST, REBAL, WARMUP = 20, "QE", 252


def main():
    nav = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    rm = load_riskmap()
    print("패널:", nav.shape, nav.index[0].date(), "~", nav.index[-1].date())
    print("조건: %s 리밸 | warmup %d | cost %dbp | DC제약(위험70/단일40)\n" % (REBAL, WARMUP, COST))

    results = {}

    # --- 10개 알고리즘 (전체 유니버스, DC제약) ---
    bt = Backtester(nav, execution_lag=1, cost_bps=COST, rebalance=REBAL)
    for name, algo in ALGOS.items():
        res = bt.run(dc_constrained(algo, rm), warmup=WARMUP)
        results[name] = res

    # --- 추천 65/35 (proxy 6종+예금) ---
    proxy = [c for c in REC_PROXY if c != "DEPOSIT"]
    navB = add_deposit(nav[proxy].dropna(how="any"))
    btB = Backtester(navB, execution_lag=1, cost_bps=COST, rebalance=REBAL)
    results["추천65/35"] = btB.run(fixed(REC_PROXY), warmup=WARMUP)

    # --- 벤치: KOSPI200 ---
    btK = Backtester(nav[["K55105BU5980"]], execution_lag=1, cost_bps=COST, rebalance=REBAL)
    results["KOSPI200"] = btK.run(fixed({"K55105BU5980": 1.0}), warmup=WARMUP)

    # ===== 성과표 =====
    print("=" * 108)
    print("%-20s %8s %7s %7s %8s %8s %8s %7s %7s" %
          ("전략", "총수익%", "CAGR%", "변동%", "Sharpe", "Sortino", "MDD%", "Calmar", "회전%"))
    rows = []
    for name, res in results.items():
        m = res["metrics"]
        rows.append((name, m))
        print("%-20s %8.2f %7.2f %7.2f %8.3f %8.3f %8.2f %7.3f %7.0f" %
              (name, m["총수익%"], m["CAGR%"], m["변동성%"], m["Sharpe"], m["Sortino"],
               m["MDD%"], m["Calmar"], m["연회전율%"]))

    # Sharpe 순위
    print("\n[Sharpe 순위]")
    for i, (name, m) in enumerate(sorted(rows, key=lambda x: -x[1]["Sharpe"]), 1):
        mark = " ★추천" if name == "추천65/35" else ""
        print("  %2d. %-20s Sharpe %.3f | CAGR %.2f%% | MDD %.2f%%%s" %
              (i, name, m["Sharpe"], m["CAGR%"], m["MDD%"], mark))

    # ===== 그래프1: equity curve =====
    fig, ax = plt.subplots(figsize=(12, 6.5))
    order = sorted(results.items(), key=lambda x: -x[1]["metrics"]["Sharpe"])
    for name, res in order:
        eq = res["equity"].dropna()
        cum = (eq / eq.iloc[0] - 1) * 100
        if name == "추천65/35":
            ax.plot(cum.index, cum, label=name, lw=3, color="black", zorder=10)
        elif name == "KOSPI200":
            ax.plot(cum.index, cum, label=name, lw=1.5, color="#999", ls="--")
        else:
            ax.plot(cum.index, cum, label=name, lw=1.3, alpha=0.8)
    ax.set_title("10개 퀀트 알고리즘 vs 추천65/35 — 누적수익률 (분기리밸·DC제약)", fontsize=13)
    ax.set_ylabel("누적수익률 (%)"); ax.axhline(0, color="k", lw=0.5)
    ax.legend(loc="upper left", fontsize=8, ncol=2); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("algos_equity_curve.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("\n저장: algos_equity_curve.png")

    # ===== 그래프2: 위험-수익 산점 =====
    fig, ax = plt.subplots(figsize=(9, 7))
    for name, res in results.items():
        m = res["metrics"]
        is_rec = name == "추천65/35"
        is_bench = name == "KOSPI200"
        col = "black" if is_rec else ("#999" if is_bench else "#1f77b4")
        sz = 180 if is_rec else 90
        ax.scatter(m["변동성%"], m["CAGR%"], s=sz, color=col, zorder=5 if is_rec else 3,
                   edgecolors="white", linewidths=1)
        ax.annotate(name, (m["변동성%"], m["CAGR%"]), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_title("위험(변동성) vs 수익(CAGR)", fontsize=13)
    ax.set_xlabel("변동성 (%)"); ax.set_ylabel("CAGR (%)"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("algos_riskreturn.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("저장: algos_riskreturn.png")

    return results


if __name__ == "__main__":
    main()
