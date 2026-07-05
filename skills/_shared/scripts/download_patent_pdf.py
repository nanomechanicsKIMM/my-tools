"""Unified patent PDF downloader for Claude patent skills.

Usage:
    python download_patent_pdf.py --kr <applno> ... --out <dir> [--verify]
    python download_patent_pdf.py --gp <patent_id> ... --out <dir> [--verify]

Sources:
    --kr  Korean patent application number (13 digits, no hyphen). Uses KIPRIS Plus API.
    --gp  Foreign patent Google Patents ID (e.g., WO2020016250A1, US8088067B2).

Requires:
    - $HOME/Claude_work/.env containing KIPRIS_REST_AccessKey=...
    - Python >= 3.9
"""

from __future__ import annotations
import argparse
import io
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Force UTF-8 on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def load_env_key(varname: str) -> str:
    env_path = Path.home() / "Claude_work" / ".env"
    if not env_path.exists():
        raise SystemExit(f"missing env file: {env_path}")
    # Accept both the canonical name and the ALL_CAPS underscore variant seen
    # in some .env files (e.g. KIPRIS_REST_AccessKey vs KIPRIS_REST_ACCESS_KEY).
    candidates = {varname, re.sub(r"(?<=[a-z])(?=[A-Z])", "_", varname).upper()}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        for cand in candidates:
            if line.startswith(f"{cand}="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"{varname} not found in {env_path}")


def http_get(url: str, extra: dict | None = None, timeout: int = 60) -> tuple[int, dict, bytes]:
    headers = dict(UA)
    if extra:
        headers.update(extra)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.getcode(), dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read() or b""
    except Exception as e:
        return -1, {}, str(e).encode()


def kipris_biblio(applno: str, key: str) -> dict:
    """Return parsed biblio dict from applicationNumberSearchInfo."""
    url = (
        "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/"
        "applicationNumberSearchInfo?"
        + urllib.parse.urlencode({"applicationNumber": applno, "accessKey": key})
    )
    _, _, raw = http_get(url, timeout=30)
    text = raw.decode("utf-8", "replace")
    fields = [
        "Applicant", "InventionName", "ApplicationNumber",
        "OpeningNumber", "OpeningDate",
        "RegistrationNumber", "RegistrationDate", "RegistrationStatus",
    ]
    out = {}
    for f in fields:
        m = re.search(rf"<{f}>([^<]*)</{f}>", text)
        out[f] = m.group(1).strip() if m else ""
    return out


def kipris_fulltext_path(applno: str, key: str, op: str) -> str | None:
    """Query KIPRIS for the PDF download path.

    op is 'getPubFullTextInfoSearch' (공개공보) or 'getAnnFullTextInfoSearch' (공고/등록).
    """
    url = (
        f"http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/{op}?"
        + urllib.parse.urlencode({"applicationNumber": applno, "ServiceKey": key})
    )
    _, _, raw = http_get(url, timeout=30)
    m = re.search(r"<path>([^<]+)</path>", raw.decode("utf-8", "replace"))
    return m.group(1).strip() if m else None


def download_kr(applno: str, out_dir: Path, key: str) -> list[Path]:
    """Download PDF(s) for a KR patent application number. Returns list of saved paths."""
    biblio = kipris_biblio(applno, key)
    title = biblio.get("InventionName", "")[:40] or "(no title)"
    status = biblio.get("RegistrationStatus", "") or "공개"
    print(f"\n=== KR {applno} — {title} [{status}] ===")
    saved: list[Path] = []
    order = ["getAnnFullTextInfoSearch", "getPubFullTextInfoSearch"] \
            if biblio.get("RegistrationNumber") \
            else ["getPubFullTextInfoSearch", "getAnnFullTextInfoSearch"]
    for op in order:
        path = kipris_fulltext_path(applno, key, op)
        suffix = "_grant" if "Ann" in op else "_pub"
        if not path:
            print(f"  [{op}] no <path>")
            continue
        _, _, data = http_get(path, timeout=120)
        if data[:4] != b"%PDF":
            print(f"  [{op}] fetched {len(data)} bytes, NOT PDF")
            continue
        safe_title = re.sub(r"[^\w\-]+", "_", title).strip("_")[:30]
        fname = f"KR{applno}_{safe_title}{suffix}.pdf"
        p = out_dir / fname
        p.write_bytes(data)
        saved.append(p)
        print(f"  [{op}] OK -> {p.name} ({len(data)//1024} KB)")
        # Skip pub if we already have grant (avoid duplicate content)
        if suffix == "_grant":
            break
    return saved


def download_gp(patent_id: str, out_dir: Path, retries: int = 4) -> Path | None:
    """Scrape Google Patents for patentimages PDF. Handle 503 with retry/backoff."""
    page = f"https://patents.google.com/patent/{patent_id}/en"
    print(f"\n=== GP {patent_id} ===")
    html = None
    for i in range(retries):
        code, _, body = http_get(page, extra={"Referer": "https://www.google.com/"})
        if code == 200 and body:
            html = body.decode("utf-8", "ignore")
            break
        wait = 3 + i * 2
        print(f"  attempt {i+1} status={code}, sleep {wait}s")
        time.sleep(wait)
    if not html:
        print(f"  FAIL: page not reachable ({patent_id})")
        return None
    m = re.search(r"https://patentimages\.storage\.googleapis\.com/[^\"'\s<>]+\.pdf", html)
    if not m:
        print(f"  FAIL: no patentimages URL in page")
        return None
    code, _, data = http_get(m.group(0), extra={"Referer": page}, timeout=120)
    if data[:4] != b"%PDF":
        print(f"  FAIL: downloaded {len(data)} bytes, not PDF")
        return None
    p = out_dir / f"{patent_id}.pdf"
    p.write_bytes(data)
    print(f"  OK -> {p.name} ({len(data)//1024} KB)")
    return p


def verify_first_page(pdf: Path) -> str:
    """Return a short identification string from first pages (title/applicant if extractable)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "(pymupdf not installed — skip verify)"
    doc = fitz.open(pdf)
    txt = ""
    for i in range(min(3, doc.page_count)):
        t = doc[i].get_text().strip()
        if t:
            txt = t
            break
    doc.close()
    if not txt:
        return "(image-only PDF — render for visual check)"
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    head = " | ".join(lines[:8])
    return head[:300]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--kr", nargs="*", default=[], help="KR application numbers (13 digits, no hyphen)")
    ap.add_argument("--gp", nargs="*", default=[], help="Google Patents IDs (e.g., WO2020016250A1)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--verify", action="store_true", help="Verify first page text of each download")
    args = ap.parse_args()

    if not args.kr and not args.gp:
        ap.error("at least one of --kr or --gp required")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []

    if args.kr:
        try:
            key = load_env_key("KIPRIS_REST_AccessKey")
        except SystemExit as e:
            print(f"KIPRIS key error: {e}", file=sys.stderr)
            return 2
        for applno in args.kr:
            applno = re.sub(r"[-\s]", "", applno)
            saved.extend(download_kr(applno, out_dir, key))
            time.sleep(1)

    for pid in args.gp:
        p = download_gp(pid, out_dir)
        if p:
            saved.append(p)
        time.sleep(3)

    print("\n=== Summary ===")
    for p in saved:
        line = f"  {p.name} ({p.stat().st_size//1024} KB)"
        if args.verify:
            line += f"\n      verify: {verify_first_page(p)}"
        print(line)
    print(f"Total: {len(saved)} file(s) saved to {out_dir}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
