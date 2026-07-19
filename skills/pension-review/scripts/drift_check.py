# -*- coding: utf-8 -*-
"""
보유내역 vs DC 한도·목표배분 드리프트 점검.
입력: status/holdings_YYYYMMDD.json (기본: status/ 최신)
  {"asof": "YYYY-MM-DD",
   "holdings": [{"name": "...", "code": "K5...|DEPOSIT|CASH", "value": 12345, "kind": "fund|deposit|cash"}]}
목표(선택): --targets JSON 경로 {"코드 또는 DEPOSIT": 비중%}
출력: 비중표 · 위험자산비중(fund_classification 기반) · 한도판정(위험≤70/단일≤40) · 목표 대비 괴리
괴리 플래그 = 5/25 규칙(Daryanani 2008·Swedroe): 임계 = min(절대 5%p, 목표×25%), 하한 0.5%p.
  절대 ±5%p 단독은 소액 위성(골드7/인도4%)에 트리거 불능 — 상대밴드로 보완. --band-pp/--band-rel로 조정.
주의: 분류 기반 위험비중은 포털 공시치와 다를 수 있음(TDF 혼합형 처리 차이) — 병기 확인.
"""
import argparse, glob, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("--holdings", default=None)
ap.add_argument("--targets", default=None)
ap.add_argument("--band-pp", type=float, default=5.0, help="절대 밴드 %%p (5/25의 5)")
ap.add_argument("--band-rel", type=float, default=0.25, help="상대 밴드 비율 (5/25의 25%%)")
a = ap.parse_args()

path = a.holdings or max(glob.glob("status/holdings_*.json"),
                         key=lambda p: re.search(r"(20\d{6})", p).group(1))
data = json.load(open(path, encoding="utf-8"))
hs = data["holdings"]
total = sum(h["value"] for h in hs)

fd = json.load(open("funds/fund_data.json", encoding="utf-8"))["funds"]
code2name = {f["fundCode"]: f["name"] for f in fd}
cls = json.load(open("funds/fund_classification.json", encoding="utf-8"))

print("보유내역 드리프트 점검 | asof=%s | 총평가액 %s원" % (data.get("asof"), format(total, ",")))
print("-" * 100)
risk = 0.0
max_single = ("", 0.0)
rows = []
for h in hs:
    w = h["value"] / total * 100
    kind = h.get("kind", "fund")
    if kind in ("deposit", "cash"):
        is_risk = False
        cat = kind
    else:
        uname = code2name.get(h["code"])
        info = cls.get(uname, {}) if uname else {}
        is_risk = bool(info.get("riskAsset", True))   # 미매칭 시 보수적으로 위험 처리
        cat = info.get("category", "미분류")
        if w > max_single[1]:
            max_single = (h["name"], w)
    if is_risk:
        risk += w
    rows.append((h["name"][:38], w, cat, "위험" if is_risk else "안전"))
for n, w, c, r in sorted(rows, key=lambda x: -x[1]):
    print("%-40s %6.2f%%  %-8s %s" % (n, w, r, c))
print("-" * 100)
print("위험자산비중(분류기반): %.2f%%  (한도 70%% → %s)" % (risk, "PASS" if risk <= 70 else "**초과**"))
etc_safe = sum(w for _, w, c, r in rows if c == "기타" and r == "안전")
if etc_safe > 0:
    print("⚠ '기타' 분류 %.2f%%p가 안전으로 집계됨(골드·TDF 등) — 포털 공시 위험비중과 차이 가능. 포털값 병기 확인 필수." % etc_safe)
print("단일펀드최대: %.2f%% [%s]  (한도 40%% → %s)" %
      (max_single[1], max_single[0], "PASS" if max_single[1] <= 40 else "**초과**"))

if a.targets:
    tg = json.load(open(a.targets, encoding="utf-8"))
    cur = {}
    for h in hs:
        key = h["code"] if h.get("kind", "fund") == "fund" else h["code"]
        cur[key] = cur.get(key, 0) + h["value"] / total * 100
    print("\n목표 대비 괴리 (양수=초과보유, 밴드=5/25 규칙 min(±%.0f%%p, 목표×%.0f%%)):" % (a.band_pp, a.band_rel * 100))
    keys = sorted(set(cur) | set(tg), key=lambda k: -(cur.get(k, 0)))
    for k in keys:
        c, t = cur.get(k, 0.0), float(tg.get(k, 0.0))
        nm = code2name.get(k, k)[:36]
        thr = max(min(a.band_pp, a.band_rel * t), 0.5)
        flag = " ←밴드이탈(±%.1f%%p)" % thr if abs(c - t) > thr else ""
        print("  %-38s 현재 %6.2f%% / 목표 %6.2f%% / 괴리 %+6.2f%%p%s" % (nm, c, t, c - t, flag))
