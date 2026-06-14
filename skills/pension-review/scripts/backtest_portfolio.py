# -*- coding: utf-8 -*-
"""
추천 포트폴리오(portfolio_recommendation.md) 6종 사후 백테스트 검증.

두 관점:
  [정확]  추천 6종 그대로 — 미국 2종이 2023년 신생 → 공통구간 2.5년(2023-11-30~2026-06-12)
  [proxy] 전략 5년 강건성 — 미국 2종을 5년 가용 대체펀드로:
          S&P500 UH → 삼성미국S&P500UH(K55105BA7360)
          나스닥100 UH → 미래에셋미국블루칩UH(K55301B51580)  ※블루칩은 나스닥100과 다름(대형우량주). caveat.

예금(35%)은 합성 NAV(연 4.9% 일복리)로 패널에 편입.
리밸런싱: 추천 정책=연간(YE). 비교로 분기(QE)/월간(ME).
"""
import pandas as pd
import numpy as np
from backtester import Backtester
from constraints import load_riskmap, apply_dc, exposure

DEPOSIT_RATE = 0.049
COST_BPS = 20

# 추천 비중 (위험자산 65% + 예금 35%)
REC_EXACT = {"K55210DT4606": 0.22, "K55301E64355": 0.13, "K55105BU5980": 0.15,
             "K55307D05993": 0.08, "K55209CT1721": 0.07, "DEPOSIT": 0.35}
REC_PROXY = {"K55105BA7360": 0.22, "K55301B51580": 0.13, "K55105BU5980": 0.15,
             "K55307D05993": 0.08, "K55209CT1721": 0.07, "DEPOSIT": 0.35}
LABELS = {"K55210DT4606": "신한S&P500UH", "K55301E64355": "미래에셋나스닥100UH",
          "K55105BU5980": "삼성KOSPI200", "K55307D05993": "유리필라델피아반도체UH",
          "K55209CT1721": "신영밸류고배당", "DEPOSIT": "예금(4.9%)",
          "K55105BA7360": "삼성S&P500UH", "K55301B51580": "미래에셋미국블루칩UH"}


def add_deposit(navdf):
    """합성 예금 NAV(연 4.9% 일복리)를 DEPOSIT 컬럼으로 추가."""
    d0 = navdf.index[0]
    days = np.array([(d - d0).days for d in navdf.index], dtype=float)
    out = navdf.copy()
    out["DEPOSIT"] = 1000.0 * (1 + DEPOSIT_RATE) ** (days / 365.0)
    return out


def fixed(weights):
    def strat(nav_upto, date):
        return dict(weights)
    return strat


def run(navdf, weights, rebalance="YE", warmup=2, cost=COST_BPS):
    bt = Backtester(navdf, execution_lag=1, cost_bps=cost, rebalance=rebalance)
    return bt.run(fixed(weights), warmup=warmup)


def show(title, res, extra=""):
    m = res["metrics"]
    print("  %-34s 총%7.2f CAGR%6.2f 변동%6.2f Sharpe%6.3f Sortino%6.3f MDD%7.2f Calmar%6.3f %s" %
          (title, m["총수익%"], m["CAGR%"], m["변동성%"], m["Sharpe"], m["Sortino"],
           m["MDD%"], m["Calmar"], extra))


def avg_exposure(navdf, weights, rm):
    """체결가능 펀드 기준 평균 위험/안전/현금 노출(편입 펀드 NaN 보정)."""
    # 예금은 안전자산으로 간주
    rm2 = dict(rm)
    rm2["DEPOSIT"] = {"risk": False, "name": "예금"}
    last = navdf.iloc[-1]
    w = {c: x for c, x in weights.items() if c in navdf.columns and pd.notna(last.get(c))}
    return exposure(w, rm2)


def main():
    nav_full = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    rm = load_riskmap()

    # ================= 분석 1: 추천 6종 정확 (공통구간) =================
    cols = [c for c in REC_EXACT if c != "DEPOSIT"]
    sub = nav_full[cols].dropna(how="any")          # 6종 모두 유효한 공통구간
    start = sub.index[0]
    navA = add_deposit(nav_full.loc[start:, cols])
    print("=" * 120)
    print("[분석 1] 추천 6종 정확 — 공통구간 %s ~ %s (%d거래일, %.1f년)" %
          (navA.index[0].date(), navA.index[-1].date(), len(navA), len(navA) / 252))
    print("  편입:", ", ".join("%s %.0f%%" % (LABELS[c], REC_EXACT[c] * 100) for c in REC_EXACT))
    ex = avg_exposure(navA, REC_EXACT, rm)
    print("  목표노출: 위험 %.0f%% / 안전 %.0f%% / 현금 %.0f%% | 단일최대 %.0f%%" %
          (ex["risk"] * 100, ex["safe"] * 100, ex["cash"] * 100, ex["max_single"] * 100))
    print("  %-34s %s" % ("[추천포트] 리밸주기 민감도", ""))
    for rb, nm in [("ME", "월간"), ("QE", "분기"), ("YE", "연간(추천정책)")]:
        show("추천6종 " + nm, run(navA, REC_EXACT, rebalance=rb))
    print("  %-34s %s" % ("[벤치마크] 연간 리밸", ""))
    # 위험자산만 100%(예금 제외, 재정규화)
    risk_only = {c: x for c, x in REC_EXACT.items() if c != "DEPOSIT"}
    rs = sum(risk_only.values()); risk_only = {c: x / rs for c, x in risk_only.items()}
    show("위험자산100%(예금0)", run(navA, risk_only, rebalance="YE"))
    show("KOSPI200 100%", run(navA, {"K55105BU5980": 1.0}, rebalance="YE"))
    show("예금 100%", run(navA, {"DEPOSIT": 1.0}, rebalance="YE"))
    ew = {c: 1.0 / len(REC_EXACT) for c in REC_EXACT}
    show("동일가중 6종", run(navA, ew, rebalance="YE"))

    # ================= 분석 2: 전략 5년 proxy =================
    colsP = [c for c in REC_PROXY if c != "DEPOSIT"]
    subP = nav_full[colsP].dropna(how="any")
    navB = add_deposit(nav_full.loc[subP.index[0]:, colsP])
    print("\n" + "=" * 120)
    print("[분석 2] 전략 5년 proxy — %s ~ %s (%d거래일, %.1f년)" %
          (navB.index[0].date(), navB.index[-1].date(), len(navB), len(navB) / 252))
    print("  편입:", ", ".join("%s %.0f%%" % (LABELS[c], REC_PROXY[c] * 100) for c in REC_PROXY))
    print("  ※ 나스닥100 UH → 미래에셋미국블루칩 UH(대형우량주) 대체: 기술주 집중도 낮음(보수적 근사)")
    exB = avg_exposure(navB, REC_PROXY, rm)
    print("  목표노출: 위험 %.0f%% / 안전 %.0f%% / 현금 %.0f%% | 단일최대 %.0f%%" %
          (exB["risk"] * 100, exB["safe"] * 100, exB["cash"] * 100, exB["max_single"] * 100))
    print("  %-34s %s" % ("[전략proxy] 리밸주기 민감도", ""))
    for rb, nm in [("ME", "월간"), ("QE", "분기"), ("YE", "연간(추천정책)")]:
        show("전략proxy " + nm, run(navB, REC_PROXY, rebalance=rb))
    print("  %-34s %s" % ("[벤치마크] 연간 리밸", ""))
    risk_onlyP = {c: x for c, x in REC_PROXY.items() if c != "DEPOSIT"}
    rsP = sum(risk_onlyP.values()); risk_onlyP = {c: x / rsP for c, x in risk_onlyP.items()}
    show("위험자산100%(예금0)", run(navB, risk_onlyP, rebalance="YE"))
    show("KOSPI200 100%", run(navB, {"K55105BU5980": 1.0}, rebalance="YE"))
    show("예금 100%", run(navB, {"DEPOSIT": 1.0}, rebalance="YE"))

    # ================= DC 한도 준수 확인 =================
    print("\n" + "=" * 120)
    print("[DC 규제 준수] 추천 비중 자체 점검")
    rm2 = dict(rm); rm2["DEPOSIT"] = {"risk": False, "name": "예금"}
    for nm, w in [("정확", REC_EXACT), ("proxy", REC_PROXY)]:
        e = exposure(w, rm2)
        ok_r = "PASS" if e["risk"] <= 0.70 + 1e-9 else "FAIL"
        ok_s = "PASS" if e["max_single"] <= 0.40 + 1e-9 else "FAIL"
        print("  [%s] 위험%.0f%%(≤70 %s) 단일최대%.0f%%(≤40 %s) 안전%.0f%%" %
              (nm, e["risk"] * 100, ok_r, e["max_single"] * 100, ok_s, e["safe"] * 100))


if __name__ == "__main__":
    main()
