#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Google Patents search queries from RFP markdown.

Modes:
  1. Main query:    python generate_query.py <rfp.md> [-o query_main.txt] [--years 10]
  2. Sub-tech queries: python generate_query.py <rfp.md> --sub-tech-json sub_techs.json
                       [-o queries_sub_techs.md] [--years 10]
  3. Single sub-tech:  python generate_query.py <rfp.md> --sub-tech-id sub1
                       --sub-tech-json sub_techs.json

Query construction:
  Main: (group1 OR ...) AND (group2 OR ...) — broad coverage of RFP
  Sub-tech: (key_terms OR ...) AND (group1 OR ...) — narrower, focused
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus


# ── Term limits ───────────────────────────────────────────────────────────────
MAX_TERMS_PER_GROUP = 10
MAX_GROUPS = 3


# ── RFP field extraction ──────────────────────────────────────────────────────

SECTION_PATTERNS = {
    "title": [r"사업명", r"RFP명", r"과제명", r"title"],
    "keywords_en": [r"영문\s*키워드", r"English\s+keyword", r"keyword"],
    "keywords_ko": [r"한글\s*키워드", r"키워드"],
    "objectives": [r"과제목표", r"연구목표", r"기술목표", r"개발목표"],
    "contents": [r"연구개발내용", r"개발내용", r"연구내용"],
}


def load_rfp(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_sub_techs(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_field(text: str, patterns: list[str], max_chars: int = 500) -> str:
    for pat in patterns:
        m = re.search(
            r"(?:#{1,4}\s*|[*_]{0,2})(?:" + pat + r")(?:[*_]{0,2})[\s:：]*([^\n]{1,200})",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if m:
            return m.group(1).strip()
    return ""


def extract_rfp_english_keywords(rfp_text: str) -> list[str]:
    """
    Extract explicitly listed English keywords from the RFP.
    Matches table cell patterns like: '영문 | Display, Transformable, Deformation sensing...'
    Falls back to scanning the keywords_en section.
    Returns deduplicated list; multi-word phrases kept as-is.
    """
    # Pattern 1: table cell with 영문 key (PDF→MD typical format)
    m = re.search(
        r"영문[^\n|]{0,15}[|：:]\s*([A-Za-z][^|\n]{5,300})",
        rfp_text,
        re.IGNORECASE,
    )
    if m:
        terms_str = m.group(1).strip().split("|")[0].strip()
        terms = [t.strip() for t in re.split(r"[,，、]", terms_str) if t.strip()]
        return [t for t in terms if len(t) >= 2]

    # Pattern 2: inline "English keyword: ..." or section-based extraction
    m = re.search(
        r"(?:English\s+[Kk]eyword|keywords?)[^\n:：]{0,20}[：:]\s*([A-Za-z][^\n]{5,200})",
        rfp_text,
        re.IGNORECASE,
    )
    if m:
        terms_str = m.group(1).strip()
        terms = [t.strip() for t in re.split(r"[,，、]", terms_str) if t.strip()]
        return [t for t in terms if len(t) >= 2]

    return []


def extract_section_text(text: str, patterns: list[str], max_chars: int = 1000) -> str:
    for pat in patterns:
        m = re.search(
            r"(?:#{1,4}\s+)(?:.*?" + pat + r".*?)\n([\s\S]*?)(?=\n#{1,4}\s+|\Z)",
            text, re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()[:max_chars]
    return ""


def extract_english_keywords(text: str, max_terms: int = MAX_TERMS_PER_GROUP) -> list[str]:
    """Extract English technical terms suitable for Google Patents search."""
    # Quoted phrases first (highest quality)
    phrases = re.findall(r'"([^"]{3,40})"', text)
    # CamelCase and hyphenated terms
    camel = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", text)
    # Regular English terms (4+ chars)
    words = re.findall(r"\b[a-zA-Z]{4,20}\b", text)

    # Filter stopwords
    stopwords = {
        "this", "that", "with", "from", "they", "have", "been", "will",
        "also", "more", "than", "such", "other", "each", "some", "into",
        "only", "over", "then", "both", "very", "make", "like", "time",
        "when", "which", "where", "there", "these", "those", "their",
        "used", "uses", "using", "based", "high", "low", "new", "good",
        "data", "type", "part", "area", "unit", "case", "work", "form",
    }
    all_terms = []
    seen = set()
    for t in phrases + camel + words:
        tl = t.lower().strip()
        if tl not in stopwords and len(tl) >= 3 and tl not in seen:
            seen.add(tl)
            all_terms.append(t)
        if len(all_terms) >= max_terms * 2:
            break

    return all_terms[:max_terms]


def build_and_groups(groups: list[list[str]], exclude_terms: list[str] = None) -> str:
    """Build (g1_t1 OR g1_t2) AND (g2_t1 OR g2_t2) query."""
    if not groups:
        return ""
    parts = []
    for g in groups:
        if not g:
            continue
        quoted = [f'"{t}"' if " " in t else t for t in g[:MAX_TERMS_PER_GROUP]]
        if len(quoted) == 1:
            parts.append(quoted[0])
        else:
            parts.append("(" + " OR ".join(quoted) + ")")
    query = " AND ".join(parts)
    if exclude_terms:
        exc_quoted = [f'"{t}"' if " " in t else t for t in exclude_terms]
        query += " NOT (" + " OR ".join(exc_quoted) + ")"
    return query


def date_range_params(years: int) -> tuple[str, str]:
    """Return (after_param, before_param) for the given year range."""
    current_year = datetime.now().year
    after_year = current_year - years
    return f"{after_year}0101", f"{current_year}1231"


def build_search_url(query: str, years: int) -> str:
    after, before = date_range_params(years)
    encoded = quote_plus(query)
    return (
        f"https://patents.google.com/?q={encoded}"
        f"&after=priority:{after}&before=priority:{before}"
    )


# ── Main query generation ─────────────────────────────────────────────────────

def generate_main_query(rfp_text: str, years: int = 10,
                         exclude_terms: list[str] = None,
                         required_terms: list[str] = None) -> dict:
    """Generate main search query covering full RFP scope."""
    # Priority 1: explicitly listed RFP English keywords
    rfp_explicit = extract_rfp_english_keywords(rfp_text)

    # Priority 2: heuristic extraction from objectives/contents sections
    heuristic = extract_english_keywords(
        extract_field(rfp_text, SECTION_PATTERNS["keywords_en"]) + "\n" +
        extract_section_text(rfp_text, SECTION_PATTERNS["objectives"]) + "\n" +
        extract_section_text(rfp_text, SECTION_PATTERNS["contents"])
    )

    # Merge: explicit keywords first, then heuristic (deduplicated)
    seen: set[str] = set()
    keywords_en: list[str] = []
    for t in rfp_explicit + heuristic:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            keywords_en.append(t)

    # Split into 2 groups: core (first half) and context (second half)
    mid = max(1, len(keywords_en) // 2)
    group1 = keywords_en[:mid]
    group2 = keywords_en[mid:mid + MAX_TERMS_PER_GROUP]

    groups = [g for g in [group1, group2] if g]

    if required_terms:
        groups.insert(0, required_terms)

    query = build_and_groups(groups, exclude_terms)
    url = build_search_url(query, years)
    after, before = date_range_params(years)

    return {
        "type": "main",
        "query": query,
        "url": url,
        "years": years,
        "date_from": after,
        "date_to": before,
        "groups": groups,
        "exclude_terms": exclude_terms or [],
    }


# ── Sub-tech query generation ─────────────────────────────────────────────────

def generate_sub_tech_query(sub_tech: dict, rfp_text: str,
                              years: int = 10,
                              global_exclude: list[str] = None,
                              global_required: list[str] = None) -> dict:
    """
    Generate focused search query for a single sub-technology.
    Query structure (when global_required is set):
      (global_required OR ...) AND (key_terms OR ...) NOT (excludes)
    This ensures sub-tech results are a subset of the main query scope.

    Guarantees at least 3 terms in key_terms group:
      1. sub_tech.key_terms (primary)
      2. RFP explicit English keywords (fallback supplement)
      3. Heuristic extraction from RFP objectives (last resort)
    """
    key_terms = sub_tech.get("key_terms", [])
    exclude = list(set((global_exclude or []) + sub_tech.get("exclude_terms", [])))

    # Priority 1: use key_terms from sub_tech definition
    group_core = list(key_terms[:MAX_TERMS_PER_GROUP])
    key_set = {t.lower() for t in group_core}

    # Priority 2: if key_terms < 3, supplement from RFP explicit English keywords
    if len(group_core) < 3:
        rfp_explicit = extract_rfp_english_keywords(rfp_text)
        for t in rfp_explicit:
            if t.lower() not in key_set and len(group_core) < 6:
                group_core.append(t)
                key_set.add(t.lower())

    # Priority 3: still < 3 → heuristic extraction from objectives
    if len(group_core) < 3:
        heuristic = extract_english_keywords(
            extract_section_text(rfp_text, SECTION_PATTERNS["objectives"]) + "\n" +
            extract_field(rfp_text, SECTION_PATTERNS["keywords_en"])
        )
        for t in heuristic:
            if t.lower() not in key_set and len(group_core) < 6:
                group_core.append(t)
                key_set.add(t.lower())

    # Build groups: global_required first (AND), then sub-tech core (AND)
    # global_required acts as the "main query scope" gate
    groups: list[list[str]] = []
    if global_required:
        groups.append(list(global_required))
    groups.append(group_core)

    query = build_and_groups(groups, exclude)
    url = build_search_url(query, years)
    after, before = date_range_params(years)

    return {
        "type": "sub_tech",
        "sub_tech_id": sub_tech["id"],
        "name_ko": sub_tech["name_ko"],
        "name_en": sub_tech.get("name_en", ""),
        "query": query,
        "url": url,
        "years": years,
        "date_from": after,
        "date_to": before,
        "key_terms": group_core,  # reflect the actual terms used (including supplements)
        "exclude_terms": exclude,
    }


def format_queries_md(main_result: dict, sub_results: list[dict]) -> str:
    """Format all queries as Obsidian-compatible Markdown."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"---",
        f"title: 특허 검색식 모음",
        f"created: {today}",
        f"tags: [특허검색, 검색식]",
        f"---",
        f"",
        f"# 특허 검색식 모음",
        f"",
        f"## 메인 검색식 (전체 RFP 범위)",
        f"",
        f"```",
        main_result["query"],
        f"```",
        f"",
        f"**검색 URL**: {main_result['url']}",
        f"**기간**: 우선일 {main_result['date_from'][:4]}~{main_result['date_to'][:4]}년",
        f"",
        f"---",
        f"",
        f"## 세부 기술별 검색식",
        f"",
    ]
    for r in sub_results:
        lines += [
            f"### [{r['sub_tech_id']}] {r['name_ko']}",
            f"",
            f"**영문**: {r['name_en']}",
            f"**핵심 키워드**: {', '.join(r['key_terms'])}",
            f"",
            f"```",
            r["query"],
            f"```",
            f"",
            f"**검색 URL**: {r['url']}",
            f"",
            f"---",
            f"",
        ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Generate Google Patents search queries from RFP")
    ap.add_argument("rfp_path", help="RFP markdown file path")
    ap.add_argument("-o", "--output", type=str, default=None,
                    help="Output file path (.txt for main, .md for sub-tech)")
    ap.add_argument("--years", type=int, default=10, help="Search date range in years (default 10)")
    ap.add_argument("--exclude-terms", type=str, default=None,
                    help="Comma-separated terms to exclude")
    ap.add_argument("--required-terms", type=str, default=None,
                    help="Comma-separated terms to require (AND block) for main query")
    ap.add_argument("--global-required-terms", type=str, default=None,
                    help="Comma-separated terms (OR group) prepended as AND gate to every sub-tech query "
                         "— use to make sub-tech results a subset of the main query scope")
    ap.add_argument("--sub-tech-json", type=str, default=None,
                    help="Path to sub_techs.json for sub-technology specific queries")
    ap.add_argument("--sub-tech-id", type=str, default=None,
                    help="Generate query for specific sub-tech ID only (e.g. sub1)")
    args = ap.parse_args()

    rfp_path = Path(args.rfp_path)
    if not rfp_path.exists():
        print(f"RFP not found: {rfp_path}", file=sys.stderr)
        sys.exit(1)

    rfp_text = load_rfp(rfp_path)
    exclude = [t.strip() for t in (args.exclude_terms or "").split(",") if t.strip()]
    required = [t.strip() for t in (args.required_terms or "").split(",") if t.strip()]
    global_required = [t.strip() for t in (args.global_required_terms or "").split(",") if t.strip()]

    # Generate main query
    main_result = generate_main_query(rfp_text, years=args.years,
                                       exclude_terms=exclude or None,
                                       required_terms=required or None)

    # Sub-tech mode
    if args.sub_tech_json:
        sub_data = load_sub_techs(Path(args.sub_tech_json))
        sub_techs = sub_data.get("sub_technologies", [])
        if args.sub_tech_id:
            sub_techs = [s for s in sub_techs if s["id"] == args.sub_tech_id]

        sub_results = [
            generate_sub_tech_query(st, rfp_text, years=args.years,
                                     global_exclude=exclude or None,
                                     global_required=global_required or None)
            for st in sub_techs
        ]

        md_content = format_queries_md(main_result, sub_results)

        out_path = Path(args.output or "queries_sub_techs.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md_content, encoding="utf-8")
        print(f"Generated {len(sub_results)} sub-tech queries → {out_path}")

        # Also print to stdout for immediate use
        for r in sub_results:
            print(f"\n[{r['sub_tech_id']}] {r['name_ko']}")
            print(f"  Query: {r['query']}")
            print(f"  URL:   {r['url']}")

    else:
        # Main query only
        out_path = Path(args.output or "query_main.txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            f"Query: {main_result['query']}\n\nURL: {main_result['url']}\n",
            encoding="utf-8",
        )
        print(f"Query: {main_result['query']}")
        print(f"URL:   {main_result['url']}")
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
