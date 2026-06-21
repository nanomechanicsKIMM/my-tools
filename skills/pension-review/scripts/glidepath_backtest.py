# -*- coding: utf-8 -*-
"""
60세 글라이드패스 비교 백테스트 + 포트폴리오별 5년 수익률 추이 그래프.

배경: portfolio_recommendation.md — "60세(2031, 5년 후) 위험자산 65%→50% 축소 검토".
백테스트는 과거 데이터이므로, 이 배분규칙을 proxy 5년 구간(글라이드 1주기)에 적용해 정적 배분과 비교.

비교 전략(위험자산 내 상대비중은 추천 동일, 위험/안전 비율만 변경):
  정적 70/30, 정적 65/35(현행), 정적 50/50(60세목표),
  글라이드 65→50(5년 선형), 글라이드 70→40(공격출발→보수도착)

산출:
  glidepath_comparison.png        — 글라이드 5종 누적수익률 + drawdown
  equity_curve_benchmark.png      — 추천 vs 벤치(위험100/KOSPI200/예금) 누적수익률 추이
  콘솔: 전략별 성과지표 표
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
from backtester import Backtester
from backtest_portfolio import add_deposit, fixed, REC_PROXY

# 위험자산 내 상대비중 (추천 기준, 합=1로 정규화)
RISK_REL = {"K55105BA7360": 0.22, "K55301B51580": 0.13, "K55105BU5980": 0.15,
            "K55307D05993": 0.08, "K55209CT1721": 0.07}
_s = sum(RISK_REL.values())
RISK_REL = {c: x / _s for c, x in RISK_REL.items()}


def static_mix(target_risk):
    w = {c: x * target_risk for c, x in RISK_REL.items()}
    w["DEPOSIT"] = round(1 - target_risk, 6)
    return w


def glidepath(start, end, r0, r1):
    span = (end - start).days
    def strat(nav_upto, date):
        frac = min(1.0, max(0.0, (date - start).days / span))
        tr = r0 + (r1 - r0) * frac
        w = {c: x * tr for c, x in RISK_REL.items()}
        w["DEPOSIT"] = 1 - tr
        return w
    return strat


def run(nav, strat):
    return Backtester(nav, execution_lag=1, cost_bps=20, rebalance="YE").run(strat, warmup=2)


def cum_ret(eq):
    return (eq / eq.iloc[0] - 1) * 100


def drawdown(eq):
    return (eq / eq.cummax() - 1) * 100


def main():
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    colsP = [c for c in REC_PROXY if c != "DEPOSIT"]
    sub = nav_full[colsP].dropna(how="any")
    navB = add_deposit(nav_full.loc[sub.index[0]:, colsP])
    start, end = navB.index[0], navB.index[-1]
    print("기간 %s ~ %s (%.1f년)\n" % (start.date(), end.date(), len(navB) / 252))

    # ---- 글라이드패스 비교 ----
    glide = {
        "정적 70/30": fixed(static_mix(0.70)),
        "정적 65/35 (현행)": fixed(static_mix(0.65)),
        "정적 50/50 (60세목표)": fixed(static_mix(0.50)),
        "글라이드 65→50": glidepath(start, end, 0.65, 0.50),
        "글라이드 70→40": glidepath(start, end, 0.70, 0.40),
    }
    gres = {k: run(navB, v) for k, v in glide.items()}
    print("=" * 100)
    print("[글라이드패스 비교] proxy 5년 | 연간 리밸 | 20bp")
    print("%-22s %8s %7s %7s %8s %8s %7s" % ("전략", "총수익%", "CAGR%", "변동%", "Sharpe", "MDD%", "Calmar"))
    for k, r in gres.items():
        m = r["metrics"]
        print("%-22s %8.2f %7.2f %7.2f %8.3f %8.2f %7.3f" %
              (k, m["총수익%"], m["CAGR%"], m["변동성%"], m["Sharpe"], m["MDD%"], m["Calmar"]))

    # ---- 벤치마크 ----
    risk_only = {c: x for c, x in RISK_REL.items()}
    bench = {
        "추천 65/35 (현행)": fixed(static_mix(0.65)),
        "위험자산 100% (예금0)": fixed({**risk_only}),
        "KOSPI200 100%": fixed({"K55105BU5980": 1.0}),
        "예금 100%": fixed({"DEPOSIT": 1.0}),
    }
    bres = {k: run(navB, v) for k, v in bench.items()}

    # ---- Fig1: 추천 vs 벤치 누적수익률 추이 ----
    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = {"추천 65/35 (현행)": "#d62728", "위험자산 100% (예금0)": "#1f77b4",
              "KOSPI200 100%": "#2ca02c", "예금 100%": "#7f7f7f"}
    for k, r in bres.items():
        ax.plot(r["equity"].index, cum_ret(r["equity"]), label=k, lw=2,
                color=colors[k], alpha=0.9)
    ax.set_title("포트폴리오별 5년 누적수익률 추이 — 추천 vs 벤치마크 (proxy, 연간 리밸)", fontsize=13)
    ax.set_ylabel("누적수익률 (%)"); ax.set_xlabel("")
    ax.axhline(0, color="k", lw=0.5); ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("equity_curve_benchmark.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("\n저장: equity_curve_benchmark.png")

    # ---- Fig2: 글라이드패스 비교 (누적수익 + drawdown) ----
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), height_ratios=[2, 1], sharex=True)
    gcolors = ["#d62728", "#ff7f0e", "#1f77b4", "#9467bd", "#2ca02c"]
    for (k, r), col in zip(gres.items(), gcolors):
        ax1.plot(r["equity"].index, cum_ret(r["equity"]), label=k, lw=2, color=col, alpha=0.9)
        ax2.plot(r["equity"].index, drawdown(r["equity"]), lw=1.5, color=col, alpha=0.85)
    ax1.set_title("글라이드패스 vs 정적 배분 — 누적수익률 (상) / 낙폭 MDD (하)", fontsize=13)
    ax1.set_ylabel("누적수익률 (%)"); ax1.axhline(0, color="k", lw=0.5)
    ax1.legend(loc="upper left", fontsize=10); ax1.grid(alpha=0.3)
    ax2.set_ylabel("낙폭 (%)"); ax2.axhline(0, color="k", lw=0.5); ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("glidepath_comparison.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("저장: glidepath_comparison.png")

    # ---- 최종 위험노출 확인(글라이드 종점) ----
    print("\n[글라이드 종점 위험비중 확인]")
    for k, st in [("글라이드 65→50", glide["글라이드 65→50"]), ("글라이드 70→40", glide["글라이드 70→40"])]:
        w0 = st(None, start); w1 = st(None, end)
        r0 = sum(v for c, v in w0.items() if c != "DEPOSIT")
        r1 = sum(v for c, v in w1.items() if c != "DEPOSIT")
        print("  %s: 시작 위험%.0f%% → 종료 위험%.0f%%" % (k, r0 * 100, r1 * 100))


if __name__ == "__main__":
    main()
