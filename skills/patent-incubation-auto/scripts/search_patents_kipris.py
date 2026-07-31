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

  # Verify both endpoints still behave as expected (no -o needed)
  python search_patents_kipris.py --selftest

Search mode selection:
  --keyword hits freeSearchInfo. It is LOW PRECISION — "마이크로LED*전사" matches
  13k+ documents and, sorted by application date, surfaces unrelated art. Prefer
  the field search (--title/--abstract/--claims/--ipc/--applicant/--inventor),
  which ANDs its fields, for prior-art screening.

  --ipc matches the code as written: "H01L33" and "H01L 33/00" are different
  queries. Try both.

Exit codes:
  0  success (0 hits is a valid success — the query simply matched nothing)
  1  bad usage / missing API key / --selftest found a failure
  2  KIPRIS returned an API error; NO output file is written, so an API failure
     is never mistaken for "no prior art found"

Requires:
  pip install requests

API key resolution (first match wins):
  --key CLI argument
  any environment variable whose name contains "kipris" and "key"
    (case- and underscore-insensitive, e.g. KIPRIS_API_KEY, KIPRIS_REST_AccessKey)
  the .env file at DEFAULT_ENV_FILE, overridable via KIPRIS_ENV_FILE

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


DEFAULT_ENV_FILE = Path.home() / "Claude_Work" / ".env"


def _key_from_env_file(env_file: Path) -> str | None:
    """Read a KIPRIS key straight from a .env file.

    Shell `set -a; eval $(cat .env)` loading is case-sensitive and chokes on
    `NAME = value` spacing, so the key silently goes missing. Parsing here makes
    the script independent of how (or whether) the caller sourced the file.
    """
    if not env_file.is_file():
        return None
    try:
        text = env_file.read_text(encoding="utf-8-sig")
    except OSError:
        return None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip().lower().replace("_", "")
        if "kipris" in name and "key" in name:
            value = value.strip().strip("'\"")
            if value:
                return value
    return None


def get_api_key(cli_key: str | None = None) -> str:
    """Resolve KIPRIS API key from CLI arg, environment, or the .env file."""
    key = cli_key
    if not key:
        for name, value in os.environ.items():
            flat = name.lower().replace("_", "")
            if "kipris" in flat and "key" in flat and value.strip():
                key = value.strip()
                break
    if not key:
        env_file = Path(os.environ.get("KIPRIS_ENV_FILE", DEFAULT_ENV_FILE))
        key = _key_from_env_file(env_file)

    if not key:
        print(
            "KIPRIS API key required.\n"
            "Set environment variable KIPRIS_API_KEY (any KIPRIS*KEY name works),\n"
            f"or put it in {DEFAULT_ENV_FILE} (override with KIPRIS_ENV_FILE),\n"
            "or use the --key CLI argument.\n"
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


class KiprisApiError(RuntimeError):
    """Raised when KIPRIS returns a non-success resultCode."""


# The two KIPRIS endpoints return DIFFERENT XML shapes. Verified 2026-07-31:
#   freeSearchInfo   -> <TotalSearchCount> + <PatentUtilityInfo> with PascalCase children
#   getAdvancedSearch-> <totalCount>       + <item>              with camelCase children
# Parsing only the free shape silently yields 0 results for advanced search.
_FREE_FIELDS = {
    "application_number": "ApplicationNumber",
    "title": "InventionName",
    "applicant": "Applicant",
    "application_date": "ApplicationDate",
    "abstract": "Abstract",
    "open_number": "OpeningNumber",
    "open_date": "OpeningDate",
    "register_number": "RegistrationNumber",
    "register_date": "RegistrationDate",
    "publication_number": "PublicNumber",
    "publication_date": "PublicDate",
    "ipc": "InternationalpatentclassificationNumber",
    "status": "RegistrationStatus",
    "drawing_path": "DrawingPath",
    "thumbnail_path": "ThumbnailPath",
}

_ADVANCED_FIELDS = {
    "application_number": "applicationNumber",
    "title": "inventionTitle",
    "applicant": "applicantName",
    "application_date": "applicationDate",
    "abstract": "astrtCont",
    "open_number": "openNumber",
    "open_date": "openDate",
    "register_number": "registerNumber",
    "register_date": "registerDate",
    "publication_number": "publicationNumber",
    "publication_date": "publicationDate",
    "ipc": "ipcNumber",
    "status": "registerStatus",
    "drawing_path": "drawing",
    "thumbnail_path": "bigDrawing",
}


def _parse_search_response(xml_text: str) -> tuple[int, list[dict]]:
    """Parse either KIPRIS search response shape into (total_count, items)."""
    root = ET.fromstring(xml_text)

    result_code = _text(root.find(".//resultCode"))
    if result_code and result_code != "00":
        result_msg = _text(root.find(".//resultMsg"))
        raise KiprisApiError(f"[{result_code}] {result_msg or 'unknown error'}")

    free_nodes = list(root.iter("PatentUtilityInfo"))
    if free_nodes:
        nodes, fields = free_nodes, _FREE_FIELDS
    else:
        nodes, fields = list(root.iter("item")), _ADVANCED_FIELDS

    total_raw = (
        _text(root.find(".//TotalSearchCount"))
        or _text(root.find(".//totalCount"))
        or "0"
    )
    total_count = int(total_raw or "0")

    items = []
    for node in nodes:
        record = {key: _text(node.find(tag)) for key, tag in fields.items()}
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

    # Inventor — <inventorInfo> is a CONTAINER (address/code/country/engName/name),
    # so its own .text is empty. Collect the <name> child of each block.
    names = []
    for block in root.iter("inventorInfo"):
        nm = _text(block.find("name")) or _text(block.find("engName"))
        if nm and nm not in names:
            names.append(nm)
    inventor = "; ".join(names) or _text(item.find(".//invntNm"))

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

        count, items = _parse_search_response(resp.text)  # may raise KiprisApiError
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
        # getAdvancedSearch pages with numOfRows/pageNo — it silently IGNORES
        # docsStart/docsCount and always returns page 1 (verified 2026-07-31).
        params: dict = {
            "ServiceKey": api_key,
            "numOfRows": PAGE_SIZE,
            "pageNo": page,
            "sortSpec": sort_by,
            "descSort": str(desc).lower(),
            "patent": "true",
            "utility": "true",
        }
        if title:
            params["inventionTitle"] = title
        if abstract:
            params["astrtCont"] = abstract
        if claims:
            params["claimScope"] = claims
        if applicant:
            params["applicant"] = applicant
        if inventor:
            # Field is "inventors"; "inventor"/"inventorName" return resultCode 10.
            params["inventors"] = inventor
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

    # Diagnostics
    p.add_argument(
        "--selftest", action="store_true",
        help="Probe both endpoints with known-good queries and exit (no -o needed)",
    )

    # Output
    p.add_argument(
        "-o", "--output",
        help="Output file path (.csv or .json). Required unless --selftest.",
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

    if args.selftest:
        sys.exit(run_selftest(api_key))

    if not args.output:
        parser.error("-o/--output is required unless --selftest is given")

    # Determine search mode
    use_advanced = any(
        [args.title, args.abstract, args.claims, args.ipc, args.inventor]
    )

    try:
        total, items = _dispatch_search(args, api_key, use_advanced)
    except KiprisApiError as e:
        print(f"KIPRIS API error: {e}", file=sys.stderr)
        print(
            "Aborting without writing an output file — an empty result file would "
            "be indistinguishable from 'no prior art found'.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"Total found: {total}, retrieved: {len(items)}", file=sys.stderr)
    if total == 0:
        print(
            "WARNING: zero hits. Check field syntax (AND=*, OR=+, NOT=!) and note "
            "that ipcNumber matches the code as written — 'H01L 33/00' and 'H01L33' "
            "are different queries.",
            file=sys.stderr,
        )

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


def _dispatch_search(args, api_key: str, use_advanced: bool) -> tuple[int, list[dict]]:
    """Route to the advanced or free-text search based on supplied filters."""
    if use_advanced:
        print("Using KIPRIS advanced search...", file=sys.stderr)
        return search_advanced(
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
    if args.keyword:
        print("Using KIPRIS free-text search...", file=sys.stderr)
        return search_free(
            api_key,
            keyword=args.keyword,
            max_results=args.max_results,
            sort_by=args.sort,
            desc=not args.asc,
        )

    print(
        "Provide --keyword for free search, or --title/--abstract/--claims/"
        "--ipc/--inventor for advanced search.",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Self-test ────────────────────────────────────────────────────────────────


def run_selftest(api_key: str) -> int:
    """Probe both endpoints with known-good queries. Returns a shell exit code.

    Guards the response-shape and pagination assumptions that silently broke
    advanced search before 2026-07-31.
    """
    failures = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        mark = "PASS" if condition else "FAIL"
        print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
        if not condition:
            failures.append(label)

    print("KIPRIS self-test")

    try:
        total, items = search_free(api_key, keyword="전사", max_results=5)
        check("free-text search returns items", bool(items), f"total={total}, got={len(items)}")
        check(
            "free-text records carry a title",
            bool(items and items[0].get("title")),
            (items[0].get("title", "")[:30] if items else "no items"),
        )
    except (KiprisApiError, requests.RequestException) as e:
        check("free-text search", False, str(e))

    try:
        total, items = search_advanced(api_key, title="레이저*전사", max_results=5)
        check("advanced search returns items", bool(items), f"total={total}, got={len(items)}")
        check(
            "advanced records parse camelCase fields",
            bool(items and items[0].get("title") and items[0].get("applicant")),
            (items[0].get("title", "")[:30] if items else "no items"),
        )
    except (KiprisApiError, requests.RequestException) as e:
        check("advanced search", False, str(e))

    try:
        total, items = search_advanced(api_key, title="레이저*전사", max_results=25)
        nums = [i["application_number"] for i in items]
        check(
            "advanced pagination yields distinct records",
            len(nums) == len(set(nums)),
            f"{len(nums)} records, {len(set(nums))} unique",
        )
    except (KiprisApiError, requests.RequestException) as e:
        check("advanced pagination", False, str(e))

    try:
        total, items = search_advanced(api_key, inventor="김재현", max_results=3)
        check("advanced inventor field accepted", total > 0, f"total={total}")
    except (KiprisApiError, requests.RequestException) as e:
        check("advanced inventor field accepted", False, str(e))

    try:
        detail = fetch_detail(api_key, "1020130047695")
        check("detail returns representative claim", bool(detail.get("representative_claim")))
        check("detail returns inventor name", bool(detail.get("inventor")), detail.get("inventor", "")[:30])
    except requests.RequestException as e:
        check("detail fetch", False, str(e))

    print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    main()
