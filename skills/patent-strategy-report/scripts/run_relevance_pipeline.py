# -*- coding: utf-8 -*-
"""
Relevance-based pipeline (replaces noise-filter loop):

1. Score all rows by title–RFP relevance (include/exclude term weights).
2. Save top 10,000 by title score -> statistics file for report.
3. Extract top 100 by title score -> fetch abstracts -> add abstract column.
4. Score those 100 by abstract–RFP relevance (same weights).
5. Save top 10 by abstract score as core patents (핵심특허_상위10건_목록.csv).
6. Aggregate 10k for report statistics; fill report; report can link to core analysis.

Usage:
  python run_relevance_pipeline.py <v1_csv> <rfp_path> -o <output_dir>
  python run_relevance_pipeline.py v1.csv rfp.md -o output --include-terms "sensor,display" --exclude-terms "OLED,LCD"
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_OUT = SKILL_ROOT / "output"


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    start = 0
    if lines and lines[0].strip().lower().startswith("search url"):
        start = 1
    if start >= len(lines):
        return [], []
    header = next(csv.reader([lines[start]]))
    rows = list(csv.DictReader(lines[start + 1 :], fieldnames=header))
    return rows, header


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Relevance pipeline: title score -> 10k stats, top 100 -> abstracts -> abstract score -> top 10 core")
    ap.add_argument("v1_csv", help="Input CSV from Google Patents (v1)")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("-o", "--output-dir", type=str, default=None, help=f"Output directory (default: {DEFAULT_OUT})")
    ap.add_argument("--include-terms", type=str, default=None, help="Comma-separated must-include terms (e.g. sensor,display)")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Comma-separated must-exclude terms (e.g. OLED,LCD)")
    ap.add_argument("--include-weight", type=float, default=0.2, help="Score per include term in title/abstract")
    ap.add_argument("--exclude-weight", type=float, default=0.5, help="Score subtracted per exclude term")
    ap.add_argument("--topic", type=str, default="특허", help="Topic for report title (e.g. 센서융합디스플레이)")
    ap.add_argument("--report-title", type=str, default=None, help="Full report title (overrides --topic)")
    ap.add_argument("--skip-fetch", action="store_true", help="Skip fetch_abstracts (use existing abstract column)")
    ap.add_argument("--fetch-delay", type=float, default=1.0, help="Delay between abstract requests (seconds)")
    args = ap.parse_args()

    out_dir = Path(args.output_dir or DEFAULT_OUT)
    v1_csv = Path(args.v1_csv)
    rfp_path = Path(args.rfp_path)
    if not v1_csv.exists():
        print(f"Input CSV not found: {v1_csv}", file=sys.stderr)
        sys.exit(1)
    if not rfp_path.exists():
        print(f"RFP not found: {rfp_path}", file=sys.stderr)
        sys.exit(1)

    venv_py = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        venv_py = Path(sys.executable)

    include_terms = [t.strip() for t in (args.include_terms or "").split(",") if t.strip()]
    exclude_terms = [t.strip() for t in (args.exclude_terms or "").split(",") if t.strip()]

    v1_top10k = out_dir / "v1_top10000.csv"
    top100_for_abstracts = out_dir / "top100_for_abstracts.csv"
    top100_with_abstracts = out_dir / "top100_with_abstracts.csv"
    top100_abstract_scored = out_dir / "top100_abstract_scored.csv"
    core10_path = out_dir / "핵심특허_상위10건_목록.csv"

    # Step 1: Title relevance score -> top 10,000 (for statistics)
    sys.path.insert(0, str(SCRIPT_DIR))
    from score_title_relevance import run as run_title_score
    run_title_score(
        str(v1_csv),
        str(rfp_path),
        str(v1_top10k),
        top_n=10000,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        include_weight=args.include_weight,
        exclude_weight=args.exclude_weight,
    )
    print("Step 1: Wrote v1_top10000.csv (top 10,000 by title relevance)")

    # Step 2: Extract top 100 for abstracts
    rows_10k, header = load_csv(v1_top10k)
    if len(rows_10k) < 100:
        print("Warning: fewer than 100 rows in 10k file; using all.", file=sys.stderr)
    top100_rows = rows_10k[:100]
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(top100_for_abstracts, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(top100_rows)
    print("Step 2: Wrote top100_for_abstracts.csv")

    # Step 3: Fetch abstracts (unless --skip-fetch)
    if not args.skip_fetch:
        r = subprocess.run(
            [
                str(venv_py),
                str(SCRIPT_DIR / "fetch_abstracts.py"),
                str(top100_for_abstracts),
                "-o", str(top100_with_abstracts),
                "--delay", str(args.fetch_delay),
            ],
            cwd=str(v1_csv.resolve().parent),
        )
        if r.returncode != 0:
            print("fetch_abstracts failed", file=sys.stderr)
            sys.exit(r.returncode)
        print("Step 3: Wrote top100_with_abstracts.csv")
    else:
        import shutil
        if not Path(top100_with_abstracts).exists():
            shutil.copy(top100_for_abstracts, top100_with_abstracts)
            print("Step 3: Copied top100_for_abstracts to top100_with_abstracts (--skip-fetch)")
        else:
            print("Step 3: Using existing top100_with_abstracts.csv")

    # Step 4: Abstract+representative_claim relevance score (5:5) -> top 100 scored
    from score_abstract_relevance import run as run_abstract_score
    run_abstract_score(
        str(top100_with_abstracts),
        str(rfp_path),
        str(top100_abstract_scored),
        top_n=100,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        include_weight=args.include_weight,
        exclude_weight=args.exclude_weight,
    )
    print("Step 4: Wrote top100_abstract_scored.csv (abstract+claim 5:5 relevance)")

    # Step 5: Top 10 by abstract score -> core patents
    scored_rows, _ = load_csv(top100_abstract_scored)
    scored_sorted = sorted(scored_rows, key=lambda r: float(r.get("relevance_score", 0)), reverse=True)
    core10 = scored_sorted[:10]
    if core10:
        h = list(core10[0].keys())
        with open(core10_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=h, extrasaction="ignore")
            w.writeheader()
            w.writerows(core10)
        print("Step 5: Wrote 핵심특허_상위10건_목록.csv")

    # Step 6: Aggregate 10k and fill report
    from aggregate_csv_report import (
        load_csv as load_csv_fn,
        aggregate_by_priority_year,
        aggregate_by_publication_year,
        aggregate_applicants,
        aggregate_countries_for_report,
        table_priority_by_year,
        table_publication_by_year,
        ascii_bar_years,
        ascii_bar,
    )
    rows, _ = load_csv_fn(str(v1_top10k))
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

    report_title = args.report_title or f"{args.topic} 세계 특허 현황 분석 보고서 (10,000건)"
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
        "rfp_reference": str(rfp_path),
    }
    json_path = out_dir / "aggregate_report_data_10k.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Aggregate written:", json_path)

    report_md = out_dir / f"{args.topic}_세계특허현황_분석보고서.md"
    r = subprocess.run(
        [
            str(venv_py),
            str(SCRIPT_DIR / "fill_report.py"),
            str(json_path),
            "-o", str(report_md),
            "--topic", args.topic,
        ],
        cwd=str(v1_csv.resolve().parent),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("Step 6: Report written:", report_md)

    # Link to core patent analysis in report placeholder
    related_docs = f"[핵심특허_상위10건_분석.md](핵심특허_상위10건_분석.md) (대표청구항·공백기술·OS matrix·특허 창출 전략)."
    report_path = Path(report_md)
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        if "{{RELATED_DOCS}}" in text:
            text = text.replace("{{RELATED_DOCS}}", related_docs)
            report_path.write_text(text, encoding="utf-8")

    print("Done. Core patent analysis can be run separately on 핵심특허_상위10건_목록.csv -> 핵심특허_상위10건_분석.md")


if __name__ == "__main__":
    main()
