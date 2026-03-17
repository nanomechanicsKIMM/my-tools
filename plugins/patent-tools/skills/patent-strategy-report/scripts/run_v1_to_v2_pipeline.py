#!/usr/bin/env python3
"""
Pipeline: v1 CSV → (1) title–RFP top 5000 → (2) add abstracts → (3) abstract–RFP top 2500 → v2.csv.

Step 1: Score each row by title–RFP relevance (TF-IDF cosine), keep top 5000, save CSV.
Step 2: Run fetch_abstracts.py on that CSV to add 'abstract' column (can be slow; use --resume).
Step 3: Score by abstract–RFP relevance, keep top 2500 sorted by score, save as v2.csv.

Usage:
  python run_v1_to_v2_pipeline.py <v1_csv> <rfp_path> [--output-dir DIR] [--top1 5000] [--top2 2500]
  python run_v1_to_v2_pipeline.py <v1_csv> <rfp_path> --skip-fetch  # run only step 1 and 3 (you run fetch_abstracts manually)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_step1(v1_csv: str, rfp_path: str, output_dir: Path, top1: int) -> Path:
    out_csv = output_dir / "v1_top5000.csv"
    if top1 != 5000:
        out_csv = output_dir / f"v1_top{top1}.csv"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "filter_title_top_n.py"),
        v1_csv,
        rfp_path,
        "-o",
        str(out_csv),
        "--top",
        str(top1),
    ]
    subprocess.run(cmd, check=True)
    return out_csv


def run_step2(csv_with_5000: Path, output_dir: Path, resume: str | None, delay: float, limit: int) -> Path:
    out_csv = output_dir / "v1_top5000_with_abstracts.csv"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "fetch_abstracts.py"),
        str(csv_with_5000),
        "-o",
        str(out_csv),
        "--delay",
        str(delay),
    ]
    if resume:
        cmd += ["--resume", resume]
    if limit > 0:
        cmd += ["--limit", str(limit)]
    subprocess.run(cmd, check=True)
    return out_csv


def run_step3(csv_with_abstracts: Path, rfp_path: str, output_dir: Path, top2: int) -> Path:
    v2_csv = output_dir / "v2.csv"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "filter_abstract_top_n.py"),
        str(csv_with_abstracts),
        rfp_path,
        "-o",
        str(v2_csv),
        "--top",
        str(top2),
    ]
    subprocess.run(cmd, check=True)
    return v2_csv


def main():
    ap = argparse.ArgumentParser(description="v1 → title top N → add abstracts → abstract top M → v2")
    ap.add_argument("v1_csv", help="Input v1 CSV from Google Patents")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("--output-dir", "-o", default="output", help="Directory for intermediate and v2 output (default: output)")
    ap.add_argument("--top1", type=int, default=5000, help="Top N by title–RFP (default 5000)")
    ap.add_argument("--top2", type=int, default=2500, help="Top M by abstract–RFP for v2 (default 2500)")
    ap.add_argument("--skip-fetch", action="store_true", help="Skip step 2 (add abstracts); run fetch_abstracts yourself then run this with --from-abstracts")
    ap.add_argument("--from-abstracts", help="CSV that already has abstract column (skip step 1 and 2, run only step 3)")
    ap.add_argument("--resume", help="Resume file for fetch_abstracts (e.g. output/abstracts_resume.json)")
    ap.add_argument("--delay", type=float, default=1.5, help="Delay between fetch_abstracts requests (seconds)")
    ap.add_argument("--limit", type=int, default=0, help="Max rows for fetch_abstracts (0 = all)")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.from_abstracts:
        # Only step 3: CSV with abstracts → v2
        v2 = run_step3(Path(args.from_abstracts), args.rfp_path, output_dir, args.top2)
        print("Done. v2:", v2)
        return

    # Step 1: v1 → top 5000 by title
    step1_out = run_step1(args.v1_csv, args.rfp_path, output_dir, args.top1)
    print("Step 1 done:", step1_out)

    if args.skip_fetch:
        print("Skipping step 2 (add abstracts). Run fetch_abstracts.py on", step1_out)
        print("Then run this script with --from-abstracts <path_to_csv_with_abstracts>")
        return

    # Step 2: add abstracts
    resume_path = args.resume or str(output_dir / "abstracts_resume_top5000.json")
    step2_out = run_step2(step1_out, output_dir, resume_path, args.delay, args.limit)
    print("Step 2 done:", step2_out)

    # Step 3: abstract top 2500 → v2
    v2 = run_step3(step2_out, args.rfp_path, output_dir, args.top2)
    print("Done. v2:", v2)


if __name__ == "__main__":
    main()
