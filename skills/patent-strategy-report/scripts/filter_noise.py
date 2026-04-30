#!/usr/bin/env python3
"""
Filter noise from a Google Patents CSV using RFP relevance.
Two modes:
  1. Keyword-based: score each row by RFP keyword overlap; drop rows below threshold.
  2. LLM-assisted: --prepare-batch writes (row_id, title, abstract) for agent/LLM;
     --apply-labels <file> reads labels and writes filtered CSV.

When REMOVAL_RATIO > 10%, suggests NOT terms from noise (frequent words in removed rows)
and an improved search query for the next round (user re-downloads CSV and re-runs).

Usage:
  python filter_noise.py <csv_path> <rfp_path> [--output PATH] [--threshold 0.15] [--current-query "query"]
  python filter_noise.py <csv_path> <rfp_path> --prepare-batch [--sample N] --output-batch batch.jsonl
  python filter_noise.py <csv_path> --apply-labels labels.jsonl [--output PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def load_rfp_keywords(rfp_path: str) -> list[str]:
    """Extract Korean and English keywords from RFP for scoring."""
    with open(rfp_path, "r", encoding="utf-8") as f:
        text = f.read()
    keywords = []
    # 영문
    for m in re.finditer(r"영문\s*[:\s]+([^\n#\-]+)", text, re.I):
        keywords.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", m.group(1)))
    for m in re.finditer(r"\*\*영문\*\*[:\s]*([^\n]+)", text):
        keywords.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", m.group(1)))
    # 한글 (multi-char terms)
    for m in re.finditer(r"한글\s*[:\s]+([^\n#\-]+)", text):
        keywords.extend(re.findall(r"[가-힣]+", m.group(1)))
    # RFP명 / 사업명: first line of technical description
    for m in re.finditer(r"RFP명\s*\n?\s*([^\n|#]+)", text):
        keywords.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*|[가-힣]+", m.group(1)))
    # Normalize and dedupe
    seen = set()
    out = []
    for k in keywords:
        k = k.strip().lower() if k.isascii() else k.strip()
        if len(k) < 2:
            continue
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def load_csv_rows(csv_path: str) -> tuple[list[dict], list[str]]:
    """Load CSV and return (list of row dicts, column names)."""
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    start = 0
    if lines and lines[0].strip().lower().startswith("search url"):
        start = 1
    if start >= len(lines):
        return [], []
    header = next(csv.reader([lines[start]]))
    rows = list(csv.DictReader(lines[start + 1 :], fieldnames=header))
    return rows, header


def text_for_scoring(row: dict) -> str:
    """Concatenate title and abstract-like columns for keyword scoring."""
    # Common Google Patents export column names (EN)
    parts = []
    for key in ["title", "Title", "title_en", "Title (English)"]:
        if key in row and row[key]:
            parts.append(str(row[key]))
            break
    for key in ["abstract", "Abstract", "abstract_en", "Abstract (English)", "snippet", "description"]:
        if key in row and row[key]:
            parts.append(str(row[key]))
            break
    if not parts:
        parts = [str(v) for v in row.values() if v]
    return " ".join(parts)


def keyword_score(text: str, keywords: list[str]) -> float:
    """Return fraction of keywords (by type) that appear in text. Normalize text for matching."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    text_ko = " ".join(re.findall(r"[가-힣]+", text))
    hit = 0
    for k in keywords:
        if k.isascii():
            if k.lower() in text_lower:
                hit += 1
        else:
            if k in text_ko:
                hit += 1
    return hit / len(keywords)


def filter_by_keyword(
    rows: list[dict],
    keywords: list[str],
    threshold: float,
    text_fn=None,
) -> tuple[list[dict], list[dict], float]:
    """Split rows into keep vs noise by keyword score. Returns (keep, noise, removal_ratio)."""
    if text_fn is None:
        text_fn = text_for_scoring
    keep, noise = [], []
    for row in rows:
        t = text_fn(row)
        s = keyword_score(t, keywords)
        if s >= threshold:
            keep.append(row)
        else:
            noise.append(row)
    total = len(rows)
    removal_ratio = len(noise) / total if total else 0.0
    return keep, noise, removal_ratio


def write_csv(rows: list[dict], cols: list[str], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# Minimal English stopwords + generic patent terms (do not suggest as NOT)
_STOP = frozenset(
    "the a an and or of in to for is on with as by at from that this it its be are was were been have has had do does did will would could should may might can must "
    "method device system apparatus systems devices methods using data unit circuit layer component "
    "sensor sensing detection".split()
)


def tokenize_for_not_terms(text: str) -> list[str]:
    """Extract candidate terms (English words, len>=3) for NOT suggestion. Lowercased."""
    if not text:
        return []
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", text)
    out = []
    for w in words:
        w = w.lower()
        if len(w) < 3 or w in _STOP or w.isdigit():
            continue
        out.append(w)
    return out


def suggest_not_terms_from_noise(
    noise_rows: list[dict],
    keep_rows: list[dict],
    text_fn,
    exclude_terms: set[str],
    top_n: int = 5,
    min_noise_count: int = 2,
) -> list[str]:
    """
    Suggest NOT terms from frequent words in noise that are relatively rare in keep.
    Returns list of terms (order: most indicative of noise first).
    """
    from collections import Counter
    noise_tokens = []
    for r in noise_rows:
        noise_tokens.extend(tokenize_for_not_terms(text_fn(r)))
    keep_tokens = []
    for r in keep_rows:
        keep_tokens.extend(tokenize_for_not_terms(text_fn(r)))
    noise_cnt = Counter(noise_tokens)
    keep_cnt = Counter(keep_tokens)
    candidates = []
    for term, n_count in noise_cnt.most_common():
        if term in exclude_terms or n_count < min_noise_count:
            continue
        k_count = keep_cnt.get(term, 0)
        score = n_count - k_count
        if score <= 0:
            continue
        candidates.append((term, score, n_count))
    candidates.sort(key=lambda x: (-x[1], -x[2]))
    return [t[0] for t in candidates[:top_n]]


def parse_query_terms(current_query: str) -> set[str]:
    """Extract simple tokens from query string to exclude from NOT suggestion."""
    if not current_query or not current_query.strip():
        return set()
    q = re.sub(r"NOT\s*\([^)]*\)", "", current_query, flags=re.I)
    q = re.sub(r"[()\"]", " ", q)
    tokens = set()
    for w in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", q):
        w = w.lower()
        if len(w) >= 2 and w not in ("and", "or", "not"):
            tokens.add(w)
    return tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="Path to Google Patents CSV")
    ap.add_argument("rfp_path", nargs="?", default=None, help="Path to RFP markdown (required for keyword mode)")
    ap.add_argument("--output", "-o", help="Output filtered CSV path")
    ap.add_argument("--threshold", "-t", type=float, default=0.15, help="Keyword score threshold (keep if >=)")
    ap.add_argument("--current-query", default="", help="Search query used for this CSV; used to suggest improved query when REMOVAL_RATIO > 10 pct")
    ap.add_argument("--suggest-top-n", type=int, default=5, help="Max number of NOT terms to suggest (default 5)")
    ap.add_argument("--prepare-batch", action="store_true", help="Write batch of (id, title, abstract) for LLM labeling")
    ap.add_argument("--output-batch", help="Output path for batch JSONL")
    ap.add_argument("--sample", type=int, default=0, help="If set, only sample N rows for batch (0 = all)")
    ap.add_argument("--apply-labels", help="Path to JSONL with row_id and is_noise (true/false); filter CSV")
    args = ap.parse_args()

    rows, cols = load_csv_rows(args.csv_path)
    if not rows:
        print("No rows in CSV", file=sys.stderr)
        sys.exit(1)

    if args.apply_labels:
        # Apply labels from LLM batch
        with open(args.apply_labels, "r", encoding="utf-8") as f:
            labels = {str(item["row_id"]): item.get("is_noise", item.get("noise", True)) for item in (json.loads(line) for line in f if line.strip())}
        keep = [r for i, r in enumerate(rows) if not labels.get(str(i), False)]
        out_path = args.output or args.csv_path.replace(".csv", "_filtered.csv")
        write_csv(keep, cols, out_path)
        print(f"Filtered: {len(keep)} kept, {len(rows) - len(keep)} removed. Written to {out_path}")
        print(f"REMOVAL_RATIO: {(len(rows) - len(keep)) / len(rows):.4f}")
        return

    if args.prepare_batch:
        batch_path = args.output_batch or "batch.jsonl"
        sample = rows if (args.sample <= 0 or args.sample >= len(rows)) else rows[: args.sample]
        with open(batch_path, "w", encoding="utf-8") as f:
            for i, row in enumerate(sample):
                obj = {"row_id": i, "title": row.get("title", row.get("Title", "")), "abstract": row.get("abstract", row.get("Abstract", ""))[:2000]}
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print(f"Wrote {len(sample)} rows to {batch_path}. Label with LLM then run --apply-labels <labels.jsonl>")
        return

    if not args.rfp_path:
        print("rfp_path required for keyword filtering", file=sys.stderr)
        sys.exit(1)

    keywords = load_rfp_keywords(args.rfp_path)
    keep, noise, removal_ratio = filter_by_keyword(rows, keywords, args.threshold)
    out_path = args.output or args.csv_path.replace(".csv", "_filtered.csv")
    write_csv(keep, cols, out_path)

    print(f"Total: {len(rows)}, Kept: {len(keep)}, Removed: {len(noise)}")
    print(f"REMOVAL_RATIO: {removal_ratio:.4f}")
    print(f"Output: {out_path}")
    if removal_ratio > 0.10 and noise:
        exclude = set(k.lower() if k.isascii() else k for k in keywords)
        if args.current_query:
            exclude |= parse_query_terms(args.current_query)
        suggested = suggest_not_terms_from_noise(
            noise, keep, text_for_scoring, exclude, top_n=args.suggest_top_n
        )
        if suggested:
            print("SUGGESTED_NOT_TERMS:", ", ".join(suggested))
            base = (args.current_query or "").strip()
            not_part = " NOT (" + " OR ".join(suggested) + ")"
            improved = (base + not_part) if base else ("NOT (" + " OR ".join(suggested) + ")")
            print("IMPROVED_QUERY_SUGGESTION:", improved)
        else:
            print("REMOVAL_RATIO > 0.10: consider refining query (add NOT terms) and re-downloading CSV, then re-run filter.")
    elif removal_ratio > 0.10:
        print("REMOVAL_RATIO > 0.10: consider refining query (add NOT terms) and re-downloading CSV, then re-run filter.")
