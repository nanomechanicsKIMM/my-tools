# -*- coding: utf-8 -*-
"""객관적 심판(referee) — 후보 펀드선정 알고리즘 vs 추천65/35 페어 부트스트랩 평가.

도출/백테스트/critic 에이전트가 공유하는 단일 평가 기준.
- 동일 부트스트랩 경로(seed 고정)에서 추천65/35와 후보를 동시 백테스트 → 페어 비교.
- 게이트: 후보 부트스트랩 중앙 CAGR ≥ 1.10×추천 AND |MDD| ≤ 0.90×추천 (둘 다 충족시 PASS).
- forward-pricing(fast_run)·DC제약·거래비용 일관. 룩어헤드 차단은 fast_run이 보장(strategy는 nav.iloc[:ts+1]만 수신).

사용:
    from algo_eval import evaluate
    r = evaluate(my_strategy_fn)        # my_strategy_fn(nav_upto_df, date)->{code:w}
    print(r["gate"], r["cand"]["CAGR%_med"], r["cand"]["MDD%_med"])
"""
import json
import numpy as np
import pandas as pd
from mc_backtest import fast_run, boot_panel, rebal_dates_idx
from backtest_portfolio import add_deposit, fixed, REC_PROXY

FREQ = "ME"
PROXY = [c for c in REC_PROXY if c != "DEPOSIT"]
CAGR_MULT, MDD_MULT = 1.10, 0.90      # +10% CAGR, -10% MDD(절대값) 목표


def _universe():
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    elig = pd.read_csv("eligibility.csv")
    full5 = sorted(set(c for c in nav_full.columns if c in set(elig[elig.full_5y == "Y"].code)) | set(PROXY))
    navA0 = nav_full[full5]
    navA0 = navA0.loc[:, navA0.iloc[-1].notna()].dropna(how="any")
    return navA0


def _summ(arr):
    a = np.array(arr, dtype=float)
    return {"med": float(np.median(a)), "p5": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95))}


def evaluate(strategy_fn, N=200, L=40, seed=20260614, verbose=True):
    """후보 전략 vs 추천65/35 페어 부트스트랩. 반환: dict(rec, cand, paired, gate)."""
    navA0 = _universe()
    ret_arr = navA0.pct_change().dropna().values
    dates, codes = navA0.index, list(navA0.columns)
    rec_fn = fixed(REC_PROXY)

    def run_pair(navA):
        navR = add_deposit(navA[PROXY])
        navD = add_deposit(navA)
        rR = fast_run(navR, rec_fn, rebal_dates_idx(navR.index, FREQ))
        rC = fast_run(navD, strategy_fn, rebal_dates_idx(navD.index, FREQ))
        return (rR[0] if rR else None), (rC[0] if rC else None)

    # 부트스트랩 (mc_backtest의 전역 RNG 사용 — seed 고정 재현)
    import mc_backtest
    mc_backtest.RNG = np.random.default_rng(seed)
    rec = {"CAGR%": [], "Sharpe": [], "MDD%": [], "변동성%": []}
    cand = {"CAGR%": [], "Sharpe": [], "MDD%": [], "변동성%": []}
    pair_cagr, pair_mdd, pair_sharpe = [], [], []
    for p in range(N):
        navA = boot_panel(ret_arr, dates, codes, L)
        mR, mC = run_pair(navA)
        if mR and mC:
            for k in rec:
                rec[k].append(mR[k]); cand[k].append(mC[k])
            pair_cagr.append(mC["CAGR%"] - mR["CAGR%"])
            pair_mdd.append(abs(mR["MDD%"]) - abs(mC["MDD%"]))    # +면 후보 MDD 개선
            pair_sharpe.append(mC["Sharpe"] - mR["Sharpe"])

    rec_cagr_med = np.median(rec["CAGR%"]); rec_mdd_med = np.median(rec["MDD%"])
    cand_cagr_med = np.median(cand["CAGR%"]); cand_mdd_med = np.median(cand["MDD%"])
    cagr_ok = cand_cagr_med >= CAGR_MULT * rec_cagr_med
    mdd_ok = abs(cand_mdd_med) <= MDD_MULT * abs(rec_mdd_med)
    out = {
        "N": len(pair_cagr),
        "rec": {"CAGR%_med": round(rec_cagr_med, 2), "MDD%_med": round(rec_mdd_med, 2),
                "Sharpe_med": round(float(np.median(rec["Sharpe"])), 3)},
        "cand": {"CAGR%_med": round(cand_cagr_med, 2), "MDD%_med": round(cand_mdd_med, 2),
                 "Sharpe_med": round(float(np.median(cand["Sharpe"])), 3),
                 "CAGR%": _summ(cand["CAGR%"]), "MDD%": _summ(cand["MDD%"])},
        "paired": {"cagr_win%": round(100 * np.mean(np.array(pair_cagr) > 0), 1),
                   "mdd_win%": round(100 * np.mean(np.array(pair_mdd) > 0), 1),
                   "sharpe_win%": round(100 * np.mean(np.array(pair_sharpe) > 0), 1),
                   "both_win%": round(100 * np.mean((np.array(pair_cagr) > 0) & (np.array(pair_mdd) > 0)), 1)},
        "target": {"CAGR%_need": round(CAGR_MULT * rec_cagr_med, 2),
                   "MDD%_need": round(-MDD_MULT * abs(rec_mdd_med), 2)},
        "gate": {"cagr_ok": bool(cagr_ok), "mdd_ok": bool(mdd_ok), "PASS": bool(cagr_ok and mdd_ok)},
    }
    if verbose:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    # 자기검증: 추천65/35를 후보로 넣으면 게이트 FAIL(자기 자신은 +10% 못 넘음), 페어 동률
    print("=== self-test: 추천65/35 as candidate (should NOT pass) ===")
    evaluate(fixed(REC_PROXY), N=50)
