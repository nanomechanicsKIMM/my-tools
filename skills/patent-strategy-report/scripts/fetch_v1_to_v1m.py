#!/usr/bin/env python3
"""Add abstracts to v1 CSV and save as v1m.csv. Uses --resume for interrupt/resume."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent
if not (REPO_ROOT / "gp-search-20260306_v1.csv").exists():
    REPO_ROOT = REPO_ROOT.parent

INPUT_CSV = REPO_ROOT / "gp-search-20260306_v1.csv"
OUTPUT_CSV = REPO_ROOT / "v1m.csv"
RESUME_JSON = SKILL_ROOT / "output" / "abstracts_resume_v1.json"

if not INPUT_CSV.exists():
    for p in REPO_ROOT.iterdir():
        if "v1" in p.name and p.suffix == ".csv" and "filtered" not in p.name:
            INPUT_CSV = p
            break
if not INPUT_CSV.exists():
    print("v1 CSV not found:", REPO_ROOT / "gp-search-20260306_v1.csv", file=sys.stderr)
    sys.exit(1)

RESUME_JSON.parent.mkdir(parents=True, exist_ok=True)

sys.argv = [
    "fetch_abstracts",
    str(INPUT_CSV),
    "-o", str(OUTPUT_CSV),
    "--delay", "1.5",
    "--resume", str(RESUME_JSON),
]

import fetch_abstracts
fetch_abstracts.main()
