# -*- coding: utf-8 -*-
"""
Phase 6: 글로벌 분산 — 상관매트릭스 + 신흥국 스크리닝 + 재구성 백테스트.
패널(panel_adj_nav.csv)·분류(funds/fund_classification.json)·자격(eligibility.csv) 필요.
"""
import json, csv
import pandas as pd
import numpy as np
from mc_backtest import fast_run, boot_panel
from backtest_portfolio import add_deposit, fixed, REC_PROXY
from algos_new import rebal_quarter_15th_idx

EM_REGIONS = ["india", "vietnam", "brazil", "emerging", "asean", "asia", "china"]


def _load():
    nav = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))
    meta = json.load(open("nav_history/_metadata.json", encoding="utf-8"))
    n2c = {meta[c]["name"]: c for c in meta if c[0] == "K" and "_" not in c}
    full5 = set(r["code"] for r in csv.DictReader(open("eligibility.csv", encoding="utf-8")) if r["full_5y"] == "Y")
    return nav, cls, meta, n2c, full5


def correlation_matrix(codes_labels):
    """codes_labels: {label: code}. 반환 (상관DataFrame, 평균상관, 0.85+클러스터, 저상관쌍)."""
    nav, *_ = _load()
    ret = nav.pct_change(fill_method=None)
    codes, labels = list(codes_labels.values()), list(codes_labels.keys())
    sub = ret[codes].dropna(); sub.columns = labels
    cor = sub.corr(); m = cor.values; n = len(m)
    avg = (m.sum() - n) / (n * (n - 1))
    dup = [(labels[i], labels[j], round(m[i, j], 2)) for i in range(n) for j in range(i + 1, n) if m[i, j] >= 0.85]
    low = [(labels[i], labels[j], round(m[i, j], 2)) for i in range(n) for j in range(i + 1, n) if m[i, j] < 0.2]
    return cor, round(avg, 3), dup, low


def screen_emerging(sp="K55105BA7360", ks="K55105BU5980"):
    """신흥국 펀드 5년 메트릭 + 미국/한국 상관. 반환 정렬된 리스트(Sharpe 내림차순)."""
    nav, cls, meta, n2c, full5 = _load()
    ret = nav.pct_change(fill_method=None)
    rows = []
    for nm, info in cls.items():
        c = n2c.get(nm)
        if not c or info.get("region") not in EM_REGIONS or c not in nav.columns:
            continue
        s = ret[c].dropna()
        if len(s) < 400:
            continue
        eq = (1 + s).cumprod(); yrs = len(s) / 252
        cagr = eq.iloc[-1] ** (1 / yrs) - 1; vol = s.std() * np.sqrt(252)
        mdd = (eq / eq.cummax() - 1).min()
        sub = ret[[c, sp, ks]].dropna()
        rows.append(dict(code=c, region=info["region"], name=nm[:34], full5=c in full5,
                         cagr=cagr * 100, vol=vol * 100, sharpe=cagr / vol if vol > 0 else 0,
                         mdd=mdd * 100, rUS=round(sub[c].corr(sub[sp]), 2), rKR=round(sub[c].corr(sub[ks]), 2)))
    return sorted(rows, key=lambda x: -x["sharpe"])


def backtest_cases(cases, N=200, extra_codes=()):
    """cases: {label: {code: weight}}. 단일+다중경로(N) 성과. extra_codes: 부트스트랩 유니버스 추가."""
    nav, cls, meta, n2c, full5 = _load()
    navAD = add_deposit(nav); ridx = rebal_quarter_15th_idx(navAD.index, 126)
    out = {}
    for lb, w in cases.items():
        m, _ = fast_run(navAD, fixed(w), ridx)
        out[lb] = {"single": m}
    proxy = [c for c in REC_PROXY if c != "DEPOSIT"]
    uni = sorted(set(c for c in nav.columns if c in full5) | set(proxy) | set(extra_codes))
    navW = nav[uni]; navW = navW.loc[:, navW.iloc[-1].notna()].dropna(how="any")
    ret_arr = navW.pct_change().dropna().values; dates, codes = navW.index, list(navW.columns)
    import mc_backtest
    mc_backtest.RNG = np.random.default_rng(20260614)
    acc = {lb: [] for lb in cases}
    for p in range(N):
        nb = add_deposit(boot_panel(ret_arr, dates, codes, 40)); ri = rebal_quarter_15th_idx(nb.index, 126)
        for lb, w in cases.items():
            r = fast_run(nb, fixed(w), ri)
            if r:
                acc[lb].append((r[0]["Sharpe"], r[0]["MDD%"], r[0]["CAGR%"]))
    for lb in cases:
        a = np.array(acc[lb])
        out[lb]["multi"] = dict(sharpe_med=round(np.median(a[:, 0]), 3), mdd_worst=round(np.min(a[:, 1]), 1),
                                cagr_med=round(np.median(a[:, 2]), 1))
    return out


if __name__ == "__main__":
    M = {"S&P500": "K55105BA7360", "美블루칩": "K55301B51580", "필반도체": "K55307D05993",
         "KOSPI200": "K55105BU5980", "신영고배당": "K55209CT1721", "중국A주": "K55223BV4542",
         "인도인프라": "K55301B25428"}
    cor, avg, dup, low = correlation_matrix(M)
    print("=== 상관매트릭스 (평균 %.3f) ===" % avg)
    print(cor.round(2).to_string())
    print("0.85+ 중복:", dup)
    print("\n=== 신흥국 스크리닝 (상위5) ===")
    for r in screen_emerging()[:5]:
        print("  %s %-8s CAGR%.1f Sharpe%.2f rUS%.2f rKR%.2f %s" %
              (r["code"], r["region"], r["cagr"], r["sharpe"], r["rUS"], r["rKR"], r["name"]))
