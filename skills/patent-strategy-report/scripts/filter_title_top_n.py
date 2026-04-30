#!/usr/bin/env python3
"""
Step 1: Filter v1 CSV by title–RFP relevance; keep top N (default 5000) and save to a new CSV.
Uses TF-IDF cosine similarity (title vs RFP). Output CSV has a relevance_score column.

Usage:
  python filter_title_top_n.py <v1_csv> <rfp_path> -o <output_csv> [--top 5000]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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


def _contains_excluded(text: str, exclude_keywords: list[str]) -> bool:
    """True if text (case-insensitive) contains any of exclude_keywords."""
    if not text or not exclude_keywords:
        return False
    t = text.upper()
    for kw in exclude_keywords:
        if kw.strip() and kw.upper() in t:
            return True
    return False


def run_filter(
    input_csv_path: str | Path,
    rfp_path: str | Path,
    output_path: str | Path,
    top_n: int = 5000,
    exclude_keywords: list[str] | None = None,
) -> int:
    """Run title–RFP relevance filter and write top N rows. Optionally exclude rows whose title contains any of exclude_keywords (e.g. OLED, LCD). Returns number of rows written."""
    input_csv_path = Path(input_csv_path)
    rfp_path = Path(rfp_path)
    output_path = Path(output_path)
    exclude_keywords = exclude_keywords or []

    rows, header = load_csv_with_header_skip(str(input_csv_path))
    if not rows:
        raise SystemExit("No rows in CSV")

    # Exclude by title before scoring (so we don't waste score on excluded)
    if exclude_keywords:
        rows = [r for r in rows if not _contains_excluded(get_title(r), exclude_keywords)]
        if not rows:
            raise SystemExit("No rows left after exclude_keywords filter")

    rfp_text = load_rfp_text(str(rfp_path))
    titles = [get_title(r) for r in rows]
    texts = [rfp_text] + titles

    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    X = vectorizer.fit_transform(texts)
    rfp_vec = X[0:1]
    scores = cosine_similarity(X[1:], rfp_vec).ravel()

    for i, row in enumerate(rows):
        row["relevance_score"] = round(float(scores[i]), 4) if i < len(scores) else 0.0

    sorted_rows = sorted(rows, key=lambda r: r.get("relevance_score", 0.0), reverse=True)
    top_rows = sorted_rows[:top_n]

    out_header = list(header)
    if "relevance_score" not in out_header:
        out_header.append("relevance_score")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(top_rows)

    return len(top_rows)


def main():
    ap = argparse.ArgumentParser(description="Keep top N patents by title–RFP relevance")
    ap.add_argument("input_csv", help="Input CSV (e.g. v1)")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("-o", "--output", required=True, help="Output CSV (top N rows + relevance_score)")
    ap.add_argument("--top", type=int, default=5000, help="Number of top patents to keep (default 5000)")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Comma-separated terms to exclude from title (e.g. OLED,LCD). Rows with any term in title are dropped before scoring.")
    args = ap.parse_args()

    exclude_keywords = []
    if getattr(args, "exclude_terms", None):
        exclude_keywords = [t.strip() for t in args.exclude_terms.split(",") if t.strip()]
    n = run_filter(args.input_csv, args.rfp_path, args.output, args.top, exclude_keywords=exclude_keywords)
    print(f"Kept (top {args.top} by title–RFP score): {n}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
