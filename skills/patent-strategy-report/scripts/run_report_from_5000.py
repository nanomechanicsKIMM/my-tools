# -*- coding: utf-8 -*-
"""Run aggregate + fill_report for v1_top5000 to produce final patent strategy report."""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

root = Path(r"c:\Users\JHKIM\Patent_Analysis")
script_dir = root / ".codex" / "skills" / "patent-strategy-report" / "scripts"
out_dir = root / ".codex" / "skills" / "patent-strategy-report" / "output"

v1_top5000 = out_dir / "v1_top5000.csv"
rfp = next(root.glob("*RFP*디스플레이*.md"), None) or next(root.glob("*RFP*.md"), None)

if not v1_top5000.exists():
    print("v1_top5000.csv not found:", v1_top5000, file=sys.stderr)
    sys.exit(1)
if not rfp or not rfp.exists():
    print("RFP not found", file=sys.stderr)
    sys.exit(1)

search_query = "(stretchable AND display) AND (sensor OR sensing OR deformation OR ...) [제목-RFP 연관성 상위 5,000건]"
search_url = "https://patents.google.com/ (검색식 기반, 15년)"

# 1) aggregate_csv_report
r1 = subprocess.run(
    [
        str(script_dir / ".venv" / "Scripts" / "python.exe"),
        str(script_dir / "aggregate_csv_report.py"),
        str(v1_top5000),
        "-o", str(out_dir),
        "--report-title", "센서 융합 디스플레이 기술 세계 특허 현황 분석 보고서 (5,000건)",
        "--search-query", search_query,
        "--search-url", search_url,
        "--rfp-path", str(rfp),
    ],
    cwd=str(root),
)
if r1.returncode != 0:
    sys.exit(r1.returncode)

# 2) fill_report
report_md = out_dir / f"{datetime.now().strftime('%Y%m%d')}_센서융합디스플레이_5000건_세계특허현황_분석보고서.md"
r2 = subprocess.run(
    [
        str(script_dir / ".venv" / "Scripts" / "python.exe"),
        str(script_dir / "fill_report.py"),
        str(out_dir / "aggregate_report_data.json"),
        "-o", str(report_md),
        "--topic", "센서융합디스플레이",
    ],
    cwd=str(root),
)
if r2.returncode != 0:
    sys.exit(r2.returncode)

print("Report written:", report_md)
