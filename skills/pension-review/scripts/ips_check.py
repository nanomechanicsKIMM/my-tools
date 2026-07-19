# -*- coding: utf-8 -*-
"""
P3-1 IPS 자동 대조 — 투자정책서(status/ips_policy.json) vs 보유내역 분기 컴플라이언스.

자동 판정 항목(6):
  ① 위험자산비중 ≤ risk_max  ② 단일펀드 ≤ single_max  ③ 목표배분 밴드 이탈 수
  ④ 펀드 수 min~max  ⑤ 가중TER ≤ ter_max  ⑥ 신흥국 합계 ≤ emerging_max
③ 밴드 = 5/25 규칙(Daryanani 2008·Swedroe): 이탈 임계 = min(절대 band_pp, 목표×band_rel_frac).
  절대 단독(±5%p)은 4~7% 위성 포지션에 트리거 불능(인도 4%→9%까지 침묵) — 상대 25%로 보완.
  ips_policy.json에 band_rel_frac 없으면 종전 절대 밴드로 동작(하위호환). 임계 하한 0.5%p(먼지 가드).
출력: PASS/FAIL 체크리스트(콘솔+ips_check_results.json). FAIL 존재 시 exit 1(전환기에는 정상 — 괴리 목록 확인).
주의: 위험비중은 분류기반(기타→안전 집계 한계) — 포털 공시값 병기 확인.

사용(작업폴더 루트): python scripts/ips_check.py [--holdings ...] [--policy status/ips_policy.json]
"""
import argparse, glob, json, re, sys

EM_REGIONS = {"india", "china", "vietnam", "brazil", "emerging", "asean", "indonesia"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="status/ips_policy.json")
    ap.add_argument("--holdings", default=None)
    a = ap.parse_args()
    pol = json.load(open(a.policy, encoding="utf-8"))
    lim = pol["limits"]
    hpath = a.holdings or max(glob.glob("status/holdings_*.json"),
                              key=lambda p: re.search(r"(20\d{6})", p).group(1))
    hd = json.load(open(hpath, encoding="utf-8"))
    total = sum(h["value"] for h in hd["holdings"])
    fd = json.load(open("funds/fund_data.json", encoding="utf-8"))["funds"]
    code2name = {f["fundCode"]: f["name"] for f in fd}
    cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))
    fees = json.load(open("funds/fund_fees.json", encoding="utf-8"))["fees"]
    feemap = ({f["fundCode"]: float(f["totalFee"]) for f in fees} if isinstance(fees, list)
              else {c: float(v["totalFee"]) for c, v in fees.items()})

    risk = ter = em = 0.0
    single_max = 0.0
    n_funds = 0
    for h in hd["holdings"]:
        w = h["value"] / total * 100
        if h.get("kind", "fund") != "fund":
            continue
        n_funds += 1
        single_max = max(single_max, w)
        info = cls.get(code2name.get(h["code"], ""), {})
        if info.get("riskAsset", True):
            risk += w
        if info.get("region", "") in EM_REGIONS:
            em += w
        ter += feemap.get(h["code"], 0.0) * w / 100.0

    # 밴드 이탈(목표배분 대비)
    tg = json.load(open(pol["allocation"]["targets_file"], encoding="utf-8"))
    cur = {}
    for h in hd["holdings"]:
        cur[h["code"]] = cur.get(h["code"], 0) + h["value"] / total * 100
    band = pol["allocation"]["band_pp"]
    band_rel = pol["allocation"].get("band_rel_frac")   # 5/25 규칙: 상대밴드(목표의 25%)
    breaches = []
    for k in set(cur) | set(tg):
        if k == "CASH":
            continue
        t = float(tg.get(k, 0.0))
        thr = band if band_rel is None else max(min(band, band_rel * t), 0.5)
        d = cur.get(k, 0.0) - t
        if abs(d) > thr:
            breaches.append((code2name.get(k, k)[:30], round(d, 1)))
    band_label = ("±%d%%p" % band) if band_rel is None else \
        "5/25(min(±%d%%p, 목표×%d%%))" % (band, round(band_rel * 100))

    checks = [
        ("위험자산비중 ≤ %d%%" % lim["risk_max_pct"], risk <= lim["risk_max_pct"], "%.1f%% (분류기반, 포털값 병기 확인)" % risk),
        ("단일펀드 ≤ %d%%" % lim["single_fund_max_pct"], single_max <= lim["single_fund_max_pct"], "%.1f%%" % single_max),
        ("목표배분 밴드 %s" % band_label, len(breaches) == 0, "이탈 %d건 %s" % (len(breaches), breaches[:4])),
        ("펀드 수 %d~%d" % (lim["fund_count_min"], lim["fund_count_max"]),
         lim["fund_count_min"] <= n_funds <= lim["fund_count_max"], "%d개" % n_funds),
        ("가중TER ≤ %.2f%%" % lim["weighted_ter_max_pct"], ter <= lim["weighted_ter_max_pct"], "%.3f%%(총자산)" % ter),
        ("신흥국 합계 ≤ %d%%" % lim["emerging_max_pct"], em <= lim["emerging_max_pct"], "%.1f%%" % em),
    ]
    print("=" * 90)
    print("IPS 컴플라이언스 — 정책 v%s vs %s | 총자산 %s원" % (pol["version"], hpath, format(int(total), ",")))
    n_fail = 0
    out = {"policy_version": pol["version"], "holdings": hpath, "checks": []}
    for name, ok, detail in checks:
        n_fail += (not ok)
        out["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
        print("  [%s] %-24s %s" % ("PASS" if ok else "FAIL", name, detail))
    print("-" * 90)
    print("판정: %d/%d PASS%s" % (len(checks) - n_fail, len(checks),
          "" if n_fail == 0 else " — FAIL은 전환 미완/정책 위반. drift_check.py 괴리표로 조치 계획 수립."))
    print("정책 리마인드: 환헤지=%s" % pol["fx_policy"].split("—")[0].strip())
    print("             리밸=%s" % pol["rebalance_policy"].split("—")[0].strip())
    json.dump(out, open("ips_check_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
