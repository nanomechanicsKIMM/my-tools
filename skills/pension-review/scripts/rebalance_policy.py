# -*- coding: utf-8 -*-
"""
P2-1 리밸런싱 정책 비교 v2 — 캘린더 vs 밴드 vs 현금흐름 + 복원 목적지·타이밍럭·비용 민감도.

정책(2버킷: 위험슬리브/예금, 목표 위험 65%):
  cal3/cal6/cal12 : k개월마다 목표비중 복원(양방향 매매). _oN 변형 = 기준월 오프셋 N(타이밍럭 측정)
  band3/band5/band7 : 위험비중이 목표±b%p 이탈 시에만 복원
  band5_d50/_d875 : 밴드 ±5%p + **부분 복원**(목표가 아니라 목표±밴드×dest 지점까지) —
                    Vanguard(2024) 'The Rebalancing Edge' 200/175 방식·Daryanani(2008) 절반 복원
  cashflow : 적립기 부담금을 언더웨이트 버킷에 전액 배정(매도 없음) + band5 안전장치,
             인출기 오버웨이트 버킷에서 인출 + band5
  cont : 매월 연속 복원(비교 기준선)
비용: 매매 노셔널 × --cost(기본 0.2%). DC 펀드 교체는 명시 수수료 0이므로 보수적 상한 —
  실비용은 환매 T+3~8 결제 지연의 out-of-market 리스크 → --delay-bd(위험버킷 매수 노셔널이
  다음 달 수익의 delay/21을 결손, 부호 보존). 민감도 블록에서 (cost, delay) 조합 자동 비교.
타이밍럭(Hoffstein·Faber·Braun 2020): 동일 캘린더 정책의 오프셋 간 결과 분산을 측정 —
  분산이 정책 간 차이와 같은 자릿수면 캘린더 정책 우열 판독은 노이즈(밴드·현금흐름 정당성 근거).
주의: 2버킷이라 5/25 상대밴드는 여기서 검증 불가(65% 목표에선 절대5%p와 동일) —
  펀드 레벨 5/25는 ips_check/drift_check에서 적용. 골드·인도·중국 지수 부재로 7버킷 시뮬 불가(한계).

게이트: cont(비용 0)가 단일수익률 공식 W×(1+0.65r+0.35d)와 경로 단위 일치(=lifecycle_sim fixed65 재현).
사용(작업폴더 루트): python scripts/rebalance_policy.py [--paths 2000] [--spend 2500000]
                    [--cost 0.002] [--delay-bd 0]
→ rebalance_policy_results.json
"""
import argparse, json
import numpy as np
from fetch_index_history import fetch, monthly_returns, REC_MULTI, REC_USONLY
from lifecycle_sim import sleeve_series, boot_paths, TER, REAL_DEP_SPREAD

COST = 0.002
TARGET = 0.65


def run_policy(sleeve, policy, w0, contrib0, spend0, pi, m_ret, T, cost=COST, delay_bd=0):
    """2버킷 월간 시뮬. 반환 (ruined, W_ret, W_end, 연평균회전율).
    policy: dict(kind, k=캘린더 개월, off=오프셋, b=밴드, dest=부분복원 비율 0~1)
      dest=0 → 목표 전량 복원(종전). 0<dest<1 → 목표±밴드×dest 지점까지만 복원.
    delay_bd: 결제 지연 영업일 — 위험버킷 '매수' 노셔널이 다음 달 수익의 delay_bd/21 결손(부호 보존)."""
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
    kind = policy["kind"]
    kk, off = policy.get("k"), policy.get("off", 0)
    b, dest = policy.get("b"), policy.get("dest", 0.0)
    delay_frac = delay_bd / 21.0
    pend = np.zeros(N)                                 # 지난달 위험버킷 매수 노셔널(결제 지연분)
    for t in range(T):
        Wr *= 1 + sleeve[:, t] - ter_m
        if delay_frac > 0:
            Wr -= pend * sleeve[:, t] * delay_frac     # 지연일만큼 시장 결손(하락월이면 이득)
            pend[:] = 0.0
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
            if (t + 1 - off) % kk == 0:
                do = alive.copy()
        elif kind == "cont":
            do = alive.copy()
        else:                                          # band / cashflow(밴드 안전장치)
            W = Wr + Wd
            frac = np.divide(Wr, W, out=np.zeros_like(Wr), where=W > 0)
            do = alive & (np.abs(frac - TARGET) > b)
        if do.any():
            W = Wr + Wd
            if dest > 0.0 and b:                       # 부분 복원: 목표±밴드×dest 지점까지
                frac = np.divide(Wr, W, out=np.zeros_like(Wr), where=W > 0)
                tgt_frac = TARGET + np.sign(frac - TARGET) * b * dest
            else:
                tgt_frac = TARGET
            tgt_r = tgt_frac * W
            trade = np.abs(tgt_r - Wr)
            fee = trade * cost
            traded += np.where(do, trade, 0.0)
            if delay_frac > 0:
                pend = np.where(do & (tgt_r > Wr), tgt_r - Wr, 0.0)
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
    _, _, W, _ = run_policy(sleeve1, {"kind": "cont"}, 100.0, 0.0, 0.0, pi, T, T, cost=0.0)
    manual = 100.0 * np.prod(1 + TARGET * (sleeve1[0] - ter_m) + (1 - TARGET) * dep_m)
    assert abs(W[0] - manual) / manual < 1e-9, (W[0], manual)
    print("self-test PASS — 연속리밸(비용0) = 단일수익률 복리(lifecycle fixed65) 경로 재현")


POLICIES = {"cont": {"kind": "cont"},
            "cal3": {"kind": "cal", "k": 3}, "cal6": {"kind": "cal", "k": 6}, "cal12": {"kind": "cal", "k": 12},
            "band3": {"kind": "band", "b": 0.03}, "band5": {"kind": "band", "b": 0.05},
            "band7": {"kind": "band", "b": 0.07},
            "band5_d50": {"kind": "band", "b": 0.05, "dest": 0.5},     # 밴드 절반 복원(Daryanani 2008)
            "band5_d875": {"kind": "band", "b": 0.05, "dest": 0.875},  # Vanguard 2024 200/175 근사
            "cashflow": {"kind": "cashflow", "b": 0.05},
            # R4 타이밍럭(Hoffstein 2020): 동일 캘린더의 기준월 오프셋 변형
            "cal3_o1": {"kind": "cal", "k": 3, "off": 1}, "cal3_o2": {"kind": "cal", "k": 3, "off": 2},
            "cal6_o3": {"kind": "cal", "k": 6, "off": 3}, "cal12_o6": {"kind": "cal", "k": 12, "off": 6}}

TIMING_GROUPS = {"cal3": ["cal3", "cal3_o1", "cal3_o2"],
                 "cal6": ["cal6", "cal6_o3"], "cal12": ["cal12", "cal12_o6"]}
SENS_SPECS = {"cost20_delay0": (0.002, 0), "cost0_delay0": (0.0, 0), "cost0_delay8": (0.0, 8)}


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
    ap.add_argument("--cost", type=float, default=COST, help="매매 노셔널당 비용(기본 0.002 — 보수적 상한)")
    ap.add_argument("--delay-bd", type=int, default=0, help="결제 지연 영업일(T+n out-of-market)")
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
                                                 a.inflation, a.retire_months, T,
                                                 cost=a.cost, delay_bd=a.delay_bd)
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

        # R4 타이밍럭 — 동일 캘린더 정책의 오프셋 간 스프레드(고갈확률·실질 말기자산)
        tl = {}
        res = out["results"][bk]
        for g, members in TIMING_GROUPS.items():
            ruins = [res[m]["ruin_mean"] for m in members]
            wends = [res[m]["w_end_med_real"] for m in members]
            tl[g] = {"ruin_spread_pp": round((max(ruins) - min(ruins)) * 100, 2),
                     "w_end_spread_pct": round((max(wends) / max(min(wends), 1) - 1) * 100, 2)}
            print("  타이밍럭 %-6s 오프셋 간 고갈확률 스프레드 %.2f%%p · 말기자산 스프레드 %.2f%%"
                  % (g, tl[g]["ruin_spread_pp"], tl[g]["w_end_spread_pct"]))
        out["results"][bk]["_timing_luck"] = tl

        # R3 비용 모델 민감도 — 명시 수수료 0 + 결제 지연 T+8 극단에서 순위 불변 확인
        sens = {}
        for pname in ("band5", "band5_d875", "cashflow"):
            sens[pname] = {}
            for sname, (c, dbd) in SENS_SPECS.items():
                ruins, wes, turns = [], [], []
                for sd in seeds:
                    r, _, w_end, tu = run_policy(paths[sd], POLICIES[pname], a.w0, a.contrib,
                                                 a.spend, a.inflation, a.retire_months, T,
                                                 cost=c, delay_bd=dbd)
                    ruins.append(float(r.mean())); wes.append(np.median(w_end)); turns.append(tu)
                infl_end = (1 + a.inflation) ** (T / 12.0)
                sens[pname][sname] = {"ruin_mean": round(float(np.mean(ruins)), 4),
                                      "w_end_med_real": round(float(np.mean(wes)) / infl_end),
                                      "turnover_yr": round(float(np.mean(turns)), 4)}
        out["results"][bk]["_sensitivity"] = sens
        print("  민감도(비용/지연): %s" % {p: {s: v["ruin_mean"] for s, v in d.items()} for p, d in sens.items()})
    json.dump(out, open("rebalance_policy_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: rebalance_policy_results.json")
    print("해석 주의: 정책 간 차이가 시드 범위보다 작으면 '차이 없음'으로 판정(스누핑 금지).")


if __name__ == "__main__":
    main()
