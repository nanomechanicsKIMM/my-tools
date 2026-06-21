# -*- coding: utf-8 -*-
"""
Phase 4/5 보강 — FDR 장기 실지수 백테스트(직교 강건성).

동기: 5년 펀드 패널·부트스트랩은 '실제 약세장'(2008·2011·2015·2018·2020·2022)을 못 봄
      (부트스트랩은 원본 분포 재샘플 → 강세 편향 잔존). walk-forward도 5y로 fold 부족(통계력↓).
      → FinanceDataReader 장기 실지수로 정책 아키타입을 실제 약세장에서 OOS 검증 + WF fold 확대.

데이터(FDR, 가격지수): US500(1979~)·IXIC(1979~)·KS200(2010~)·USD/KRW(2003~).
  - 코어 펀드(K55…)는 FDR에 없음 → 이 모듈은 코어 파이프라인 대체가 아니라 '직교 검증층'.
  - SOX(반도체) 미제공 → 반도체 슬롯은 IXIC로 흡수. NDX(나스닥100) 2020~ 단기 → IXIC(나스닥종합) 대용(caveat).

가드(검토 결론 반영):
  - TR 갭: 가격지수에 배당수익률 평탄 가산(문서화 근사). r_tr = r_pr + div/12.
  - 통화: US자산은 USD지수 × USD/KRW → KRW 언헤지 관점(추천 UH펀드 정합). USD/KRW 2003~ → GFC 포함.
  - 비동기 캘린더: US+KR 일별 혼합 금지 → 월말(ME) 리샘플 후 결합.
  - 엔진: 월간 전용 sim(ppy=12) — fast_run의 PPY=252 하드코딩 회피, forward(룩어헤드 차단) 일관.
  - 레이블: 결과는 '추천 펀드'가 아니라 '정책 아키타입의 실약세장 스트레스'. 펀드단위 결론과 구분.

사용: 작업폴더에서  python <skill>/scripts/fetch_index_history.py [--refresh]
      → index_panel.csv, index_longrun_results.json
"""
import sys
import json
import numpy as np
import pandas as pd
from backtester import perf_metrics

CACHE = "index_raw.csv"
DEPOSIT_RATE = 0.049
COST = 0.002
# 자산: fx=USD환산 필요 여부, div=연배당수익률(TR 근사)
ASSETS = {"US500": {"fx": True, "div": 0.019},
          "IXIC":  {"fx": True, "div": 0.010},
          "KS200": {"fx": False, "div": 0.019}}
RISK = ["US500", "IXIC", "KS200"]
# 정책 아키타입(추천 슬롯 매핑): S&P22 / 나스닥13+반도체8=IXIC21 / KOSPI15+고배당7=KS200 22 / 예금35
REC_MULTI = {"US500": 0.22, "IXIC": 0.21, "KS200": 0.22, "DEPOSIT": 0.35}
REC_USONLY = {"US500": 0.33, "IXIC": 0.32, "DEPOSIT": 0.35}   # KS200 부재(2003~) 시 재정규화
CRISES = [("2008 GFC", "2007-10", "2009-06"), ("2011 유럽", "2011-05", "2011-12"),
          ("2015 중국", "2015-04", "2016-02"), ("2018 Q4", "2018-09", "2018-12"),
          ("2020 COVID", "2020-01", "2020-06"), ("2022 금리", "2022-01", "2022-12")]


# ---------------- 데이터 수집(캐시) ----------------
def fetch(refresh=False):
    import os
    if not refresh and os.path.exists(CACHE):
        df = pd.read_csv(CACHE, index_col=0, parse_dates=True)
        print("캐시 로드: %s (%s~%s)" % (CACHE, df.index[0].date(), df.index[-1].date()))
        return df
    import FinanceDataReader as fdr
    tickers = list(ASSETS) + ["USD/KRW"]
    out = {}
    for t in tickers:
        try:
            out[t] = fdr.DataReader(t)["Close"].rename(t)
            print("  fetch %-8s %s~%s n=%d" % (t, out[t].index[0].date(), out[t].index[-1].date(), len(out[t])))
        except Exception as e:
            print("  ⚠ fetch 실패 %s: %s" % (t, type(e).__name__))
    df = pd.concat(out.values(), axis=1).sort_index()
    df.to_csv(CACHE, encoding="utf-8-sig")
    print("캐시 저장: %s" % CACHE)
    return df


# ---------------- 월간 KRW TR-근사 수익률 ----------------
def monthly_returns(raw, assets):
    """assets: 사용할 위험자산 리스트. 반환: 월간 수익률 DataFrame(위험자산 + DEPOSIT)."""
    fx_m = raw["USD/KRW"].resample("ME").last()
    rfx = fx_m.pct_change()
    cols = {}
    for t in assets:
        s = raw[t].resample("ME").last()
        r = s.pct_change() + ASSETS[t]["div"] / 12.0           # TR 근사
        if ASSETS[t]["fx"]:
            r = (1 + r) * (1 + rfx) - 1                          # KRW 언헤지 환산
        cols[t] = r
    R = pd.DataFrame(cols).dropna()
    R["DEPOSIT"] = (1 + DEPOSIT_RATE) ** (1 / 12.0) - 1          # 월 예금수익(상수)
    return R


# ---------------- 월간 경량 백테스터(forward) ----------------
def sim(R, wfn, rebal=3, lookback=12, cost=COST):
    """R: 월간수익률(DEPOSIT 포함). wfn(R[:i+1], cols)->{col:w}. 가중치는 i+1부터 적용(룩어헤드 차단)."""
    cols = list(R.columns)
    w = pd.Series(0.0, index=cols)
    eq = pd.Series(np.nan, index=R.index)
    val = 1.0
    for i in range(len(R)):
        if i > 0:
            val *= 1 + float((w * R.iloc[i]).sum())             # 보유가중에 당월 수익 적용
        if i >= lookback and (i - lookback) % rebal == 0:
            tw = wfn(R.iloc[:i + 1], cols)
            neww = pd.Series(0.0, index=cols)
            for c, x in tw.items():
                if c in neww.index:
                    neww[c] = x
            val *= 1 - float((neww - w).abs().sum()) * cost     # 회전 비용
            w = neww
        eq.iloc[i] = val
    return eq.dropna()


def _m(eq):
    x = perf_metrics(eq, 0.0, 0, 0.0, ppy=12)
    return {k: x[k] for k in ("CAGR%", "Sharpe", "MDD%", "Sortino", "변동성%", "Calmar")}


# ---------------- 배분 알고리즘(위험슬리브, 월간) ----------------
def fixed(weights):
    return lambda R, cols: dict(weights)


def _sleeve(alloc, L=12):
    """위험슬리브 alloc(Rrisk_win)->{risk:w(합1)} → 위험65% + 예금35%."""
    def wfn(R, cols):
        risk = [c for c in RISK if c in cols]
        wr = alloc(R[risk].iloc[-L:])
        return {**{c: 0.65 * wr.get(c, 0.0) for c in risk}, "DEPOSIT": 0.35}
    return wfn


def a_ew(Rw):
    c = list(Rw.columns)
    return {x: 1.0 / len(c) for x in c}


def a_invvol(Rw):
    v = Rw.std()
    iv = 1.0 / v.replace(0, np.nan)
    iv = iv.fillna(0)
    return (iv / iv.sum()).to_dict() if iv.sum() > 0 else a_ew(Rw)


def a_invvar(Rw):
    v = Rw.var()
    iv = 1.0 / v.replace(0, np.nan)
    iv = iv.fillna(0)
    return (iv / iv.sum()).to_dict() if iv.sum() > 0 else a_ew(Rw)


def a_mom(Rw):
    m = (1 + Rw).prod() - 1
    pos = m.clip(lower=0)
    return (pos / pos.sum()).to_dict() if pos.sum() > 0 else a_ew(Rw)


SLEEVE_ALGOS = {"동일가중": a_ew, "역변동성": a_invvol, "역분산": a_invvar, "모멘텀": a_mom}


# ---------------- 분석 ----------------
def archetype_table(R, rec, label):
    print("\n[%s] %s~%s (%d개월, %.1fy)" % (label, R.index[0].date(), R.index[-1].date(), len(R), len(R) / 12))
    risk = [c for c in RISK if c in R.columns]
    rsum = sum(rec[c] for c in risk)
    cases = {
        "추천아키타입(65/35)": fixed(rec),
        "60/40": fixed({**{c: 0.60 * rec[c] / rsum for c in risk}, "DEPOSIT": 0.40}),
        "주식100%(예금0)": fixed({c: rec[c] / rsum for c in risk}),
        "S&P500 100%": fixed({"US500": 1.0}),
        "예금 100%": fixed({"DEPOSIT": 1.0}),
    }
    if "KS200" in R.columns:
        cases["KOSPI200 100%"] = fixed({"KS200": 1.0})
    res = {}
    for nm, fn in cases.items():
        m = _m(sim(R, fn, rebal=3, lookback=1))
        res[nm] = m
        print("  %-20s CAGR%7.2f Sharpe%7.3f MDD%8.2f Sortino%7.3f Calmar%7.3f"
              % (nm, m["CAGR%"], m["Sharpe"], m["MDD%"], m["Sortino"], m["Calmar"]))
    return res


def crisis_table(R, rec, label):
    eq = sim(R, fixed(rec), rebal=3, lookback=1)
    risk = [c for c in RISK if c in R.columns]
    rsum = sum(rec[c] for c in risk)
    eqE = sim(R, fixed({c: rec[c] / rsum for c in risk}), rebal=3, lookback=1)
    print("\n[실약세장 최대낙폭(MDD) — %s]  추천아키타입 vs 주식100%%" % label)
    rows = {}
    for nm, s, e in CRISES:
        w = eq.loc[s:e]
        wE = eqE.loc[s:e]
        if len(w) < 2:
            continue
        dd = float((w / w.cummax() - 1).min()) * 100
        ddE = float((wE / wE.cummax() - 1).min()) * 100
        rows[nm] = {"arch_mdd": round(dd, 1), "equity_mdd": round(ddE, 1)}
        print("  %-12s 추천 %6.1f%%  |  주식100%% %6.1f%%  (방어 %+.1f%%p)" % (nm, dd, ddE, dd - ddE))
    return rows


def walkforward(R, rec, test=12, lb=12, min_train=36):
    """장기 월간 WF: 위험슬리브 4종 학습Sharpe 선택 → OOS, vs 고정 추천아키타입. 동일 fold stitch."""
    n = len(R)
    folds = []
    t = lb + min_train
    while t + test <= n:
        folds.append((t, t + test))
        t += test
    if not folds:
        return None
    cands = {nm: _sleeve(al) for nm, al in SLEEVE_ALGOS.items()}
    rec_fn = fixed(rec)

    def win_eq(fn, lo, hi):
        seg = sim(R.iloc[max(0, lo - lb):hi], fn, rebal=3, lookback=lb)
        seg = seg.loc[R.index[lo]:R.index[hi - 1]]
        return (seg / seg.iloc[0]) if len(seg) >= 2 else None

    sel_lvl = rec_lvl = 1.0
    prev = None
    sel_segs, rec_segs, rows = [], [], []
    sel_win = 0
    for k, (t, hi) in enumerate(folds):
        scores = {}
        for nm, fn in cands.items():
            tr = sim(R.iloc[:t], fn, rebal=3, lookback=lb)
            scores[nm] = _m(tr)["Sharpe"] if len(tr) > 6 else -1e9
        winner = max(scores, key=scores.get)
        sp, rp = win_eq(cands[winner], t, hi), win_eq(rec_fn, t, hi)
        if sp is None or rp is None:
            continue
        if prev is not None and winner != prev:
            sel_lvl *= 1 - COST
        ss = sel_lvl * sp; sel_lvl = float(ss.iloc[-1])
        rs = rec_lvl * rp; rec_lvl = float(rs.iloc[-1])
        sel_segs.append(ss if not sel_segs else ss.iloc[1:])
        rec_segs.append(rs if not rec_segs else rs.iloc[1:])
        better = _m(sp)["CAGR%"] > _m(rp)["CAGR%"]
        sel_win += better
        rows.append((k + 1, str(R.index[t].date()), winner, round(scores[winner], 2),
                     _m(sp)["CAGR%"], _m(sp)["MDD%"], _m(rp)["CAGR%"], _m(rp)["MDD%"]))
        prev = winner
    sel_oos, rec_oos = pd.concat(sel_segs), pd.concat(rec_segs)
    ms, mr = _m(sel_oos), _m(rec_oos)
    cagr_ok = ms["CAGR%"] >= 1.10 * mr["CAGR%"]
    mdd_ok = abs(ms["MDD%"]) <= 0.90 * abs(mr["MDD%"])
    print("\n[장기 Walk-Forward OOS]  fold %d개 (TEST%d개월 anchored, 위험슬리브 4종 선택)" % (len(rows), test))
    print("  %-3s %-11s %-10s %5s | %7s %7s | %7s %7s" % ("#", "테스트시작", "승자", "Shp", "선택CAGR", "선택MDD", "추천CAGR", "추천MDD"))
    for (i, d, w, sh, sc, sm, rc, rmd) in rows:
        print("  %-3d %-11s %-10s %5.2f | %7.2f %7.2f | %7.2f %7.2f %s" %
              (i, d, w, sh, sc, sm, rc, rmd, "←WF승" if sc > rc else ""))
    print("  OOS 종합: WF-Select CAGR%6.2f Sharpe%6.3f MDD%7.2f | 추천 CAGR%6.2f Sharpe%6.3f MDD%7.2f"
          % (ms["CAGR%"], ms["Sharpe"], ms["MDD%"], mr["CAGR%"], mr["Sharpe"], mr["MDD%"]))
    print("  판정: CAGR %s | MDD %s | fold승률 %d/%d → %s" %
          ("OK" if cagr_ok else "X", "OK" if mdd_ok else "X", sel_win, len(rows),
           "PASS" if (cagr_ok and mdd_ok) else "FAIL — 고정 추천 표본외 우위"))
    return {"folds": len(rows), "sel_fold_win": int(sel_win),
            "oos": {"WF-Select": ms, "추천": mr},
            "gate": {"cagr_ok": bool(cagr_ok), "mdd_ok": bool(mdd_ok), "PASS": bool(cagr_ok and mdd_ok)},
            "fold_detail": [{"fold": i, "test_start": d, "winner": w, "train_sharpe": sh,
                             "sel_cagr": sc, "sel_mdd": sm, "rec_cagr": rc, "rec_mdd": rmd}
                            for (i, d, w, sh, sc, sm, rc, rmd) in rows]}


def main(refresh=False):
    raw = fetch(refresh)
    R_multi = monthly_returns(raw, ["US500", "IXIC", "KS200"])   # 2010~ (KS200 제약)
    R_us = monthly_returns(raw, ["US500", "IXIC"])               # 2003~ (USD/KRW 제약, GFC 포함)
    R_multi.to_csv("index_panel.csv", encoding="utf-8-sig")
    print("=" * 100)
    print("FDR 장기 실지수 백테스트 — KRW 언헤지·TR근사·월간 (정책 아키타입 스트레스, 펀드단위 결론과 구분)")

    out = {}
    out["archetype_multi"] = archetype_table(R_multi, REC_MULTI, "다자산 아키타입(US+나스닥+KOSPI+예금)")
    out["archetype_usonly"] = archetype_table(R_us, REC_USONLY, "US-only 아키타입(2003~, GFC 포함)")
    out["crisis_multi"] = crisis_table(R_multi, REC_MULTI, "다자산 2010~")
    out["crisis_usonly"] = crisis_table(R_us, REC_USONLY, "US-only 2003~")
    out["wf_multi"] = walkforward(R_multi, REC_MULTI)
    out["wf_usonly"] = walkforward(R_us, REC_USONLY)
    json.dump(out, open("index_longrun_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n저장: index_panel.csv, index_longrun_results.json")
    return out


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
