# -*- coding: utf-8 -*-
"""
Pipeline: v1 -> 10k (title-RFP) -> top 500 -> fetch abstracts -> 500 abstract-scored.
Then: 10k aggregate/report; top 10 core patents list.
Paths resolved in-process to avoid encoding issues.
"""
import csv
import subprocess
import sys
from pathlib import Path

root = Path(r"c:\Users\JHKIM\Patent_Analysis")
script_dir = root / ".codex" / "skills" / "patent-strategy-report" / "scripts"
out_dir = root / ".codex" / "skills" / "patent-strategy-report" / "output"
v1_csv = root / "gp-search-20260306_v1.csv"
rfp = next(root.glob("*RFP*디스플레이*.md"), None) or next(root.glob("*RFP*.md"), None)
v1_top10k = out_dir / "v1_top10000.csv"
top500_for_abstracts = out_dir / "top500_for_abstracts.csv"
top500_with_abstracts = out_dir / "top500_with_abstracts.csv"
top500_abstract_scored = out_dir / "top500_abstract_scored.csv"
venv_py = script_dir / ".venv" / "Scripts" / "python.exe"


def load_csv(path: Path):
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
    if not rfp or not rfp.exists():
        print("RFP not found", file=sys.stderr)
        sys.exit(1)

    # Step 1: Ensure 10k with relevance_score (from v1). Exclude OLED/LCD in title per RFP scope.
    if not v1_top10k.exists() and v1_csv.exists():
        sys.path.insert(0, str(script_dir))
        from filter_title_top_n import run_filter
        run_filter(str(v1_csv), str(rfp), str(v1_top10k), 10000, exclude_keywords=["OLED", "LCD"])
        print("Wrote v1_top10000.csv (exclude_keywords=OLED,LCD)")
    else:
        print("Using existing v1_top10000.csv")

    # Step 2: Extract top 500 rows -> top500_for_abstracts.csv
    rows_10k, header = load_csv(v1_top10k)
    if len(rows_10k) < 500:
        print("10k CSV has fewer than 500 rows", file=sys.stderr)
        sys.exit(1)
    top500_rows = rows_10k[:500]
    with open(top500_for_abstracts, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(top500_rows)
    print("Wrote top500_for_abstracts.csv (500 rows)")

    # Step 3: Fetch abstracts for 500 -> top500_with_abstracts.csv
    r = subprocess.run(
        [
            str(venv_py),
            str(script_dir / "fetch_abstracts.py"),
            str(top500_for_abstracts),
            "-o", str(top500_with_abstracts),
            "--delay", "1.0",
        ],
        cwd=str(root),
    )
    if r.returncode != 0:
        print("fetch_abstracts failed", file=sys.stderr)
        sys.exit(r.returncode)
    print("Wrote top500_with_abstracts.csv")

    # Step 4: Abstract–RFP relevance score on 500 -> top500_abstract_scored.csv
    r = subprocess.run(
        [
            str(venv_py),
            str(script_dir / "filter_abstract_top_n.py"),
            str(top500_with_abstracts),
            str(rfp),
            "-o", str(top500_abstract_scored),
            "--top", "500",
        ],
        cwd=str(root),
    )
    if r.returncode != 0:
        print("filter_abstract_top_n failed", file=sys.stderr)
        sys.exit(r.returncode)
    print("Wrote top500_abstract_scored.csv (relevance_score updated by abstract–RFP)")

    # Step 5: Aggregate 10k and fill report
    sys.path.insert(0, str(script_dir))
    import json
    from datetime import datetime
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
        "report_title": "센서 융합 디스플레이 기술 세계 특허 현황 분석 보고서 (10,000건)",
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "search_query": "제목-RFP 연관성 상위 10,000건",
        "search_url": "https://patents.google.com/",
        "rfp_reference": str(rfp),
    }
    json_path = out_dir / "aggregate_report_data_10k.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Aggregate written:", json_path)
    r = subprocess.run(
        [str(venv_py), str(script_dir / "fill_report.py"), str(json_path),
         "-o", str(out_dir / "20260307_센서융합디스플레이_10000건_세계특허현황_분석보고서.md"),
         "--topic", "센서융합디스플레이"],
        cwd=str(root),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("Report (10k) written.")

    # Step 6: Top 10 core patents list (exclude OLED/LCD in title or abstract)
    EXCLUDE_CORE = ["OLED", "LCD"]

    def _contains_excluded(row, keywords):
        title = (row.get("title") or "").upper()
        abstract = (row.get("abstract") or "").upper()
        for kw in keywords:
            if kw.upper() in title or kw.upper() in abstract:
                return True
        return False

    scored_rows, _ = load_csv(top500_abstract_scored)
    scored_rows_sorted = sorted(scored_rows, key=lambda r: float(r.get("relevance_score", 0)), reverse=True)
    core_candidates = [r for r in scored_rows_sorted if not _contains_excluded(r, EXCLUDE_CORE)]
    core10 = core_candidates[:10]
    core_path = out_dir / "핵심특허_상위10건_목록.csv"
    if core10:
        h = list(core10[0].keys())
        with open(core_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=h, extrasaction="ignore")
            w.writeheader()
            w.writerows(core10)
        print("Wrote 핵심특허_상위10건_목록.csv")
    print("Done.")


if __name__ == "__main__":
    main()
