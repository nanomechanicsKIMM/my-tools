"""참고문헌 DOI로부터 PDF를 자동 다운로드하는 스크립트.

다운로드 우선순위 (검증된 순서):
1. Semantic Scholar — Open Access PDF
2. Publisher 직접 접근 — 출판사별 PDF URL 패턴
3. sci-hub.vg — iframe에서 CDN PDF URL 추출
4. Google Scholar — [PDF] 링크 탐색

사용법:
    PYTHONUTF8=1 python download_refs.py --input doi_list.txt --output ./refs
    PYTHONUTF8=1 python download_refs.py --doi-map '{"01":"10.xxxx/yyyy", "02":"10.xxxx/zzzz"}'
"""
import argparse
import io
import json
import os
import re
import sys
import time

import requests
import urllib3

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
session = requests.Session()
# 기관 내부망의 SSL 인터셉션 때문에 기본은 검증 비활성화.
# REQUESTS_CA_BUNDLE(또는 CURL_CA_BUNDLE)에 기관 CA 경로를 지정하면 검증 활성화.
_ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE")
if _ca_bundle:
    session.verify = _ca_bundle
else:
    session.verify = False
    urllib3.disable_warnings()
session.headers["User-Agent"] = UA


def is_pdf(content):
    return len(content) > 1000 and content[:5] == b"%PDF-"


def dl(url, referer=None):
    """URL에서 PDF 다운로드 시도."""
    try:
        h = {"User-Agent": UA}
        if referer:
            h["Referer"] = referer
        r = session.get(url, timeout=60, allow_redirects=True, headers=h)
        if r.status_code == 200 and is_pdf(r.content):
            return r.content
    except Exception:
        pass
    return None


# --- Source 1: Semantic Scholar ---
def try_semantic_scholar(doi):
    try:
        r = session.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=isOpenAccess,openAccessPdf",
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            oa_pdf = data.get("openAccessPdf")
            if oa_pdf and oa_pdf.get("url"):
                return dl(oa_pdf["url"])
    except Exception:
        pass
    return None


# --- Source 2: Publisher Direct ---
def try_publisher(doi):
    try:
        r = session.get(f"https://doi.org/{doi}", timeout=20, allow_redirects=True)
        if r.status_code != 200:
            return None
        url = r.url
        candidates = []

        if "nature.com" in url:
            candidates.append(url.rstrip("/") + ".pdf")
        if "journals.aps.org" in url:
            candidates.append(url.replace("/abstract/", "/pdf/"))
        if "pnas.org" in url:
            m = re.search(r"doi/(?:abs/|full/)?(10\.\d+/\S+)", url)
            if m:
                candidates.append(f"https://www.pnas.org/doi/pdf/{m.group(1)}")
        if "science.org" in url:
            candidates.append(re.sub(r"/doi/(abs|full)/", "/doi/pdf/", url))
            if "/doi/10." in url:
                candidates.append(url.replace("/doi/", "/doi/pdf/"))
        if "pubs.aip.org" in url or "asa.scitation.org" in url:
            candidates.append(
                url.replace("/doi/", "/doi/pdf/")
                .replace("/abs/", "/pdf/")
                .replace("/full/", "/pdf/")
            )
        if "sciencedirect.com" in url or "elsevier.com" in url:
            pii = re.search(r"pii/(\S+?)(?:\?|$|#)", url)
            if pii:
                candidates.append(
                    f"https://www.sciencedirect.com/science/article/pii/{pii.group(1)}/pdfft"
                )
        if "ieeexplore.ieee.org" in url:
            m = re.search(r"document/(\d+)", url)
            if m:
                arnumber = m.group(1)
                candidates.append(
                    f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?arnumber={arnumber}"
                )
                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={arnumber}"
                candidates.append(stamp_url)

        for c in candidates:
            content = dl(c, referer=url)
            if content:
                return content

        # IEEE stamp fallback: parse iframe
        if "ieeexplore.ieee.org" in url:
            m = re.search(r"document/(\d+)", url)
            if m:
                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={m.group(1)}"
                try:
                    sr = session.get(stamp_url, timeout=30, headers={"Referer": url})
                    if sr.status_code == 200:
                        if is_pdf(sr.content):
                            return sr.content
                        pdf_m = re.search(r'iframe[^>]+src="(https?://[^"]+)"', sr.text)
                        if pdf_m:
                            return dl(pdf_m.group(1), referer=stamp_url)
                except Exception:
                    pass
    except Exception:
        pass
    return None


# --- Source 3: sci-hub.vg ---
def try_scihub(doi):
    try:
        r = session.get(f"https://sci-hub.vg/{doi}", timeout=30)
        if r.status_code != 200:
            return None

        # Extract iframe src (PDF URL)
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\'\s]+)["\']', r.text)
        if iframes:
            pdf_url = iframes[0].split("#")[0] + "?download=true"
            pr = session.get(pdf_url, timeout=60, headers={"Referer": "https://sci-hub.vg/"})
            if pr.status_code == 200 and is_pdf(pr.content):
                return pr.content

        # Fallback: save button URL
        save_urls = re.findall(r"location\.href='([^']+)'", r.text)
        for save_url in save_urls:
            save_url = save_url.replace("\\/", "/")
            if "pdf" in save_url.lower():
                pr = session.get(save_url, timeout=60, headers={"Referer": "https://sci-hub.vg/"})
                if pr.status_code == 200 and is_pdf(pr.content):
                    return pr.content
    except Exception:
        pass
    return None


# --- Source 4: Google Scholar ---
def try_google_scholar(doi):
    try:
        r = session.get(
            f"https://scholar.google.com/scholar?q={doi}",
            timeout=15,
            headers={"User-Agent": UA},
        )
        if r.status_code == 200:
            pdf_links = re.findall(
                r'href="(https?://[^"]+)"[^>]*>\[PDF\]', r.text, re.IGNORECASE
            )
            for link in pdf_links[:3]:
                content = dl(link)
                if content:
                    return content
    except Exception:
        pass
    return None


# --- Main ---
SOURCES = [
    ("SemanticScholar", try_semantic_scholar),
    ("Publisher", try_publisher),
    ("Sci-Hub", try_scihub),
    ("GoogleScholar", try_google_scholar),
]


def download_one(doi, output_dir, ref_num):
    """단일 DOI에 대해 PDF 다운로드 시도. 성공 시 파일 경로 반환."""
    outpath = os.path.join(output_dir, f"ref_{ref_num}.pdf")
    if os.path.exists(outpath) and os.path.getsize(outpath) > 1000:
        return outpath, "이미 존재"

    for name, func in SOURCES:
        content = func(doi)
        if content:
            with open(outpath, "wb") as f:
                f.write(content)
            return outpath, name
        time.sleep(1)

    return None, "FAILED"


def load_doi_map(input_path):
    """doi_list.txt 또는 JSON에서 DOI 맵 로드."""
    doi_map = {}
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                doi_map[parts[0].strip()] = parts[1].strip()
            else:
                # Auto-number
                num = f"{len(doi_map) + 1:02d}"
                doi_map[num] = line
    return doi_map


def main():
    parser = argparse.ArgumentParser(description="참고문헌 PDF 자동 다운로드")
    parser.add_argument("--input", help="doi_list.txt 경로")
    parser.add_argument("--doi-map", help="DOI JSON 맵 (직접 지정)")
    parser.add_argument("--output", required=True, help="출력 폴더 경로")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if args.doi_map:
        doi_map = json.loads(args.doi_map)
    elif args.input:
        doi_map = load_doi_map(args.input)
    else:
        print("ERROR: --input 또는 --doi-map 필요", file=sys.stderr)
        sys.exit(1)

    success = []
    failed = []

    for num in sorted(doi_map.keys()):
        doi = doi_map[num]
        print(f"[{num}] {doi} ... ", end="", flush=True)
        path, source = download_one(doi, output_dir, num)
        if path:
            print(f"OK ({source})")
            success.append((num, doi, source))
        else:
            print("FAILED")
            failed.append((num, doi))
        time.sleep(1)

    # Generate report
    report_path = os.path.join(output_dir, "download_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 참고문헌 다운로드 결과\n\n")
        f.write(f"전체: {len(doi_map)}건 | 성공: {len(success)}건 | 실패: {len(failed)}건\n\n")

        if success:
            f.write("## 성공\n\n")
            f.write("| # | DOI | 소스 |\n|---|-----|------|\n")
            for num, doi, source in success:
                f.write(f"| {num} | `{doi}` | {source} |\n")
            f.write("\n")

        if failed:
            f.write("## 수동 다운로드 필요\n\n")
            f.write("아래 링크에서 직접 PDF를 다운로드하여 `ref_NN.pdf`로 저장하세요.\n\n")
            for num, doi in failed:
                f.write(f"- **ref_{num}**: [https://doi.org/{doi}](https://doi.org/{doi})\n")
            f.write("\n")

    print(f"\n=== 결과 ===")
    print(f"성공: {len(success)}/{len(doi_map)}")
    print(f"보고서: {report_path}")
    if failed:
        print(f"실패 ({len(failed)}건) — 수동 다운로드 필요:")
        for num, doi in failed:
            print(f"  [{num}] https://doi.org/{doi}")


if __name__ == "__main__":
    main()
