#!/usr/bin/env python3
"""
Score each patent row by abstract+representative_claim–RFP relevance (5:5 weight) with include/exclude term weights.
Expects CSV with 'abstract' and optionally 'representative_claim' columns (from fetch_abstracts.py).
- Base: 0.5 * (abstract–RFP cosine) + 0.5 * (claim–RFP cosine). If claim missing, uses abstract only.
- Must-include / must-exclude terms applied to combined text.

Output: CSV with relevance_score column, sorted by score descending.

Usage:
  python score_abstract_relevance.py <csv_with_abstract> <rfp_path> -o <output_csv> [--top 10]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from score_relevance_weighted import score_abstract_claim_pairs_relevance_weighted


def load_csv_with_header_skip(path: str) -> tuple[list[dict], list[str]]:
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


def load_rfp_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_abstract(row: dict) -> str:
    for key in ("abstract", "Abstract", "crawled_abstract", "abstract_en", "Abstract (English)"):
        if key in row and row[key]:
            s = str(row[key]).strip()
            if s and not s.startswith("[fetch error"):
                return s
    return ""


def get_representative_claim(row: dict) -> str:
    for key in ("representative_claim", "Representative claim", "claim_1", "claim1"):
        if key in row and row[key]:
            s = str(row[key]).strip()
            if s and not s.startswith("[fetch error"):
                return s
    return ""


def run(
    input_csv_path: str | Path,
    rfp_path: str | Path,
    output_path: str | Path,
    top_n: int | None = None,
    include_terms: list[str] | None = None,
    exclude_terms: list[str] | None = None,
    include_weight: float = 0.2,
    exclude_weight: float = 0.5,
) -> int:
    """Score rows by abstract+representative_claim (5:5), sort desc, write top_n or all. Returns rows written."""
    input_csv_path = Path(input_csv_path)
    rfp_path = Path(rfp_path)
    output_path = Path(output_path)
    include_terms = include_terms or []
    exclude_terms = exclude_terms or []

    rows, header = load_csv_with_header_skip(str(input_csv_path))
    if not rows:
        raise SystemExit("No rows in CSV")

    abstracts = [get_abstract(r) for r in rows]
    if all(not a for a in abstracts):
        raise SystemExit("No abstract column or all empty. Run fetch_abstracts.py first.")

    claims = [get_representative_claim(r) for r in rows]
    rfp_text = load_rfp_text(str(rfp_path))
    scores = score_abstract_claim_pairs_relevance_weighted(
        abstracts,
        claims,
        rfp_text,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        include_weight=include_weight,
        exclude_weight=exclude_weight,
        abstract_weight=0.5,
        claim_weight=0.5,
    )
    for i, row in enumerate(rows):
        row["relevance_score"] = scores[i] if i < len(scores) else 0.0

    sorted_rows = sorted(rows, key=lambda r: float(r.get("relevance_score", 0)), reverse=True)
    to_write = sorted_rows[:top_n] if top_n is not None and top_n > 0 else sorted_rows

    out_header = list(header)
    if "relevance_score" not in out_header:
        out_header.append("relevance_score")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(to_write)
    return len(to_write)


def main():
    ap = argparse.ArgumentParser(description="Score patents by abstract+representative_claim–RFP relevance (5:5 weight, include/exclude terms)")
    ap.add_argument("input_csv", help="CSV with abstract column")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("-o", "--output", required=True, help="Output CSV with relevance_score")
    ap.add_argument("--top", type=int, default=0, help="Keep only top N rows (0 = all)")
    ap.add_argument("--include-terms", type=str, default=None, help="Comma-separated must-include terms")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Comma-separated must-exclude terms")
    ap.add_argument("--include-weight", type=float, default=0.2, help="Score per include term (default 0.2)")
    ap.add_argument("--exclude-weight", type=float, default=0.5, help="Score subtracted per exclude term (default 0.5)")
    args = ap.parse_args()

    include_terms = [t.strip() for t in args.include_terms.split(",")] if getattr(args, "include_terms", None) else []
    exclude_terms = [t.strip() for t in args.exclude_terms.split(",")] if getattr(args, "exclude_terms", None) else []
    top_n = args.top if args.top > 0 else None
    n = run(
        args.input_csv,
        args.rfp_path,
        args.output,
        top_n=top_n,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        include_weight=args.include_weight,
        exclude_weight=args.exclude_weight,
    )
    print(f"Scored and wrote {n} rows (abstract+representative_claim 5:5 relevance with include/exclude weights)")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
