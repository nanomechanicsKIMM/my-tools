#!/usr/bin/env python
"""library_check.py <DOI> <library_dir>

Crossref로 DOI의 (연도, 첫저자 family, 제목)을 조회한 뒤, library_dir의
'(YYYY Author) Title.pdf' 파일들과 대조하여 이미 보관된 논문이면 그 파일명을
stdout에 한 줄 출력한다. 매치 없거나 어떤 오류든 발생하면 아무것도 출력하지
않고 exit 0 (다운로드 진행). KIMM 프록시 SSL은 truststore로 우회.

매치 규칙 (연도 ±1 허용 — online-first/print 연도 불일치 대응):
  1) 정규화 제목 유사도 >= 0.90 (difflib), 또는
  2) 유사도 >= 0.80 이고 첫저자 family(ASCII)가 파일명에 포함
한국어 표기 저자(예: '채희엽 교수')는 family 매치가 안 되므로 1)에만 의존.
"""
import sys, os, json, re, difflib
import urllib.request

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

def main():
    if len(sys.argv) < 3:
        return
    doi, lib = sys.argv[1], sys.argv[2]
    if not os.path.isdir(lib):
        return
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
    req = urllib.request.Request(
        f"https://api.crossref.org/works/{doi}",
        headers={"User-Agent": "library-check/1.0 (mailto:jaehkim@kimm.re.kr)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        m = json.load(r)["message"]
    title = (m.get("title") or [""])[0]
    if not title:
        return
    years = set()
    for k in ("published-print", "published-online", "issued"):
        try:
            years.add(int(m[k]["date-parts"][0][0]))
        except Exception:
            pass
    fam = ""
    try:
        fam = (m.get("author") or [{}])[0].get("family", "") or ""
    except Exception:
        pass
    tnorm = norm(title)
    fam_l = fam.lower() if fam and fam.isascii() else ""
    yset = set()
    for y in years:
        yset.update({y - 1, y, y + 1})

    best, best_ratio = None, 0.0
    pat = re.compile(r'^\((\d{4})[^)]*\)\s*(.+)\.pdf$', re.I)
    for fn in os.listdir(lib):
        g = pat.match(fn)
        if not g:
            continue
        if int(g.group(1)) not in yset:
            continue
        ratio = difflib.SequenceMatcher(None, tnorm, norm(g.group(2))).ratio()
        ok = ratio >= 0.90 or (ratio >= 0.80 and fam_l and fam_l in fn.lower())
        if ok and ratio > best_ratio:
            best, best_ratio = fn, ratio
    if best:
        print(best)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
