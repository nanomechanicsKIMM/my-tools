# -*- coding: utf-8 -*-
"""
fund_classification.json 알려진 자동분류 오류 정정(멱등).
- JSON 최상위 키 = 펀드명(별도 name 필드 없음)에 주의.
- 정정 규칙:
  ① 펀드명에 골드/gold 가 없는데 themes 에 'gold' 포함 → 제거 (키워드 false-positive)
  ② 펀드명 '(UH)' 포함 → hedged=false 강제, '(H)' 포함 → hedged=true 강제
사용: python scripts/fix_classification.py [경로...]
     (기본: funds/fund_classification.json funds/all/all_fund_classification.json)
"""
import json, re, sys

DEFAULT = ["funds/fund_classification.json", "funds/all/all_fund_classification.json"]

def fix(path):
    d = json.load(open(path, encoding="utf-8"))
    gold_rm = hedge_fix = 0
    kept = []
    for name, info in d.items():
        if not isinstance(info, dict):
            continue
        th = info.get("themes")
        if th and "gold" in th:
            if re.search(r"골드|gold", name, re.I):
                kept.append(name)
            else:
                th.remove("gold"); gold_rm += 1
        if "(UH)" in name and info.get("hedged") is not False:
            info["hedged"] = False; hedge_fix += 1
        elif "(H)" in name and info.get("hedged") is not True:
            info["hedged"] = True; hedge_fix += 1
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("%s | gold제거 %d · gold유지 %d · hedged정정 %d" % (path, gold_rm, len(kept), hedge_fix))
    for n in kept:
        print("   유지:", n)

if __name__ == "__main__":
    for p in (sys.argv[1:] or DEFAULT):
        fix(p)
