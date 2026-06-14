# -*- coding: utf-8 -*-
"""
10개 퀀트 배분 알고리즘 — 자체 구현(numpy/scipy/sklearn), 의존성 0(외부 퀀트 라이브러리 불요).

설계:
- 공통 후보 풀: 각 리밸일 직전 lookback 데이터 보유 펀드 중 모멘텀 상위 N종 → 공정 비교 + 표본/계산 안정(N<<lookback).
- 선택형(1~3): 자체 선택 로직 → 동일가중.
- 배분형(4~10): 후보 풀 N종에 비중 최적화(역변동성/MinVar/MaxSharpe/ERC/HRP/HERC/Mean-CVaR).
- 반환: {code: weight}(합≤1). DC 제약(위험70/단일40)은 호출측에서 apply_dc로 후처리.

참고: HRP/HERC = López de Prado(2016). Mean-CVaR = Rockafellar-Uryasev(2000) LP.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize, linprog
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf

LOOKBACK = 252
POOL_N = 20
PPY = 252


# ---------------- 공통 헬퍼 ----------------
def _window(nav_upto, lookback=LOOKBACK):
    win = nav_upto.iloc[-lookback - 1:].dropna(axis=1, how="any")
    return win if win.shape[1] >= 5 else None


def _pool(nav_upto, lookback=LOOKBACK, n=POOL_N):
    """모멘텀 상위 n 후보 풀: (win_prices, rets, codes)."""
    win = _window(nav_upto, lookback)
    if win is None:
        return None, None, None
    mom = win.iloc[-1] / win.iloc[0] - 1
    top = list(mom.nlargest(min(n, win.shape[1])).index)
    w = win[top]
    return w, w.pct_change().dropna(), top


def _cov(rets):
    """Ledoit-Wolf 수축 공분산(연율화)."""
    return LedoitWolf().fit(rets.values).covariance_ * PPY


def _norm(w):
    w = np.clip(w, 0, None)
    s = w.sum()
    return w / s if s > 0 else w


# ---------------- 1~3 선택형 ----------------
def momentum_topn(n=10, lookback=LOOKBACK):
    def s(nav_upto, date):
        win = _window(nav_upto, lookback)
        if win is None:
            return {}
        mom = win.iloc[-1] / win.iloc[0] - 1
        top = mom.nlargest(min(n, win.shape[1])).index
        return {c: 1.0 / len(top) for c in top}
    return s


def dual_momentum(n=10, lookback=LOOKBACK):
    """절대(과거수익>0) 필터 + 상대 상위n. 전부 음수면 현금(빈 dict)."""
    def s(nav_upto, date):
        win = _window(nav_upto, lookback)
        if win is None:
            return {}
        mom = win.iloc[-1] / win.iloc[0] - 1
        pos = mom[mom > 0]
        if pos.empty:
            return {}
        top = pos.nlargest(min(n, len(pos))).index
        return {c: 1.0 / len(top) for c in top}
    return s


def trend_following(ma=200):
    """NAV > ma일 이동평균인 펀드 동일가중(추세 위)."""
    def s(nav_upto, date):
        win = _window(nav_upto, max(ma, LOOKBACK))
        if win is None:
            return {}
        last = win.iloc[-1]
        mavg = win.iloc[-ma:].mean()
        up = last[last > mavg].index
        return {c: 1.0 / len(up) for c in up} if len(up) else {}
    return s


# ---------------- 4~10 배분형(후보 풀) ----------------
def inverse_vol(lookback=LOOKBACK, n=POOL_N):
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None:
            return {}
        vol = rets.std().values
        w = _norm(1.0 / np.where(vol > 0, vol, np.nan))
        return {c: float(x) for c, x in zip(codes, np.nan_to_num(w))}
    return s


def risk_parity(lookback=LOOKBACK, n=POOL_N):
    """ERC: 위험기여 균등화."""
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None:
            return {}
        S = _cov(rets)
        k = len(codes)

        def obj(w):
            sig = np.sqrt(w @ S @ w)
            if sig <= 0:
                return 1e6
            rc = w * (S @ w) / sig
            return np.sum((rc - rc.mean()) ** 2)
        r = minimize(obj, np.ones(k) / k, method="SLSQP",
                     bounds=[(1e-4, 1)] * k,
                     constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                     options={"maxiter": 200, "ftol": 1e-10})
        return {c: float(x) for c, x in zip(codes, _norm(r.x))}
    return s


def min_variance(lookback=LOOKBACK, n=POOL_N):
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None:
            return {}
        S = _cov(rets)
        k = len(codes)
        r = minimize(lambda w: w @ S @ w, np.ones(k) / k, method="SLSQP",
                     bounds=[(0, 1)] * k,
                     constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                     options={"maxiter": 200, "ftol": 1e-12})
        return {c: float(x) for c, x in zip(codes, _norm(r.x))}
    return s


def max_sharpe(lookback=LOOKBACK, n=POOL_N, rf=0.0):
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None:
            return {}
        S = _cov(rets)
        mu = rets.mean().values * PPY
        k = len(codes)

        def neg(w):
            v = np.sqrt(w @ S @ w)
            return -(w @ mu - rf) / v if v > 0 else 1e6
        r = minimize(neg, np.ones(k) / k, method="SLSQP",
                     bounds=[(0, 1)] * k,
                     constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                     options={"maxiter": 300, "ftol": 1e-10})
        return {c: float(x) for c, x in zip(codes, _norm(r.x))}
    return s


# --- HRP (López de Prado) ---
def _quasi_diag(link):
    link = link.astype(int)
    sortIx = pd.Series([link[-1, 0], link[-1, 1]])
    numItems = link[-1, 3]
    while sortIx.max() >= numItems:
        sortIx.index = range(0, sortIx.shape[0] * 2, 2)
        df0 = sortIx[sortIx >= numItems]
        i = df0.index
        j = df0.values - numItems
        sortIx[i] = link[j, 0]
        df0 = pd.Series(link[j, 1], index=i + 1)
        sortIx = pd.concat([sortIx, df0]).sort_index()
        sortIx.index = range(sortIx.shape[0])
    return sortIx.tolist()


def _cluster_var(cov, items):
    c = cov[np.ix_(items, items)]
    ivp = 1.0 / np.diag(c)
    ivp /= ivp.sum()
    return float(ivp @ c @ ivp)


def _rec_bipart(cov, sortIx):
    w = pd.Series(1.0, index=sortIx)
    clusters = [sortIx]
    while clusters:
        clusters = [i[j:k] for i in clusters
                    for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1]
        for i in range(0, len(clusters), 2):
            c0, c1 = clusters[i], clusters[i + 1]
            v0, v1 = _cluster_var(cov, c0), _cluster_var(cov, c1)
            alpha = 1 - v0 / (v0 + v1)
            w[c0] *= alpha
            w[c1] *= 1 - alpha
    return w


def hrp(lookback=LOOKBACK, n=POOL_N):
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None or len(codes) < 3:
            return {}
        corr = rets.corr().values
        cov = rets.cov().values * PPY
        dist = np.sqrt(np.clip(0.5 * (1 - corr), 0, None))
        link = linkage(squareform(dist, checks=False), "single")
        order = _quasi_diag(link)
        w = _rec_bipart(cov, order)
        return {codes[i]: float(w[i]) for i in w.index}
    return s


def herc(lookback=LOOKBACK, n=POOL_N, k_clusters=4):
    """HERC 근사: 군집 k개로 분할 → 군집간 역분산 + 군집내 역변동성."""
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None or len(codes) < 4:
            return {}
        corr = rets.corr().values
        cov = rets.cov().values * PPY
        dist = np.sqrt(np.clip(0.5 * (1 - corr), 0, None))
        link = linkage(squareform(dist, checks=False), "ward")
        kk = min(k_clusters, len(codes) - 1)
        labels = fcluster(link, kk, criterion="maxclust")
        # 군집간 역분산
        cvar = {}
        for c in set(labels):
            items = list(np.where(labels == c)[0])
            cvar[c] = _cluster_var(cov, items)
        inv = {c: 1.0 / v for c, v in cvar.items()}
        tot = sum(inv.values())
        cw = {c: inv[c] / tot for c in inv}
        # 군집내 역변동성
        w = np.zeros(len(codes))
        vol = np.sqrt(np.diag(cov))
        for c in set(labels):
            items = np.where(labels == c)[0]
            iv = 1.0 / vol[items]
            iv /= iv.sum()
            w[items] = cw[c] * iv
        return {codes[i]: float(w[i]) for i in range(len(codes))}
    return s


def mean_cvar(lookback=LOOKBACK, n=POOL_N, alpha=0.95):
    """Rockafellar-Uryasev LP: 최소 CVaR 포트폴리오.
    vars=[w(k), zeta(1), u(T)] | min zeta + 1/((1-a)T) sum u
    s.t. u_t >= -R_t w - zeta ; u>=0 ; sum w=1 ; w>=0."""
    def s(nav_upto, date):
        _, rets, codes = _pool(nav_upto, lookback, n)
        if codes is None:
            return {}
        R = rets.values
        T, k = R.shape
        nv = k + 1 + T
        c = np.concatenate([np.zeros(k), [1.0], np.ones(T) / ((1 - alpha) * T)])
        # u_t + R_t w + zeta >= 0  ->  -R_t w - zeta - u_t <= 0
        A = np.zeros((T, nv))
        A[:, :k] = -R
        A[:, k] = -1.0
        A[:, k + 1:] = -np.eye(T)
        b = np.zeros(T)
        Aeq = np.zeros((1, nv))
        Aeq[0, :k] = 1.0
        beq = [1.0]
        bounds = [(0, 1)] * k + [(None, None)] + [(0, None)] * T
        res = linprog(c, A_ub=A, b_ub=b, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
        if not res.success:
            return {c2: 1.0 / k for c2 in codes}
        w = _norm(res.x[:k])
        return {c2: float(x) for c2, x in zip(codes, w)}
    return s


# ---------------- 레지스트리 ----------------
ALGOS = {
    "1.모멘텀Top10": momentum_topn(10),
    "2.듀얼모멘텀": dual_momentum(10),
    "3.트렌드추종(MA200)": trend_following(200),
    "4.역변동성": inverse_vol(),
    "5.리스크패리티(ERC)": risk_parity(),
    "6.최소분산": min_variance(),
    "7.최대샤프(MVO)": max_sharpe(),
    "8.HRP": hrp(),
    "9.HERC": herc(),
    "10.평균-CVaR": mean_cvar(),
}
