#!/usr/bin/env python3
"""
Run the full patent report pipeline when the user has provided a CSV from Google Patents.
Applicable to any research/technology domain; no hard-coded topic or RFP.

Noise-filter loop: if REMOVAL_RATIO > 10%, the pipeline stops and prints an improved
search query; the user re-downloads CSV with that query and runs the pipeline again.
Repeat until REMOVAL_RATIO <= 10%, then aggregation and report are run.

Usage:
  python run_full_pipeline.py <path_to_csv> [--rfp-path RFP.md] [--output-dir DIR] [--report-title "Title"] [--topic slug] [--search-query "query"] [--search-url "url"] [--no-filter]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    r = subprocess.run(cmd, cwd=cwd or REPO_ROOT)
    return r.returncode == 0


def run_filter_and_parse(
    csv_path: Path,
    rfp_path: Path,
    filtered_path: Path,
    current_query: str,
) -> tuple[bool, float | None, str | None]:
    """Run filter_noise, capture stdout, return (success, removal_ratio, improved_query_suggestion)."""
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "filter_noise.py"),
        str(csv_path),
        str(rfp_path),
        "-o", str(filtered_path),
        "--threshold", "0.15",
    ]
    if current_query:
        cmd.extend(["--current-query", current_query])
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        return False, None, None
    removal_ratio = None
    improved = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("REMOVAL_RATIO:"):
            try:
                removal_ratio = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("IMPROVED_QUERY_SUGGESTION:"):
            improved = line.split(":", 1)[1].strip()
    return True, removal_ratio, improved


def main():
    ap = argparse.ArgumentParser(description="Patent report pipeline (user-provided CSV, any domain)")
    ap.add_argument("csv_path", type=Path, help="Path to Google Patents CSV (user-downloaded)")
    ap.add_argument("--rfp-path", type=Path, default=None, help="Path to RFP markdown (for noise filter)")
    ap.add_argument("--output-dir", "-o", type=Path, default=SKILL_ROOT / "output")
    ap.add_argument("--report-title", default="세계 특허 현황 분석 보고서", help="Report title (any domain)")
    ap.add_argument("--topic", default="patent", help="Topic slug for file naming and tags")
    ap.add_argument("--search-query", default="", help="Search query string used (for report reference)")
    ap.add_argument("--search-url", default="", help="Search URL used (for report reference)")
    ap.add_argument("--no-filter", action="store_true", help="Skip noise filtering")
    args = ap.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    current_csv = csv_path
    if not args.no_filter and args.rfp_path and Path(args.rfp_path).exists():
        rfp_path = Path(args.rfp_path).resolve()
        filtered = out_dir / "filtered.csv"
        ok, removal_ratio, improved_query = run_filter_and_parse(
            csv_path, rfp_path, filtered, (args.search_query or "").strip()
        )
        if not ok:
            print("filter_noise failed", file=sys.stderr)
            sys.exit(1)
        if removal_ratio is not None and removal_ratio > 0.10:
            print("REMOVAL_RATIO > 10%. Refine the search query, re-download CSV, then run this pipeline again.", file=sys.stderr)
            print("---")
            if improved_query:
                print("IMPROVED_QUERY_SUGGESTION:", improved_query)
                if args.search_url:
                    new_q = quote_plus(improved_query)
                    improved_url = re.sub(r"q=[^&]*", "q=" + new_q, args.search_url, count=1)
                    print("IMPROVED_SEARCH_URL:", improved_url)
            print("---")
            print("Next: 1) Open IMPROVED_SEARCH_URL in browser, 2) Download CSV, 3) Run: python run_full_pipeline.py <new_csv> --rfp-path ... --search-query \"...\" --search-url \"...\"")
            sys.exit(0)
        current_csv = filtered
    elif not args.no_filter and (not args.rfp_path or not Path(args.rfp_path).exists()):
        print("RFP path not given or not found; skipping filter.", file=sys.stderr)

    rfp_arg = str(args.rfp_path) if args.rfp_path and Path(args.rfp_path).exists() else ""
    if not run([
        sys.executable,
        str(SCRIPT_DIR / "aggregate_csv_report.py"),
        str(current_csv),
        "-o", str(out_dir),
        "--report-title", args.report_title,
        "--search-query", args.search_query,
        "--search-url", args.search_url,
        "--rfp-path", rfp_arg,
    ]):
        print("aggregate_csv_report failed", file=sys.stderr)
        sys.exit(1)

    from datetime import datetime
    report_md = out_dir / f"{datetime.now().strftime('%Y%m%d')}_{args.topic}_세계특허현황_분석보고서.md"
    if not run([
        sys.executable,
        str(SCRIPT_DIR / "fill_report.py"),
        str(out_dir / "aggregate_report_data.json"),
        "-o", str(report_md),
        "--topic", args.topic,
    ]):
        print("fill_report failed", file=sys.stderr)
        sys.exit(1)

    print("Report written to:", report_md)


if __name__ == "__main__":
    main()
