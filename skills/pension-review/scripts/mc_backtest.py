# -*- coding: utf-8 -*-
"""
다중경로(부트스트랩) 재검증 — 강세장 편향 제거.

방법:
- Stationary Block Bootstrap(Politis-Romano 1994): 일별 수익률을 가변 블록(평균 L일)으로
  리샘플링 → N개 합성 5년 경로. 변동성군집·횡단상관 보존, 시간순서 제거.
- 각 경로에서 추천65/35 + 대표 알고리즘 백테스트 → 성과지표 분포.
- 하위 경로(CAGR 하위25%) = 하락장 시나리오 → 추천 방어력 검증.

엔진: 구간 벡터화 경량 백테스터(forward-pricing·DC제약·거래비용 일관). 단일 원본경로로
      기존 backtester.py와 근사 일치 검증.
"""
import numpy as np
import pandas as pd
from backtester import perf_metrics
from constraints import load_riskmap, dc_constrained
from backtest_portfolio import add_deposit, fixed, REC_PROXY
import algos

PPY = 252
COST = 0.002
LAG = 1
RNG = np.random.default_rng(20260614)


# ---------------- 경량 백테스터(구간 벡터화) ----------------
def fast_run(nav, strategy, rebal_idx, lag=LAG, cost=COST, init=1e8):
    """nav: DataFrame(T×N). rebal_idx: 신호일 정수인덱스. strategy(nav_upto_df, date)->{code:w}."""
    navff = nav.ffill().values
    dates = nav.index
    T, N = navff.shape
    codes = list(nav.columns)
    cpos = {c: i for i, c in enumerate(codes)}

    exec_pts = sorted((rs + lag, rs) for rs in rebal_idx if 0 <= rs and rs + lag < T)
    if not exec_pts:
        return None
    bounds = [te for te, _ in exec_pts] + [T]

    equity = np.full(T, np.nan)
    equity[:bounds[0]] = init
    holdings = np.zeros(N)
    cash = init
    turnover_sum = 0.0
    total_cost = 0.0
    ntr = 0

    for k, (te, ts) in enumerate(exec_pts):
        price_eval = navff[te]
        v = float(np.nansum(holdings * price_eval) + cash)
        if v <= 0:
            equity[te:bounds[k + 1]] = max(v, 0)
            continue
        w = strategy(nav.iloc[:ts + 1], dates[ts])
        price_exec = nav.values[te]
        w = {c: x for c, x in w.items()
             if x > 0 and c in cpos and not np.isnan(price_exec[cpos[c]])}
        wsum = sum(w.values())
        if wsum > 1.0:
            w = {c: x / wsum for c, x in w.items()}
            wsum = 1.0
        w_new = np.zeros(N)
        for c, x in w.items():
            w_new[cpos[c]] = x
        w_old = np.nan_to_num(holdings * price_eval) / v  # 보유=0 신생펀드 0×NaN 차단
        turnover = np.abs(w_new - w_old).sum()
        c_cost = v * turnover * cost
        v_after = v - c_cost
        pe = np.where(np.isnan(price_exec), np.nan, price_exec)
        new_hold = np.zeros(N)
        mask = w_new > 0
        new_hold[mask] = v_after * w_new[mask] / pe[mask]
        holdings = np.nan_to_num(new_hold)
        cash = v_after * (1.0 - wsum)
        turnover_sum += turnover / 2
        total_cost += c_cost
        ntr += 1
        seg = np.nan_to_num(navff[te:bounds[k + 1]], nan=0.0)  # 0×NaN 전파 차단(보유=0 펀드)
        equity[te:bounds[k + 1]] = seg @ holdings + cash

    eq = pd.Series(equity, index=dates).dropna()
    return perf_metrics(eq, turnover_sum, ntr, total_cost, ppy=PPY), eq


# ---------------- Stationary Block Bootstrap ----------------
def stationary_idx(T, L, n):
    idx = np.empty(n, dtype=int)
    idx[0] = RNG.integers(T)
    p = 1.0 / L
    for i in range(1, n):
        idx[i] = RNG.integers(T) if RNG.random() < p else (idx[i - 1] + 1) % T
    return idx


def boot_panel(ret_arr, dates, codes, L=40):
    """수익률 배열(T×N)을 블록 부트스트랩 → 합성 NAV DataFrame(원본 날짜 인덱스 재사용)."""
    T = ret_arr.shape[0]
    idx = stationary_idx(T, L, len(dates) - 1)
    r = ret_arr[idx]                      # (T-1, N)
    nav = np.vstack([np.ones((1, r.shape[1])), np.cumprod(1 + r, axis=0)]) * 1000.0
    return pd.DataFrame(nav, index=dates, columns=codes)


def rebal_dates_idx(index, freq="YE", warmup=252):
    s = index.to_series()
    grp = s.groupby(index.to_period({"YE": "Y", "QE": "Q", "ME": "M"}[freq])).last()
    pos = {d: i for i, d in enumerate(index)}
    return [pos[d] for d in grp.values if pos[d] >= warmup]


# ---------------- 전략 세트 ----------------
def strategy_set(rm):
    proxy = [c for c in REC_PROXY if c != "DEPOSIT"]
    return {
        "추천65/35": ("R", fixed(REC_PROXY)),                         # 예금패널
        "동일가중": ("A", algos.momentum_topn(9999)),                  # 전체 동일가중 근사
        "모멘텀Top10": ("A", dc_constrained(algos.momentum_topn(10), rm)),
        "트렌드추종": ("A", dc_constrained(algos.trend_following(200), rm)),
        "역변동성": ("A", dc_constrained(algos.inverse_vol(), rm)),
        "리스크패리티": ("A", dc_constrained(algos.risk_parity(), rm)),
        "최소분산": ("A", dc_constrained(algos.min_variance(), rm)),
    }


def main(N=300, L=40, freq="YE"):
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    elig = pd.read_csv("eligibility.csv")
    full5 = [c for c in nav_full.columns
             if c in set(elig[elig.full_5y == "Y"].code)]
    proxy = [c for c in REC_PROXY if c != "DEPOSIT"]
    full5 = sorted(set(full5) | set(proxy))           # 추천 proxy 포함 보장
    navA0 = nav_full[full5]
    navA0 = navA0.loc[:, navA0.iloc[-1].notna()].dropna(how="any")  # 조기종료(EMP 등) 제외→6-12까지
    ret_arr = navA0.pct_change().dropna().values
    dates = navA0.index
    codes = list(navA0.columns)
    rm = load_riskmap()
    strats = strategy_set(rm)
    print("부트스트랩 유니버스: %d펀드 | 기간 %s~%s | N=%d 경로 L=%d %s리밸" %
          (len(codes), dates[0].date(), dates[-1].date(), N, L, freq))

    # ---- 검증: 원본경로(부트스트랩 안함) vs 분포 sanity ----
    def run_all(navA):
        navR = add_deposit(navA[proxy])
        ridxA = rebal_dates_idx(navA.index, freq)
        ridxR = rebal_dates_idx(navR.index, freq)
        out = {}
        for name, (pnl, fn) in strats.items():
            nv = navR if pnl == "R" else navA
            ri = ridxR if pnl == "R" else ridxA
            res = fast_run(nv, fn, ri)
            out[name] = res[0] if res else None
        return out

    base = run_all(navA0)
    print("\n[원본경로 sanity] (기존 backtester.py 추천65/35 연간≈CAGR14.7/Sharpe1.39 대조)")
    for n, m in base.items():
        if m: print("  %-12s CAGR%6.2f Sharpe%6.3f MDD%7.2f" % (n, m["CAGR%"], m["Sharpe"], m["MDD%"]))

    # ---- N경로 부트스트랩 ----
    metrics = {n: {"CAGR%": [], "Sharpe": [], "MDD%": [], "변동성%": []} for n in strats}
    for p in range(N):
        navA = boot_panel(ret_arr, dates, codes, L)
        res = run_all(navA)
        for n, m in res.items():
            if m:
                for k in metrics[n]:
                    metrics[n][k].append(m[k])
        if (p + 1) % 50 == 0:
            print("  ...%d/%d 경로" % (p + 1, N))

    # 저장(분석/그래프용)
    import json
    json.dump({n: {k: v for k, v in d.items()} for n, d in metrics.items()},
              open("mc_results.json", "w"), ensure_ascii=False)
    print("\n저장: mc_results.json (경로별 지표)")

    # ---- 분포 요약 ----
    print("\n" + "=" * 96)
    print("%-12s | %-22s | %-22s | %-18s" % ("전략", "Sharpe(중앙[5,95])", "CAGR%(중앙[5,95])", "MDD%(중앙/최악)"))
    rank_win = {n: 0 for n in strats}
    sharpe_mat = {n: np.array(metrics[n]["Sharpe"]) for n in strats}
    npath = min(len(v) for v in sharpe_mat.values())
    for i in range(npath):
        best = max(strats, key=lambda n: sharpe_mat[n][i])
        rank_win[best] += 1
    for n in strats:
        sh = np.array(metrics[n]["Sharpe"]); cg = np.array(metrics[n]["CAGR%"]); md = np.array(metrics[n]["MDD%"])
        print("%-12s | %5.2f [%5.2f,%5.2f] | %6.1f [%5.1f,%5.1f] | %6.1f / %6.1f" %
              (n, np.median(sh), np.percentile(sh, 5), np.percentile(sh, 95),
               np.median(cg), np.percentile(cg, 5), np.percentile(cg, 95),
               np.median(md), np.min(md)))
    print("\n[Sharpe 1위 빈도 / %d경로]" % npath)
    for n, w in sorted(rank_win.items(), key=lambda x: -x[1]):
        print("  %-12s %d회 (%.0f%%)" % (n, w, w / npath * 100))

    # ---- 하락장(CAGR 하위25% 경로) 분석: 추천 기준 ----
    rec_cagr = np.array(metrics["추천65/35"]["CAGR%"])
    thr = np.percentile(rec_cagr, 25)
    bear = np.where(rec_cagr <= thr)[0]
    print("\n[하락장 시나리오: 추천 CAGR 하위25%% (%d경로, CAGR≤%.1f%%)] 평균 Sharpe·MDD" % (len(bear), thr))
    for n in strats:
        sh = np.array(metrics[n]["Sharpe"])[bear]
        md = np.array(metrics[n]["MDD%"])[bear]
        print("  %-12s Sharpe %5.2f | MDD %6.1f%%" % (n, np.mean(sh), np.mean(md)))

    return metrics


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(N=N)
