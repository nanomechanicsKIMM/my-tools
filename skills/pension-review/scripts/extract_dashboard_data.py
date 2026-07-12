# -*- coding: utf-8 -*-
"""Phase 7: 대시보드용 NAV 데이터(dashboard_data.js) 생성.
핵심 펀드(미국/한국/인도/중국/아세안/골드)의 월말 수정기준가 → portfolio_dashboard.html이
로드하는 JS 데이터(const DATA). 분기 리밸·모멘텀·역변동성 백테스트의 입력.
분석 요약(라이프사이클·실질·비용·IPS 결과 JSON이 있으면)을 DATA.summary로 임베드.

사용: 작업 폴더(panel_adj_nav.csv 존재)에서 `python scripts/extract_dashboard_data.py`
      → dashboard/dashboard_data.js 생성. portfolio_dashboard.html과 같은 폴더에서 로컬 서버로 열기.
"""
import datetime
import json
import os
import pandas as pd

# 대시보드 핵심 펀드 (5년 데이터 proxy). 필요 시 코드 교체.
FUNDS = {
    "sp500":  ("K55105BA7360", "미국 S&P500", "미국"),
    "nasdaq": ("K55301B51580", "미국 나스닥(블루칩)", "미국"),
    "sox":    ("K55307D05993", "미국 필라델피아반도체", "미국"),
    "kospi":  ("K55105BU5980", "한국 KOSPI200", "한국"),
    "div":    ("K55209CT1721", "한국 신영밸류고배당", "한국"),
    "india":  ("K55301B25428", "인도 인프라", "인도"),
    "china":  ("K55223BV4542", "중국 본토A주", "중국"),
    "asean":  ("K55105BD5817", "아세안", "아세안"),
    "gold":   ("K55366BU9572", "골드(월드골드 UH)", "골드"),
}
DEPOSIT_RATE = 0.049


def analysis_summary():
    """P1~P3 산출 JSON이 작업폴더에 있으면 요약 카드 데이터 구성(없으면 항목 생략)."""
    s = {"generated": datetime.date.today().isoformat()}
    try:
        lc = json.load(open("lifecycle_results.json", encoding="utf-8"))
        s["safe_spend_us2003"] = round(lc["safe_spend"]["us2003_fixed65"])
        for g in lc["grid"]:
            if (g["base"], g["policy"], g["inflation"], g["spend"]) == ("us2003", "fixed65", 0.03, 2500000.0):
                s["ruin_250_us2003"] = g["ruin"]
    except Exception:
        pass
    try:
        rr = json.load(open("real_report.json", encoding="utf-8"))
        s["real_cagr_rec_pi3"] = rr["scenarios"]["3%"]["추천65/35"]["real_cagr_med"]
        s["p_neg_real_rec_pi3"] = rr["scenarios"]["3%"]["추천65/35"]["p_negative_real"]
    except Exception:
        pass
    try:
        fd = json.load(open("fee_drag.json", encoding="utf-8"))
        for k, v in fd["ports"].items():
            tag = "ter_current" if k.startswith("현재") else "ter_target"
            s[tag] = v["weighted_ter_pct"]
    except Exception:
        pass
    try:
        ic = json.load(open("ips_check_results.json", encoding="utf-8"))
        s["ips_pass"] = sum(1 for c in ic["checks"] if c["pass"])
        s["ips_total"] = len(ic["checks"])
    except Exception:
        pass
    return s


def main(panel="panel_adj_nav.csv", out="dashboard/dashboard_data.js"):
    nav = pd.read_csv(panel, index_col=0, parse_dates=True)
    monthly = nav.resample("ME").last()
    codes = [v[0] for v in FUNDS.values()]
    sub = monthly[codes].dropna()          # 전 펀드 공통 5년 구간
    dates = [d.strftime("%Y-%m") for d in sub.index]
    deposit = [round(1000 * (1 + DEPOSIT_RATE) ** (i / 12.0), 2) for i in range(len(sub))]
    funds = {k: {"code": c, "name": nm, "cls": cls,
                 "nav": [round(x, 2) for x in sub[c].tolist()]}
             for k, (c, nm, cls) in FUNDS.items()}
    payload = {"dates": dates, "funds": funds, "deposit": deposit, "summary": analysis_summary()}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("const DATA = " + json.dumps(payload, ensure_ascii=False) + ";")
    print("생성: %s (%d개월 %s~%s, %d펀드+예금, summary %d항목)"
          % (out, len(dates), dates[0], dates[-1], len(funds), len(payload["summary"])))


if __name__ == "__main__":
    main()
