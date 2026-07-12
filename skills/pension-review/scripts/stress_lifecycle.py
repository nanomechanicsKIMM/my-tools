# -*- coding: utf-8 -*-
"""
P2-3 스트레스 확장 — 부트스트랩이 평균화하는 꼬리 시나리오를 명시 주입해 고갈확률 스트레스.

시나리오(us2003 기반·fixed65·π3% 기본, 인출 시작 시점에 주입):
  baseline        : stationary bootstrap 그대로 (P1-1과 동일)
  gfc_at_retire   : 은퇴 직후 21개월을 실제 2007-10~2009-06 GFC 시퀀스로 강제 치환 (최악 sequence)
  inflation_shock : 인출 첫 10년 π=6%, 이후 3% (지출·예금금리 연동)
  lost_decade     : 인출 첫 10년 위험슬리브 실질수익 ≈ 0 으로 시프트 (저수익 10년)
IMF 1997(보조, 자산군 수준): FDR KS11(1981~) 페치 → KR 아키타입 65/35 vs KS11 100% 위기 MDD.
  예금 4.9% 상수 사용 — 1997 실제 예금금리(15%+)보다 낮아 방어 과소평가(보수적). 오프라인 시 스킵.

게이트: 상수 π 시나리오 엔진이 lifecycle_sim.simulate와 고갈확률 일치(동일 경로).
사용(작업폴더 루트): python scripts/stress_lifecycle.py → stress_results.json
"""
import argparse, json
import numpy as np
import pandas as pd
from fetch_index_history import fetch, monthly_returns, REC_USONLY, ASSETS
from lifecycle_sim import sleeve_series, boot_paths, simulate, TER, REAL_DEP_SPREAD


def sim_v2(sleeve, w0, contrib0, spend0, pi_y, m_ret, T):
    """시간가변 π 지원 코어(π_y: 길이 T 연율 배열). 반환 dict(ruin, ruin_ci)."""
    N = sleeve.shape[0]
    ter_m = TER / 12.0
    pi_m = (1 + pi_y) ** (1 / 12.0) - 1
    cum = np.concatenate([[1.0], np.cumprod(1 + pi_m)])[:-1]   # cum[t]=Π_{k<t} → simulate의 (1+π)^(t/12)와 일치
    dep_m = (1 + pi_y + REAL_DEP_SPREAD) ** (1 / 12.0) - 1
    W = np.full(N, float(w0))
    alive = np.ones(N, bool)
    for t in range(T):
        r = 0.65 * (sleeve[:, t] - ter_m) + 0.35 * dep_m[t]
        cf = contrib0 * cum[t] if t < m_ret else -spend0 * cum[t]
        W = W * (1 + r) + cf
        dead = alive & (W <= 0)
        W[dead] = 0.0
        alive &= ~dead
    p = float((~alive).mean())
    return {"ruin": p, "ruin_ci": 1.96 * np.sqrt(max(p * (1 - p), 1e-12) / N)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=2000)
    ap.add_argument("--w0", type=float, default=388_037_775)
    ap.add_argument("--contrib", type=float, default=1_500_000)
    ap.add_argument("--spend", default="2500000,3000000")
    ap.add_argument("--retire-months", type=int, default=84)
    ap.add_argument("--decum-months", type=int, default=360)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    spends = [float(x) for x in a.spend.split(",")]
    T = a.retire_months + a.decum_months
    m_ret = a.retire_months
    raw = fetch(False)
    R = monthly_returns(raw, ["US500", "IXIC"])
    x = sleeve_series(R, REC_USONLY)
    rng = np.random.default_rng(a.seed)
    base_paths = boot_paths(x, a.paths, T, rng)

    # 게이트: 상수 π에서 sim_v2 == lifecycle_sim.simulate
    pi_const = np.full(T, 0.03)
    r1 = sim_v2(base_paths, a.w0, a.contrib, 2_500_000, pi_const, m_ret, T)
    r0 = simulate(base_paths, a.w0, a.contrib, 2_500_000, 0.03, m_ret, T, "fixed65")
    assert abs(r1["ruin"] - r0["ruin"]) < 1e-12, (r1["ruin"], r0["ruin"])
    print("self-test PASS — 상수 π 시나리오 엔진 = lifecycle_sim.simulate 고갈확률 일치 (%.4f)" % r1["ruin"])

    # GFC 실시퀀스 (2007-10~2009-06)
    gfc = x[(R.index >= "2007-10-01") & (R.index <= "2009-06-30")]
    gfc_paths = base_paths.copy()
    gfc_paths[:, m_ret:m_ret + len(gfc)] = gfc
    # 인플레 쇼크 π 배열
    pi_shock = np.full(T, 0.03)
    pi_shock[m_ret:m_ret + 120] = 0.06
    # 저수익 10년: 인출 첫 120개월 슬리브 실질 ≈ 0
    shift = np.median(x) - ((1.03) ** (1 / 12.0) - 1)
    lost_paths = base_paths.copy()
    lost_paths[:, m_ret:m_ret + 120] -= shift

    scenarios = {
        "baseline": (base_paths, pi_const),
        "gfc_at_retire": (gfc_paths, pi_const),
        "inflation_shock": (base_paths, pi_shock),
        "lost_decade": (lost_paths, pi_const),
    }
    print("=" * 100)
    print("라이프사이클 스트레스 — us2003·fixed65 | GFC시퀀스 %d개월 주입, 저수익 시프트 %.2f%%p/월 | 투자 권유 아님"
          % (len(gfc), shift * 100))
    out = {"assumptions": vars(a), "gfc_months": int(len(gfc)), "results": {}}
    print("  %-16s" % "시나리오" + "".join("  월 %.0f만 고갈확률" % (s / 1e4) for s in spends))
    for nm, (paths, piv) in scenarios.items():
        row = {}
        cells = []
        for s0 in spends:
            r = sim_v2(paths, a.w0, a.contrib, s0, piv, m_ret, T)
            row["%.0f만" % (s0 / 1e4)] = {"ruin": round(r["ruin"], 4), "ci": round(r["ruin_ci"], 4)}
            cells.append("     %5.1f%% ±%.1f" % (r["ruin"] * 100, r["ruin_ci"] * 100))
        out["results"][nm] = row
        print("  %-16s%s" % (nm, "".join(cells)))

    # IMF 1997 (자산군 수준, KS11)
    try:
        import FinanceDataReader as fdr
        ks11 = fdr.DataReader("KS11", "1981-01-01")["Close"].resample("ME").last()
        r_kr = ks11.pct_change() + ASSETS["KS200"]["div"] / 12.0
        r_kr = r_kr.dropna()
        dep_m = 1.049 ** (1 / 12.0) - 1
        port = 0.65 * r_kr + 0.35 * dep_m
        crises = [("1997 IMF", "1997-01", "1998-12"), ("2000 IT버블", "2000-01", "2001-09"),
                  ("2008 GFC", "2008-01", "2009-03")]
        print("\n[IMF 포함 KR 아키타입 위기 MDD — KS11 %s~ | 예금 4.9%% 상수(1997 실제금리 15%%+보다 보수적)]"
              % r_kr.index[0].date())
        imf = {}
        for nm, s0, e0 in crises:
            seg65 = port.loc[s0:e0]; seg100 = r_kr.loc[s0:e0]
            if len(seg65) < 3:
                continue
            m65 = float(((1 + seg65).cumprod() / (1 + seg65).cumprod().cummax() - 1).min()) * 100
            m100 = float(((1 + seg100).cumprod() / (1 + seg100).cumprod().cummax() - 1).min()) * 100
            imf[nm] = {"kr65_35_mdd": round(m65, 1), "ks11_mdd": round(m100, 1)}
            print("  %-12s KR 65/35 %7.1f%%  vs KS11 100%% %7.1f%%  (방어 %+.1f%%p)" % (nm, m65, m100, m65 - m100))
        out["imf_kr_archetype"] = imf
    except Exception as e:
        print("\n[IMF 1997] KS11 페치 실패(%s) — 스킵(오프라인 허용)" % type(e).__name__)
        out["imf_kr_archetype"] = None

    json.dump(out, open("stress_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: stress_results.json")
    print("레이블: 정책 아키타입 스트레스 — 시나리오는 '가능한 미래'이지 예측이 아님.")


if __name__ == "__main__":
    main()
