# -*- coding: utf-8 -*-
"""Aggregate v1_top5000.csv in-process and write report (guarantee 5000 rows)."""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

root = Path(r"c:\Users\JHKIM\Patent_Analysis")
script_dir = root / ".codex" / "skills" / "patent-strategy-report" / "scripts"
out_dir = root / ".codex" / "skills" / "patent-strategy-report" / "output"
v1_top5000 = out_dir / "v1_top5000.csv"
rfp = next(root.glob("*RFP*디스플레이*.md"), None) or next(root.glob("*RFP*.md"), None)

sys.path.insert(0, str(script_dir))
from aggregate_csv_report import (
    load_csv,
    aggregate_by_priority_year,
    aggregate_by_publication_year,
    aggregate_applicants,
    aggregate_countries,
    table_priority_by_year,
    table_publication_by_year,
    ascii_bar_years,
    ascii_bar,
)

rows, header = load_csv(str(v1_top5000))
if len(rows) != 5000:
    print("Expected 5000 rows, got", len(rows), file=sys.stderr)
total = len(rows)

by_priority = aggregate_by_priority_year(rows)
by_pub = aggregate_by_publication_year(rows)
applicants = aggregate_applicants(rows, 10)
countries = aggregate_countries(rows)
table_pri_str, table_pri_data = table_priority_by_year(by_priority)
table_pub_str = table_publication_by_year(by_pub)
ascii_priority = ascii_bar_years(by_priority)
ascii_applicants = ascii_bar([(a["name"], a["pct"]) for a in applicants])
ascii_countries = ascii_bar([(c["code"], c["pct"]) for c in countries])
year_min = min(by_priority.keys()) if by_priority else 0
year_max = max(by_priority.keys()) if by_priority else 0
date_range = f"우선일 {year_min}.01.01 ~ {year_max}.12.31"

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
    "report_title": "센서 융합 디스플레이 기술 세계 특허 현황 분석 보고서 (5,000건)",
    "analysis_date": datetime.now().strftime("%Y-%m-%d"),
    "search_query": "(stretchable AND display) AND (디스플레이·센서/변형 개념) [제목-RFP 연관성 상위 5,000건]",
    "search_url": "https://patents.google.com/ (검색식 기반, 15년)",
    "rfp_reference": str(rfp) if rfp else "",
}

json_path = out_dir / "aggregate_report_data.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Aggregate written:", json_path, "TOTAL_COUNT:", total)

report_md = out_dir / "20260307_센서융합디스플레이_5000건_세계특허현황_분석보고서.md"
r = subprocess.run(
    [
        str(script_dir / ".venv" / "Scripts" / "python.exe"),
        str(script_dir / "fill_report.py"),
        str(json_path),
        "-o", str(report_md),
        "--topic", "센서융합디스플레이",
    ],
    cwd=str(root),
)
sys.exit(0 if r.returncode == 0 else r.returncode)
