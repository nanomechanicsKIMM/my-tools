#!/usr/bin/env python3
"""
Run the improved noise pipeline: fetch abstracts → score relevance (abstract vs RFP) → extract NOT from noise.
Use this when you want NOT terms derived from abstract-based noise classification.

Usage:
  python run_noise_pipeline_with_abstracts.py <input_csv> <rfp_path> --current-query "..." --search-url "..." [options]

Steps:
  1. fetch_abstracts: crawl result links, add abstract column (optional if CSV already has abstract)
  2. score_relevance: TF-IDF cosine similarity(abstract, RFP); mark low-score as noise
  3. extract_not_from_noise: from noise abstracts, extract NOT keywords and improved query
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    r = subprocess.run(cmd, cwd=cwd or REPO_ROOT)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Noise pipeline with abstract crawling and NOT extraction")
    ap.add_argument("input_csv", help="Google Patents CSV (with result link column)")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("--current-query", required=True, help="Current search query string")
    ap.add_argument("--search-url", required=True, help="Current search URL")
    ap.add_argument("-o", "--output-dir", type=Path, default=SKILL_ROOT / "output", help="Output directory")
    ap.add_argument("--fetch-limit", type=int, default=0, help="If >0, only fetch this many abstracts (0=all)")
    ap.add_argument("--fetch-delay", type=float, default=1.5, help="Delay between crawl requests (seconds)")
    ap.add_argument("--skip-fetch", action="store_true", help="Skip fetch step (CSV already has abstract column)")
    ap.add_argument("--threshold", type=float, default=0.12, help="Relevance score threshold below which = noise")
    ap.add_argument("--top-n", type=int, default=8, help="Max NOT terms to suggest")
    args = ap.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_with_abstract = out_dir / "csv_with_abstract.csv"
    scored_csv = out_dir / "scored_relevance.csv"
    not_result = out_dir / "not_from_noise_result.txt"

    if not args.skip_fetch:
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "fetch_abstracts.py"),
            args.input_csv,
            "-o", str(csv_with_abstract),
            "--delay", str(args.fetch_delay),
        ]
        if args.fetch_limit > 0:
            cmd.extend(["--limit", str(args.fetch_limit)])
        if not run(cmd):
            print("fetch_abstracts failed", file=sys.stderr)
            sys.exit(1)
        input_for_score = str(csv_with_abstract)
    else:
        input_for_score = args.input_csv

    if not run([
        sys.executable,
        str(SCRIPT_DIR / "score_relevance.py"),
        input_for_score,
        args.rfp_path,
        "-o", str(scored_csv),
        "--threshold", str(args.threshold),
        "--no-abstract-use-title",
    ]):
        print("score_relevance failed", file=sys.stderr)
        sys.exit(1)

    if not run([
        sys.executable,
        str(SCRIPT_DIR / "extract_not_from_noise.py"),
        str(scored_csv),
        args.rfp_path,
        "--current-query", args.current_query,
        "--search-url", args.search_url,
        "-o", str(not_result),
        "--top-n", str(args.top_n),
    ]):
        print("extract_not_from_noise failed", file=sys.stderr)
        sys.exit(1)

    print("Done. NOT suggestion:", not_result)
    if not_result.exists():
        print(not_result.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
