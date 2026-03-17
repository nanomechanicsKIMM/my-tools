#!/usr/bin/env python3
"""Run full pipeline with v1 CSV and RFP in repo root (avoids CLI encoding)."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent.parent  # Patent_Analysis

CSV_NAME = "gp-search-20260306_v1.csv"
RFP_NAME = "(2026)_RFP_센서_융합_디스플레이_기술.md"
QUERY = "(Display OR Transformable OR Deformation OR sensing OR User OR interface OR User OR Experience OR display OR panel OR screen OR OLED OR LED OR flexible OR stretchable OR foldable OR rollable OR backplane OR TFT OR pixel)"
URL = "https://patents.google.com/?q=%28Display+OR+Transformable+OR+Deformation+OR+sensing+OR+User+OR+interface+OR+User+OR+Experience+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable+OR+foldable+OR+rollable+OR+backplane+OR+TFT+OR+pixel%29&after=priority:20110101&before=priority:20261231"

csv_path = REPO_ROOT / CSV_NAME
rfp_path = REPO_ROOT / RFP_NAME
if not csv_path.exists():
    for p in REPO_ROOT.iterdir():
        if "v1" in p.name and p.suffix == ".csv":
            csv_path = p
            break
if not csv_path.exists():
    print("CSV not found:", REPO_ROOT / CSV_NAME, file=sys.stderr)
    sys.exit(1)
if not rfp_path.exists():
    for p in REPO_ROOT.iterdir():
        if "RFP" in p.name and p.suffix == ".md":
            rfp_path = p
            break
if not rfp_path.exists():
    print("RFP not found:", REPO_ROOT / RFP_NAME, file=sys.stderr)
    sys.exit(1)

sys.argv = [
    "run_full_pipeline.py",
    str(csv_path),
    "--no-filter",
    "--rfp-path", str(rfp_path),
    "--output-dir", str(SKILL_ROOT / "output"),
    "--report-title", "센서 융합 디스플레이 15년 세계 특허 현황 분석",
    "--topic", "센서융합디스플레이",
    "--search-query", QUERY,
    "--search-url", URL,
]

import run_full_pipeline
run_full_pipeline.main()
