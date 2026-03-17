#!/usr/bin/env python3
"""
Step 3: From a CSV that has an 'abstract' column, score each row by abstract–RFP relevance,
keep top N (default 2500) sorted by score descending, and save as v2 CSV.

Usage:
  python filter_abstract_top_n.py <csv_with_abstract> <rfp_path> -o v2.csv [--top 2500]
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


def get_abstract(row: dict) -> str:
    for key in ("abstract", "Abstract", "crawled_abstract", "abstract_en", "Abstract (English)"):
        if key in row and row[key]:
            s = str(row[key]).strip()
            if s and not s.startswith("[fetch error"):
                return s
    return ""


def main():
    ap = argparse.ArgumentParser(description="Keep top N patents by abstract–RFP relevance, sorted by score")
    ap.add_argument("input_csv", help="CSV with abstract column (e.g. after fetch_abstracts)")
    ap.add_argument("rfp_path", help="RFP markdown path")
    ap.add_argument("-o", "--output", required=True, help="Output CSV (e.g. v2.csv)")
    ap.add_argument("--top", type=int, default=2500, help="Number of top patents to keep (default 2500)")
    args = ap.parse_args()

    rows, header = load_csv_with_header_skip(args.input_csv)
    if not rows:
        print("No rows in CSV", file=sys.stderr)
        sys.exit(1)

    abstracts = [get_abstract(r) for r in rows]
    missing = sum(1 for a in abstracts if not a)
    if missing == len(rows):
        print("No abstract column or all empty. Run fetch_abstracts.py first.", file=sys.stderr)
        sys.exit(1)
    if missing:
        print(f"Warning: {missing} rows have empty abstract; scored as 0.", file=sys.stderr)

    rfp_text = load_rfp_text(args.rfp_path)
    texts = [rfp_text] + [a or " " for a in abstracts]

    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    try:
        X = vectorizer.fit_transform(texts)
    except Exception as e:
        print("TfidfVectorizer failed:", e, file=sys.stderr)
        sys.exit(1)

    rfp_vec = X[0:1]
    scores = cosine_similarity(X[1:], rfp_vec).ravel()

    for i, row in enumerate(rows):
        if i < len(scores):
            row["relevance_score"] = round(float(scores[i]), 4)
        else:
            row["relevance_score"] = 0.0

    sorted_rows = sorted(rows, key=lambda r: r.get("relevance_score", 0.0), reverse=True)
    top_rows = sorted_rows[: args.top]

    out_header = list(header)
    if "relevance_score" not in out_header:
        out_header.append("relevance_score")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(top_rows)

    print(f"Total rows: {len(rows)}, Kept (top {args.top} by abstract-RFP score, score-sorted): {len(top_rows)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
