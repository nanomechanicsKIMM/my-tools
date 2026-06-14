# -*- coding: utf-8 -*-
"""
분배락 식별 신호 검증 — 과표기준가(tax_nav)가 분배 vs 시장하락을 구분하는가?

가설: 분배락일 d에서 기준가(nav)는 분배금만큼 급락하나, 과표기준가의 일일변화는
      시장하락과 다른 패턴 → nav%변화와 tax_nav%변화의 '괴리'가 분배 신호.

검증:
  (A) 알려진 분배락(K55301B43371 12건, 1000근처 명확)에서 nav% vs tax% 비교
  (B) 같은 펀드 비분배 시장하락일(-2%↓, 1000 무관)에서 nav% vs tax% 비교
  (C) 미탐지 의심펀드(K55209CT1721, 분배락0건이나 1년 과소)에서 nav-tax 괴리 큰 날
"""
import csv, json
import pandas as pd
import numpy as np

DIST = json.load(open("adjusted_nav/_distributions.json", encoding="utf-8"))


def load(code):
    rows = [r for r in list(csv.reader(open("nav_history/%s.csv" % code, encoding="utf-8")))[1:]
            if r and r[1] and r[2]]
    d = [r[0] for r in rows]
    nav = np.array([float(r[1]) for r in rows])
    tax = np.array([float(r[2]) for r in rows])
    return d, nav, tax


def daily(arr):
    return arr[1:] / arr[:-1] - 1


def main():
    # ===== (A)+(B) K55301B43371: 분배락일 vs 비분배 급락일 =====
    code = "K55301B43371"
    d, nav, tax = load(code)
    nav_r = daily(nav); tax_r = daily(tax)
    exdates = {e["date"] for e in DIST.get(code, [])}
    idx = {x: i for i, x in enumerate(d)}

    print("=" * 78)
    print("【%s】 분배락일 nav%% vs 과표%% (괴리=nav급락하나 과표는 다름?)" % code)
    print("  %-10s %8s %8s %8s" % ("date", "nav%", "tax%", "괴리|n-t|"))
    ex_gaps = []
    for ed in sorted(exdates):
        i = idx[ed]
        if i == 0: continue
        nr, tr = nav_r[i - 1] * 100, tax_r[i - 1] * 100
        gap = abs(nr - tr)
        ex_gaps.append(gap)
        print("  %-10s %8.2f %8.2f %8.2f" % (ed, nr, tr, gap))

    # 비분배 시장하락일(-2%↓, 분배락 아닌 날)
    print("\n  [비분배 시장하락일 -2%%↓ 샘플8] nav%% vs 과표%%")
    print("  %-10s %8s %8s %8s" % ("date", "nav%", "tax%", "괴리|n-t|"))
    nonex_gaps = []
    shown = 0
    for i in range(len(nav_r)):
        if nav_r[i] <= -0.02 and d[i + 1] not in exdates:
            nr, tr = nav_r[i] * 100, tax_r[i] * 100
            gap = abs(nr - tr)
            nonex_gaps.append(gap)
            if shown < 8:
                print("  %-10s %8.2f %8.2f %8.2f" % (d[i + 1], nr, tr, gap))
                shown += 1
    print("\n  >> 분배락일 괴리 중앙 %.2f%%p | 비분배하락일 괴리 중앙 %.2f%%p" %
          (np.median(ex_gaps) if ex_gaps else 0, np.median(nonex_gaps) if nonex_gaps else 0))
    print("  >> 가설 성립 조건: 분배락 괴리 >> 비분배 괴리")

    # ===== (C) 미탐지 의심: K55209CT1721 =====
    code2 = "K55209CT1721"
    d2, nav2, tax2 = load(code2)
    nav_r2 = daily(nav2); tax_r2 = daily(tax2)
    gap2 = np.abs(nav_r2 - tax_r2) * 100
    order = np.argsort(-gap2)[:10]
    print("\n" + "=" * 78)
    print("【%s】 분배락 0건(미탐지 의심) — nav-과표 괴리 상위10 (=숨은 분배?)" % code2)
    print("  %-10s %8s %8s %8s" % ("date", "nav%", "tax%", "괴리"))
    for i in sorted(order):
        print("  %-10s %8.2f %8.2f %8.2f" % (d2[i + 1], nav_r2[i] * 100, tax_r2[i] * 100, gap2[i]))

    # 전체 괴리 분포(정상일은 괴리~0이어야)
    print("\n  괴리 분포: 중앙 %.3f / p95 %.3f / 최대 %.3f (%%p)" %
          (np.median(gap2), np.percentile(gap2, 95), gap2.max()))


if __name__ == "__main__":
    main()
