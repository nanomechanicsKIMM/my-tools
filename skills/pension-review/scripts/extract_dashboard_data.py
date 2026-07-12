# -*- coding: utf-8 -*-
"""Phase 7: 대시보드용 NAV 데이터(dashboard_data.js) 생성.
핵심 펀드(미국/한국/인도/중국/아세안/골드)의 월말 수정기준가 → portfolio_dashboard.html이
로드하는 JS 데이터(const DATA). 분기 리밸·모멘텀·역변동성 백테스트의 입력.
분석 요약(라이프사이클·실질·비용·IPS 결과 JSON이 있으면)을 DATA.summary로 임베드.

사용: 작업 폴더(panel_adj_nav.csv 존재)에서 `python scripts/extract_dashboard_data.py`
      → dashboard/dashboard_data.js 생성. portfolio_dashboard.html과 같은 폴더에서 로컬 서버로 열기.
"""
import datetime
import glob
import json
import os
import re
import pandas as pd

# 대시보드 핵심 펀드 (5년 데이터 proxy). 필요 시 코드 교체.
FUNDS = {
    "sp500":  ("K55105BA7360", "미국 S&P500", "미국"),
    "nasdaq": ("K55301B51580", "미국 나스닥100", "미국"),
    "sox":    ("K55307D05993", "미국 필라델피아반도체", "미국"),
    "kospi":  ("K55105BU5980", "한국 KOSPI200", "한국"),
    "div":    ("K55209CT1721", "한국 신영밸류고배당", "한국"),
    "india":  ("K55301B25428", "인도 인프라", "인도"),
    "china":  ("K55223BV4542", "중국 (과창판)", "중국"),
    "asean":  ("K55105BD5817", "아세안", "아세안"),
    "gold":   ("K55366BU9572", "골드(월드골드 UH)", "골드"),
}
DEPOSIT_RATE = 0.049


# 보유 표준코드 → 대시보드 키 (동일 자산군 proxy 포함)
CODE2KEY = {
    "K55105BA7360": "sp500", "K55210DT4606": "sp500",     # 삼성/신한 S&P500
    "K55301B51580": "nasdaq", "K55301E64355": "nasdaq",   # 블루칩proxy/나스닥100
    "K55307D05993": "sox",
    "K55105BU5980": "kospi",
    "K55209CT1721": "div",
    "K55301B25428": "india",
    "K55223BV4542": "china", "K55301DD9983": "china",     # 본토A/과창판 proxy
    "K55105BD5817": "asean",
    "K55366BU9572": "gold", "K55366BU9754": "gold",       # UH/H
}


def load_holdings():
    """status/holdings_*.json 최신본 → 대시보드 키별 보유액(byKey)·미매핑 목록(other)."""
    files = glob.glob("status/holdings_*.json")
    if not files:
        return None
    path = max(files, key=lambda p: re.search(r"(20\d{6})", p).group(1))
    hd = json.load(open(path, encoding="utf-8"))
    by_key, other, total = {}, [], 0
    for h in hd["holdings"]:
        v = h["value"]
        total += v
        if h.get("kind", "fund") != "fund":
            by_key["deposit"] = by_key.get("deposit", 0) + v
        elif h["code"] in CODE2KEY:
            k = CODE2KEY[h["code"]]
            by_key[k] = by_key.get(k, 0) + v
        else:
            other.append({"name": h["name"], "value": v})
    return {"asof": hd.get("asof"), "total": total, "byKey": by_key, "other": other}


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


# 대시보드 키 → 실제 매수/매도 대상 펀드(추천·B안 기준). 미기재 키는 데이터 펀드 = 매매 펀드.
TRADE_OVERRIDE = {
    "sp500": "K55210DT4606",    # 신한미국S&P500인덱스(UH) — 데이터는 삼성 proxy
    "nasdaq": "K55301E64355",   # 미래에셋미국나스닥100인덱스(UH) — 데이터는 블루칩 proxy
    "china": "K55301DD9983",    # 미래에셋차이나과창판(보유·B안) — 데이터는 본토A proxy
}


def main(panel="panel_adj_nav.csv", out="dashboard/dashboard_data.js"):
    nav = pd.read_csv(panel, index_col=0, parse_dates=True)
    monthly = nav.resample("ME").last()
    codes = [v[0] for v in FUNDS.values()]
    sub = monthly[codes].dropna()          # 전 펀드 공통 5년 구간
    dates = [d.strftime("%Y-%m") for d in sub.index]
    deposit = [round(1000 * (1 + DEPOSIT_RATE) ** (i / 12.0), 2) for i in range(len(sub))]
    official = {f["fundCode"]: f["name"]
                for f in json.load(open("funds/fund_data.json", encoding="utf-8"))["funds"]}
    funds = {}
    for k, (c, nm, cls) in FUNDS.items():
        tc = TRADE_OVERRIDE.get(k, c)
        funds[k] = {"code": c, "name": nm, "cls": cls,
                    "official": official.get(c, ""),               # 백테스트 데이터 펀드 정식명
                    "trade": {"code": tc, "name": official.get(tc, "")},  # 실제 매매 대상 정식명
                    "proxy": tc != c,
                    "nav": [round(x, 2) for x in sub[c].tolist()]}
    payload = {"dates": dates, "funds": funds, "deposit": deposit,
               "summary": analysis_summary(), "holdings": load_holdings()}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("const DATA = " + json.dumps(payload, ensure_ascii=False) + ";")
    print("생성: %s (%d개월 %s~%s, %d펀드+예금, summary %d항목)"
          % (out, len(dates), dates[0], dates[-1], len(funds), len(payload["summary"])))


if __name__ == "__main__":
    main()
