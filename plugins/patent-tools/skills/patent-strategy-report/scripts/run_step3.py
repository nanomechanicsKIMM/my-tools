# -*- coding: utf-8 -*-
"""Run Step 3 pipeline with comma-separated terms (avoids PowerShell splitting)."""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(r"c:\Users\JHKIM\Patent_Analysis")

v1_csv = WORKSPACE / "gp-search-20260306-v1.csv"
rfp_path = WORKSPACE / "(2026)_RFP_센서_융합_디스플레이_기술.md"
out_dir = SCRIPT_DIR.parent / "output"

args = [
    sys.executable,
    "run_relevance_pipeline.py",
    str(v1_csv),
    str(rfp_path),
    "-o", str(out_dir),
    "--include-terms", "stretchable,display",
    "--exclude-terms", "OLED,perovskite,LCD",
    "--topic", "센서융합디스플레이",
]
subprocess.run(args, cwd=SCRIPT_DIR)
