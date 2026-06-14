# -*- coding: utf-8 -*-
"""
연금펀드 백테스터 엔진 — 거래비용/지연/forward-pricing 반영.

한국 펀드 특성:
- NAV(수정기준가)에 총보수(TER)가 이미 일할 차감 반영됨 → 엔진에서 TER 재차감 금지(이중계산).
  엔진의 cost_bps는 펀드 교체 시 발생하는 거래비용(환매수수료/스프레드 대용)만 모델링.
- forward pricing: 신호는 T일 종가 NAV까지만 사용, 체결은 T+execution_lag NAV → 룩어헤드 차단.
- 일 1회 NAV 체결. 보유 중 NaN(휴면 공백)은 직전가 동결 평가.

전략 인터페이스:
  strategy(nav_upto: DataFrame[~t_signal], date) -> dict{code: weight}  (weight 합 1, 빈 dict=현금)
"""
import numpy as np
import pandas as pd


# ---------------- 성과지표 ----------------
def perf_metrics(equity, turnover_sum, n_rebal, total_cost, rf_annual=0.0, ppy=252):
    eq = equity.dropna()
    ret = eq.pct_change().dropna()
    years = len(eq) / ppy
    total = eq.iloc[-1] / eq.iloc[0] - 1
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    vol = ret.std() * np.sqrt(ppy)
    sharpe = (ret.mean() * ppy - rf_annual) / vol if vol > 0 else np.nan
    dd = eq / eq.cummax() - 1
    mdd = dd.min()
    calmar = cagr / abs(mdd) if mdd < 0 else np.nan
    downside = ret[ret < 0].std() * np.sqrt(ppy)
    sortino = (ret.mean() * ppy - rf_annual) / downside if downside > 0 else np.nan
    return {
        "총수익%": round(total * 100, 2), "CAGR%": round(cagr * 100, 2),
        "변동성%": round(vol * 100, 2), "Sharpe": round(sharpe, 3),
        "Sortino": round(sortino, 3), "MDD%": round(mdd * 100, 2),
        "Calmar": round(calmar, 3), "연회전율%": round(turnover_sum / years * 100, 1),
        "총거래비용%": round(total_cost / eq.iloc[0] * 100, 2), "리밸런스": n_rebal,
    }


# ---------------- 엔진 ----------------
class Backtester:
    def __init__(self, nav, init_capital=1e8, execution_lag=1, cost_bps=20.0,
                 rebalance="ME", rf_annual=0.0, ppy=252):
        """nav: DataFrame(date×code) 수정기준가. cost_bps: 편도 거래비용(bp)."""
        self.nav = nav.sort_index()
        self.navff = self.nav.ffill()              # 보유 중 NaN(공백) 직전가 평가용
        self.init = init_capital
        self.lag = execution_lag
        self.cost = cost_bps / 1e4
        self.rebalance = rebalance
        self.rf = rf_annual
        self.ppy = ppy

    _PERIOD = {"ME": "M", "M": "M", "QE": "Q", "Q": "Q", "W": "W", "YE": "Y", "A": "Y"}

    def _rebal_signal_dates(self):
        idx = self.nav.index
        freq = self._PERIOD.get(self.rebalance, self.rebalance)
        # 각 리밸런스 주기의 마지막 거래일 = 신호일
        grp = idx.to_series().groupby(idx.to_period(freq)).last()
        return list(grp.values)

    def run(self, strategy, warmup=126):
        dates = self.nav.index
        pos = {d: i for i, d in enumerate(dates)}
        # 신호일 -> 체결일 매핑 (forward pricing)
        exec_map = {}
        for t_s in self._rebal_signal_dates():
            i = pos[pd.Timestamp(t_s)]
            if i < warmup or i + self.lag >= len(dates):
                continue
            t_e = dates[i + self.lag]
            exec_map[t_e] = pd.Timestamp(t_s)

        codes = self.nav.columns
        holdings = pd.Series(0.0, index=codes)     # 좌수
        cash = self.init
        invested = False
        equity = pd.Series(index=dates, dtype=float)
        turnover_sum = 0.0
        total_cost = 0.0
        trades = []

        for t in dates:
            price_eval = self.navff.loc[t]
            v = (holdings * price_eval).sum() + cash           # 현금 비중 포함 평가

            if t in exec_map:
                t_s = exec_map[t]
                w = strategy(self.nav.loc[:t_s], t_s)          # 룩어헤드 없음: t_s 종가까지
                price_exec = self.nav.loc[t]                    # 체결가 = 체결일 실제 NAV
                # 체결일 NAV 유효 펀드만 (가중치 합<1이면 잔여=현금 보유)
                w = {c: x for c, x in w.items() if x > 0 and pd.notna(price_exec.get(c, np.nan))}
                wsum = sum(w.values())
                if wsum > 1.0:                                  # 합>1일 때만 정규화(현금≥0 보장)
                    w = {c: x / wsum for c, x in w.items()}
                    wsum = 1.0
                if v > 0:
                    w_new = pd.Series(0.0, index=codes)
                    for c, x in w.items():
                        w_new[c] = x
                    w_old = (holdings * price_eval) / v          # 현 보유 비중(현금은 자동 1-합)
                    turnover = (w_new - w_old).abs().sum()      # 현금↔펀드 이동 포함(매수+매도)
                    cost = v * turnover * self.cost
                    v_after = v - cost
                    holdings = (v_after * w_new / price_exec).fillna(0.0)
                    cash = v_after * (1.0 - wsum)               # 잔여 현금(무수익; rf 미적용)
                    invested = True
                    turnover_sum += turnover / 2                # 편도 환산
                    total_cost += cost
                    trades.append({"date": t, "signal": t_s, "n": len(w),
                                   "turnover": round(turnover, 4), "cost": round(cost, 0),
                                   "cash_w": round(1.0 - wsum, 4)})
                    v = v_after
            equity[t] = v

        m = perf_metrics(equity, turnover_sum, len(trades), total_cost, self.rf, self.ppy)
        return {"equity": equity, "metrics": m, "trades": pd.DataFrame(trades)}


# ---------------- 데모 전략 ----------------
def momentum_topN(N=10, lookback=126):
    def strat(nav_upto, date):
        if len(nav_upto) < lookback + 1:
            return {}
        win = nav_upto.iloc[-lookback - 1:]
        valid = win.iloc[0].notna() & win.iloc[-1].notna()      # 전 구간 데이터 보유 펀드만
        mom = (win.iloc[-1] / win.iloc[0] - 1)[valid].dropna()
        top = mom.nlargest(N).index
        return {c: 1.0 / len(top) for c in top} if len(top) else {}
    return strat


def equal_weight_all():
    def strat(nav_upto, date):
        valid = nav_upto.iloc[-1].dropna().index
        return {c: 1.0 / len(valid) for c in valid} if len(valid) else {}
    return strat


# ---------------- 데모 실행 ----------------
if __name__ == "__main__":
    nav = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    print("패널:", nav.shape, nav.index[0].date(), "~", nav.index[-1].date())

    def show(title, res):
        print("\n[%s]" % title)
        for k, v in res["metrics"].items():
            print("  %-10s %s" % (k, v))

    # 1) 모멘텀 Top10, 월간, lag1, 비용 20bp
    bt = Backtester(nav, execution_lag=1, cost_bps=20)
    show("모멘텀Top10 월간 lag1 cost20bp", bt.run(momentum_topN(10)))

    # 2) 벤치마크: 전체 동일가중 월간 리밸런스
    show("동일가중(벤치마크) 월간 lag1 cost20bp", bt.run(equal_weight_all()))

    # 3) 룩어헤드 검증: lag0(미래정보 누출) vs lag1
    bt0 = Backtester(nav, execution_lag=0, cost_bps=20)
    show("모멘텀Top10 lag0 (룩어헤드 점검용)", bt0.run(momentum_topN(10)))

    # 4) 비용 민감도: 0bp vs 50bp
    show("모멘텀Top10 cost0bp", Backtester(nav, execution_lag=1, cost_bps=0).run(momentum_topN(10)))
    show("모멘텀Top10 cost50bp", Backtester(nav, execution_lag=1, cost_bps=50).run(momentum_topN(10)))

    # 5) DC 규제 제약: 위험자산 ≤70%, 단일펀드 ≤40% (잔여=현금)
    from constraints import load_riskmap, dc_constrained, apply_dc, exposure
    rm = load_riskmap()
    res_dc = bt.run(dc_constrained(momentum_topN(10), rm))
    show("모멘텀Top10 + DC제약(위험70/단일40) 월간 lag1 cost20bp", res_dc)
    # 리밸런스별 한도 준수 전수검증: 각 신호일 전략가중치에 제약 적용 후 노출 점검
    strat = momentum_topN(10)
    viol_r = viol_s = checks = 0
    risk_series = []
    for t_s in bt._rebal_signal_dates():
        w = apply_dc(strat(nav.loc[:pd.Timestamp(t_s)], pd.Timestamp(t_s)), rm)
        if not w:
            continue
        ex = exposure(w, rm); checks += 1
        risk_series.append(ex["risk"])
        if ex["risk"] > 0.70 + 1e-6: viol_r += 1
        if ex["max_single"] > 0.40 + 1e-6: viol_s += 1
    import numpy as _np
    print("\n[DC 한도 준수 전수검증] 리밸런스 %d회" % checks)
    print("  위험자산>70%% 위반: %d | 단일>40%% 위반: %d" % (viol_r, viol_s))
    print("  위험노출 평균 %.1f%% (min %.1f%% / max %.1f%%) — 모멘텀은 거의 전부 위험자산→70%% 상시 도달" %
          (_np.mean(risk_series)*100, _np.min(risk_series)*100, _np.max(risk_series)*100))
