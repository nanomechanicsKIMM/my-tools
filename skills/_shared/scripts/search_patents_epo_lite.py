#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight EPO OPS patent search for prior art analysis.

Shared utility for patent skills (patent-incubation-auto, patent-draft-review,
patent-defence). Uses python-epo-ops-client or falls back to direct REST API.

Usage:
  # Keyword search (title + abstract)
  python search_patents_epo_lite.py --keyword "ultrasound aberration skull" -o results.json

  # CQL query
  python search_patents_epo_lite.py --cql 'ta="conjugate plane" AND ta=ultrasound' -o results.json

  # With date filter
  python search_patents_epo_lite.py --keyword "reflection matrix aberration" --years 10 -o results.json

  # Get specific patent details
  python search_patents_epo_lite.py --get EP3456789 -o patent_detail.json

  # Family search
  python search_patents_epo_lite.py --family EP3456789 -o family.json

Environment variables:
  EPO_OPS_KEY=<consumer_key>
  EPO_OPS_SECRET=<consumer_secret>

Requires: pip install python-epo-ops-client  (or requests for fallback mode)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

NS = {
    "ops": "http://ops.epo.org",
    "exch": "http://www.epo.org/exchange",
    "epo": "http://www.epo.org/fulltext",
}


# ── Client ──────────────────────────────────────────────────────────────────

def get_credentials():
    """Get EPO OPS credentials from env or .env file."""
    key = os.environ.get("EPO_OPS_KEY", "")
    secret = os.environ.get("EPO_OPS_SECRET", "")
    if not key or not secret:
        # Try loading from .env files
        for env_path in [".env", os.path.expanduser("~/Claude_Work/.env"),
                         os.path.expanduser("~/.env")]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("EPO_OPS_KEY"):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("EPO_OPS_SECRET"):
                            secret = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key, secret


def create_client():
    """Create EPO OPS client. Try python-epo-ops-client first, fallback to REST."""
    key, secret = get_credentials()
    if not key or not secret:
        print("EPO OPS credentials not found. Set EPO_OPS_KEY and EPO_OPS_SECRET.", file=sys.stderr)
        sys.exit(1)

    try:
        import epo_ops
        client = epo_ops.Client(key=key, secret=secret,
                                middlewares=[epo_ops.middlewares.Throttler()])
        return ("epo_ops", client)
    except ImportError:
        pass

    # Fallback: direct REST API
    import requests
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    resp = requests.post(
        "https://ops.epo.org/3.2/auth/accesstoken",
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data="grant_type=client_credentials",
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return ("rest", token)


# ── Search ──────────────────────────────────────────────────────────────────

def keyword_to_cql(keyword: str, years: int = None) -> str:
    """Convert keyword string to EPO CQL query."""
    terms = keyword.split()
    cql_parts = []
    for term in terms:
        if term.upper() in ("AND", "OR", "NOT"):
            cql_parts.append(term.upper())
        else:
            cql_parts.append(f'ta="{term}"' if " " not in term else f'ta="{term}"')
    cql = " AND ".join(cql_parts) if not any(t in ("AND", "OR", "NOT") for t in terms) else " ".join(cql_parts)

    if years:
        year_from = datetime.now().year - years
        cql += f" AND pd>={year_from}"
    return cql


def search_epo(client_info, cql: str, max_results: int = 25):
    """Search EPO OPS with CQL query."""
    client_type, client = client_info
    results = []

    if client_type == "epo_ops":
        import epo_ops
        try:
            resp = client.published_data_search(cql, range_begin=1, range_end=min(max_results, 100))
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"EPO search error: {e}", file=sys.stderr)
            return results
    else:
        import requests
        try:
            resp = requests.get(
                "https://ops.epo.org/3.2/rest-services/published-data/search",
                headers={"Authorization": f"Bearer {client}", "Accept": "application/xml"},
                params={"q": cql, "Range": f"1-{min(max_results, 100)}"},
                timeout=30,
            )
            if resp.status_code == 404:
                return results
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"EPO search error: {e}", file=sys.stderr)
            return results

    # Parse results
    total = root.find(".//ops:biblio-search", NS)
    total_count = int(total.get("total-result-count", "0")) if total is not None else 0

    for pub_ref in root.findall(".//ops:publication-reference", NS):
        doc_ids = pub_ref.findall(".//exch:document-id", NS) or pub_ref.findall(".//document-id")
        if not doc_ids:
            doc_ids = pub_ref.findall(".//{http://www.epo.org/exchange}document-id")
        for doc_id in doc_ids:
            fmt = doc_id.get("document-id-type", "")
            if fmt == "docdb":
                country = doc_id.findtext("{http://www.epo.org/exchange}country", "")
                number = doc_id.findtext("{http://www.epo.org/exchange}doc-number", "")
                kind = doc_id.findtext("{http://www.epo.org/exchange}kind", "")
                results.append({
                    "publication_number": f"{country}{number}{kind}",
                    "country": country, "doc_number": number, "kind": kind,
                })

    return results[:max_results], total_count


def get_patent_details(client_info, pub_number: str) -> dict:
    """Get bibliographic details for a specific patent."""
    client_type, client = client_info
    # Parse publication number
    country = pub_number[:2]
    rest = pub_number[2:]
    kind = ""
    for k in ["A1", "A2", "A3", "B1", "B2", "B3"]:
        if rest.endswith(k):
            kind = k
            rest = rest[:-2]
            break

    if client_type == "epo_ops":
        try:
            resp = client.published_data("publication", {"country": country, "number": rest, "kind": kind}, "biblio")
            root = ET.fromstring(resp.content)
        except Exception as e:
            return {"error": str(e), "publication_number": pub_number}
    else:
        import requests
        try:
            url = f"https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{country}.{rest}.{kind}/biblio"
            resp = requests.get(url, headers={"Authorization": f"Bearer {client}", "Accept": "application/xml"}, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            return {"error": str(e), "publication_number": pub_number}

    # Parse bibliographic data
    result = {"publication_number": pub_number}

    # Title
    for title in root.findall(".//{http://www.epo.org/exchange}invention-title"):
        if title.get("lang", "") == "en":
            result["title"] = title.text or ""
            break
    if "title" not in result:
        t = root.find(".//{http://www.epo.org/exchange}invention-title")
        if t is not None:
            result["title"] = t.text or ""

    # Applicant
    for app in root.findall(".//{http://www.epo.org/exchange}applicant"):
        name = app.findtext(".//{http://www.epo.org/exchange}name", "")
        if name:
            result["applicant"] = name
            break

    # Abstract
    for abstract in root.findall(".//{http://www.epo.org/exchange}abstract"):
        if abstract.get("lang", "") == "en":
            p = abstract.find("{http://www.epo.org/exchange}p")
            if p is not None and p.text:
                result["abstract"] = p.text[:500]
            break

    # Dates
    for date_tag in root.findall(".//{http://www.epo.org/exchange}date"):
        result.setdefault("date", date_tag.text)

    # IPC codes
    ipcs = []
    for ipc in root.findall(".//{http://www.epo.org/exchange}classification-ipc"):
        text = ipc.findtext("{http://www.epo.org/exchange}text", "")
        if text:
            ipcs.append(text.strip())
    if ipcs:
        result["ipc_codes"] = ipcs

    return result


def get_patent_family(client_info, pub_number: str) -> list:
    """Get INPADOC patent family members."""
    client_type, client = client_info
    country = pub_number[:2]
    rest = pub_number[2:]
    kind = ""
    for k in ["A1", "A2", "B1", "B2"]:
        if rest.endswith(k):
            kind = k
            rest = rest[:-2]
            break

    family = []
    # Always use REST/JSON for family search (epo_ops client has issues with dict input)
    import requests as req
    try:
        if client_type == "epo_ops":
            # Re-authenticate for REST call
            _key, _secret = get_credentials()
            _auth = base64.b64encode(f"{_key}:{_secret}".encode()).decode()
            _token = req.post("https://ops.epo.org/3.2/auth/accesstoken",
                headers={"Authorization": f"Basic {_auth}", "Content-Type": "application/x-www-form-urlencoded"},
                data="grant_type=client_credentials", timeout=15).json()["access_token"]
        else:
            _token = client

        url = f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{country}.{rest}.{kind}"
        resp = req.get(url, headers={"Authorization": f"Bearer {_token}", "Accept": "application/json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        members = data.get("ops:world-patent-data", {}).get("ops:patent-family", {}).get("ops:family-member", [])
        if isinstance(members, dict):
            members = [members]
        for m in members:
            pubs = m.get("publication-reference", {}).get("document-id", [])
            if isinstance(pubs, dict):
                pubs = [pubs]
            for p in pubs:
                if p.get("@document-id-type") == "docdb":
                    c = p.get("country", {}).get("$", "")
                    n = p.get("doc-number", {}).get("$", "")
                    k = p.get("kind", {}).get("$", "")
                    family.append({"publication_number": f"{c}{n}{k}", "country": c})
    except Exception as e:
        return [{"error": str(e)}]
    return family


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="EPO OPS Patent Search (Lite)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--keyword", help="Keyword search (auto-converted to CQL)")
    group.add_argument("--cql", help="Direct CQL query")
    group.add_argument("--get", help="Get specific patent details by publication number")
    group.add_argument("--family", help="Get patent family by publication number")
    parser.add_argument("--years", type=int, help="Limit to recent N years")
    parser.add_argument("--max-results", type=int, default=25, help="Max results (default 25)")
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument("--with-detail", action="store_true", help="Fetch details for each result")
    parser.add_argument("--max-detail", type=int, default=10, help="Max patents to fetch details for")
    args = parser.parse_args()

    client_info = create_client()

    if args.get:
        result = get_patent_details(client_info, args.get)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        return

    if args.family:
        family = get_patent_family(client_info, args.family)
        print(json.dumps(family, ensure_ascii=False, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(family, f, ensure_ascii=False, indent=2)
        return

    # Search
    if args.keyword:
        cql = keyword_to_cql(args.keyword, args.years)
    else:
        cql = args.cql

    print(f"CQL: {cql}", file=sys.stderr)
    results, total = search_epo(client_info, cql, args.max_results)
    print(f"Found: {total}, Retrieved: {len(results)}", file=sys.stderr)

    # Fetch details if requested
    if args.with_detail and results:
        detailed = []
        for i, r in enumerate(results[:args.max_detail]):
            print(f"  Detail {i+1}/{min(len(results), args.max_detail)}: {r['publication_number']}", file=sys.stderr)
            detail = get_patent_details(client_info, r["publication_number"])
            detailed.append(detail)
            time.sleep(0.5)  # Rate limiting
        results = detailed

    output = {"query": cql, "total": total, "count": len(results), "patents": results}
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(results)} results to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
