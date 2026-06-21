# -*- coding: utf-8 -*-
"""
사용자 정의 3개 알고리즘 — 월간(15일근접) 리밸, 펀드65%(5종 동일 13%) + 안전자산35%.

방식1(모멘텀 가속): 3개월 수익률 상위10 중 1개월 수익률 최고 5개
방식2(단기 반전):   3개월 수익률 상위10 중 1개월 수익률 최저 5개
방식3(섹터 로테이션): 5섹터(금/바이오/중국/인도/미국) 각 3개월 수익률 최고 1개

안전자산: safe='DEPOSIT'(예금4.9%) 또는 safe=None(현금 무수익).
"""
import json
import numpy as np
import pandas as pd

L3, L1, L6 = 63, 21, 126  # 3개월/1개월/6개월 거래일
FUND_W, SAFE_W = 0.13, 0.35


def load_sectors():
    cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))
    meta = json.load(open("nav_history/_metadata.json", encoding="utf-8"))
    n2c = {meta[c]["name"]: c for c in meta if c[0] == "K" and "_" not in c}
    sec = {"금": [], "바이오": [], "중국": [], "인도": [], "미국": []}
    for nm, info in cls.items():
        c = n2c.get(nm)
        if not c:
            continue
        themes = info.get("themes", [])
        region = info.get("region")
        if "골드" in nm or "금광" in nm:
            sec["금"].append(c)
        elif "healthcare" in themes or any(k in nm for k in ["바이오", "헬스", "제약"]):
            sec["바이오"].append(c)
        elif region == "china":
            sec["중국"].append(c)
        elif region == "india":
            sec["인도"].append(c)
        elif region == "us":
            sec["미국"].append(c)
    return sec


def _valid(nav_upto, n=L3):
    w = nav_upto.iloc[-n - 1:]
    w = w.drop(columns=["DEPOSIT"], errors="ignore")
    return w.dropna(axis=1, how="any")


def _add_safe(picks, safe):
    if not len(picks):
        return {"DEPOSIT": 1.0} if safe else {}
    w = {c: FUND_W for c in picks}
    if safe:
        w[safe] = SAFE_W
    return w  # safe=None이면 합 0.65(잔여 현금)


def method1(safe="DEPOSIT", top=20):
    def s(nav_upto, date):
        w = _valid(nav_upto)
        if w.shape[1] < top:
            return {}
        r3 = w.iloc[-1] / w.iloc[-L3 - 1] - 1
        topN = r3.nlargest(top).index
        r1 = (w.iloc[-1] / w.iloc[-L1 - 1] - 1)[topN]
        return _add_safe(r1.nlargest(5).index, safe)
    return s


def method2(safe="DEPOSIT", top=20):
    def s(nav_upto, date):
        w = _valid(nav_upto)
        if w.shape[1] < top:
            return {}
        r3 = w.iloc[-1] / w.iloc[-L3 - 1] - 1
        topN = r3.nlargest(top).index
        r1 = (w.iloc[-1] / w.iloc[-L1 - 1] - 1)[topN]
        return _add_safe(r1.nsmallest(5).index, safe)
    return s


def method3(sectors, safe="DEPOSIT", lookback=L6):  # 6개월 수익률 기준
    def s(nav_upto, date):
        win = nav_upto.iloc[-lookback - 1:]
        picks = []
        for sec, codes in sectors.items():
            avail = [c for c in codes if c in win.columns and win[c].notna().all()]
            if not avail:
                continue
            r6 = {c: win[c].iloc[-1] / win[c].iloc[0] - 1 for c in avail}
            picks.append(max(r6, key=r6.get))
        if not picks:
            return {}
        wf = 0.65 / len(picks)
        w = {c: wf for c in picks}
        if safe:
            w[safe] = SAFE_W
            # 펀드 합 0.65 + 예금 0.35 = 1.0
        return w
    return s


# ========================================================================
# TradingAgents 생태계 수집 → DC 펀드 변환 3종 (200SMA 레짐 / 변동성타게팅 / 앙상블투표)
# 공통: 위험자산 cap 0.65, 안전 35% 기준. 위험-off분은 예금으로 라우팅.
#       모두 구조적 DC준수(위험≤65%·단일=cap/5≤13%) → dc_constrained 불요.
# 출처: [[(20260614)_TradingAgents_퀀트알고리즘_수집]]
# ========================================================================
MA200, RISK_CAP, N_CORE = 200, 0.65, 5


def _navwin(nav_upto, n):
    """직전 n+1봉 가격창(예금 제외, 전구간 유효 펀드만)."""
    w = nav_upto.iloc[-n - 1:].drop(columns=["DEPOSIT"], errors="ignore")
    return w.dropna(axis=1, how="any")


def _core(w, n=N_CORE, mom=L3):
    """3개월 모멘텀 상위 n 코어."""
    return list((w.iloc[-1] / w.iloc[-mom - 1] - 1).nlargest(n).index)


def _macd_bull(px):
    """MACD(12,26,9) 라인 > 시그널 → 강세."""
    e12 = px.ewm(span=12, adjust=False).mean()
    e26 = px.ewm(span=26, adjust=False).mean()
    macd = e12 - e26
    return float(macd.iloc[-1]) > float(macd.ewm(span=9, adjust=False).mean().iloc[-1])


def _rsi_bull(px, n=14):
    """RSI(14) 50~70(상승 모멘텀, 과매수 아님) → 강세."""
    d = px.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    r = float((100 - 100 / (1 + rs)).iloc[-1])
    return 50.0 < r < 70.0


def regime_gate(safe="DEPOSIT", ma=MA200, n_core=N_CORE, risk_cap=RISK_CAP):
    """200SMA 레짐 게이트: 코어 펀드별 NAV>200SMA면 보유, 아니면 그 슬리브를 예금으로."""
    def s(nav_upto, date):
        w = _navwin(nav_upto, max(ma, L3))
        if w.shape[1] < n_core:
            return {safe: 1.0} if safe else {}
        sleeve = risk_cap / n_core
        out, off = {}, 0.0
        for c in _core(w, n_core):
            if w[c].iloc[-1] > w[c].iloc[-ma:].mean():
                out[c] = sleeve
            else:
                off += sleeve
        if safe:
            out[safe] = (1 - risk_cap) + off
        return out
    return s


def vol_target(safe="DEPOSIT", target=0.10, vol_lb=L3, n_core=N_CORE, risk_cap=RISK_CAP):
    """변동성 타게팅: 코어 동일가중 실현변동성=target이 되도록 위험노출 절대 스케일(무차입, cap)."""
    def s(nav_upto, date):
        w = _navwin(nav_upto, max(vol_lb, L3) + 1)
        if w.shape[1] < n_core:
            return {safe: 1.0} if safe else {}
        core = _core(w, n_core)
        pr = w[core].pct_change().dropna().iloc[-vol_lb:].mean(axis=1)  # 동일가중 슬리브 일수익
        realized = float(pr.std()) * np.sqrt(252)
        scale = 1.0 if realized <= 0 else min(1.0, target / realized)
        risk_total = risk_cap * scale
        out = {c: risk_total / n_core for c in core}
        if safe:
            out[safe] = 1.0 - risk_total
        return out
    return s


def ensemble_vote(safe="DEPOSIT", ma=MA200, n_core=N_CORE, risk_cap=RISK_CAP, pool=15, min_votes=2):
    """다중시그널 앙상블: 모멘텀풀에서 MACD·200SMA·RSI 다수결(≥2) 통과 펀드 선택, 미달분 예금."""
    def s(nav_upto, date):
        w = _navwin(nav_upto, max(ma, L3) + 1)
        if w.shape[1] < n_core:
            return {safe: 1.0} if safe else {}
        mom = w.iloc[-1] / w.iloc[-L3 - 1] - 1
        scored = []
        for c in mom.nlargest(min(pool, w.shape[1])).index:
            px = w[c]
            v = int(_macd_bull(px)) + int(px.iloc[-1] > px.iloc[-ma:].mean()) + int(_rsi_bull(px))
            if v >= min_votes:
                scored.append((c, v, float(mom[c])))
        scored.sort(key=lambda t: (-t[1], -t[2]))
        picks = scored[:n_core]
        sleeve = risk_cap / n_core
        out = {c: sleeve for c, _, _ in picks}
        if safe:
            out[safe] = (1 - risk_cap) + (n_core - len(picks)) * sleeve
        return out
    return s


def mom5_base(safe="DEPOSIT", n_core=N_CORE, risk_cap=RISK_CAP):
    """기준선: 타이밍 無 — 모멘텀 상위5 항상 위험-on(65%) + 예금35%. 오버레이 순효과 분리용."""
    def s(nav_upto, date):
        w = _navwin(nav_upto, L3 + 1)
        if w.shape[1] < n_core:
            return {safe: 1.0} if safe else {}
        out = {c: risk_cap / n_core for c in _core(w, n_core)}
        if safe:
            out[safe] = 1 - risk_cap
        return out
    return s


# ========================================================================
# 분산-리스크버짓 선정 (Iter1 후보 B) — 추천65/35 대비 MDD·Sharpe 강건 개선 목표.
# 방법: 큐레이션 저상관 분산풀 inverse-vol 리스크버짓(위험65%) + 예금 35% 플로어.
#   근거 레포: Riskfolio-Lib(risk-budgeting), PyPortfolioOpt, López de Prado HRP.
#   설계철학: 단순 inverse-vol(자유파라미터 최소) — 과적합 회피. 풀은 region/theme 분산 고정.
# 검증: algo_eval.evaluate (페어 부트스트랩). 한계: 비동기NAV 시차로 분산효과 과대평가 가능.
# ⚠️ Critic 결론([[algo_critic_report]]): MDD/Sharpe 개선만 견고. +10% CAGR 우위는
#    사후편향(풀의 고수익 자산 사전선택) 산물 → 수익booster 아님. 하방방어 목적 한정.
# ========================================================================
DIV_POOL = [
    "K55105BA7360",  # 미국 S&P500 (코어)
    "K55105BU5980",  # KOSPI200
    "K55307D05993",  # 필라델피아반도체 (성장엔진)
    "K55209CT1721",  # 신영밸류고배당 (방어·가치)
    "K55301B59864",  # 일본 밸류중소형 (저상관 corr0.18)
    "K55301B25428",  # 인디아 인프라 (저상관 corr0.26)
    "K55366BU9754",  # 글로벌 에너지 (저상관 corr0.17)
    "K55366BU9572",  # 금(광주) (저상관 corr0.12)
]


def diversified_riskbudget(pool=None, eq=0.65, safe="DEPOSIT", lb=120, min_n=3):
    """분산풀 inverse-vol 리스크버짓 + 예금 플로어. forward-pricing(nav_upto만 사용)."""
    pool = pool or DIV_POOL
    def s(nav_upto, date):
        w = nav_upto.iloc[-lb - 1:][[c for c in pool if c in nav_upto.columns]].dropna(axis=1, how="any")
        if w.shape[1] < min_n:
            return {safe: 1.0} if safe else {}
        vol = w.pct_change().dropna().std().values            # 과거 lb일 일변동성
        iv = 1.0 / np.where(vol > 0, vol, np.nan)
        iv = np.nan_to_num(iv) / np.nansum(iv)                 # 정규화(합=1)
        out = {c: float(eq * x) for c, x in zip(w.columns, iv)}
        if safe:
            out[safe] = 1.0 - eq
        return out
    return s


def rebal_15th_idx(index, warmup, months=None):
    """15일 근접 거래일 인덱스. months=None이면 매월, (3,6,9,12)면 분기."""
    out = []
    seen = set()
    for d in index:
        if months is not None and d.month not in months:
            continue
        key = (d.year, d.month)
        if key in seen:
            continue
        seen.add(key)
        md = index[(index.year == d.year) & (index.month == d.month)]
        target = pd.Timestamp(d.year, d.month, 15)
        nearest = md[int(np.argmin(np.abs((md - target).days)))]
        pos = index.get_loc(nearest)
        if pos >= warmup:
            out.append(pos)
    return sorted(set(out))


def rebal_quarter_15th_idx(index, warmup):
    """분기(3·6·9·12월) 15일 근접 거래일."""
    return rebal_15th_idx(index, warmup, months=(3, 6, 9, 12))
