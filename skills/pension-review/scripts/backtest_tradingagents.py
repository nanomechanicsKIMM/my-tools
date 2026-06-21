# -*- coding: utf-8 -*-
"""TradingAgents 수집 3종(레짐게이트/변동성타게팅/앙상블투표) vs 추천65/35 검증.

- 엔진: mc_backtest.fast_run(forward-pricing·거래비용·DC) + Stationary Block Bootstrap 다중경로.
- 패널: 추천65/35는 proxy5+예금("R"). 신규3종+기준선은 전체유니버스+예금("D").
- 공정성: 전 전략 동일 월간(ME) 리밸. 타이밍無 mom5_base로 오버레이 순효과 분리.
- 출처: [[(20260614)_TradingAgents_퀀트알고리즘_수집]]
"""
import sys
import json
import numpy as np
import pandas as pd
from mc_backtest import fast_run, boot_panel, rebal_dates_idx
from backtest_portfolio import add_deposit, fixed, REC_PROXY
import algos_new as an

FREQ = "ME"
RNG = np.random.default_rng(20260614)
PROXY = [c for c in REC_PROXY if c != "DEPOSIT"]

STRATS = {
    "추천65/35":            ("R", fixed(REC_PROXY)),
    "모멘텀Top5(타이밍無)":  ("D", an.mom5_base()),
    "200SMA레짐게이트":      ("D", an.regime_gate()),
    "변동성타게팅10%":       ("D", an.vol_target(target=0.10)),
    "앙상블투표(MACD+SMA+RSI)": ("D", an.ensemble_vote()),
}


def run_all(navA):
    navR = add_deposit(navA[PROXY])
    navD = add_deposit(navA)
    riR = rebal_dates_idx(navR.index, FREQ)
    riD = rebal_dates_idx(navD.index, FREQ)
    out = {}
    for name, (t, fn) in STRATS.items():
        nv, ri = (navR, riR) if t == "R" else (navD, riD)
        res = fast_run(nv, fn, ri)
        out[name] = res[0] if res else None
    return out


def main(N=200, L=40):
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    elig = pd.read_csv("eligibility.csv")
    full5 = [c for c in nav_full.columns if c in set(elig[elig.full_5y == "Y"].code)]
    full5 = sorted(set(full5) | set(PROXY))
    navA0 = nav_full[full5]
    navA0 = navA0.loc[:, navA0.iloc[-1].notna()].dropna(how="any")
    ret_arr = navA0.pct_change().dropna().values
    dates, codes = navA0.index, list(navA0.columns)
    print("유니버스 %d펀드 | %s~%s | N=%d L=%d %s리밸" %
          (len(codes), dates[0].date(), dates[-1].date(), N, L, FREQ))

    base = run_all(navA0)
    print("\n[원본경로 sanity]")
    for n, m in base.items():
        if m:
            print("  %-22s CAGR%6.2f Sharpe%6.3f MDD%7.2f 변동%6.2f 회전%5.1f" %
                  (n, m["CAGR%"], m["Sharpe"], m["MDD%"], m["변동성%"], m.get("회전", 0)))

    metrics = {n: {"CAGR%": [], "Sharpe": [], "MDD%": [], "변동성%": []} for n in STRATS}
    for p in range(N):
        res = run_all(boot_panel(ret_arr, dates, codes, L))
        for n, m in res.items():
            if m:
                for k in metrics[n]:
                    metrics[n][k].append(m[k])
        if (p + 1) % 50 == 0:
            print("  ...%d/%d 경로" % (p + 1, N))

    json.dump(metrics, open("mc_tradingagents.json", "w"), ensure_ascii=False)
    print("\n저장: mc_tradingagents.json")

    print("\n" + "=" * 92)
    print("%-22s | %-20s | %-20s | %-14s" %
          ("전략", "Sharpe(중앙[5,95])", "CAGR%(중앙[5,95])", "MDD%(중앙/최악)"))
    sm = {n: np.array(metrics[n]["Sharpe"]) for n in STRATS}
    npath = min(len(v) for v in sm.values())
    win = {n: 0 for n in STRATS}
    for i in range(npath):
        win[max(STRATS, key=lambda n: sm[n][i])] += 1
    for n in STRATS:
        sh, cg, md = (np.array(metrics[n][k]) for k in ("Sharpe", "CAGR%", "MDD%"))
        print("%-22s | %5.2f [%5.2f,%5.2f] | %6.1f [%5.1f,%5.1f] | %6.1f / %6.1f" %
              (n, np.median(sh), np.percentile(sh, 5), np.percentile(sh, 95),
               np.median(cg), np.percentile(cg, 5), np.percentile(cg, 95),
               np.median(md), np.min(md)))
    print("\n[Sharpe 1위 빈도 / %d경로]" % npath)
    for n, w in sorted(win.items(), key=lambda x: -x[1]):
        print("  %-22s %d회 (%.0f%%)" % (n, w, w / npath * 100))

    rec = np.array(metrics["추천65/35"]["CAGR%"])
    thr = np.percentile(rec, 25)
    bear = np.where(rec <= thr)[0]
    print("\n[하락장: 추천 CAGR 하위25%% (%d경로, ≤%.1f%%)] 평균 Sharpe·MDD" % (len(bear), thr))
    for n in STRATS:
        sh = np.array(metrics[n]["Sharpe"])[bear]
        md = np.array(metrics[n]["MDD%"])[bear]
        print("  %-22s Sharpe %5.2f | MDD %6.1f%%" % (n, np.mean(sh), np.mean(md)))
    return metrics


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    main(N=N)
