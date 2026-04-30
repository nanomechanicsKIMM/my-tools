#!/usr/bin/env python3
"""
Extract NOT keywords from noise rows (from score_relevance.py output).
Analyzes abstracts of noise vs keep rows and suggests terms that are
characteristic of noise (frequent in noise, rare in keep). Excludes RFP/query terms and stopwords.

Usage:
  python extract_not_from_noise.py <scored_csv> <rfp_path> --current-query "..." --search-url "..." [--output result.txt] [--top-n 8]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus


# Stopwords + generic patent terms (do not suggest as NOT)
_STOP = frozenset(
    "the a an and or of in to for is on with as by at from that this it its be are was were been have has had do does did will would could should may might can must "
    "method device system apparatus systems devices methods using data unit circuit layer component "
    "sensor sensing detection display panel screen".split()
)


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


def load_rfp_keywords(rfp_path: str) -> set[str]:
    with open(rfp_path, "r", encoding="utf-8") as f:
        text = f.read()
    keywords = set()
    for m in re.finditer(r"[a-zA-Z][a-zA-Z0-9\-]*", text):
        w = m.group(0).lower()
        if len(w) >= 2:
            keywords.add(w)
    for m in re.finditer(r"영문\s*[:\s]+([^\n#\-]+)", text, re.I):
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", m.group(1)):
            keywords.add(w.lower())
    return keywords


def parse_query_terms(current_query: str) -> set[str]:
    if not current_query or not current_query.strip():
        return set()
    q = re.sub(r"NOT\s*\([^)]*\)", "", current_query, flags=re.I)
    q = re.sub(r"[()\"]", " ", q)
    return {w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", q) if len(w) >= 2 and w.lower() not in ("and", "or", "not")}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    out = []
    for w in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", text):
        w = w.lower()
        if len(w) >= 3 and w not in _STOP and not w.isdigit():
            out.append(w)
    return out


def text_for_row(row: dict) -> str:
    for key in ["abstract", "Abstract", "crawled_abstract"]:
        if key in row and row[key] and str(row[key]).strip() and not str(row[key]).startswith("[fetch error"):
            return str(row[key]).strip()
    for key in ["title", "Title"]:
        if key in row and row[key]:
            return str(row[key]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description="Extract NOT keywords from noise rows (scored CSV)")
    ap.add_argument("scored_csv", help="CSV with is_noise and abstract columns (from score_relevance.py)")
    ap.add_argument("rfp_path", help="RFP markdown path (for exclude terms)")
    ap.add_argument("--current-query", required=True, help="Current search query string")
    ap.add_argument("--search-url", required=True, help="Current search URL (to build improved URL)")
    ap.add_argument("-o", "--output", help="Write result to file (default: stdout)")
    ap.add_argument("--top-n", type=int, default=8, help="Max NOT terms to suggest")
    ap.add_argument("--noise-column", default="is_noise", help="Column name for noise flag (true/false)")
    args = ap.parse_args()

    rows, _ = load_csv_with_header_skip(args.scored_csv)
    if not rows:
        print("No rows", file=sys.stderr)
        sys.exit(1)

    noise_rows = [r for r in rows if str(r.get(args.noise_column, "")).strip().lower() == "true"]
    keep_rows = [r for r in rows if r not in noise_rows]

    exclude = load_rfp_keywords(args.rfp_path) | parse_query_terms(args.current_query)

    noise_tokens = []
    for r in noise_rows:
        noise_tokens.extend(tokenize(text_for_row(r)))
    keep_tokens = []
    for r in keep_rows:
        keep_tokens.extend(tokenize(text_for_row(r)))

    noise_cnt = Counter(noise_tokens)
    keep_cnt = Counter(keep_tokens)
    candidates = []
    min_noise = max(2, len(noise_rows) // 500)  # at least in 0.2% of noise docs
    for term, n_count in noise_cnt.most_common():
        if term in exclude or n_count < min_noise:
            continue
        k_count = keep_cnt.get(term, 0)
        # Prefer terms that are much more frequent in noise than in keep (ratio or difference)
        score = n_count - k_count
        if score <= 0:
            continue
        # Optional: require term to be relatively rare in keep (e.g. noise_ratio)
        keep_ratio = k_count / (len(keep_rows) + 1)
        if keep_ratio > 0.5:  # skip if term appears in >50% of keep
            continue
        candidates.append((term, score, n_count, keep_ratio))
    candidates.sort(key=lambda x: (-x[1], -x[2], x[3]))
    suggested = [t[0] for t in candidates[: args.top_n]]

    base = args.current_query.strip()
    if suggested:
        not_part = " NOT (" + " OR ".join(suggested) + ")"
        improved_query = (base + not_part) if base else ("NOT (" + " OR ".join(suggested) + ")")
    else:
        improved_query = base

    new_q = quote_plus(improved_query)
    improved_url = re.sub(r"q=[^&]*", "q=" + new_q, args.search_url, count=1)

    lines = [
        "SUGGESTED_NOT_TERMS: " + ", ".join(suggested),
        "IMPROVED_QUERY_SUGGESTION: " + improved_query,
        "IMPROVED_SEARCH_URL: " + improved_url,
    ]
    text = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    print(text)


if __name__ == "__main__":
    main()
