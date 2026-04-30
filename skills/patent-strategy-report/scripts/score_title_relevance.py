#!/usr/bin/env python3
"""
Score each patent row by title–RFP relevance with include/exclude term weights.
- Base: TF-IDF cosine similarity (title vs RFP).
- Must-include terms in title: add +include_weight each (high positive).
- Must-exclude terms in title: add -exclude_weight each (high negative).

Output: CSV with relevance_score column, sorted by score descending.
Optionally write only top N rows (e.g. --top 10000 for statistics).

Usage:
  python score_title_relevance.py <input_csv> <rfp_path> -o <output_csv> [--top 10000]
  python score_title_relevance.py <input_csv> <rfp_path> -o scored.csv --include-terms "sensor,display" --exclude-terms "OLED,LCD"
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from score_relevance_weighted import score_texts_relevance_weighted


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


def get_title(row: dict) -> str:
    for key in ("title", "Title", "title_en", "Title (English)"):
        if key in row and row[key]:
            return str(row[key]).strip()
    return " ".join(str(v) for v in row.values() if v)[:2000]


def run(
    input_csv_path: str | Path,
    rfp_path: str | Path,
    output_path: str | Path,
    top_n: int | None = 10000,
    include_terms: list[str] | None = None,
    exclude_terms: list[str] | None = None,
    include_weight: float = 0.2,
    exclude_weight: float = 0.5,
) -> int:
    """Score all rows by title, sort by score desc, write top_n (or all) to output_path. Returns rows written."""
    input_csv_path = Path(input_csv_path)
    rfp_path = Path(rfp_path)
    output_path = Path(output_path)
    include_terms = include_terms or []
    exclude_terms = exclude_terms or []

    rows, header = load_csv_with_header_skip(str(input_csv_path))
    if not rows:
        raise SystemExit("No rows in CSV")

    rfp_text = load_rfp_text(str(rfp_path))
    titles = [get_title(r) for r in rows]
    scores = score_texts_relevance_weighted(
        titles,
        rfp_text,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        include_weight=include_weight,
        exclude_weight=exclude_weight,
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
    ap = argparse.ArgumentParser(description="Score patents by title–RFP relevance (include/exclude term weights)")
    ap.add_argument("input_csv", help="Input CSV (e.g. v1 from Google Patents)")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("-o", "--output", required=True, help="Output CSV (top N rows + relevance_score)")
    ap.add_argument("--top", type=int, default=10000, help="Write only top N rows (default 10000). 0 = write all.")
    ap.add_argument("--include-terms", type=str, default=None, help="Comma-separated must-include terms (positive weight)")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Comma-separated must-exclude terms (negative weight)")
    ap.add_argument("--include-weight", type=float, default=0.2, help="Score added per include term in title (default 0.2)")
    ap.add_argument("--exclude-weight", type=float, default=0.5, help="Score subtracted per exclude term in title (default 0.5)")
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
    print(f"Scored and wrote top {n} rows (title–RFP relevance with include/exclude weights)")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
