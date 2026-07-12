# -*- coding: utf-8 -*-
"""
P1-1 적립·인출 통합 라이프사이클 몬테카를로 (정책 아키타입 수준).

목적: DC 퇴직연금을 '수익률 문제'가 아닌 '자금조달 문제'로 평가한다.
  월 부담금 적립(~은퇴) → 30년 실질 지출 인출 경로에서
  ① 고갈확률(ruin, 95% CI) ② 은퇴시점 자금충족률(funded ratio)
  ③ sequence risk(인출 첫 5년 수익 사분위 조건부 고갈률) ④ 안전인출액(고갈≤10%)을 산출.

수익 모델(과적합 가드 — 경로 밖 기대수익 주입 금지):
  fetch_index_history의 월간 KRW TR근사 패널을 재사용해 위험슬리브(아키타입 가중 고정)
  월간 수익률을 stationary block bootstrap(평균 블록 24개월)으로 재샘플.
  - 기반 2종 병기: multi2010(US500/IXIC/KS200, 2010~) / us2003(GFC 포함, 2003~)
  - 위험슬리브에 TER 차감. 예금 레그는 시나리오 결정적(명목 = 인플레 + 실질스프레드).
  - 레이블: '추천 펀드 성과'가 아니라 **정책 아키타입의 자금조달 스트레스**.

게이트: ① 무현금흐름·무비용 경로가 cumprod와 일치(self-test)
       ② 다시드(3종) 고갈확률 안정성 ③ 결과에 가정(부담금·기반 CAGR) 명시.

사용(작업폴더 루트): python scripts/lifecycle_sim.py [--paths 2000] [--contrib 1500000]
    [--spend 1500000,2000000,2500000,3000000] [--inflation 0.02,0.03,0.04]
    [--w0 388037775] [--retire-months 84] [--decum-months 360] [--seeds 11,42,77]
→ lifecycle_results.json, lifecycle_sim.png
"""
import argparse, json
import numpy as np
import pandas as pd
from fetch_index_history import fetch, monthly_returns, REC_MULTI, REC_USONLY

TER = 0.008            # 추천 위험슬리브 가중보수(연) — NAV 기준 정합 위해 지수수익에서 차감
BLOCK_MEAN = 24        # stationary bootstrap 평균 블록(개월)
REAL_DEP_SPREAD = 0.005  # 예금 명목금리 = 인플레 + 0.5%p (한국 장기 실질예금 근사)
RUIN_TARGET = 0.10     # 안전인출액 기준 고갈확률


def sleeve_series(R, rec):
    """월간 패널 → 위험슬리브(아키타입 가중, 슬리브 내 재정규화) 수익률 1차원 배열."""
    risk = [c for c in R.columns if c != "DEPOSIT" and c in rec]
    w = np.array([rec[c] for c in risk]); w = w / w.sum()
    return R[risk].values @ w


def boot_paths(x, N, T, rng, mean_block=BLOCK_MEAN):
    """stationary block bootstrap 인덱스로 (N,T) 경로 생성."""
    n = len(x)
    starts = rng.integers(0, n, size=(N, T))
    renew = rng.random((N, T)) < 1.0 / mean_block
    idx = np.empty((N, T), dtype=int)
    idx[:, 0] = starts[:, 0]
    for t in range(1, T):
        cont = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(renew[:, t], starts[:, t], cont)
    return x[idx]


def risk_schedule(policy, T, m_ret):
    """월별 위험슬리브 비중. fixed65 | glide(T-3부터 65→40, 은퇴+3년 완료)."""
    w = np.full(T, 0.65)
    if policy == "glide":
        s, e = max(0, m_ret - 36), m_ret + 36          # T-3 ~ 은퇴+3
        ramp = np.linspace(0.65, 0.40, e - s)
        w[s:e] = ramp
        w[e:] = 0.40
    return w


def simulate(sleeve, w0, contrib0, spend0, pi, m_ret, T, policy):
    """sleeve:(N,T) 위험슬리브 월수익. 반환: dict(ruin, W_ret, FR, W_end, ruined mask...)"""
    N = sleeve.shape[0]
    dep_m = (1 + pi + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    ter_m = TER / 12.0
    wr = risk_schedule(policy, T, m_ret)
    months = np.arange(T)
    infl = (1 + pi) ** (months / 12.0)
    contrib = np.where(months < m_ret, contrib0 * infl, 0.0)   # 임금상승=인플레 가정
    spend = np.where(months >= m_ret, spend0 * infl, 0.0)      # 오늘 실질가치 고정 지출
    W = np.full(N, float(w0))
    alive = np.ones(N, bool)
    ruin_month = np.full(N, -1)
    W_ret = np.zeros(N)
    for t in range(T):
        r = wr[t] * (sleeve[:, t] - ter_m) + (1 - wr[t]) * dep_m
        W = W * (1 + r) + contrib[t] - spend[t]
        dead = alive & (W <= 0)
        ruin_month[dead] = t
        W[dead] = 0.0
        alive &= ~dead
        if t == m_ret - 1:
            W_ret = W.copy()
    ruined = ~alive
    # 자금충족률: 은퇴시점 자산 / 인출스트림 PV(명목지출을 예금금리로 할인 = 실질지출을 스프레드로 할인)
    k = np.arange(1, T - m_ret + 1)
    pv = float(np.sum(spend0 * (1 + pi) ** (m_ret / 12.0) * (1 + pi) ** (k / 12.0)
                      / (1 + pi + REAL_DEP_SPREAD) ** (k / 12.0)))
    fr = W_ret / pv if pv > 0 else np.full(N, 1.0)   # 지출 0(자기시험 경로)이면 FR 무의미 → 1 고정
    # sequence risk: 인출 첫 60개월 슬리브 실질수익(연율) 사분위 조건부 고갈률
    if T - m_ret >= 60:
        g = (1 + sleeve[:, m_ret:m_ret + 60]).prod(axis=1) ** (12 / 60.0) - 1 - pi
        q = np.quantile(g, [0.25, 0.5, 0.75])
        seq = [float(ruined[g <= q[0]].mean()),
               float(ruined[(g > q[0]) & (g <= q[2])].mean()),
               float(ruined[g > q[2]].mean())]
    else:
        seq = [float("nan")] * 3
    p = float(ruined.mean())
    ci = 1.96 * np.sqrt(max(p * (1 - p), 1e-12) / N)
    return {"ruin": p, "ruin_ci": ci, "fr_med": float(np.median(fr)),
            "fr_p10": float(np.quantile(fr, 0.10)), "p_fr_ge1": float((fr >= 1).mean()),
            "w_ret_med": float(np.median(W_ret)), "w_end_med_real": float(np.median(W) / infl[-1]),
            "seq_ruin_q1_mid_q4": seq, "ruin_month_med": float(np.median(ruin_month[ruined])) if p > 0 else None}


def safe_spend(sleeve, w0, contrib0, pi, m_ret, T, policy, lo=5e5, hi=6e6, iters=22):
    """동일 부트스트랩 경로 재사용 이분탐색: 고갈확률<=RUIN_TARGET 최대 월지출(오늘 실질)."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        r = simulate(sleeve, w0, contrib0, mid, pi, m_ret, T, policy)["ruin"]
        lo, hi = (mid, hi) if r <= RUIN_TARGET else (lo, mid)
    return lo


def self_test(sleeve1):
    """게이트①: 무현금흐름 경로가 손계산 복리(cumprod)와 일치하는지 — 결정적 2케이스.
    (a) 슬리브 상수 +1%/월: r = 0.65*(0.01-ter_m) + 0.35*dep_m 복리 재현
    (b) 부트스트랩 실경로 1개: 동일 공식 cumprod와 일치"""
    pi = 0.03
    dep_m = (1 + pi + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    ter_m = TER / 12.0
    const = np.full((1, 24), 0.01)
    res = simulate(const, 100.0, 0.0, 0.0, pi, 24, 24, "fixed65")
    manual = 100.0 * (1 + 0.65 * (0.01 - ter_m) + 0.35 * dep_m) ** 24
    assert abs(res["w_ret_med"] - manual) / manual < 1e-12, (res["w_ret_med"], manual)
    T = sleeve1.shape[1]
    res2 = simulate(sleeve1, 100.0, 0.0, 0.0, pi, T, T, "fixed65")
    manual2 = 100.0 * np.prod(1 + 0.65 * (sleeve1[0] - ter_m) + 0.35 * dep_m)
    assert abs(res2["w_ret_med"] - manual2) / manual2 < 1e-9, (res2["w_ret_med"], manual2)
    print("self-test PASS — 무현금흐름 경로 = 손계산 복리 재현 (상수·실경로 2케이스)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=2000)
    ap.add_argument("--w0", type=float, default=388_037_775)
    ap.add_argument("--contrib", type=float, default=1_500_000)
    ap.add_argument("--spend", default="1500000,2000000,2500000,3000000")
    ap.add_argument("--inflation", default="0.02,0.03,0.04")
    ap.add_argument("--retire-months", type=int, default=84)   # 2026-07 → 2033-07
    ap.add_argument("--decum-months", type=int, default=360)
    ap.add_argument("--seeds", default="11,42,77")
    a = ap.parse_args()
    spends = [float(x) for x in a.spend.split(",")]
    pis = [float(x) for x in a.inflation.split(",")]
    seeds = [int(x) for x in a.seeds.split(",")]
    T = a.retire_months + a.decum_months

    raw = fetch(False)
    bases = {"multi2010": (sleeve_series(monthly_returns(raw, ["US500", "IXIC", "KS200"]), REC_MULTI),
                           "다자산 2010~ (2008 GFC 미포함)"),
             "us2003": (sleeve_series(monthly_returns(raw, ["US500", "IXIC"]), REC_USONLY),
                        "US-only 2003~ (GFC 포함)")}
    print("=" * 110)
    print("적립·인출 라이프사이클 몬테카를로 — 정책 아키타입 수준 (추천 펀드 성과 아님) | 투자 권유 아님")
    print("가정: W0=%.0f원, 월부담금 %.0f원(임금상승=인플레), 은퇴 %d개월 후, 인출 %d개월, TER %.2f%%/y, 예금=π+%.1f%%p"
          % (a.w0, a.contrib, a.retire_months, a.decum_months, TER * 100, REAL_DEP_SPREAD * 100))
    for k, (x, lab) in bases.items():
        yrs = len(x) / 12
        cagr = (np.prod(1 + x)) ** (1 / yrs) - 1
        print("  기반 %-10s %-28s n=%d개월 | 슬리브 명목CAGR %.1f%% 변동성 %.1f%% ← 이 수치가 시뮬의 내재 가정"
              % (k, lab, len(x), cagr * 100, np.std(x) * np.sqrt(12) * 100))

    rng0 = np.random.default_rng(seeds[0])
    self_test(boot_paths(bases["multi2010"][0], 1, T, rng0))

    results = {"assumptions": {"w0": a.w0, "contrib0": a.contrib, "retire_months": a.retire_months,
                               "decum_months": a.decum_months, "ter": TER, "real_dep_spread": REAL_DEP_SPREAD,
                               "block_mean": BLOCK_MEAN, "paths": a.paths, "seeds": seeds,
                               "label": "정책 아키타입 자금조달 스트레스 — 투자 권유 아님"}, "grid": []}
    print("\n[고갈확률 그리드]  N=%d×seed%d | 정책 fixed65/glide | 지출=오늘 실질 월액" % (a.paths, len(seeds)))
    print("%-10s %-7s π%%   %-9s | %-16s %-16s | FR중앙 P(FR≥1)" % ("기반", "정책", "월지출", "고갈확률(95%CI)", "다시드 범위"))
    cache = {}
    for bk, (x, lab) in bases.items():
        for sd in seeds:
            cache[(bk, sd)] = boot_paths(x, a.paths, T, np.random.default_rng(sd))
    for bk, (x, lab) in bases.items():
        for policy in ["fixed65", "glide"]:
            for pi in pis:
                for s0 in spends:
                    rs = [simulate(cache[(bk, sd)], a.w0, a.contrib, s0, pi,
                                   a.retire_months, T, policy) for sd in seeds]
                    r0 = rs[0]
                    pr = [r["ruin"] for r in rs]
                    row = {"base": bk, "policy": policy, "inflation": pi, "spend": s0, **r0,
                           "ruin_seed_range": [min(pr), max(pr)]}
                    results["grid"].append(row)
                    if pi == 0.03:  # 콘솔은 중앙 시나리오만 (전체는 json)
                        print("%-10s %-7s %.0f  %7.0f만 | %5.1f%% ±%.1f      %5.1f~%4.1f%%     | %5.2f  %4.0f%%  seq(Q1/mid/Q4)=%s"
                              % (bk, policy, pi * 100, s0 / 1e4, r0["ruin"] * 100, r0["ruin_ci"] * 100,
                                 min(pr) * 100, max(pr) * 100, r0["fr_med"], r0["p_fr_ge1"] * 100,
                                 "/".join("%.0f%%" % (v * 100) for v in r0["seq_ruin_q1_mid_q4"])))
    print("\n[안전인출액]  고갈확률 ≤ %.0f%% 최대 월지출(오늘 실질, π=3%%, seed=%d)" % (RUIN_TARGET * 100, seeds[0]))
    for bk in bases:
        for policy in ["fixed65", "glide"]:
            s = safe_spend(cache[(bk, seeds[0])], a.w0, a.contrib, 0.03, a.retire_months, T, policy)
            results.setdefault("safe_spend", {})["%s_%s" % (bk, policy)] = s
            print("  %-10s %-7s → 월 %.0f만원" % (bk, policy, s / 1e4))

    json.dump(results, open("lifecycle_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    plot(cache, bases, results, a, seeds[0], T)
    print("\n저장: lifecycle_results.json, lifecycle_sim.png")
    print("주의: 기반 패널의 내재 CAGR(위 출력)이 미래에도 유지된다는 가정이 최대 한계. 두 기반 병기 해석 필수.")


def plot(cache, bases, results, a, seed, T):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    # (1) 기준 케이스 실질자산 fan (us2003·fixed65·π3%·월250만)
    pi, s0 = 0.03, 2_500_000
    sleeve = cache[("us2003", seed)]
    N = sleeve.shape[0]
    dep_m = (1 + pi + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    months = np.arange(T); infl = (1 + pi) ** (months / 12.0)
    contrib = np.where(months < a.retire_months, a.contrib * infl, 0.0)
    spend = np.where(months >= a.retire_months, s0 * infl, 0.0)
    W = np.full(N, float(a.w0)); traj = np.zeros((N, T))
    for t in range(T):
        r = 0.65 * (sleeve[:, t] - TER / 12) + 0.35 * dep_m
        W = np.maximum(W * (1 + r) + contrib[t] - spend[t], 0.0)
        traj[:, t] = W / infl[t]
    yrs = 2026.5 + months / 12.0
    for q, c, l in [(0.05, "#c0392b", "p5"), (0.25, "#e67e22", "p25"), (0.5, "#2c3e50", "중앙"),
                    (0.75, "#27ae60", "p75"), (0.95, "#2980b9", "p95")]:
        axes[0].plot(yrs, np.quantile(traj, q, axis=0) / 1e8, color=c, lw=1.6, label=l)
    axes[0].axvline(2026.5 + a.retire_months / 12, color="gray", ls="--", lw=1)
    axes[0].set_title("실질자산 경로 (us2003·fixed65·π3%·월 250만 인출)")
    axes[0].set_ylabel("억원(오늘 실질)"); axes[0].legend(); axes[0].grid(alpha=0.3)
    # (2) 고갈확률 히트맵 (us2003·fixed65)
    g = [r for r in results["grid"] if r["base"] == "us2003" and r["policy"] == "fixed65"]
    pis = sorted({r["inflation"] for r in g}); sps = sorted({r["spend"] for r in g})
    M = np.array([[next(r["ruin"] for r in g if r["inflation"] == p and r["spend"] == s)
                   for s in sps] for p in pis])
    im = axes[1].imshow(M * 100, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=60)
    axes[1].set_xticks(range(len(sps)), ["%.0f만" % (s / 1e4) for s in sps])
    axes[1].set_yticks(range(len(pis)), ["%.0f%%" % (p * 100) for p in pis])
    axes[1].set_xlabel("월 실질지출"); axes[1].set_ylabel("인플레")
    axes[1].set_title("고갈확률 % (us2003·fixed65, 30년 인출)")
    for i in range(len(pis)):
        for j in range(len(sps)):
            axes[1].text(j, i, "%.0f" % (M[i, j] * 100), ha="center", va="center", fontsize=11)
    fig.colorbar(im, ax=axes[1], shrink=0.8)
    fig.suptitle("적립·인출 라이프사이클 몬테카를로 — 정책 아키타입 (투자 권유 아님)", fontsize=11)
    fig.tight_layout()
    fig.savefig("lifecycle_sim.png", dpi=110)


if __name__ == "__main__":
    main()
