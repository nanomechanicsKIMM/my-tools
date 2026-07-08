#!/usr/bin/env python
# fast_get.py - HTTP-first fast path for paper-pdf-download (2026-07-08).
# Runs BEFORE any browser work:
#   1. classify the DOI/URL (publisher + KIMM access mode, from kimm_subscriptions.json
#      + access_overrides.json)
#   2. try cheap direct HTTP GET for non-protected hosts (arXiv, university servers,
#      OA repositories, Unpaywall-provided PDF URLs)
#   3. suggest the canonical output filename "(YYYY Author) Title.pdf" via Crossref
#
# stdout: ONE JSON line (machine-readable for get_paper.sh)
# stderr: human-readable progress
# exit codes: 0 = PDF downloaded here (browser not needed)
#             3 = not downloaded, proceed to browser path
#             4 = classified 'none' (unsubscribed) AND no OA candidate -> skip browser
#             2 = usage error
import sys, os, re, json, glob, io
import urllib.request

sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import truststore  # KIMM proxy SSL (see memory: reference_hf_ssl_truststore)
    truststore.inject_into_ssl()
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")
GET_TIMEOUT = 12

# hosts where a plain GET is known-useless (bot wall / CDN token / login) -> browser path
PROTECTED = (
    "sciencedirect.com", "wiley.com", "pubs.acs.org", "nature.com", "mdpi.com",
    "opg.optica.org", "opticapublishing.org", "pubs.rsc.org",
    "royalsocietypublishing.org", "cambridge.org", "science.org", "sciencemag.org",
    "ieeexplore.ieee.org", "tandfonline.com", "iopscience.iop.org",
    "asmedigitalcollection.asme.org", "academic.oup.com", "pnas.org",
)

# DOI prefix -> publisher key (aligned with kimm_subscriptions.json / access_overrides.json)
DOI_PREFIX = {
    "10.1016": "Elsevier", "10.1002": "Wiley_SID", "10.1111": "Wiley_SID",
    "10.1038": "Nature", "10.1021": "ACS", "10.3390": "MDPI", "10.48550": "arXiv",
    "10.1364": "Optica", "10.1039": "RSC", "10.1007": "Springer", "10.1140": "Springer",
    "10.1109": "IEEE", "10.1080": "TaylorFrancis", "10.1017": "Cambridge",
    "10.1088": "IOP", "10.1115": "ASME", "10.1103": "APS", "10.1126": "Science",
    "10.1098": "RoyalSociety", "10.1073": "PNAS",
}

SDIR = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(os.path.dirname(SDIR), "references")


def eprint(*a):
    print(*a, file=sys.stderr)


def http_get(url, timeout=GET_TIMEOUT, accept="application/pdf,*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url, timeout=10):
    return json.loads(http_get(url, timeout, accept="application/json").decode("utf-8", "replace"))


def try_pdf(url):
    try:
        data = http_get(url)
        if data[:4] == b"%PDF":
            return data
        eprint(f"  fast-get: not PDF ({data[:12]!r}) {url[:90]}")
    except Exception as e:
        eprint(f"  fast-get: miss ({e.__class__.__name__}) {url[:90]}")
    return None


def load_access_tables():
    """kimm_subscriptions.json (live plugin copy preferred, snapshot fallback) + overrides."""
    subs = {}
    paths = sorted(glob.glob(os.path.expanduser(
        "~/.claude/plugins/cache/wolfpack/paper-pack/*/skills/paper-fetch-runner/scripts/kimm_subscriptions.json")))
    cand = ([paths[-1]] if paths else []) + [os.path.join(REFS, "kimm_subscriptions.json")]
    for p in cand:
        try:
            with open(p, encoding="utf-8") as f:
                subs = json.load(f)
            break
        except Exception:
            continue
    table = {}
    for name, e in (subs.get("publishers") or {}).items():
        table[name] = {"access": e.get("access", "?"), "domains": e.get("domains", []),
                       "note": e.get("note", "")}
    for name, doms in (subs.get("_subscribed_no_handler") or {}).items():
        if name.startswith("_"):
            continue
        table.setdefault(name, {"access": "ip", "domains": [], "note": ""})
        table[name]["domains"] = [d for d in doms if not d.startswith("10.")]
        table[name]["prefixes"] = [d for d in doms if d.startswith("10.")]
        table[name]["note"] = (table[name]["note"] + " KIMM 구독, paper-pack 핸들러 없음").strip()
    try:
        with open(os.path.join(REFS, "access_overrides.json"), encoding="utf-8") as f:
            ov = json.load(f)
        for name, e in ov.items():
            if name.startswith("_"):
                continue
            table.setdefault(name, {"access": "?", "domains": [], "note": ""})
            table[name].update({k: v for k, v in e.items() if k in ("access", "domains", "note")})
    except Exception:
        pass
    return table


def classify(doi, url, table):
    host = ""
    if url:
        m = re.match(r"https?://([^/]+)", url)
        host = (m.group(1) if m else "").lower()
    pub = None
    if host:
        for name, e in table.items():
            if any(d in host for d in e.get("domains", [])):
                pub = name
                break
    if not pub and doi:
        pref = doi.split("/")[0]
        pub = DOI_PREFIX.get(pref)
        if not pub:
            for name, e in table.items():
                if any(doi.startswith(p) for p in e.get("prefixes", [])):
                    pub = name
                    break
    if not pub:
        return {"publisher": None, "access": "?", "note": "unknown publisher"}
    e = table.get(pub, {})
    return {"publisher": pub, "access": e.get("access", "?"), "note": e.get("note", "")}


_ILLEGAL = re.compile(r'[\\*?"<>|]')


def sanitize_title(t):
    t = t.replace(":", "_").replace("/", "_")
    t = _ILLEGAL.sub("_", t)
    t = re.sub(r"\s+", " ", t).strip().rstrip(".")
    return t


def crossref_meta(doi):
    try:
        m = http_json(f"https://api.crossref.org/works/{urllib.request.quote(doi)}")["message"]
        year = None
        for k in ("issued", "published-print", "published-online"):
            dp = (m.get(k) or {}).get("date-parts") or []
            if dp and dp[0] and dp[0][0]:
                year = dp[0][0]
                break
        fam = ((m.get("author") or [{}])[0].get("family") or "").strip()
        title = sanitize_title((m.get("title") or [""])[0])
        if year and fam and title:
            return {"year": year, "author": fam, "title": title,
                    "filename": f"({year} {fam}) {title}.pdf"}
    except Exception as e:
        eprint(f"  crossref: miss ({e.__class__.__name__})")
    return {}


def unpaywall(doi, email):
    try:
        d = http_json(f"https://api.unpaywall.org/v2/{urllib.request.quote(doi)}?email={email}")
        urls, seen = [], set()
        for loc in ([d.get("best_oa_location")] + (d.get("oa_locations") or [])):
            u = (loc or {}).get("url_for_pdf")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
        return {"is_oa": d.get("is_oa"), "oa_status": d.get("oa_status"), "pdf_urls": urls[:4]}
    except Exception as e:
        eprint(f"  unpaywall: miss ({e.__class__.__name__})")
        return {"is_oa": None, "oa_status": "?", "pdf_urls": []}


def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"ok": False, "error": "usage: fast_get.py <DOI-or-URL> [--out F] [--dest D] [--classify-only]"}))
        return 2
    inp, out, dest, classify_only = args[0], "", ".", False
    email = os.environ.get("UNPAYWALL_EMAIL", "test@example.com")
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--out":
            out = args[i + 1]; i += 2
        elif a == "--dest":
            dest = args[i + 1]; i += 2
        elif a == "--email":
            email = args[i + 1]; i += 2
        elif a == "--classify-only":
            classify_only = True; i += 1
        else:
            i += 1

    doi_m = re.search(r"10\.\d{4,9}/[^\s?#]+", inp)
    doi = doi_m.group(0) if doi_m and "arxiv.org" not in inp.lower() else (doi_m.group(0) if doi_m else "")
    url = inp if inp.lower().startswith("http") else ""

    table = load_access_tables()
    cls = classify(doi, url, table)
    eprint(f"  classify: publisher={cls['publisher']} access={cls['access']}"
           + (f" ({cls['note']})" if cls.get("note") else ""))

    res = {"ok": False, "action": "to-browser", "classification": cls}

    # canonical filename via Crossref (also used by the browser path)
    meta = crossref_meta(doi) if (doi and not out) else {}
    if meta:
        res["suggest"] = meta
        eprint(f"  crossref: {meta['filename']}")

    if classify_only:
        res["action"] = "classified"
        print(json.dumps(res, ensure_ascii=True))
        return 3

    # candidate direct-PDF URLs, cheapest first
    cands = []
    if url:
        m = re.search(r"arxiv\.org/(abs|pdf)/([\w.\-/]+?)(v\d+)?(\.pdf)?$", url, re.I)
        if m:
            cands.append(f"https://arxiv.org/pdf/{m.group(2)}")
        elif re.search(r"\.pdf(\?|$)", url, re.I) or "/pdf" in url.lower():
            cands.append(url)
    if doi:
        if doi.startswith("10.48550/"):
            cands.append("https://arxiv.org/pdf/" + doi.split("arXiv.")[-1])
        oa = unpaywall(doi, email)
        res["oa"] = oa
        cands += oa["pdf_urls"]

    tried = []
    data, src = None, None
    for c in cands:
        host = (re.match(r"https?://([^/]+)", c) or [None, ""])[1].lower()
        if any(p in host for p in PROTECTED):
            eprint(f"  fast-get: skip protected host {host}")
            continue
        tried.append(c)
        data = try_pdf(c)
        if data:
            src = c
            break
    res["tried"] = len(tried)

    if data:
        fname = out or meta.get("filename") or ""
        if not fname:
            base = re.sub(r"[\\/:?&=#]", "_", (src.rsplit("/", 1)[-1] or "paper"))[:80]
            fname = base if base.lower().endswith(".pdf") else base + ".pdf"
        os.makedirs(dest, exist_ok=True)
        path = os.path.join(dest, fname)
        with open(path, "wb") as f:
            f.write(data)
        res.update({"ok": True, "action": "downloaded", "source": src,
                    "path": path.replace("\\", "/"), "filename": fname, "size": len(data)})
        eprint(f"  fast-get: OK {len(data)} B <- {src[:90]}")
        print(json.dumps(res, ensure_ascii=True))
        return 0

    if cls["access"] == "none" and not (res.get("oa") or {}).get("pdf_urls"):
        res["action"] = "skip-none"
        print(json.dumps(res, ensure_ascii=True))
        return 4

    print(json.dumps(res, ensure_ascii=True))
    return 3


if __name__ == "__main__":
    sys.exit(main())
