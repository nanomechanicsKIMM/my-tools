# -*- coding: utf-8 -*-
"""
P1-3 보수(TER) 복리 드래그 정량화 — 비용은 '확실한 마이너스 알파'.

입력: status/holdings_YYYYMMDD.json(보유), [--targets] 목표배분 JSON({코드|DEPOSIT: 비중%}),
      funds/fund_fees.json(totalFee, SoT).
산출: ①포트별 가중 TER(총자산 기준) ②연간 보수(원) ③총수익 시나리오별 30년 복리 자산 차이
      → fee_drag.json
게이트: 보유/목표의 펀드코드가 fund_fees.json에 전부 매칭되어야 함(미매칭 0 요구, 있으면 명시 후 종료코드 1).

사용(작업폴더 루트): python scripts/fee_drag.py [--holdings ...] [--targets ...]
    [--gross 0.03,0.05,0.07] [--years 30]
"""
import argparse, glob, json, re, sys


def load_fees():
    fees = json.load(open("funds/fund_fees.json", encoding="utf-8"))["fees"]
    if isinstance(fees, list):
        return {f["fundCode"]: float(f["totalFee"]) for f in fees}
    return {c: float(v["totalFee"]) for c, v in fees.items()}


def weighted_ter(weights, fees, label):
    """weights: {code|DEPOSIT|CASH: 비중(합~100)}. 반환 (총자산 가중 TER%, 미매칭 코드들)."""
    ter = 0.0
    missing = []
    for code, w in weights.items():
        if code in ("DEPOSIT", "CASH"):
            continue
        if code not in fees:
            missing.append(code)
            continue
        ter += fees[code] * w / 100.0
    return ter, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdings", default=None)
    ap.add_argument("--targets", default=None)
    ap.add_argument("--gross", default="0.03,0.05,0.07")
    ap.add_argument("--years", type=int, default=30)
    a = ap.parse_args()
    fees = load_fees()

    hpath = a.holdings or max(glob.glob("status/holdings_*.json"),
                              key=lambda p: re.search(r"(20\d{6})", p).group(1))
    hd = json.load(open(hpath, encoding="utf-8"))
    total = sum(h["value"] for h in hd["holdings"])
    cur_w = {}
    for h in hd["holdings"]:
        key = h["code"] if h.get("kind", "fund") == "fund" else h["code"]
        cur_w[key] = cur_w.get(key, 0) + h["value"] / total * 100

    ports = {"현재보유(%s)" % hd.get("asof", "?"): cur_w}
    if a.targets:
        ports["목표배분(%s)" % a.targets.split("/")[-1]] = json.load(open(a.targets, encoding="utf-8"))

    print("=" * 100)
    print("보수(TER) 복리 드래그 — fund_fees.json SoT | 총자산 %s원 | 투자 권유 아님" % format(int(total), ","))
    out = {"total_value": total, "ports": {}, "years": a.years}
    ters = {}
    fail = False
    for name, w in ports.items():
        ter, missing = weighted_ter(w, fees, name)
        if missing:
            print("  ✗ %s: fund_fees.json 미매칭 코드 %s — 게이트 실패" % (name, missing))
            fail = True
            continue
        ann = total * ter / 100.0
        ters[name] = ter
        out["ports"][name] = {"weighted_ter_pct": round(ter, 4), "annual_cost_krw": round(ann)}
        print("  %-24s 가중TER(총자산) %.3f%%  → 연간 보수 %s원" % (name, ter, format(round(ann), ",")))
    if fail:
        sys.exit(1)

    grosses = [float(x) for x in a.gross.split(",")]
    print("\n[%d년 복리 자산 차이]  FV = 총자산×(1+총수익−TER)^%d  (총수익=보수차감 전 가정)" % (a.years, a.years))
    hdr = "  %-14s" + " %16s" * len(ports)
    print(hdr % ("총수익 가정", *ports.keys()))
    out["compound"] = {}
    names = list(ters)
    for g in grosses:
        fvs = {n: total * (1 + g - ters[n] / 100.0) ** a.years for n in names}
        row = {n: round(fvs[n]) for n in names}
        if len(names) == 2:
            row["diff"] = round(fvs[names[1]] - fvs[names[0]])
        out["compound"]["%.0f%%" % (g * 100)] = row
        cells = " ".join("%13.2f억" % (fvs[n] / 1e8) for n in names)
        extra = ("   차이 %+.2f억" % ((fvs[names[1]] - fvs[names[0]]) / 1e8)) if len(names) == 2 else ""
        print("  %-14s %s%s" % ("%.0f%%" % (g * 100), cells, extra))
    json.dump(out, open("fee_drag.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: fee_drag.json  |  분기 보고서에 비용 드래그 섹션 의무(§15).")


if __name__ == "__main__":
    main()
