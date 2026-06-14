# -*- coding: utf-8 -*-
"""Phase 7: 대시보드용 NAV 데이터(dashboard_data.js) 생성.
핵심 펀드(미국/한국/인도/중국/아세안)의 월말 수정기준가 → portfolio_dashboard.html이
로드하는 JS 데이터(const DATA). 분기 리밸·모멘텀·역변동성 백테스트의 입력.

사용: 작업 폴더(panel_adj_nav.csv 존재)에서 `python extract_dashboard_data.py`
      → dashboard_data.js 생성. portfolio_dashboard.html과 같은 폴더에 두고 로컬 서버로 열기.
"""
import json
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
}
DEPOSIT_RATE = 0.049


def main(panel="panel_adj_nav.csv", out="dashboard_data.js"):
    nav = pd.read_csv(panel, index_col=0, parse_dates=True)
    monthly = nav.resample("ME").last()
    codes = [v[0] for v in FUNDS.values()]
    sub = monthly[codes].dropna()          # 전 펀드 공통 5년 구간
    dates = [d.strftime("%Y-%m") for d in sub.index]
    deposit = [round(1000 * (1 + DEPOSIT_RATE) ** (i / 12.0), 2) for i in range(len(sub))]
    funds = {k: {"code": c, "name": nm, "cls": cls,
                 "nav": [round(x, 2) for x in sub[c].tolist()]}
             for k, (c, nm, cls) in FUNDS.items()}
    payload = {"dates": dates, "funds": funds, "deposit": deposit}
    with open(out, "w", encoding="utf-8") as f:
        f.write("const DATA = " + json.dumps(payload, ensure_ascii=False) + ";")
    print("생성: %s (%d개월 %s~%s, %d펀드+예금)" % (out, len(dates), dates[0], dates[-1], len(funds)))


if __name__ == "__main__":
    main()
