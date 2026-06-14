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
