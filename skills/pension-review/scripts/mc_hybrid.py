# -*- coding: utf-8 -*-
"""
하이브리드 백테스트 — 최소분산(위험자산 동적선택) + 예금 안전자산 결합 vs 추천65/35.
다중경로(부트스트랩 N경로)로 강세장 편향 제거.

전략:
- 추천65/35           : 인간 선택 6종 고정 + 예금35%
- 순수최소분산         : 위험자산만(DC캡 현금)
- MinVar65+예금35      : 최소분산 위험자산 ×0.65 + 예금0.35  ← 핵심(추천과 동일 비율, 선택만 알고리즘)
- MinVar50+예금50      : 보수
- MinVar변동성타겟9%   : 목표변동성 9.4%(추천 수준)에 맞춰 위험비중 동적 조정
- RP65+예금35          : 리스크패리티 하이브리드(비교)
"""
import numpy as np
import pandas as pd
import json
from mc_backtest import fast_run, boot_panel, rebal_dates_idx, PPY
from constraints import load_riskmap, dc_constrained
from backtest_portfolio import add_deposit, fixed, REC_PROXY
import algos
import recommend_algo as ra

RNG = np.random.default_rng(20260614)


def hybrid(base_factory, risk_ratio):
    base = base_factory()
    def strat(nav_upto, date):
        w = {c: x for c, x in base(nav_upto, date).items() if c != "DEPOSIT" and x > 0}
        s = sum(w.values())
        if s <= 0:
            return {"DEPOSIT": 1.0}
        out = {c: x / s * risk_ratio for c, x in w.items()}
        out["DEPOSIT"] = 1 - risk_ratio
        return out
    return strat


def vol_target(base_factory, target=0.094, lookback=252):
    base = base_factory()
    def strat(nav_upto, date):
        w = {c: x for c, x in base(nav_upto, date).items() if c != "DEPOSIT" and x > 0}
        s = sum(w.values())
        if s <= 0:
            return {"DEPOSIT": 1.0}
        w = {c: x / s for c, x in w.items()}
        codes = list(w)
        rets = nav_upto[codes].iloc[-lookback - 1:].pct_change().dropna()
        wv = np.array([w[c] for c in codes])
        pv = float(np.sqrt(wv @ (rets.cov().values * PPY) @ wv))
        rr = min(1.0, target / pv) if pv > 0 else 0.5
        out = {c: x * rr for c, x in w.items()}
        out["DEPOSIT"] = 1 - rr
        return out
    return strat


def strategy_set(rm):
    return {
        "추천65/35": fixed(REC_PROXY),
        "추천알고리즘(슬롯)": ra.recommend_strategy(),
        "순수최소분산": dc_constrained(algos.min_variance(), rm),
        "MinVar65+예금35": hybrid(algos.min_variance, 0.65),
        "MinVar50+예금50": hybrid(algos.min_variance, 0.50),
        "MinVar변동성타겟9%": vol_target(algos.min_variance, 0.094),
        "RP65+예금35": hybrid(algos.risk_parity, 0.65),
        "KOSPI200": fixed({"K55105BU5980": 1.0}),
    }


def main(N=300, L=40, freq="YE"):
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    elig = pd.read_csv("eligibility.csv")
    full5 = [c for c in nav_full.columns if c in set(elig[elig.full_5y == "Y"].code)]
    proxy = [c for c in REC_PROXY if c != "DEPOSIT"]
    full5 = sorted(set(full5) | set(proxy))
    navW = nav_full[full5]
    navW = navW.loc[:, navW.iloc[-1].notna()].dropna(how="any")
    ret_arr = navW.pct_change().dropna().values
    dates, codes = navW.index, list(navW.columns)
    rm = load_riskmap()
    strats = strategy_set(rm)
    print("유니버스 %d펀드 | %s~%s | N=%d L=%d %s" %
          (len(codes), dates[0].date(), dates[-1].date(), N, L, freq))

    def run_all(navAD):
        ri = rebal_dates_idx(navAD.index, freq)
        out = {}
        for n, fn in strats.items():
            res = fast_run(navAD, fn, ri)
            out[n] = res[0] if res else None
        return out

    # 원본경로 sanity
    base = run_all(add_deposit(navW))
    print("\n[원본경로]")
    for n, m in base.items():
        if m: print("  %-18s CAGR%6.2f Sharpe%6.3f MDD%7.2f" % (n, m["CAGR%"], m["Sharpe"], m["MDD%"]))

    # 부트스트랩
    import mc_backtest
    mc_backtest.RNG = RNG
    met = {n: {"CAGR%": [], "Sharpe": [], "MDD%": [], "변동성%": []} for n in strats}
    for p in range(N):
        navAD = add_deposit(boot_panel(ret_arr, dates, codes, L))
        for n, m in run_all(navAD).items():
            if m:
                for k in met[n]:
                    met[n][k].append(m[k])
        if (p + 1) % 50 == 0:
            print("  ...%d/%d" % (p + 1, N))
    json.dump(met, open("hybrid_results.json", "w"), ensure_ascii=False)

    # 분포 + 1위빈도
    print("\n" + "=" * 92)
    print("%-18s | %-20s | %-18s | %-16s" % ("전략", "Sharpe 중앙[5,95]", "CAGR%중앙[5,95]", "MDD%중앙/최악"))
    sh = {n: np.array(met[n]["Sharpe"]) for n in strats}
    npath = min(len(v) for v in sh.values())
    win = {n: 0 for n in strats}
    for i in range(npath):
        win[max(strats, key=lambda n: sh[n][i])] += 1
    for n in strats:
        s, c, m = np.array(met[n]["Sharpe"]), np.array(met[n]["CAGR%"]), np.array(met[n]["MDD%"])
        print("%-18s | %5.2f [%5.2f,%5.2f] | %5.1f [%5.1f,%5.1f] | %6.1f /%6.1f" %
              (n, np.median(s), np.percentile(s, 5), np.percentile(s, 95),
               np.median(c), np.percentile(c, 5), np.percentile(c, 95), np.median(m), np.min(m)))
    print("\n[Sharpe 1위 빈도 /%d]" % npath)
    for n, w in sorted(win.items(), key=lambda x: -x[1]):
        print("  %-18s %d (%.0f%%)" % (n, w, w / npath * 100))

    # 하락장(추천 CAGR 하위25%)
    rc = np.array(met["추천65/35"]["CAGR%"])
    thr = np.percentile(rc, 25)
    bear = np.where(rc <= thr)[0]
    print("\n[하락장 하위25%% (%d경로)] 평균 Sharpe / MDD" % len(bear))
    for n in strats:
        print("  %-18s %5.2f / %6.1f%%" %
              (n, np.mean(np.array(met[n]["Sharpe"])[bear]), np.mean(np.array(met[n]["MDD%"])[bear])))


if __name__ == "__main__":
    import sys
    main(N=int(sys.argv[1]) if len(sys.argv) > 1 else 300)
