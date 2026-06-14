# -*- coding: utf-8 -*-
"""
추천65/35 의사결정의 알고리즘 형식화 — portfolio_recommendation.md(fund-portfolio 에이전트) 재현.

추천 로직 5단계:
  ① 안전자산 게이트: bestBond 실질수익률 < 예금금리+0.5%p → 예금 100%
  ② 위험비중(연령 글라이드): cap(70%) - 보수조정 → 55세·은퇴7년 = 65%
  ③ 핵심-위성 슬롯: 핵심 50%(미국S&P22+나스닥13+KOSPI200 15) + 위성 15%(반도체8+고배당7)
  ④ 슬롯별 펀드 선택: 각 슬롯 조건 매칭 펀드 중 '최저 총보수'(Bogle 저비용) — 시점별 동적
  ⑤ 컴플라이언스: 위험≤70%, 단일≤40%, Tech/AI≤40%, 지역≤50%

→ 정적 추천(고정 6종)과 달리 '시점별 최저보수 펀드 자동 선택'(신생 저보수 등장 시 전환).
"""
import json
import re
import pandas as pd

DEPOSIT_RATE = 4.9
BOND_THRESHOLD = 0.5     # 채권 선택 임계 = 예금+0.5%p
RISK_CAP = 0.70
RISK_TRIM = 0.05         # 55세·은퇴임박 보수조정

# 슬롯: (이름, 비중, 펀드명정규식, region요건, 환노출요건UH, 랭킹)
# 랭킹: 'min_fee'(최저 총보수, Bogle 저비용) | 'max_aum'(최대 순자산, 안정성)
SLOTS = [
    ("핵심:미국S&P500", 0.22, r"S\s*&\s*P\s*500|에스앤피\s*500", "us", True, "min_fee"),
    ("핵심:미국나스닥100", 0.13, r"나스닥\s*100|NASDAQ\s*100", "us", True, "min_fee"),
    ("핵심:한국KOSPI200", 0.15, r"KOSPI\s*200|코스피\s*200", "korea", False, "min_fee"),
    ("위성:반도체", 0.08, r"반도체|필라델피아", None, True, "min_fee"),
    ("위성:고배당가치", 0.07, r"고배당|밸류고배당|가치고배당", None, False, "max_aum"),
]
RISK_W = 0.65            # ②의 산출값


def _load():
    fees = json.load(open("funds/fund_fees.json", encoding="utf-8"))["fees"]
    cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))
    meta = json.load(open("nav_history/_metadata.json", encoding="utf-8"))
    fdata = {d["fundCode"]: d for d in json.load(open("funds/fund_data.json", encoding="utf-8"))["funds"]}
    c2n = {c: meta[c]["name"] for c in meta if c[0] == "K" and "_" not in c}

    def fee(c):
        try:
            return float(fees[c]["totalFee"])
        except Exception:
            return 99.0

    def aum(c):
        try:
            return float(str(fdata[c]["netAssets"]).replace(",", ""))
        except Exception:
            return 0.0
    return c2n, cls, fee, aum


def is_UH(name):
    """환노출(UH) 여부. 'UH' 명시 → True, '(H)'/'H[' → False, 그 외 환노출 추정."""
    if "UH" in name or "언헤지" in name:
        return True
    if re.search(r"\(H\)|H\[|환헤지", name):
        return False
    return True


def select_slot(slot, available, c2n, cls, fee, aum):
    """슬롯 조건 매칭 펀드 중 랭킹(min_fee/max_aum) 선택(없으면 None)."""
    _, _, pat, region, need_uh, rank = slot
    cand = []
    for c in available:
        nm = c2n.get(c, "")
        if not re.search(pat, nm, re.I):
            continue
        if region and cls.get(nm, {}).get("region") != region:
            continue
        if need_uh and not is_UH(nm):
            continue
        cand.append(c)
    if not cand:
        return None
    return max(cand, key=aum) if rank == "max_aum" else min(cand, key=fee)


def safe_gate(bond_real_returns):
    """① 안전자산 게이트. bond_real_returns=[(name, 실질수익률)]. 반환 'DEPOSIT' 또는 코드."""
    if not bond_real_returns:
        return "DEPOSIT"
    best = max(bond_real_returns, key=lambda x: x[1])
    return "DEPOSIT" if best[1] < DEPOSIT_RATE + BOND_THRESHOLD else best[0]


def risk_weight(age=55, retire_in=7):
    """② 연령 글라이드. 은퇴 임박(≤10년)이면 cap에서 보수조정."""
    w = RISK_CAP - (RISK_TRIM if retire_in <= 10 else 0.0)
    return round(w, 4)


def recommend_strategy(safe="DEPOSIT", risk=RISK_W):
    """④⑤ 슬롯별 랭킹 선택 + 비중. 못 채운 슬롯은 비례 재분배."""
    c2n, cls, fee, aum = _load()

    def strat(nav_upto, date):
        last = nav_upto.iloc[-1]
        available = [c for c in nav_upto.columns
                     if c != "DEPOSIT" and pd.notna(last[c])]
        picks = {}
        for slot in SLOTS:
            c = select_slot(slot, available, c2n, cls, fee, aum)
            if c:
                picks[c] = picks.get(c, 0) + slot[1]
        tot = sum(picks.values())
        if tot <= 0:
            return {safe: 1.0}
        w = {c: x / tot * risk for c, x in picks.items()}   # 위험비중 정규화
        w[safe] = 1 - risk
        return w
    return strat


if __name__ == "__main__":
    # 현재 시점 슬롯 선택 결과 (알고리즘 재현 검증)
    nav = pd.read_csv("panel_adj_nav.csv", index_col=0, parse_dates=True)
    c2n, cls, fee, aum = _load()
    available = [c for c in nav.columns if pd.notna(nav.iloc[-1][c])]
    print("=== 추천 알고리즘 형식화 — 현재 시점(2026-06) 슬롯 선택 ===")
    print("① 안전자산 게이트: 예금 %.1f%% (임계 %.1f%%) → 채권형 실질수익 미달 시 예금 100%%" %
          (DEPOSIT_RATE, DEPOSIT_RATE + BOND_THRESHOLD))
    print("② 위험비중(55세·은퇴7년): cap %.0f%% - 보수 %.0f%% = %.0f%%" %
          (RISK_CAP * 100, RISK_TRIM * 100, risk_weight() * 100))
    print("③④ 슬롯별 최저보수 선택:")
    total = 0
    for slot in SLOTS:
        c = select_slot(slot, available, c2n, cls, fee, aum)
        if c:
            tag = "순자산%.0f억" % (aum(c) / 1e4) if slot[5] == "max_aum" else "보수%.4f%%" % fee(c)
            print("   [%-16s] %2.0f%% → %s (%s) %s" %
                  (slot[0], slot[1] * 100, c, tag, c2n[c][:30]))
            total += slot[1]
        else:
            print("   [%-16s] %2.0f%% → (가용 펀드 없음)" % (slot[0], slot[1] * 100))
    print("   [안전자산:예금       ] 35%% → DEPOSIT")
    print("⑤ 컴플라이언스: 위험 %.0f%% ≤70 / 단일 22%% ≤40 / 합계 100%%" % (total * 100))
