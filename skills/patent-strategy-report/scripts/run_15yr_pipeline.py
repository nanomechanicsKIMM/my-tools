#!/usr/bin/env python3
"""
Run the full patent report pipeline for 15-year RFP analysis when CSV already exists.
Usage: python run_15yr_pipeline.py <path_to_csv> [--output-dir DIR] [--no-filter]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent
RFP_PATH = REPO_ROOT / "(2026)_RFP_센서_융합_디스플레이_기술.md"
if not RFP_PATH.exists():
    RFP_PATH = REPO_ROOT / "./(2026)_RFP_센서_융합_디스플레이_기술.md"

SEARCH_QUERY = '(Display OR Transformable OR Deformation OR sensing OR User OR interface OR User OR Experience OR display OR panel OR screen OR OLED OR LED OR flexible OR stretchable OR foldable OR rollable OR backplane OR TFT OR pixel)'
SEARCH_URL = "https://patents.google.com/?q=%28Display+OR+Transformable+OR+Deformation+OR+sensing+OR+User+OR+interface+OR+User+OR+Experience+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable+OR+foldable+OR+rollable+OR+backplane+OR+TFT+OR+pixel%29&after=priority:20110101&before=priority:20251231"


def run(cmd: list[str]) -> bool:
    r = subprocess.run(cmd, cwd=REPO_ROOT)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path, help="Path to Google Patents CSV (raw or filtered)")
    ap.add_argument("--output-dir", "-o", type=Path, default=SKILL_ROOT / "output")
    ap.add_argument("--no-filter", action="store_true", help="Skip noise filtering (use CSV as-is)")
    args = ap.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    current_csv = csv_path
    if not args.no_filter and RFP_PATH.exists():
        filtered = out_dir / "filtered_15yr.csv"
        if not run([
            sys.executable,
            str(SCRIPT_DIR / "filter_noise.py"),
            str(current_csv),
            str(RFP_PATH),
            "-o", str(filtered),
            "--threshold", "0.15",
        ]):
            print("filter_noise failed", file=sys.stderr)
            sys.exit(1)
        current_csv = filtered
    else:
        if not args.no_filter and not RFP_PATH.exists():
            print("RFP not found, skipping filter", file=sys.stderr)

    if not run([
        sys.executable,
        str(SCRIPT_DIR / "aggregate_csv_report.py"),
        str(current_csv),
        "-o", str(out_dir),
        "--report-title", "센서 융합 디스플레이 세계 특허 현황 분석 (2011-2025)",
        "--search-query", SEARCH_QUERY,
        "--search-url", SEARCH_URL,
        "--rfp-path", str(RFP_PATH) if RFP_PATH.exists() else "",
    ]):
        print("aggregate_csv_report failed", file=sys.stderr)
        sys.exit(1)

    report_md = out_dir / "20260306_센서융합디스플레이_15년_세계특허현황_분석보고서.md"
    if not run([
        sys.executable,
        str(SCRIPT_DIR / "fill_report.py"),
        str(out_dir / "aggregate_report_data.json"),
        "-o", str(report_md),
        "--topic", "센서융합디스플레이",
    ]):
        print("fill_report failed", file=sys.stderr)
        sys.exit(1)

    print("Report written to:", report_md)


if __name__ == "__main__":
    main()
