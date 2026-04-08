#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search patents via KIPRIS Plus REST API and export as CSV.

Korean patent search using KIPRIS (Korean Intellectual Property Rights
Information Service) Open API. Supports free-text keyword search and
advanced field-specific search with bibliographic detail retrieval.

Usage:
  # Keyword search (AND = *, OR = +, NOT = !)
  python search_patents_kipris.py --keyword "마이크로LED*전사" -o results.csv

  # Advanced search with field filters
  python search_patents_kipris.py --title "레이저*전사" --ipc "H01L33" -o results.csv

  # With applicant filter
  python search_patents_kipris.py --keyword "플렉서블 디스플레이" --applicant "삼성" -o results.csv

  # Fetch abstracts + representative claims for top N results (detail API calls)
  python search_patents_kipris.py --keyword "인공지능*의료" --with-detail --max-detail 10 -o results.csv

  # JSON output
  python search_patents_kipris.py --keyword "자율주행" --format json -o results.json

Requires:
  pip install requests

Environment variables:
  KIPRIS_API_KEY=<your_api_key>    (from plus.kipris.or.kr or data.go.kr)
  KIPRIS_REST_ACCESS_KEY=<key>     (alternative env var name)

KIPRIS limits: ~1000 API calls/month (free tier), max ~30 results per page.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("requests not installed.\n  pip install requests\n", file=sys.stderr)
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

# NOTE: "Sevice" (missing 'r') is the actual KIPRIS API path — do NOT correct it.
FREE_SEARCH_URL = (
    "http://plus.kipris.or.kr/openapi/rest/"
    "patUtiModInfoSearchSevice/freeSearchInfo"
)
ADVANCED_SEARCH_URL = (
    "http://plus.kipris.or.kr/kipo-api/kipi/"
    "patUtiModInfoSearchSevice/getAdvancedSearch"
)
DETAIL_URL = (
    "http://plus.kipris.or.kr/kipo-api/kipi/"
    "patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch"
)

PAGE_SIZE = 20  # safe default; max ~30
REQUEST_DELAY = 0.7  # seconds between API calls (polite rate limiting)

CSV_COLUMNS = [
    "id",
    "application_number",
    "title",
    "applicant",
    "inventor",
    "application_date",
    "open_number",
    "open_date",
    "register_number",
    "register_date",
    "publication_number",
    "publication_date",
    "ipc",
    "claim_count",
    "representative_claim",
    "abstract",
    "status",
    "kipris_link",
]


# ── API key ──────────────────────────────────────────────────────────────────


def get_api_key(cli_key: str | None = None) -> str:
    """Resolve KIPRIS API key from CLI arg or environment."""
    key = (
        cli_key
        or os.environ.get("KIPRIS_API_KEY")
        or os.environ.get("KIPRIS_REST_ACCESS_KEY")
    )
    if not key:
        print(
            "KIPRIS API key required.\n"
            "Set environment variable KIPRIS_API_KEY or KIPRIS_REST_ACCESS_KEY,\n"
            "or use --key CLI argument.\n"
            "\n"
            "Register at: https://plus.kipris.or.kr or https://www.data.go.kr\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


# ── XML parsing helpers ──────────────────────────────────────────────────────


def _text(el: ET.Element | None) -> str:
    """Extract text from an XML element, returning '' if None."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_search_response(xml_text: str) -> tuple[int, list[dict]]:
    """Parse KIPRIS search response XML into (total_count, items)."""
    root = ET.fromstring(xml_text)

    # Check for error
    result_code = _text(root.find(".//resultCode"))
    if result_code and result_code != "00":
        result_msg = _text(root.find(".//resultMsg"))
        print(f"KIPRIS API error: [{result_code}] {result_msg}", file=sys.stderr)
        return 0, []

    total_count = int(_text(root.find(".//TotalSearchCount")) or "0")

    items = []
    for item in root.iter("PatentUtilityInfo"):
        record = {
            "application_number": _text(item.find("ApplicationNumber")),
            "title": _text(item.find("InventionName")),
            "applicant": _text(item.find("Applicant")),
            "application_date": _text(item.find("ApplicationDate")),
            "abstract": _text(item.find("Abstract")),
            "open_number": _text(item.find("OpeningNumber")),
            "open_date": _text(item.find("OpeningDate")),
            "register_number": _text(item.find("RegistrationNumber")),
            "register_date": _text(item.find("RegistrationDate")),
            "publication_number": _text(item.find("PublicNumber")),
            "publication_date": _text(item.find("PublicDate")),
            "ipc": _text(item.find("InternationalpatentclassificationNumber")),
            "status": _text(item.find("RegistrationStatus")),
            "drawing_path": _text(item.find("DrawingPath")),
            "thumbnail_path": _text(item.find("ThumbnailPath")),
        }
        if record["application_number"]:
            items.append(record)

    return total_count, items


def _parse_detail_response(xml_text: str) -> dict:
    """Parse KIPRIS bibliographic detail response XML."""
    root = ET.fromstring(xml_text)

    result_code = _text(root.find(".//resultCode"))
    if result_code and result_code != "00":
        return {}

    item = root.find(".//item")
    if item is None:
        item = root.find(".//body")
    if item is None:
        return {}

    # Abstract
    abstract = (
        _text(item.find(".//AbstractInfo"))
        or _text(item.find(".//abstractInfo"))
        or _text(item.find(".//astrtCont"))
    )

    # Inventor
    inventor = (
        _text(item.find(".//InventorInfo"))
        or _text(item.find(".//inventorInfo"))
        or _text(item.find(".//invntNm"))
    )

    # Claim count
    claim_count = _text(item.find(".//claimCount")) or "0"

    # Representative claim (claim 1) — collect all <claim> elements, take first
    claims = [_text(c) for c in root.iter("claim")]
    representative_claim = ""
    if claims:
        # First claim is the representative (independent) claim
        representative_claim = claims[0].strip()
    else:
        # Fallback: try ClaimInfo / claimInfo as single text
        raw = (
            _text(item.find(".//ClaimInfo"))
            or _text(item.find(".//claimInfo"))
        )
        if raw:
            # Extract claim 1 from concatenated text
            first_end = raw.find("2.")
            representative_claim = raw[:first_end].strip() if first_end > 0 else raw.strip()

    detail = {
        "abstract": abstract,
        "inventor": inventor,
        "claim_count": claim_count,
        "representative_claim": representative_claim,
    }
    return detail


# ── Search functions ─────────────────────────────────────────────────────────


def search_free(
    api_key: str,
    keyword: str,
    max_results: int = 50,
    sort_by: str = "AD",
    desc: bool = True,
    patent: bool = True,
    utility: bool = True,
) -> tuple[int, list[dict]]:
    """Free-text keyword search via KIPRIS."""
    all_items: list[dict] = []
    page = 1
    total_count = 0

    while len(all_items) < max_results:
        params = {
            "accessKey": api_key,
            "word": keyword,
            "patent": str(patent).lower(),
            "utility": str(utility).lower(),
            "docsStart": (page - 1) * PAGE_SIZE + 1,
            "docsCount": PAGE_SIZE,
            "sortSpec": sort_by,
            "descSort": str(desc).lower(),
        }

        try:
            resp = requests.get(FREE_SEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"KIPRIS request failed (page {page}): {e}", file=sys.stderr)
            break

        count, items = _parse_search_response(resp.text)
        if page == 1:
            total_count = count
            if total_count == 0:
                break

        if not items:
            break

        all_items.extend(items)
        page += 1

        if len(all_items) >= total_count:
            break

        time.sleep(REQUEST_DELAY)

    return total_count, all_items[:max_results]


def search_advanced(
    api_key: str,
    title: str | None = None,
    abstract: str | None = None,
    claims: str | None = None,
    applicant: str | None = None,
    inventor: str | None = None,
    ipc: str | None = None,
    app_date_from: str | None = None,
    app_date_to: str | None = None,
    max_results: int = 50,
    sort_by: str = "AD",
    desc: bool = True,
) -> tuple[int, list[dict]]:
    """Advanced field-specific search via KIPRIS."""
    all_items: list[dict] = []
    page = 1
    total_count = 0

    while len(all_items) < max_results:
        params: dict = {
            "ServiceKey": api_key,
            "docsStart": (page - 1) * PAGE_SIZE + 1,
            "docsCount": PAGE_SIZE,
            "sortSpec": sort_by,
            "descSort": str(desc).lower(),
            "patent": "true",
            "utility": "true",
        }
        if title:
            params["inventionTitle"] = title
        if abstract:
            params["abstCont"] = abstract
        if claims:
            params["claimScope"] = claims
        if applicant:
            params["applicant"] = applicant
        if inventor:
            params["inventor"] = inventor
        if ipc:
            params["ipcNumber"] = ipc
        if app_date_from and app_date_to:
            params["applicationDate"] = f"{app_date_from}~{app_date_to}"

        try:
            resp = requests.get(ADVANCED_SEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"KIPRIS advanced search failed (page {page}): {e}", file=sys.stderr)
            break

        count, items = _parse_search_response(resp.text)
        if page == 1:
            total_count = count
            if total_count == 0:
                break

        if not items:
            break

        all_items.extend(items)
        page += 1

        if len(all_items) >= total_count:
            break

        time.sleep(REQUEST_DELAY)

    return total_count, all_items[:max_results]


def fetch_detail(api_key: str, application_number: str) -> dict:
    """Fetch bibliographic detail (abstract, claims) for a single patent."""
    params = {
        "ServiceKey": api_key,
        "applicationNumber": application_number.replace("-", ""),
    }
    try:
        resp = requests.get(DETAIL_URL, params=params, timeout=30)
        resp.raise_for_status()
        return _parse_detail_response(resp.text)
    except requests.RequestException as e:
        print(
            f"Detail fetch failed for {application_number}: {e}", file=sys.stderr
        )
        return {}


def enrich_with_details(
    api_key: str, items: list[dict], max_detail: int = 10
) -> list[dict]:
    """Enrich top N search results with abstract, representative claim, and claim count."""
    for i, item in enumerate(items[:max_detail]):
        app_num = item.get("application_number", "")
        if not app_num:
            continue
        detail = fetch_detail(api_key, app_num)
        if detail.get("abstract"):
            item["abstract"] = detail["abstract"]
        if detail.get("inventor") and not item.get("inventor"):
            item["inventor"] = detail["inventor"]
        item["claim_count"] = detail.get("claim_count", "")
        item["representative_claim"] = detail.get("representative_claim", "")
        if i < max_detail - 1:
            time.sleep(REQUEST_DELAY)
    return items


# ── KIPRIS link builder ──────────────────────────────────────────────────────


def kipris_link(application_number: str) -> str:
    """Build a KIPRIS detail page URL."""
    num = application_number.replace("-", "")
    return f"http://kpat.kipris.or.kr/kpat/biblioa.do?method=biblioFrame&applno={num}"


# ── Output writers ───────────────────────────────────────────────────────────


def write_csv(items: list[dict], output_path: str) -> None:
    """Write search results to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for i, item in enumerate(items, 1):
            item["id"] = str(i)
            item["kipris_link"] = kipris_link(item.get("application_number", ""))
            writer.writerow(item)

    print(f"Wrote {len(items)} results to {path}", file=sys.stderr)


def write_json(items: list[dict], output_path: str) -> None:
    """Write search results to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(items, 1):
        item["id"] = str(i)
        item["kipris_link"] = kipris_link(item.get("application_number", ""))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(items)} results to {path}", file=sys.stderr)


# ── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search Korean patents via KIPRIS Plus REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Search mode
    g = p.add_argument_group("Search")
    g.add_argument(
        "--keyword", "-k",
        help="Free-text keyword (AND=*, OR=+, NOT=!). e.g. '마이크로LED*전사'",
    )
    g.add_argument("--title", help="Title field search (advanced)")
    g.add_argument("--abstract", help="Abstract field search (advanced)")
    g.add_argument("--claims", help="Claims field search (advanced)")
    g.add_argument("--applicant", help="Applicant name filter")
    g.add_argument("--inventor", help="Inventor name filter")
    g.add_argument("--ipc", help="IPC classification code (e.g. H01L33)")
    g.add_argument(
        "--date-from",
        help="Application date start (YYYYMMDD)",
    )
    g.add_argument(
        "--date-to",
        help="Application date end (YYYYMMDD)",
        default=datetime.now().strftime("%Y%m%d"),
    )

    # Options
    o = p.add_argument_group("Options")
    o.add_argument(
        "--max-results", "-n", type=int, default=50,
        help="Maximum number of search results (default: 50)",
    )
    o.add_argument(
        "--with-detail", action="store_true",
        help="Fetch abstract + representative claim via detail API (slower)",
    )
    o.add_argument(
        "--max-detail", type=int, default=10,
        help="Max results to fetch detail for (default: 10)",
    )
    o.add_argument(
        "--sort", choices=["AD", "PD", "GD", "OPD"], default="AD",
        help="Sort field: AD=출원일, PD=공고일, GD=등록일, OPD=공개일 (default: AD)",
    )
    o.add_argument("--asc", action="store_true", help="Sort ascending (default: desc)")

    # Auth
    a = p.add_argument_group("Authentication")
    a.add_argument("--key", help="KIPRIS API key (overrides env var)")

    # Output
    p.add_argument(
        "-o", "--output", required=True,
        help="Output file path (.csv or .json)",
    )
    p.add_argument(
        "--format", choices=["csv", "json"], default=None,
        help="Output format (auto-detected from extension if omitted)",
    )

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    api_key = get_api_key(args.key)

    # Determine search mode
    use_advanced = any([args.title, args.abstract, args.claims, args.ipc])

    if use_advanced:
        print("Using KIPRIS advanced search...", file=sys.stderr)
        total, items = search_advanced(
            api_key,
            title=args.title,
            abstract=args.abstract,
            claims=args.claims,
            applicant=args.applicant,
            inventor=args.inventor,
            ipc=args.ipc,
            app_date_from=args.date_from,
            app_date_to=args.date_to,
            max_results=args.max_results,
            sort_by=args.sort,
            desc=not args.asc,
        )
    elif args.keyword:
        print("Using KIPRIS free-text search...", file=sys.stderr)
        total, items = search_free(
            api_key,
            keyword=args.keyword,
            max_results=args.max_results,
            sort_by=args.sort,
            desc=not args.asc,
        )
    else:
        parser.error("Provide --keyword for free search or --title/--abstract/--ipc for advanced search")
        return

    print(f"Total found: {total}, retrieved: {len(items)}", file=sys.stderr)

    # Enrich with detail (abstract + representative claim) if requested
    if args.with_detail and items:
        print(
            f"Fetching details for top {min(args.max_detail, len(items))} results...",
            file=sys.stderr,
        )
        items = enrich_with_details(api_key, items, args.max_detail)

    # Determine output format
    fmt = args.format
    if fmt is None:
        fmt = "json" if args.output.endswith(".json") else "csv"

    if fmt == "json":
        write_json(items, args.output)
    else:
        write_csv(items, args.output)


if __name__ == "__main__":
    main()
