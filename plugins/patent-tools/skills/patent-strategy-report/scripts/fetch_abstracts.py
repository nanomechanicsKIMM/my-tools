#!/usr/bin/env python3
"""
Fetch patent abstracts and representative claim (claim 1) by crawling the result link from a Google Patents CSV.
Adds 'abstract' and 'representative_claim' columns. Supports --limit, --delay, and --resume.

Usage:
  python fetch_abstracts.py <input_csv> -o <output_csv> [--limit N] [--delay 1.5] [--resume cache.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# User-Agent to reduce block risk
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_csv_with_header_skip(path: str) -> tuple[list[dict], list[str]]:
    """Load CSV; if first line starts with 'search URL', use second line as header."""
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


def extract_abstract_from_html(html: str, url: str = "") -> str:
    """Extract abstract text from Google Patents HTML. Tries multiple strategies."""
    soup = BeautifulSoup(html, "html.parser")

    # 1) meta description (often contains abstract)
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        content = meta["content"].strip()
        if len(content) > 50:
            return content

    # 2) itemprop="abstract"
    for tag in soup.find_all(attrs={"itemprop": "abstract"}):
        t = tag.get_text(separator=" ", strip=True)
        if len(t) > 30:
            return t

    # 3) Section heading "Abstract" then next block of text
    for heading in soup.find_all(["h2", "h3", "h4", "span", "div"]):
        if not heading.get_text(strip=True).strip().lower() == "abstract":
            continue
        # Next sibling or parent's next sibling that has text
        parent = heading.parent
        if not parent:
            continue
        parts = []
        for sib in parent.find_next_siblings():
            text = sib.get_text(separator=" ", strip=True)
            if not text:
                continue
            if re.match(r"^(Description|Claims|Citations|Classifications)", text, re.I):
                break
            if len(text) > 20:
                parts.append(text)
            if len(parts) >= 3:  # cap at a few paragraphs
                break
        if parts:
            return " ".join(parts)

    # 4) Any div/section with class containing 'abstract'
    for tag in soup.find_all(class_=re.compile(r"abstract", re.I)):
        t = tag.get_text(separator=" ", strip=True)
        if 50 < len(t) < 5000:
            return t

    # 5) Raw text: between "Abstract" and "Description" or "Claims"
    raw = soup.get_text(separator="\n")
    abstract_match = re.search(r"\bAbstract\b\s*\n+([^\n]+(?:\n(?!\s*(?:Description|Claims|Citations|Classifications)\b)[^\n]+)*)", raw, re.I | re.DOTALL)
    if abstract_match:
        t = abstract_match.group(1).strip()
        t = re.sub(r"\s+", " ", t)
        if 30 < len(t) < 5000:
            return t

    return ""


def extract_representative_claim_from_html(html: str, url: str = "") -> str:
    """Extract representative claim (Claim 1) text from Google Patents HTML."""
    soup = BeautifulSoup(html, "html.parser")
    raw = soup.get_text(separator="\n")

    # 1) Between "Claim 1" / "1." and "Claim 2" / "2." or "Description" or end of claims block
    for pattern in [
        r"(?:Claim\s+1|1\.)\s*\n+([\s\S]*?)(?=\n\s*(?:Claim\s+2|2\.)\s|Description\s|Detailed\s+Description\s|\Z)",
        r"\bClaim\s+1\b[:\s]*([^\n]+(?:\n(?!\s*Claim\s+2\b|\s*2\.\s)[^\n]+)*)",
        r"\n1\.\s+([^\n]+(?:\n(?!(?:\d+\.\s|Claim\s+\d+|Description\b))[^\n]+)*)",
    ]:
        m = re.search(pattern, raw, re.I | re.MULTILINE)
        if m:
            t = re.sub(r"\s+", " ", m.group(1).strip())
            if 20 < len(t) < 8000:
                return t

    # 2) itemprop="claim" or class containing claim
    for tag in soup.find_all(attrs={"itemprop": re.compile(r"claim", re.I)}):
        t = tag.get_text(separator=" ", strip=True)
        if 30 < len(t) < 8000:
            return t
    for tag in soup.find_all(class_=re.compile(r"claim", re.I)):
        t = tag.get_text(separator=" ", strip=True)
        if 30 < len(t) < 8000 and "claim" in t.lower()[:50]:
            return t

    # 3) Section "Claims" then first substantial block
    for heading in soup.find_all(["h2", "h3", "h4", "span", "div"]):
        if "claim" not in heading.get_text(strip=True).lower():
            continue
        parent = heading.parent
        if not parent:
            continue
        parts = []
        for sib in parent.find_next_siblings():
            text = sib.get_text(separator=" ", strip=True)
            if not text or len(text) < 30:
                continue
            if re.match(r"^(Description|Abstract|Citations|Classifications)", text, re.I):
                break
            parts.append(text)
            if len(parts) >= 1:
                break
        if parts:
            return re.sub(r"\s+", " ", parts[0])[:8000]

    return ""


def fetch_abstract_and_claim(url: str, session: requests.Session) -> tuple[str, str]:
    """GET URL and return (abstract, representative_claim)."""
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text
        abstract = extract_abstract_from_html(html, url)
        claim = extract_representative_claim_from_html(html, url)
        return abstract, claim
    except Exception as e:
        return f"[fetch error: {e}]", ""


def main():
    ap = argparse.ArgumentParser(description="Crawl patent pages from CSV and add abstract column")
    ap.add_argument("input_csv", help="Input Google Patents CSV (with result link column)")
    ap.add_argument("-o", "--output", required=True, help="Output CSV path (with abstract column)")
    ap.add_argument("--limit", type=int, default=0, help="Max number of rows to process (0 = all)")
    ap.add_argument("--delay", type=float, default=1.5, help="Seconds to wait between requests")
    ap.add_argument("--resume", help="JSON file with {id: abstract} to skip already fetched")
    ap.add_argument("--link-column", default="result link", help="Column name for patent page URL")
    args = ap.parse_args()

    rows, header = load_csv_with_header_skip(args.input_csv)
    if not rows:
        print("No rows in CSV", file=sys.stderr)
        sys.exit(1)

    link_col = args.link_column
    if link_col not in header and "result link" in (r.get("result link") for r in rows[:1] if r):
        link_col = "result link"
    if link_col not in header:
        for c in header:
            if "link" in c.lower() or "url" in c.lower():
                link_col = c
                break
    if not any(link_col in r for r in rows[:1]):
        print("No link column found", file=sys.stderr)
        sys.exit(1)

    resume = {}
    if args.resume and Path(args.resume).exists():
        with open(args.resume, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Support both legacy {id: abstract_str} and {id: {abstract, representative_claim}}
            for k, v in data.items():
                if isinstance(v, dict):
                    resume[k] = v
                else:
                    resume[k] = {"abstract": str(v), "representative_claim": ""}

    out_header = list(header)
    for col in ("abstract", "representative_claim"):
        if col not in out_header:
            out_header.append(col)

    session = requests.Session()
    total = len(rows) if args.limit <= 0 else min(args.limit, len(rows))
    id_col = "id" if "id" in header else (header[0] if header else "id")

    for i, row in enumerate(rows):
        if args.limit > 0 and i >= args.limit:
            break
        pid = row.get(id_col, str(i))
        if pid in resume:
            cached = resume[pid]
            if isinstance(cached, dict):
                row["abstract"] = cached.get("abstract", "")
                row["representative_claim"] = cached.get("representative_claim", "")
            else:
                row["abstract"] = str(cached)
                row["representative_claim"] = ""
        else:
            url = row.get(link_col, "").strip()
            if not url or not url.startswith("http"):
                row["abstract"] = ""
                row["representative_claim"] = ""
            else:
                abstract, claim = fetch_abstract_and_claim(url, session)
                row["abstract"] = abstract
                row["representative_claim"] = claim
                resume[pid] = {"abstract": abstract, "representative_claim": claim}
                time.sleep(args.delay)
        if (i + 1) % 50 == 0:
            print(f"Fetched {i + 1}/{total} ...", file=sys.stderr)
            if args.resume:
                with open(args.resume, "w", encoding="utf-8") as f:
                    json.dump(resume, f, ensure_ascii=False, indent=0)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    if args.resume:
        with open(args.resume, "w", encoding="utf-8") as f:
            json.dump(resume, f, ensure_ascii=False, indent=0)

    print(f"Wrote {args.output} with {total} rows (abstract + representative_claim columns added).")


if __name__ == "__main__":
    main()
