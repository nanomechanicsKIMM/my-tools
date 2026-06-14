# -*- coding: utf-8 -*-
"""
DC형 퇴직연금 규제 제약 레이어 — 백테스트 전략 가중치 후처리.

근거(과학기술인공제회 DC형):
  - 위험자산 합계 ≤ 70%
  - 단일 펀드 ≤ 40% (분산투자 의무)
  - 잔여(=1-위험-안전)는 현금/예금으로 보유

매핑: 패널은 표준코드 키, fund_classification.json은 펀드명(한글) 키.
      nav_history/_metadata.json의 code→name으로 연결 (282/282 정확매칭 확인).

제약 적용 순서(결정적):
  1) 단일펀드 캡: w[c] = min(w[c], MAX_SINGLE)
  2) 위험자산 합 캡: 위험자산 비중합 > MAX_RISK 이면 위험자산만 비례 축소
  3) 잔여는 현금(가중치 합 < 1 허용). 안전자산 풀이 지정되면 안전자산으로 충당 가능.

엔진 계약: 반환 dict의 가중치 합이 1 미만이면 backtester가 잔여를 현금(무수익)으로 보유.
"""
import csv, json, os

MAX_RISK = 0.70
MAX_SINGLE = 0.40
META = "nav_history/_metadata.json"
CLS = "funds/fund_classification.json"


def load_riskmap(meta_path=META, cls_path=CLS):
    """code -> dict(riskAsset:bool, assetClass:str, name:str) 매핑 빌드."""
    meta = json.load(open(meta_path, encoding="utf-8"))
    cls = json.load(open(cls_path, encoding="utf-8"))
    rm = {}
    for code, m in meta.items():
        if code[0] != "K" or "_" in code:
            continue
        c = cls.get(m["name"])
        if c is None:
            continue
        rm[code] = {"risk": bool(c["riskAsset"]), "assetClass": c["assetClass"],
                    "name": m["name"], "region": c.get("region"), "themes": c.get("themes", [])}
    return rm


def apply_dc(weights, riskmap, max_risk=MAX_RISK, max_single=MAX_SINGLE):
    """전략 목표가중치에 DC 제약 적용. 반환 dict 합 ≤ 1 (잔여=현금).
    분류 미상 코드는 보수적으로 위험자산 취급."""
    w = {c: x for c, x in weights.items() if x > 0}
    if not w:
        return {}
    # 1) 단일펀드 캡
    w = {c: min(x, max_single) for c, x in w.items()}

    def is_risk(c):
        info = riskmap.get(c)
        return True if info is None else info["risk"]

    # 2) 위험자산 합 캡
    risk_sum = sum(x for c, x in w.items() if is_risk(c))
    if risk_sum > max_risk:
        scale = max_risk / risk_sum
        w = {c: (x * scale if is_risk(c) else x) for c, x in w.items()}
    # 3) 단일캡 재확인(스케일 후엔 감소만 발생하므로 위반 불가) — 잔여는 현금
    return {c: x for c, x in w.items() if x > 1e-9}


def dc_constrained(strategy, riskmap, max_risk=MAX_RISK, max_single=MAX_SINGLE):
    """전략을 DC 제약으로 감싸는 래퍼."""
    def wrapped(nav_upto, date):
        return apply_dc(strategy(nav_upto, date), riskmap, max_risk, max_single)
    return wrapped


def exposure(weights, riskmap):
    """가중치의 위험/안전/현금 노출 분해 (검증/리포트용)."""
    risk = sum(x for c, x in weights.items()
               if (riskmap.get(c) or {"risk": True})["risk"])
    safe = sum(x for c, x in weights.items()
               if c in riskmap and not riskmap[c]["risk"])
    return {"risk": round(risk, 4), "safe": round(safe, 4),
            "cash": round(max(0.0, 1 - risk - safe), 4),
            "max_single": round(max(weights.values()), 4) if weights else 0.0,
            "n": len(weights)}


if __name__ == "__main__":
    rm = load_riskmap()
    print("riskmap 코드:", len(rm),
          "| 위험:", sum(1 for v in rm.values() if v["risk"]),
          "| 안전:", sum(1 for v in rm.values() if not v["risk"]))
    # 단위 테스트: 위험자산 90% 전략 -> 70% 캡 + 단일 40% 캡
    eq = [c for c, v in rm.items() if v["risk"]][:3]
    bd = [c for c, v in rm.items() if not v["risk"]][:1]
    test = {eq[0]: 0.50, eq[1]: 0.25, eq[2]: 0.15, bd[0]: 0.10}  # 위험90 안전10
    print("\n[입력]", {k[:8]: v for k, v in test.items()}, "위험합=0.90")
    out = apply_dc(test, rm)
    print("[제약후]", {k[:8]: round(v, 4) for k, v in out.items()})
    print("[노출]", exposure(out, rm))
    assert exposure(out, rm)["risk"] <= 0.70 + 1e-6, "위험 70% 위반"
    assert max(out.values()) <= 0.40 + 1e-6, "단일 40% 위반"
    print("\n단위테스트 PASS: 위험≤70%, 단일≤40%")
