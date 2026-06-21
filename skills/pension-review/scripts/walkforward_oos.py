# -*- coding: utf-8 -*-
"""
Phase 5 확장 — Walk-Forward 표본외(OOS) 검증.

목적: 부트스트랩(분포 재샘플)이 못 보는 '알고리즘 선택의 과적합'을 시간순 전진으로 측정.
  - algos        = algos.py 배분 알고리즘(검증 대상)
  - OOS          = 학습에 안 쓴 다음 구간 성과(표본외)
  - walk-forward = 학습창을 미래로 전진시키며 매 fold마다 OOS 측정

핵심 질문: "과거에 가장 좋아 보인 algo를 매번 고르는 것"이 고정 추천65/35를 표본외에서 이기는가?
  (methodology 결론 예측: NO — 선택은 과적합, 고정비중이 OOS 우위)

설계(검증된 엔진 재사용. skfolio 미사용 이유: DC제약·예금쿠션·forward-pricing·동적자격을
     기존 Phase 5와 동일 수치체계로 유지해 비교 가능성 확보):
  - 유니버스: algo_eval._universe (full_5y 생존펀드 + 추천 proxy, dropna 고정유니버스)
  - 엔진: mc_backtest.fast_run (forward-pricing lag1·거래비용·NaN안전)
  - fold: anchored(expanding) 학습 [0,t) → OOS 테스트 [t,t+TEST), STEP씩 전진(비중첩 OOS)
  - 매 fold: 후보 10종을 학습구간 Sharpe로 채점 → 승자 → 테스트구간 적용(OOS)
  - 비교군: WF-Select(메타) / 추천65/35(고정) / 개별 algo 고정 / 동일가중 — 동일 fold로 stitch
  - algo 전환 fold 경계엔 전환비용(COST) 차감(낙관편향 방지)
  - 게이트: WF-Select OOS CAGR ≥ 1.10×추천 AND |MDD| ≤ 0.90×추천 (algo_eval과 동일)

한계: 5년 일별 → fold 수 적음(통계력 낮음). FDR 장기 실지수 백테스트와 병행 권장.

사용: 작업 폴더(panel_adj_nav.csv 등)에서
      PYTHONPATH=<skill>/scripts python <skill>/scripts/walkforward_oos.py [TEST] [STEP] [FREQ]
"""
import sys
import json
import numpy as np
import pandas as pd
from backtester import perf_metrics
from mc_backtest import fast_run, rebal_dates_idx
from backtest_portfolio import add_deposit, fixed, REC_PROXY
from constraints import load_riskmap, dc_constrained
from algo_eval import _universe
import algos

WARMUP = 252       # algos 룩백(1y) — 첫 학습 시작 오프셋
MIN_TRAIN = 252    # 최소 학습 span(선택 채점용)
TEST = 126         # OOS 테스트창(6개월)
STEP = 126         # 전진 간격(비중첩)
FREQ = "QE"        # 리밸 주기(짧은 테스트창에 적정 리밸 수 확보)
COST = 0.002       # algo 전환비용(fold 경계 승자 변경 시)
PROXY = [c for c in REC_PROXY if c != "DEPOSIT"]


def _ridx_in(index, lo, hi):
    """[lo,hi) 정수구간에 드는 리밸 신호 인덱스."""
    return [i for i in rebal_dates_idx(index, FREQ, WARMUP) if lo <= i < hi]


def window_equity(nav, strategy, lo, hi):
    """nav에서 strategy를 [lo,hi) 리밸로 실행 → 그 구간 정규화 수익경로(start=1) Series.
    리밸 전(포지션 미설정) 구간은 현금 평탄 → 정규화로 ~0수익 처리(구간 누락 없음)."""
    ridx = _ridx_in(nav.index, lo, hi)
    if not ridx:
        return None
    res = fast_run(nav, strategy, ridx)
    if res is None:
        return None
    _, eq = res
    end = min(hi, len(nav.index)) - 1
    seg = eq.loc[nav.index[lo]:nav.index[end]].dropna()
    if len(seg) < 5 or seg.iloc[0] <= 0:
        return None
    return seg / seg.iloc[0]


def _metrics(eq):
    m = perf_metrics(eq, 0.0, 0, 0.0)
    return {k: m[k] for k in ("CAGR%", "Sharpe", "MDD%", "Sortino", "변동성%", "Calmar")}


def make_folds(T):
    folds, t = [], WARMUP + MIN_TRAIN
    while t + TEST <= T:
        folds.append((t, t + TEST))
        t += STEP
    if t < T and (T - t) >= 40:          # 잔여(≥40일)는 부분 fold로 포함
        folds.append((t, T))
    return folds


def stitch_fixed(nav, strat, folds):
    """고정 전략을 동일 fold 경계로 OOS stitch(전환비용 없음)."""
    lvl, segs = 1.0, []
    for (t, hi) in folds:
        p = window_equity(nav, strat, t, hi)
        if p is None:
            return None
        s = lvl * p
        lvl = float(s.iloc[-1])
        segs.append(s if not segs else s.iloc[1:])
    return pd.concat(segs)


def main(test=TEST, step=STEP, freq=FREQ):
    global TEST, STEP, FREQ
    TEST, STEP, FREQ = test, step, freq

    navA0 = _universe()
    T = len(navA0)
    rm = load_riskmap()
    navD = add_deposit(navA0)             # 후보 algo 패널(전 유니버스, DEPOSIT 컬럼은 미선택)
    navR = add_deposit(navA0[PROXY])      # 추천 proxy 패널
    cands = {n: dc_constrained(fn, rm) for n, fn in algos.ALGOS.items()}
    rec_fn = fixed(REC_PROXY)
    ew_fn = dc_constrained(algos.momentum_topn(9999), rm)

    folds = make_folds(T)
    print("=" * 100)
    print("Walk-Forward OOS | %d펀드 | %s~%s (%d일,%.1fy) | fold %d개 (TEST%d STEP%d %s리밸, anchored)"
          % (navA0.shape[1], navA0.index[0].date(), navA0.index[-1].date(), T, T / 252,
             len(folds), TEST, STEP, FREQ))
    if len(folds) < 3:
        print("  ⚠ fold<3 — 통계력 매우 낮음. FDR 장기 실지수 백테스트 병행 필수.")

    # ---- WF-Select + 추천(동일 fold) stitch ----
    sel_lvl, rec_lvl, prev = 1.0, 1.0, None
    sel_segs, rec_segs, rows = [], [], []
    for k, (t, hi) in enumerate(folds):
        scores = {}
        for n, fn in cands.items():
            tr = window_equity(navD, fn, WARMUP, t)     # anchored 학습 [WARMUP,t)
            scores[n] = _metrics(tr)["Sharpe"] if tr is not None else -1e9
        winner = max(scores, key=scores.get)
        sp = window_equity(navD, cands[winner], t, hi)
        rp = window_equity(navR, rec_fn, t, hi)
        if sp is None or rp is None:
            continue
        if prev is not None and winner != prev:
            sel_lvl *= (1 - COST)
        sseg = sel_lvl * sp; sel_lvl = float(sseg.iloc[-1])
        rseg = rec_lvl * rp; rec_lvl = float(rseg.iloc[-1])
        sel_segs.append(sseg if not sel_segs else sseg.iloc[1:])
        rec_segs.append(rseg if not rec_segs else rseg.iloc[1:])
        sm, rmx = _metrics(sp), _metrics(rp)
        rows.append((k + 1, str(navA0.index[t].date()), winner, round(scores[winner], 2),
                     sm["CAGR%"], sm["MDD%"], rmx["CAGR%"], rmx["MDD%"]))
        prev = winner

    sel_oos, rec_oos = pd.concat(sel_segs), pd.concat(rec_segs)

    # ---- fold별 표 ----
    print("\n[fold별 OOS]  승자algo(학습Sharpe) | WF-Select OOS | 추천65/35 OOS")
    print("  %-3s %-11s %-16s %6s | %7s %7s | %7s %7s" %
          ("#", "테스트시작", "승자", "Shp", "선택CAGR", "선택MDD", "추천CAGR", "추천MDD"))
    sel_win = 0
    for (i, d, w, sh, sc, sm_, rc, rm_) in rows:
        better = sc > rc
        sel_win += better
        print("  %-3d %-11s %-16s %6.2f | %7.2f %7.2f | %7.2f %7.2f %s" %
              (i, d, w[:16], sh, sc, sm_, rc, rm_, "←WF승" if better else ""))

    # ---- 개별 algo 고정 OOS(전 fold 동일 algo 유지) + 동일가중 ----
    fixed_oos = {}
    for n, fn in cands.items():
        e = stitch_fixed(navD, fn, folds)
        if e is not None:
            fixed_oos[n] = e
    ew_oos = stitch_fixed(navD, ew_fn, folds)

    # ---- OOS 요약 ----
    def line(label, eq):
        m = _metrics(eq)
        print("  %-20s CAGR%7.2f  Sharpe%7.3f  MDD%8.2f  Sortino%7.3f" %
              (label, m["CAGR%"], m["Sharpe"], m["MDD%"], m["Sortino"]))

    print("\n[OOS 종합 — 동일 fold 경계 stitch]")
    line("WF-Select(메타)", sel_oos)
    line("추천65/35(고정)", rec_oos)
    if ew_oos is not None:
        line("동일가중(DC)", ew_oos)
    print("  --- 개별 algo 고정(사후 최선 참고) ---")
    best_fixed = max(fixed_oos, key=lambda n: _metrics(fixed_oos[n])["Sharpe"]) if fixed_oos else None
    for n in sorted(fixed_oos, key=lambda n: -_metrics(fixed_oos[n])["Sharpe"]):
        tag = "  ★사후최선" if n == best_fixed else ""
        line(n, fixed_oos[n])
        if tag:
            print("  " + " " * 18 + tag)

    # ---- 게이트(algo_eval 기준) ----
    ms, mr = _metrics(sel_oos), _metrics(rec_oos)
    cagr_ok = ms["CAGR%"] >= 1.10 * mr["CAGR%"]
    mdd_ok = abs(ms["MDD%"]) <= 0.90 * abs(mr["MDD%"])
    npaths = len(rows)
    print("\n[판정] WF-Select vs 추천65/35  (게이트: CAGR≥1.10× AND |MDD|≤0.90×)")
    print("  CAGR %.2f vs 필요 %.2f → %s | MDD %.2f vs 허용 %.2f → %s | fold승률 %d/%d(%.0f%%)" %
          (ms["CAGR%"], 1.10 * mr["CAGR%"], "OK" if cagr_ok else "X",
           ms["MDD%"], -0.90 * abs(mr["MDD%"]), "OK" if mdd_ok else "X",
           sel_win, npaths, 100 * sel_win / npaths if npaths else 0))
    verdict = "PASS — 선택이 표본외 우위" if (cagr_ok and mdd_ok) else "FAIL — 고정 추천65/35가 표본외 우위(과적합 확인)"
    print("  => %s" % verdict)

    # ---- 저장 ----
    out = {
        "config": {"TEST": TEST, "STEP": STEP, "FREQ": FREQ, "folds": len(folds),
                   "universe_n": int(navA0.shape[1]), "period": [str(navA0.index[0].date()), str(navA0.index[-1].date())]},
        "folds": [{"fold": i, "test_start": d, "winner": w, "train_sharpe": sh,
                   "sel_cagr": sc, "sel_mdd": sm_, "rec_cagr": rc, "rec_mdd": rm_}
                  for (i, d, w, sh, sc, sm_, rc, rm_) in rows],
        "oos": {"WF-Select": _metrics(sel_oos), "추천65/35": _metrics(rec_oos),
                **({"동일가중": _metrics(ew_oos)} if ew_oos is not None else {}),
                **{n: _metrics(e) for n, e in fixed_oos.items()}},
        "gate": {"cagr_ok": bool(cagr_ok), "mdd_ok": bool(mdd_ok),
                 "PASS": bool(cagr_ok and mdd_ok), "sel_fold_win": int(sel_win), "n_folds": int(npaths)},
    }
    json.dump(out, open("wf_oos_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n저장: wf_oos_results.json")
    return out


if __name__ == "__main__":
    a = sys.argv
    main(test=int(a[1]) if len(a) > 1 else TEST,
         step=int(a[2]) if len(a) > 2 else STEP,
         freq=a[3] if len(a) > 3 else FREQ)
