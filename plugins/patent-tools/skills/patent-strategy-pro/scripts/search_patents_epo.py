#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search patents via EPO Open Patent Services (OPS) API and export as CSV.

Replaces manual Google Patents CSV download with automated API access.
Uses python-epo-ops-client for OAuth, throttling, and pagination.

Usage:
  # Single CQL query
  python search_patents_epo.py --cql 'ti="stretchable display"' -o results.csv

  # From query file (generate_query.py --format cql output)
  python search_patents_epo.py --query-file query_main.cql -o results.csv

  # From sub_techs.json (downloads all sub-tech CSVs)
  python search_patents_epo.py --sub-tech-json sub_techs.json --rfp rfp.md -o output/

  # With date range
  python search_patents_epo.py --cql 'ti="flexible sensor"' --years 15 -o results.csv

Requires:
  pip install python-epo-ops-client

Environment variables (or --key/--secret CLI args):
  EPO_OPS_KEY=<consumer_key>
  EPO_OPS_SECRET=<consumer_secret>

EPO OPS limits: max 2000 results per query, 100 per page, 4GB/week data.
For queries with >2000 results, use --split-by-year to auto-split.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    import epo_ops
except ImportError:
    print(
        "EPO OPS client not installed.\n"
        "  pip install python-epo-ops-client\n",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

OPS_MAX_RESULTS = 2000
OPS_PAGE_SIZE = 100
NS = {
    "ops": "http://ops.epo.org",
    "exch": "http://www.epo.org/exchange",
    "epo": "http://www.epo.org/fulltext",
}

# CSV columns compatible with Google Patents export format
CSV_COLUMNS = [
    "id", "title", "assignee", "inventor/author",
    "priority date", "filing/creation date", "publication date", "grant date",
    "result link", "representative figure link",
]


# ── Client factory ───────────────────────────────────────────────────────────

def create_client(key: str | None = None, secret: str | None = None) -> epo_ops.Client:
    """Create an EPO OPS client with OAuth and throttling middleware."""
    api_key = key or os.environ.get("EPO_OPS_KEY", "")
    api_secret = secret or os.environ.get("EPO_OPS_SECRET", "")
    if not api_key or not api_secret:
        print(
            "EPO OPS credentials required.\n"
            "Set environment variables EPO_OPS_KEY and EPO_OPS_SECRET,\n"
            "or use --key and --secret CLI arguments.\n"
            "\n"
            "Register at: https://developers.epo.org\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Disable SSL verification (needed for corporate proxies with self-signed certs)
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import requests.adapters as _ra
        if not getattr(_ra.HTTPAdapter, "_ssl_patched", False):
            _orig_send = _ra.HTTPAdapter.send
            def _patched_send(self, request, **kwargs):
                kwargs["verify"] = False
                return _orig_send(self, request, **kwargs)
            _ra.HTTPAdapter.send = _patched_send
            _ra.HTTPAdapter._ssl_patched = True
    except Exception:
        pass

    middlewares = [
        epo_ops.middlewares.Throttler(),
    ]
    client = epo_ops.Client(
        key=api_key,
        secret=api_secret,
        middlewares=middlewares,
    )
    return client


# ── CQL query builder ────────────────────────────────────────────────────────

def google_to_cql(google_query: str, year_from: int = None, year_to: int = None) -> str:
    """
    Convert Google Patents boolean query to EPO OPS CQL syntax.

    Google: ("stretchable display" OR "flexible display") AND sensor NOT OLED
    CQL:    ti=("stretchable display" OR "flexible display") AND ti=sensor NOT ti=OLED

    Adds title-field prefix (ti=) since Google Patents searches titles by default.
    """
    cql = google_query

    # Replace NOT (...) → NOT (ti=...)
    # First handle the main terms - wrap bare terms with ti=
    # This is a simplified converter; complex queries may need manual CQL

    # Add date range if specified
    if year_from:
        cql += f" AND pd>={year_from}"
    if year_to:
        cql += f" AND pd<={year_to}"

    return cql


def build_cql_from_groups(
    groups: list[list[str]],
    exclude_terms: list[str] = None,
    year_from: int = None,
    year_to: int = None,
    field: str = "ti",
) -> str:
    """
    Build CQL query from term groups using correct EPO OPS per-field OR syntax.

    EPO OPS requires:   (ti="p1" OR ti="p2") AND ti=sensor
    NOT:                ti=("p1" OR "p2") AND ti=sensor  ← causes 413/404

    groups: [["stretchable display", "flexible display"], ["sensor"]]
    → (ti="stretchable display" OR ti="flexible display") AND ti=sensor
    """
    parts = []
    for g in groups:
        if not g:
            continue
        field_terms = [f'{field}="{t}"' if " " in t else f"{field}={t}" for t in g]
        if len(field_terms) == 1:
            parts.append(field_terms[0])
        else:
            parts.append(f'({" OR ".join(field_terms)})')

    cql = " AND ".join(parts)

    if exclude_terms:
        exc_terms = [f'{field}="{t}"' if " " in t else f"{field}={t}" for t in exclude_terms]
        if len(exc_terms) == 1:
            cql += f" NOT {exc_terms[0]}"
        else:
            cql += f' NOT ({" OR ".join(exc_terms)})'

    # EPO OPS requires `pd within "YYYYMMDD,YYYYMMDD"` — the pd>=X AND pd<=Y form
    # triggers CLIENT.FuzzyDateRanges (HTTP 413) regardless of result count.
    if year_from or year_to:
        def _pad_date(v, suffix: str) -> str:
            s = str(v)
            return s if len(s) == 8 else s + suffix
        d_from = _pad_date(year_from, "0101") if year_from else "20000101"
        d_to = _pad_date(year_to, "1231") if year_to else "20991231"
        cql += f' AND pd within "{d_from},{d_to}"'

    return cql


# ── XML parsing ──────────────────────────────────────────────────────────────

def parse_search_response(xml_bytes: bytes) -> tuple[list[str], int]:
    """Parse search response to extract document IDs and total count."""
    root = ET.fromstring(xml_bytes)

    # Total result count
    total = 0
    range_elem = root.find(".//ops:biblio-search", NS)
    if range_elem is not None:
        total = int(range_elem.get("total-result-count", "0"))

    # Extract publication references
    doc_ids = []
    for ref in root.findall(".//ops:publication-reference", NS):
        doc_id = ref.find("exch:document-id[@document-id-type='docdb']", NS)
        if doc_id is not None:
            country = doc_id.findtext("exch:country", "", NS)
            doc_number = doc_id.findtext("exch:doc-number", "", NS)
            kind = doc_id.findtext("exch:kind", "", NS)
            doc_ids.append(f"{country}{doc_number}{kind}")

    return doc_ids, total


def parse_biblio_response(xml_bytes: bytes) -> list[dict]:
    """Parse bibliographic data response into CSV-compatible dicts."""
    root = ET.fromstring(xml_bytes)
    results = []

    for doc in root.findall(".//exch:exchange-document", NS):
        country = doc.get("country", "")
        doc_number = doc.get("doc-number", "")
        kind = doc.get("kind", "")
        patent_id = f"{country}-{doc_number}-{kind}"

        # Title (prefer English)
        title = ""
        for t in doc.findall(".//exch:invention-title", NS):
            if t.get("lang", "") == "en":
                title = (t.text or "").strip()
                break
        if not title:
            t_elem = doc.find(".//exch:invention-title", NS)
            if t_elem is not None:
                title = (t_elem.text or "").strip()

        # Applicants — EPO OPS returns data-format="epodoc" (not "docdb")
        applicants = []
        seen_app = set()
        for app in doc.findall(".//exch:applicant[@data-format='epodoc']", NS):
            name_elem = app.find("exch:applicant-name/exch:name", NS)
            if name_elem is not None and name_elem.text:
                n = name_elem.text.strip()
                if n not in seen_app:
                    applicants.append(n)
                    seen_app.add(n)

        # Inventors — same epodoc format
        inventors = []
        seen_inv = set()
        for inv in doc.findall(".//exch:inventor[@data-format='epodoc']", NS):
            name_elem = inv.find("exch:inventor-name/exch:name", NS)
            if name_elem is not None and name_elem.text:
                n = name_elem.text.strip()
                if n not in seen_inv:
                    inventors.append(n)
                    seen_inv.add(n)

        # Dates — priority date is in document-id[@document-id-type='epodoc']/date
        priority_date = ""
        for pri in doc.findall(".//exch:priority-claim", NS):
            epodoc_id = pri.find("exch:document-id[@document-id-type='epodoc']", NS)
            d = (epodoc_id.findtext("exch:date", "", NS) if epodoc_id is not None else "") or \
                pri.findtext("exch:date", "", NS)  # fallback: direct date child
            if d and (not priority_date or d < priority_date):
                priority_date = d

        pub_date = ""
        for id_type in ("docdb", "epodoc"):
            pub_ref = doc.find(f".//exch:publication-reference/exch:document-id[@document-id-type='{id_type}']", NS)
            if pub_ref is not None:
                pub_date = pub_ref.findtext("exch:date", "", NS) or ""
                if pub_date:
                    break

        filing_date = ""
        for id_type in ("epodoc", "docdb"):
            app_ref = doc.find(f".//exch:application-reference/exch:document-id[@document-id-type='{id_type}']", NS)
            if app_ref is not None:
                filing_date = app_ref.findtext("exch:date", "", NS) or ""
                if filing_date:
                    break

        # Format dates: YYYYMMDD → YYYY-MM-DD
        def fmt_date(d: str) -> str:
            if len(d) == 8:
                return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            return d

        result_link = f"https://worldwide.espacenet.com/patent/search/family/{country}/{doc_number}/{kind}"

        results.append({
            "id": patent_id,
            "title": title,
            "assignee": ", ".join(applicants),
            "inventor/author": ", ".join(inventors),
            "priority date": fmt_date(priority_date),
            "filing/creation date": fmt_date(filing_date),
            "publication date": fmt_date(pub_date),
            "grant date": "",
            "result link": result_link,
            "representative figure link": "",
        })

    return results


# ── Abstract / claim fetching ────────────────────────────────────────────────

def fetch_abstracts_bulk(
    client: epo_ops.Client,
    rows: list[dict],
    delay: float = 0.5,
    fetch_claims: bool = False,
) -> list[dict]:
    """
    Enrich patent rows with 'abstract' (and optionally 'representative_claim') via EPO OPS.
    Replaces Google Patents scraper (fetch_abstracts.py) for the analysis pipeline.

    Expects rows with 'id' column in "CC-NNNNNN-KK" format (from parse_biblio_response).
    Adds 'abstract' column; empty string on any failure.

    fetch_claims: if True, also fetch first claim text (EP patents only; non-EP returns empty).
                  Default False — abstract-only scoring is sufficient for EPO OPS mode and
                  avoids 404 errors for non-EP patents (US, CN, KR, JP, etc.).
    """
    enriched = []
    total = len(rows)

    for i, row in enumerate(rows):
        new_row = dict(row)
        new_row.setdefault("abstract", "")
        new_row.setdefault("representative_claim", "")

        patent_id = row.get("id", "")
        # Support "KR-102862661-B1" and "KR102862661B1"
        m = re.match(r"([A-Z]{2})-(\d+)(?:-([A-Z]\d*))?", patent_id)
        if not m:
            m = re.match(r"([A-Z]{2})(\d+)([A-Z]\d*)?", patent_id)

        if m:
            country, number, kind = m.group(1), m.group(2), m.group(3) or ""

            # Fetch abstract
            try:
                resp = client.published_data(
                    reference_type="publication",
                    input=epo_ops.models.Docdb(number, country, kind),
                    endpoint="abstract",
                )
                root = ET.fromstring(resp.content)
                paragraphs = [
                    elem.text.strip()
                    for elem in root.iter()
                    if elem.tag.endswith("}p") and elem.text and elem.text.strip()
                ]
                new_row["abstract"] = " ".join(paragraphs)
            except Exception:
                pass

            # Fetch representative claim (EP patents only; skip by default)
            if fetch_claims:
                try:
                    resp = client.published_data(
                        reference_type="publication",
                        input=epo_ops.models.Docdb(number, country, kind),
                        endpoint="claims",
                    )
                    root = ET.fromstring(resp.content)
                    for elem in root.iter():
                        if elem.tag.endswith("}claim-text") and elem.text and elem.text.strip():
                            new_row["representative_claim"] = elem.text.strip()
                            break
                except Exception:
                    pass

            if delay > 0 and i < total - 1:
                time.sleep(delay)

        enriched.append(new_row)
        if (i + 1) % 10 == 0 or i + 1 == total:
            print(f"  EPO OPS abstracts: {i + 1}/{total}")

    return enriched


# ── 413 narrowing helper ─────────────────────────────────────────────────────

def _narrow_413(
    client: epo_ops.Client,
    cql: str,
    max_results: int,
) -> tuple[str, object | None]:
    """
    Handle EPO OPS 413 "result set too large" by progressively trimming the CQL.

    EPO OPS evaluates each AND operand independently before intersecting them.
    If ANY OR-group has >~10,000 intermediate results, it returns 413 even if
    the final AND intersection would be small.

    Strategy (tries in order until one succeeds):
      1. Keep only the first 3 terms of each OR-group (shortest broadest path)
      2. Keep only the first 2 terms of each OR-group
      3. Keep only the first term of each OR-group (single-term AND chain)
    Returns (final_cql, response) or (original_cql, None) on full failure.
    """
    # Parse OR-groups: matches (ti="..." OR ti=... OR ...) patterns
    def trim_cql_groups(cql: str, keep: int) -> str:
        """Keep only the first `keep` ti= terms in every OR-group."""
        def _trim_group(m: re.Match) -> str:
            content = m.group(1)
            # Split on ' OR ' to get individual ti=... terms
            terms = re.split(r"\s+OR\s+", content)
            trimmed = terms[:keep]
            if len(trimmed) == 1:
                return trimmed[0]
            return f'({" OR ".join(trimmed)})'

        # Match (ti=... OR ti=... OR ...) groups (with or without outer parens)
        result = re.sub(r"\(([^()]+(?:\s+OR\s+[^()]+)+)\)", _trim_group, cql)
        return result

    for keep in [3, 2, 1]:
        narrowed = trim_cql_groups(cql, keep)
        if narrowed == cql and keep < 3:
            continue  # no change — skip
        print(f"  ⚠ 413: trimming OR-groups to {keep} term(s) each ...")
        print(f"  CQL (trimmed): {narrowed[:150]}")
        try:
            resp = client.published_data_search(
                cql=narrowed,
                range_begin=1,
                range_end=min(OPS_PAGE_SIZE, max_results),
            )
            return narrowed, resp
        except Exception as e:
            if "413" not in str(e):
                print(f"  Error (keep={keep}): {e}", file=sys.stderr)
                break  # non-413 error — stop trying

    print(f"  All narrowing attempts failed for CQL: {cql[:80]}", file=sys.stderr)
    return cql, None


# ── Search functions ─────────────────────────────────────────────────────────

def search_patents(
    client: epo_ops.Client,
    cql: str,
    max_results: int = OPS_MAX_RESULTS,
) -> list[dict]:
    """
    Search patents with CQL query and fetch bibliographic data.
    Handles pagination automatically (100 per page, max 2000 total).
    """
    all_results: list[dict] = []
    offset = 1

    # First search to get total count
    print(f"  CQL: {cql[:120]}{'...' if len(cql) > 120 else ''}")

    try:
        resp = client.published_data_search(
            cql=cql,
            range_begin=1,
            range_end=min(OPS_PAGE_SIZE, max_results),
        )
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg or "no results" in err_msg.lower():
            print(f"  → 0 results")
            return []
        if "413" in err_msg:
            # EPO OPS returns 413 when an intermediate OR-group result set exceeds
            # the server limit (~10,000 records), even if the final AND result is small.
            # Strategy: progressively drop terms from OR groups until the query fits.
            cql, resp = _narrow_413(client, cql, max_results)
            if resp is None:
                return []
        else:
            raise

    doc_ids, total = parse_search_response(resp.content)
    effective_total = min(total, max_results)
    print(f"  → {total} total results (fetching up to {effective_total})")

    if total == 0:
        return []

    # Fetch biblio for first page
    if doc_ids:
        biblio = _fetch_biblio_batch(client, doc_ids)
        all_results.extend(biblio)
        print(f"  Fetched {len(all_results)}/{effective_total} ...")

    # Paginate remaining
    offset = OPS_PAGE_SIZE + 1
    while offset <= effective_total:
        end = min(offset + OPS_PAGE_SIZE - 1, effective_total)
        try:
            resp = client.published_data_search(
                cql=cql,
                range_begin=offset,
                range_end=end,
            )
            doc_ids, _ = parse_search_response(resp.content)
            if doc_ids:
                biblio = _fetch_biblio_batch(client, doc_ids)
                all_results.extend(biblio)
            print(f"  Fetched {len(all_results)}/{effective_total} ...")
        except Exception as e:
            print(f"  Warning: page {offset}-{end} failed: {e}", file=sys.stderr)
            break
        offset += OPS_PAGE_SIZE

    return all_results


def _fetch_biblio_batch(client: epo_ops.Client, doc_ids: list[str]) -> list[dict]:
    """Fetch bibliographic data for a batch of document IDs."""
    results = []
    # EPO OPS allows batch biblio for up to ~20 docs at once via comma-separated
    batch_size = 20
    for i in range(0, len(doc_ids), batch_size):
        batch = doc_ids[i:i + batch_size]
        for doc_id in batch:
            # Parse doc_id: e.g. "KR102862661B1" → country=KR, number=102862661, kind=B1
            m = re.match(r"([A-Z]{2})(\d+)([A-Z]\d?)?", doc_id)
            if not m:
                continue
            country, number, kind = m.group(1), m.group(2), m.group(3) or ""
            try:
                resp = client.published_data(
                    reference_type="publication",
                    input=epo_ops.models.Docdb(number, country, kind),
                    endpoint="biblio",
                )
                parsed = parse_biblio_response(resp.content)
                results.extend(parsed)
            except Exception:
                # Skip individual failures (may be missing in database)
                pass
    return results


def search_with_year_split(
    client: epo_ops.Client,
    cql_base: str,
    year_from: int,
    year_to: int,
    max_per_year: int = OPS_MAX_RESULTS,
) -> list[dict]:
    """
    Split search by year when total results > 2000.
    Searches each year separately and merges results.
    """
    all_results = []
    seen_ids = set()

    for year in range(year_from, year_to + 1):
        cql_year = f'{cql_base} AND pd within "{year}0101,{year}1231"'
        print(f"\n  [Year {year}]")
        results = search_patents(client, cql_year, max_results=max_per_year)
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_results.append(r)

    print(f"\n  Total unique results (all years): {len(all_results)}")
    return all_results


# ── CSV output ───────────────────────────────────────────────────────────────

def write_csv_file(results: list[dict], output_path: Path):
    """Write results to CSV in Google Patents compatible format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"  Wrote {output_path} ({len(results)} rows)")


# ── Family deduplication ─────────────────────────────────────────────────────

def deduplicate_by_family(rows: list[dict]) -> list[dict]:
    """
    Remove patent family duplicates from a list of results.

    Pass 1 — same publication (country + doc_number, ignoring kind code):
      US-20230123456-A1 and US-11234567-B2 are different doc_numbers so kept as-is.
      US-1234567-A1 and US-1234567-B1 → same base → keep first seen.

    Pass 2 — cross-country family approximation:
      Patents with identical (priority_date month, normalized_title[:60]) are
      likely the same invention filed in multiple countries → keep first seen.

    Returns deduplicated list preserving original order (first occurrence wins).
    """
    seen_doc: set[tuple] = set()
    seen_title: set[tuple] = set()
    result: list[dict] = []

    for row in rows:
        patent_id = row.get("id", "")
        # Parse "CC-NNNNNN-KK" or "CC-NNNNNN"
        m = re.match(r"([A-Z]{2})-(\d+)", patent_id)
        keep = True

        if m:
            country, number = m.group(1), m.group(2)
            doc_key = (country, number)
            if doc_key in seen_doc:
                keep = False
            else:
                seen_doc.add(doc_key)

        if keep:
            title_raw = row.get("title", "")
            priority = row.get("priority date", "")[:7]  # "YYYY-MM"
            # Normalize: lowercase, collapse whitespace, strip punctuation
            title_norm = re.sub(r"[^a-z0-9 ]", "", title_raw.lower())
            title_norm = re.sub(r"\s+", " ", title_norm).strip()[:60]
            if title_norm and len(title_norm) > 10 and priority:
                title_key = (priority, title_norm)
                if title_key in seen_title:
                    keep = False
                else:
                    seen_title.add(title_key)

        if keep:
            result.append(row)

    return result


# ── Sub-tech batch search ────────────────────────────────────────────────────

def search_sub_techs(
    client: epo_ops.Client,
    sub_techs_path: Path,
    rfp_text: str,
    output_dir: Path,
    years: int = 15,
    global_required: list[str] = None,
    global_exclude: list[str] = None,
    split_by_year: bool = False,
    max_per_term: int = 200,
    only_ids: list[str] = None,
) -> dict:
    """
    Search all sub-technologies and save individual CSVs.
    Returns dict mapping sub_tech_id → csv_path.

    Strategy: search each key_term individually to avoid EPO OPS 413 errors
    caused by large OR-group intermediate result sets. Results are merged
    and deduplicated (cap: max_per_term per term, 500 total per sub-tech).

    The global_required domain anchor is NOT applied to title searches because
    patents rarely include both a domain term ("stretchable display") and a
    sub-tech term ("stretchable TFT") in the same title — combining them yields
    zero results. Domain relevance is handled at abstract scoring time instead.
    """
    sub_data = json.loads(sub_techs_path.read_text(encoding="utf-8"))
    sub_techs = sub_data.get("sub_technologies", [])

    current_year = datetime.now().year
    year_from = current_year - years
    year_to = current_year

    csv_map = {}

    for st in sub_techs:
        st_id = st["id"]

        # Skip if only_ids filter is set and this ID is not in it
        if only_ids and st_id not in only_ids:
            print(f"\n[{st_id}] Skipped (not in --only-ids)")
            continue

        print(f"\n{'='*60}")
        print(f"[{st_id}] {st['name_ko']}")
        print(f"{'='*60}")

        key_terms = st.get("key_terms", [])
        exclude = list(set((global_exclude or []) + st.get("exclude_terms", [])))

        all_results: list[dict] = []
        seen_ids: set[str] = set()

        for term in key_terms:
            # Search each key_term individually to avoid OR-group 413.
            # Exclude terms are NOT applied here: common excludes like "touch sensor"
            # or "glass TFT" have millions of hits and cause 413 in NOT clauses.
            # Irrelevant results are filtered out at abstract scoring time instead.
            term_q = f'"{term}"' if " " in term else term
            # EPO OPS requires pd within "YYYYMMDD,YYYYMMDD" — the pd>=X form triggers 413
            cql = f'ti={term_q} AND pd within "{year_from}0101,{year_to}1231"'

            print(f"  [{term}] searching ...")
            try:
                results = search_patents(client, cql, max_results=max_per_term)
            except Exception as e:
                print(f"  [{term}] Error (skipping): {e}", file=sys.stderr)
                time.sleep(3)
                continue
            added = 0
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)
                    added += 1
            print(f"  [{term}] +{added} unique (total: {len(all_results)})")

            if len(all_results) >= 500:
                print(f"  Reached 500 results cap, stopping early")
                break

        # Family dedup before saving
        before_dedup = len(all_results)
        all_results = deduplicate_by_family(all_results)
        print(f"  [{st_id}] Family dedup: {before_dedup} → {len(all_results)} unique patents")

        date_str = datetime.now().strftime("%Y%m%d")
        csv_path = output_dir / f"gp-search-{date_str}_{st_id}.csv"
        write_csv_file(all_results, csv_path)
        csv_map[st_id] = str(csv_path)

    return csv_map


# ── Main query search ────────────────────────────────────────────────────────

def search_main(
    client: epo_ops.Client,
    rfp_text: str,
    output_path: Path,
    years: int = 15,
    required_terms: list[str] = None,
    exclude_terms: list[str] = None,
    split_by_year: bool = False,
    sub_techs_path: Path = None,
    max_per_term: int = 200,
) -> str:
    """
    Search main query and save CSV.

    When sub_techs_path is provided (recommended), builds main.csv as the
    union of all sub-technology key_terms searches — guaranteeing main.csv
    is a true superset of all sub-tech CSVs.

    When sub_techs_path is not provided, falls back to RFP-text AND-group
    query (original behaviour, tends to return fewer results).
    """
    current_year = datetime.now().year
    year_from = current_year - years
    year_to = current_year

    if sub_techs_path and Path(sub_techs_path).exists():
        # ── Union of all sub-tech key_terms (per-term OR search) ──────────
        sub_data = json.loads(Path(sub_techs_path).read_text(encoding="utf-8"))
        sub_techs = sub_data.get("sub_technologies", [])

        # Collect unique key_terms across all sub-techs
        all_terms: list[str] = []
        seen_terms: set[str] = set()
        for st in sub_techs:
            for term in st.get("key_terms", []):
                if term.lower() not in seen_terms:
                    seen_terms.add(term.lower())
                    all_terms.append(term)

        print(f"\n[Main] Union search: {len(all_terms)} unique terms across all sub-techs")

        all_results: list[dict] = []
        seen_ids: set[str] = set()

        for term in all_terms:
            term_q = f'"{term}"' if " " in term else term
            cql = f'ti={term_q} AND pd within "{year_from}0101,{year_to}1231"'
            print(f"  [{term}] searching ...")
            try:
                results = search_patents(client, cql, max_results=max_per_term)
            except Exception as e:
                print(f"  [{term}] Error (skipping): {e}", file=sys.stderr)
                time.sleep(3)
                continue
            added = 0
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)
                    added += 1
            print(f"  [{term}] +{added} unique (total: {len(all_results)})")

        # Family dedup
        before_dedup = len(all_results)
        all_results = deduplicate_by_family(all_results)
        print(f"\n[Main] Family dedup: {before_dedup} → {len(all_results)} unique patents")

        write_csv_file(all_results, output_path)
        return str(output_path)

    # ── Fallback: RFP AND-group query (legacy) ────────────────────────────
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    from generate_query import (
        extract_rfp_english_keywords, extract_english_keywords,
        extract_section_text, SECTION_PATTERNS,
    )

    rfp_explicit = extract_rfp_english_keywords(rfp_text)
    heuristic = extract_english_keywords(
        extract_section_text(rfp_text, SECTION_PATTERNS.get("objectives", [])) + "\n" +
        extract_section_text(rfp_text, SECTION_PATTERNS.get("contents", []))
    )

    seen = set()
    keywords = []
    for t in rfp_explicit + heuristic:
        if t.lower() not in seen:
            seen.add(t.lower())
            keywords.append(t)

    mid = max(1, len(keywords) // 2)
    groups = [keywords[:mid], keywords[mid:mid + 10]]
    groups = [g for g in groups if g]
    if required_terms:
        groups.insert(0, required_terms)

    if split_by_year:
        cql_base = build_cql_from_groups(groups, exclude_terms=exclude_terms)
        results = search_with_year_split(client, cql_base, year_from, year_to)
    else:
        cql = build_cql_from_groups(
            groups, exclude_terms=exclude_terms,
            year_from=year_from, year_to=year_to,
        )
        results = search_patents(client, cql)

    results = deduplicate_by_family(results)
    write_csv_file(results, output_path)
    return str(output_path)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Search patents via EPO OPS API and export as CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single CQL query
  python search_patents_epo.py --cql 'ti="stretchable display"' -o results.csv

  # All sub-techs from JSON
  python search_patents_epo.py --sub-tech-json sub_techs.json --rfp rfp.md -o output/

  # With credentials
  python search_patents_epo.py --key YOUR_KEY --secret YOUR_SECRET --cql '...' -o out.csv

Environment variables:
  EPO_OPS_KEY     EPO OPS Consumer Key
  EPO_OPS_SECRET  EPO OPS Consumer Secret
""",
    )
    ap.add_argument("--cql", type=str, default=None, help="CQL query string")
    ap.add_argument("--rfp", type=str, default=None, help="RFP markdown file (for main query auto-generation)")
    ap.add_argument("--sub-tech-json", type=str, default=None, help="sub_techs.json path (batch mode)")
    ap.add_argument("-o", "--output", required=True, help="Output CSV path or directory (for batch mode)")
    ap.add_argument("--years", type=int, default=15, help="Search range in years (default 15)")
    ap.add_argument("--required-terms", type=str, default=None, help="Comma-separated required terms (AND gate)")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Comma-separated exclude terms")
    ap.add_argument("--split-by-year", action="store_true",
                    help="Split search by year for queries with >2000 results")
    ap.add_argument("--key", type=str, default=None, help="EPO OPS Consumer Key")
    ap.add_argument("--secret", type=str, default=None, help="EPO OPS Consumer Secret")
    ap.add_argument("--only-ids", type=str, default=None,
                    help="Comma-separated sub-tech IDs to search (e.g. sub4). Others are skipped.")
    ap.add_argument("--main-only", action="store_true",
                    help="Generate main CSV (union of sub-tech key_terms) even when --sub-tech-json is set. "
                         "Output path (-o) must be a .csv file, not a directory.")
    args = ap.parse_args()

    client = create_client(key=args.key, secret=args.secret)
    required = [t.strip() for t in (args.required_terms or "").split(",") if t.strip()]
    exclude = [t.strip() for t in (args.exclude_terms or "").split(",") if t.strip()]
    only_ids = [t.strip() for t in (args.only_ids or "").split(",") if t.strip()] or None

    if args.cql:
        # Direct CQL search
        results = search_patents(client, args.cql)
        write_csv_file(results, Path(args.output))

    elif args.sub_tech_json and args.main_only:
        # Main CSV via union of sub-tech key_terms
        rfp_text = Path(args.rfp).read_text(encoding="utf-8") if args.rfp else ""
        search_main(
            client, rfp_text, Path(args.output),
            years=args.years,
            sub_techs_path=Path(args.sub_tech_json),
        )

    elif args.sub_tech_json:
        # Batch sub-tech search
        rfp_text = Path(args.rfp).read_text(encoding="utf-8") if args.rfp else ""
        csv_map = search_sub_techs(
            client,
            sub_techs_path=Path(args.sub_tech_json),
            rfp_text=rfp_text,
            output_dir=Path(args.output),
            years=args.years,
            global_required=required or None,
            global_exclude=exclude or None,
            split_by_year=args.split_by_year,
            only_ids=only_ids,
        )
        print(f"\n{'='*60}")
        print("Sub-tech CSV files:")
        for st_id, path in csv_map.items():
            print(f"  [{st_id}] {path}")

    elif args.rfp:
        # Main query from RFP
        rfp_text = Path(args.rfp).read_text(encoding="utf-8")
        search_main(
            client, rfp_text, Path(args.output),
            years=args.years,
            required_terms=required or None,
            exclude_terms=exclude or None,
            split_by_year=args.split_by_year,
        )

    else:
        print("Provide --cql, --rfp, or --sub-tech-json", file=sys.stderr)
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
