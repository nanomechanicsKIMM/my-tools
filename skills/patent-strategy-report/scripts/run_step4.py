# -*- coding: utf-8 -*-
"""
Step 4: 집계·보고서 생성만 실행.
v1_top10000.csv 기준으로 연도/출원인/국가 집계 후 보고서 템플릿 채움.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
OUT_DIR = SKILL_ROOT / "output"
TOP10K_CSV = OUT_DIR / "v1_top10000.csv"
RFP_PATH = Path(r"c:\Users\JHKIM\Patent_Analysis\(2026)_RFP_센서_융합_디스플레이_기술.md")
TOPIC = "센서융합디스플레이"

def main():
    if not TOP10K_CSV.exists():
        print(f"v1_top10000.csv not found: {TOP10K_CSV}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(SCRIPT_DIR))
    from aggregate_csv_report import (
        load_csv,
        aggregate_by_priority_year,
        aggregate_by_publication_year,
        aggregate_applicants,
        aggregate_countries_for_report,
        table_priority_by_year,
        table_publication_by_year,
        ascii_bar_years,
        ascii_bar,
    )
    from datetime import datetime

    rows, _ = load_csv(str(TOP10K_CSV))
    total = len(rows)
    by_priority = aggregate_by_priority_year(rows)
    by_pub = aggregate_by_publication_year(rows)
    applicants = aggregate_applicants(rows, 10)
    countries = aggregate_countries_for_report(rows)
    table_pri_str, table_pri_data = table_priority_by_year(by_priority)
    table_pub_str = table_publication_by_year(by_pub)
    ascii_priority = ascii_bar_years(by_priority)
    ascii_applicants = ascii_bar([(a["name"], a["pct"]) for a in applicants])
    ascii_countries = ascii_bar([(c.get("name_ko", c["code"]), c["pct"]) for c in countries])
    year_min = min(by_priority.keys()) if by_priority else 0
    year_max = max(by_priority.keys()) if by_priority else 0
    date_range = f"우선일 {year_min}.01.01 ~ {year_max}.12.31"

    report_title = f"{TOPIC} 세계 특허 현황 분석 보고서 (10,000건)"
    out = {
        "total_count": total,
        "date_range": date_range,
        "table_priority_by_year": table_pri_str,
        "table_priority_data": table_pri_data,
        "table_publication_by_year": table_pub_str,
        "ascii_chart_priority": ascii_priority,
        "ascii_chart_applicants": ascii_applicants,
        "ascii_chart_country": ascii_countries,
        "top_applicants": applicants,
        "countries": countries,
        "report_title": report_title,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "search_query": "제목-RFP 상관성 점수(포함/제외 가중치) 상위 10,000건",
        "search_url": "https://patents.google.com/",
        "rfp_reference": str(RFP_PATH),
    }
    json_path = OUT_DIR / "aggregate_report_data_10k.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Aggregate written:", json_path)

    report_md = OUT_DIR / f"{TOPIC}_세계특허현황_분석보고서.md"
    venv_py = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        venv_py = Path(sys.executable)
    r = subprocess.run(
        [
            str(venv_py),
            str(SCRIPT_DIR / "fill_report.py"),
            str(json_path),
            "-o", str(report_md),
            "--topic", TOPIC,
        ],
        cwd=str(SCRIPT_DIR),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("Report written:", report_md)

if __name__ == "__main__":
    main()
