# -*- coding: utf-8 -*-
"""
P2-2 동적 환헤지 트리거 실측 — 규칙으로만 존재하던 단계별 헤지를 2003~ 실데이터로 검증.

트리거(메모리 규칙, 전월말 환율로 판정 = 룩어헤드 차단):
  USD/KRW ≥1500→헤지 30% | ≥1400→50% | ≥1300→70% | <1300→80%
  (환율이 낮을수록=원화 강할수록 헤지↑ — 달러 약세 방어)
비교: UH(0%) / H100 / H50 / 동적트리거. 대상 = US 위험슬리브(US500 51%/IXIC 49%, 아키타입 US-only 위험부).
헤지 수익 근사: r_hedged = r_local(USD, TR근사) − 헤지비용/12 (금리차 캐리 무시 — 비용 파라미터로 흡수, 근사 명시).
게이트: UH(h=0)가 fetch_index_history.monthly_returns의 KRW 언헤지 수익과 경로 일치.

사용(작업폴더 루트): python scripts/fx_overlay.py [--hedge-cost 0.01]
→ fx_overlay_results.json
"""
import argparse, json
import numpy as np
import pandas as pd
from fetch_index_history import fetch, monthly_returns, ASSETS, REC_USONLY

TRIGGERS = [(1500, 0.30), (1400, 0.50), (1300, 0.70), (-1e9, 0.80)]
CRISES = [("2008 GFC", "2007-10", "2009-06"), ("2020 COVID", "2020-01", "2020-06"),
          ("2022 금리", "2022-01", "2022-12"), ("전기간", None, None)]


def hedge_ratio(fx):
    for lvl, h in TRIGGERS:
        if fx >= lvl:
            return h
    return TRIGGERS[-1][1]


def metrics(r):
    eq = (1 + r).cumprod()
    yrs = len(r) / 12.0
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    vol = float(r.std() * np.sqrt(12))
    mdd = float((eq / eq.cummax() - 1).min())
    return {"CAGR%": round(cagr * 100, 2), "vol%": round(vol * 100, 2),
            "Sharpe": round(cagr / vol, 3) if vol > 0 else None, "MDD%": round(mdd * 100, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedge-cost", type=float, default=0.01, help="연간 헤지비용(스왑포인트 근사)")
    a = ap.parse_args()
    raw = fetch(False)
    fx_m = raw["USD/KRW"].resample("ME").last()
    rfx = fx_m.pct_change()
    # 위험슬리브 로컬(USD) TR근사 수익
    w = {"US500": REC_USONLY["US500"], "IXIC": REC_USONLY["IXIC"]}
    s = sum(w.values()); w = {k: v / s for k, v in w.items()}
    r_local = sum(w[t] * (raw[t].resample("ME").last().pct_change() + ASSETS[t]["div"] / 12.0)
                  for t in w)
    df = pd.DataFrame({"local": r_local, "rfx": rfx, "fx": fx_m}).dropna()
    r_uh = (1 + df["local"]) * (1 + df["rfx"]) - 1
    # 게이트: monthly_returns의 KRW 언헤지와 일치
    R = monthly_returns(raw, ["US500", "IXIC"])
    ref = R["US500"] * w["US500"] + R["IXIC"] * w["IXIC"]
    common = r_uh.index.intersection(ref.index)
    assert np.allclose(r_uh.loc[common], ref.loc[common], atol=1e-12), "UH 게이트 실패"
    print("self-test PASS — UH(h=0) = monthly_returns KRW 언헤지 경로 일치 (n=%d)" % len(common))

    hc_m = a.hedge_cost / 12.0
    r_h = df["local"] - hc_m
    h_dyn = df["fx"].shift(1).map(lambda v: hedge_ratio(v) if pd.notna(v) else 0.5)
    cases = {"UH(0%)": r_uh,
             "H100": r_h,
             "H50": 0.5 * r_h + 0.5 * r_uh,
             "동적트리거": h_dyn * r_h + (1 - h_dyn) * r_uh}
    print("=" * 100)
    print("동적 환헤지 실측 — US 위험슬리브(KRW 관점) 2003~ | 헤지비용 %.1f%%/y (캐리 무시 근사) | 투자 권유 아님"
          % (a.hedge_cost * 100))
    print("동적 헤지비율: 평균 %.0f%% | 전환 %d회 (%.1f년)"
          % (h_dyn.mean() * 100, int((h_dyn.diff() != 0).sum()), len(df) / 12))
    out = {"hedge_cost": a.hedge_cost, "mean_dyn_ratio": round(float(h_dyn.mean()), 3), "cases": {}}
    for nm, r in cases.items():
        out["cases"][nm] = {}
        for cn, s0, e0 in CRISES:
            seg = r if s0 is None else r.loc[s0:e0]
            if len(seg) < 3:
                continue
            m = metrics(seg.dropna())
            out["cases"][nm][cn] = m
        m = out["cases"][nm]["전기간"]
        print("  %-10s 전기간 CAGR %6.2f%% vol %5.1f%% Sharpe %5.3f MDD %7.2f%% | GFC MDD %7.2f%% | 2022 MDD %6.2f%%"
              % (nm, m["CAGR%"], m["vol%"], m["Sharpe"], m["MDD%"],
                 out["cases"][nm]["2008 GFC"]["MDD%"], out["cases"][nm]["2022 금리"]["MDD%"]))
    # 헤지비용 민감도(동적 vs UH, 전기간 CAGR 차)
    print("\n[민감도] 동적트리거 − UH 전기간 CAGR%p (헤지비용별)")
    sens = {}
    for hc in (0.0, 0.01, 0.02):
        rh = df["local"] - hc / 12.0
        rd = h_dyn * rh + (1 - h_dyn) * r_uh
        d = metrics(rd.dropna())["CAGR%"] - metrics(r_uh.dropna())["CAGR%"]
        sens["%.0f%%" % (hc * 100)] = round(d, 2)
        print("  비용 %.0f%%/y → %+.2f%%p" % (hc * 100, d))
    out["sensitivity_dyn_minus_uh"] = sens
    json.dump(out, open("fx_overlay_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: fx_overlay_results.json")
    print("한계: 캐리(한미 금리차) 무시·월말 리밸 근사. 환헤지는 위기(원화 약세) 시 UH의 자연 방어를 줄임 — MDD 비교 필수.")


if __name__ == "__main__":
    main()
