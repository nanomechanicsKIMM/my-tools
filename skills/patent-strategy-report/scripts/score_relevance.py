#!/usr/bin/env python3
"""
Score each patent row by relevance (abstract vs RFP) and classify as noise if score is low.
Requires CSV with an 'abstract' column (e.g. from fetch_abstracts.py).

Usage:
  python score_relevance.py <csv_with_abstract> <rfp_path> -o <output_csv> [--threshold 0.12] [--no-abstract-use-title]
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


def col_find(row: dict, *candidates: str) -> str:
    for c in candidates:
        if c in row and row[c]:
            return str(row[c]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description="Score patent relevance to RFP and mark noise")
    ap.add_argument("input_csv", help="CSV with abstract column")
    ap.add_argument("rfp_path", help="RFP markdown file path")
    ap.add_argument("-o", "--output", required=True, help="Output CSV with relevance_score and is_noise")
    ap.add_argument("--threshold", type=float, default=0.12, help="Relevance score threshold: below = noise")
    ap.add_argument("--no-abstract-use-title", action="store_true", help="If abstract empty, use title for scoring")
    args = ap.parse_args()

    rows, header = load_csv_with_header_skip(args.input_csv)
    if not rows:
        print("No rows", file=sys.stderr)
        sys.exit(1)

    rfp_text = load_rfp_text(args.rfp_path)

    # Build corpus: RFP first, then each row's text (abstract or title)
    texts = [rfp_text]
    for row in rows:
        ab = col_find(row, "abstract", "Abstract", "crawled_abstract")
        if not ab and args.no_abstract_use_title:
            ab = col_find(row, "title", "Title")
        texts.append(ab or " ")

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

    # First row is RFP
    rfp_vec = X[0:1]
    scores = cosine_similarity(X[1:], rfp_vec).ravel()

    out_header = list(header)
    if "relevance_score" not in out_header:
        out_header.append("relevance_score")
    if "is_noise" not in out_header:
        out_header.append("is_noise")

    for i, row in enumerate(rows):
        if i < len(scores):
            row["relevance_score"] = round(float(scores[i]), 4)
            row["is_noise"] = "true" if scores[i] < args.threshold else "false"
        else:
            row["relevance_score"] = 0.0
            row["is_noise"] = "true"

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    n_noise = sum(1 for r in rows if r.get("is_noise") == "true")
    n_keep = len(rows) - n_noise
    removal = n_noise / len(rows) if rows else 0
    print(f"Total: {len(rows)}, Kept: {n_keep}, Noise: {n_noise}")
    print(f"REMOVAL_RATIO: {removal:.4f}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
