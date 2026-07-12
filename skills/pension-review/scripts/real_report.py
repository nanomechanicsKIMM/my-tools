# -*- coding: utf-8 -*-
"""
P1-2 실질(인플레 조정) 수익 리포트 — 명목/실질 병기 의무화.

동기: 장기(30년+) 지평에서 인플레 2~4%는 MDD보다 큰 구매력 파괴 변수인데
      기존 산출물은 전부 명목 기준. 특히 예금 슬리브(35%)의 실질수익이 가려짐.

입력: mc_results.json(부트스트랩 경로별 명목 CAGR 분포), funds/deposit_rates.json(예금금리)
산출: 시나리오 π=2/3/4%별 전략 실질 CAGR 분포(중앙[5,95]) + 예금 실질수익 +
      구매력 침식표(10/20/30년) → real_report.json
공식: 실질 = (1+명목)/(1+π) − 1 (근사 아닌 정확식)

사용(작업폴더 루트): python scripts/real_report.py [--inflation 0.02,0.03,0.04] [--deposit 0.049]
"""
import argparse, json
import numpy as np


def deposit_rate(cli):
    if cli is not None:
        return cli, "CLI"
    try:
        d = json.load(open("funds/deposit_rates.json", encoding="utf-8"))
        r = d["rates"][0]
        for k in ("rate", "interestRate", "annualRate"):
            if k in r:
                v = float(r[k])
                v = v / 100 if v > 1 else v
                return v, "deposit_rates.json(%s, %s)" % (r.get("productName", "?"), d["_meta"]["version"])
    except Exception:
        pass
    return 0.049, "기본값"


def real(nom, pi):
    return (1 + nom) / (1 + pi) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inflation", default="0.02,0.03,0.04")
    ap.add_argument("--deposit", type=float, default=None)
    a = ap.parse_args()
    pis = [float(x) for x in a.inflation.split(",")]
    dep, dep_src = deposit_rate(a.deposit)

    mc = json.load(open("mc_results.json", encoding="utf-8"))
    print("=" * 100)
    print("실질(인플레 조정) 수익 리포트 — 부트스트랩 경로 분포 기반 | 예금 %.2f%% (%s) | 투자 권유 아님" % (dep * 100, dep_src))
    print("공식: 실질 = (1+명목)/(1+π)-1. MDD는 명목 기준(단기 드로다운은 실질≈명목, 장기 침식은 아래 구매력표 참조).")
    out = {"deposit_nominal": dep, "deposit_source": dep_src, "scenarios": {}}
    for pi in pis:
        print("\n[π = %.0f%%]  전략별 실질 CAGR%%  (부트스트랩 300경로: 중앙 [5%%ile, 95%%ile])" % (pi * 100))
        sc = {"deposit_real": real(dep, pi)}
        for strat, m in mc.items():
            arr = np.array(m["CAGR%"]) / 100.0
            r = real(arr, pi) * 100
            q5, q50, q95 = np.percentile(r, [5, 50, 95])
            neg = float((r < 0).mean())
            sc[strat] = {"real_cagr_med": round(float(q50), 2), "p5": round(float(q5), 2),
                         "p95": round(float(q95), 2), "p_negative_real": round(neg, 3)}
            print("  %-12s %6.1f [%6.1f, %6.1f]   P(실질<0)=%3.0f%%" % (strat, q50, q5, q95, neg * 100))
        print("  %-12s %6.1f  ← 예금 100%% 실질수익 (명목 %.1f%%)" % ("예금", sc["deposit_real"] * 100, dep * 100))
        out["scenarios"]["%.0f%%" % (pi * 100)] = sc
    print("\n[구매력 침식]  오늘 100의 실질가치 (예금 100% 보유 시)")
    print("  %-6s %8s %8s %8s" % ("π", "10년", "20년", "30년"))
    pp = {}
    for pi in pis:
        row = [100 * ((1 + real(dep, pi)) ** y) for y in (10, 20, 30)]
        pp["%.0f%%" % (pi * 100)] = [round(v, 1) for v in row]
        print("  %-6s %8.1f %8.1f %8.1f" % ("%.0f%%" % (pi * 100), *row))
    out["deposit_purchasing_power"] = pp
    json.dump(out, open("real_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: real_report.json  |  분기 보고서에 명목/실질 병기 의무(§15).")


if __name__ == "__main__":
    main()
