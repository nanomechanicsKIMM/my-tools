# -*- coding: utf-8 -*-
"""
P2-1 리밸런싱 정책 비교 — 캘린더 vs 밴드 vs 현금흐름, 평가지표 = 고갈확률(P1-1 프레임).

정책(2버킷: 위험슬리브/예금, 목표 위험 65%):
  cal3/cal6/cal12 : k개월마다 목표비중 복원(양방향 매매)
  band3/band5/band7 : 위험비중이 목표±b%p 이탈 시에만 복원
  cashflow : 적립기 부담금을 언더웨이트 버킷에 전액 배정(매도 없음) + band5 안전장치,
             인출기 오버웨이트 버킷에서 인출 + band5
  cont : 매월 연속 복원(비교 기준선)
비용: 매매 노셔널 × 0.2%(COST, 편도 합산). 회전율 = 연간 매매 노셔널/자산.

게이트: cont(비용 0)가 단일수익률 공식 W×(1+0.65r+0.35d)와 경로 단위 일치(=lifecycle_sim fixed65 재현).
사용(작업폴더 루트): python scripts/rebalance_policy.py [--paths 2000] [--spend 2500000]
→ rebalance_policy_results.json
"""
import argparse, json
import numpy as np
from fetch_index_history import fetch, monthly_returns, REC_MULTI, REC_USONLY
from lifecycle_sim import sleeve_series, boot_paths, TER, REAL_DEP_SPREAD

COST = 0.002
TARGET = 0.65


def run_policy(sleeve, policy, w0, contrib0, spend0, pi, m_ret, T, cost=COST):
    """2버킷 월간 시뮬. 반환 (ruined, W_ret, W_end, 연평균회전율)."""
    N = sleeve.shape[0]
    dep_m = (1 + pi + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    ter_m = TER / 12.0
    months = np.arange(T)
    infl = (1 + pi) ** (months / 12.0)
    contrib = np.where(months < m_ret, contrib0 * infl, 0.0)
    spend = np.where(months >= m_ret, spend0 * infl, 0.0)
    Wr = np.full(N, w0 * TARGET)
    Wd = np.full(N, w0 * (1 - TARGET))
    alive = np.ones(N, bool)
    traded = np.zeros(N)
    W_ret = np.zeros(N)
    kind, param = policy
    for t in range(T):
        Wr *= 1 + sleeve[:, t] - ter_m
        Wd *= 1 + dep_m
        # 현금흐름 배정
        if contrib[t] > 0:
            if kind == "cashflow":
                W = Wr + Wd
                under_risk = Wr < TARGET * W          # 위험 언더웨이트면 위험에 전액
                Wr = np.where(under_risk, Wr + contrib[t], Wr)
                Wd = np.where(under_risk, Wd, Wd + contrib[t])
            else:                                      # 목표비중 분할 매수
                Wr += contrib[t] * TARGET
                Wd += contrib[t] * (1 - TARGET)
        if spend[t] > 0:
            if kind == "cashflow":
                W = Wr + Wd
                over_risk = Wr > TARGET * W            # 오버웨이트 버킷에서 인출
                dr = np.where(over_risk, np.minimum(spend[t], Wr), 0.0)
                dd = np.where(over_risk, spend[t] - dr, np.minimum(spend[t], Wd))
                rem = spend[t] - dr - dd               # 부족분은 반대 버킷
                Wr -= dr + np.where(over_risk, 0.0, rem)
                Wd -= dd + np.where(over_risk, rem, 0.0)
            else:                                      # 목표비중 비례 인출
                Wr -= spend[t] * TARGET
                Wd -= spend[t] * (1 - TARGET)
        W = Wr + Wd
        dead = alive & (W <= 0)
        Wr[dead] = Wd[dead] = 0.0
        alive &= ~dead
        # 리밸런스 판단
        do = np.zeros(N, bool)
        if kind == "cal":
            if (t + 1) % param == 0:
                do = alive.copy()
        elif kind == "cont":
            do = alive.copy()
        else:                                          # band / cashflow(밴드 안전장치)
            W = Wr + Wd
            frac = np.divide(Wr, W, out=np.zeros_like(Wr), where=W > 0)
            do = alive & (np.abs(frac - TARGET) > param)
        if do.any():
            W = Wr + Wd
            tgt_r = TARGET * W
            trade = np.abs(tgt_r - Wr)
            fee = trade * cost
            traded += np.where(do, trade, 0.0)
            Wr = np.where(do, tgt_r - fee * TARGET, Wr)
            Wd = np.where(do, W - tgt_r - fee * (1 - TARGET), Wd)
        if t == m_ret - 1:
            W_ret = (Wr + Wd).copy()
    W = Wr + Wd
    ruined = ~alive
    turn = traded / np.maximum(W_ret, 1.0) / (T / 12.0)   # 연평균 회전(은퇴시 자산 대비 근사)
    return ruined, W_ret, W, float(np.mean(turn))


def self_test(sleeve1, pi=0.03):
    """게이트: cont(비용0) == 단일수익률 공식 복리 (경로 단위)."""
    T = sleeve1.shape[1]
    dep_m = (1 + pi + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    ter_m = TER / 12.0
    _, _, W, _ = run_policy(sleeve1, ("cont", None), 100.0, 0.0, 0.0, pi, T, T, cost=0.0)
    manual = 100.0 * np.prod(1 + TARGET * (sleeve1[0] - ter_m) + (1 - TARGET) * dep_m)
    assert abs(W[0] - manual) / manual < 1e-9, (W[0], manual)
    print("self-test PASS — 연속리밸(비용0) = 단일수익률 복리(lifecycle fixed65) 경로 재현")


POLICIES = {"cont": ("cont", None),
            "cal3": ("cal", 3), "cal6": ("cal", 6), "cal12": ("cal", 12),
            "band3": ("band", 0.03), "band5": ("band", 0.05), "band7": ("band", 0.07),
            "cashflow": ("cashflow", 0.05)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=2000)
    ap.add_argument("--w0", type=float, default=388_037_775)
    ap.add_argument("--contrib", type=float, default=1_500_000)
    ap.add_argument("--spend", type=float, default=2_500_000)
    ap.add_argument("--inflation", type=float, default=0.03)
    ap.add_argument("--retire-months", type=int, default=84)
    ap.add_argument("--decum-months", type=int, default=360)
    ap.add_argument("--seeds", default="11,42,77")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    T = a.retire_months + a.decum_months
    raw = fetch(False)
    bases = {"multi2010": sleeve_series(monthly_returns(raw, ["US500", "IXIC", "KS200"]), REC_MULTI),
             "us2003": sleeve_series(monthly_returns(raw, ["US500", "IXIC"]), REC_USONLY)}
    print("=" * 110)
    print("리밸런싱 정책 비교 — 정책 아키타입·고갈확률 지표 | π=%.0f%% 월지출 %.0f만(실질) 부담금 %.0f만 | 투자 권유 아님"
          % (a.inflation * 100, a.spend / 1e4, a.contrib / 1e4))
    self_test(boot_paths(bases["us2003"], 1, T, np.random.default_rng(seeds[0])))

    out = {"assumptions": vars(a), "results": {}}
    for bk, x in bases.items():
        paths = {sd: boot_paths(x, a.paths, T, np.random.default_rng(sd)) for sd in seeds}
        print("\n[%s]  %-9s %14s %12s %14s %12s" % (bk, "정책", "고갈확률(3시드)", "중앙 FR근사", "말기자산 중앙(실질억)", "연회전율"))
        rank_by_seed = {sd: [] for sd in seeds}
        for name, pol in POLICIES.items():
            ruins, wrs, wes, turns = [], [], [], []
            for sd in seeds:
                r, w_ret, w_end, tu = run_policy(paths[sd], pol, a.w0, a.contrib, a.spend,
                                                 a.inflation, a.retire_months, T)
                ruins.append(float(r.mean())); wrs.append(np.median(w_ret))
                wes.append(np.median(w_end)); turns.append(tu)
                rank_by_seed[sd].append((name, float(r.mean())))
            infl_end = (1 + a.inflation) ** (T / 12.0)
            row = {"ruin_mean": round(float(np.mean(ruins)), 4),
                   "ruin_range": [round(min(ruins), 4), round(max(ruins), 4)],
                   "w_ret_med": round(float(np.mean(wrs))),
                   "w_end_med_real": round(float(np.mean(wes)) / infl_end),
                   "turnover_yr": round(float(np.mean(turns)), 4)}
            out["results"].setdefault(bk, {})[name] = row
            print("  %-9s %5.1f%% [%4.1f~%4.1f] %12.2f억 %12.2f억 %11.1f%%"
                  % (name, np.mean(ruins) * 100, min(ruins) * 100, max(ruins) * 100,
                     np.mean(wrs) / 1e8, row["w_end_med_real"] / 1e8, np.mean(turns) * 100))
        # 순위 안정성: 시드별 고갈확률 최저 정책
        best = [min(rank_by_seed[sd], key=lambda z: z[1])[0] for sd in seeds]
        out["results"][bk]["_best_by_seed"] = best
        print("  시드별 고갈확률 최저: %s" % best)
    json.dump(out, open("rebalance_policy_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: rebalance_policy_results.json")
    print("해석 주의: 정책 간 차이가 시드 범위보다 작으면 '차이 없음'으로 판정(스누핑 금지).")


if __name__ == "__main__":
    main()
