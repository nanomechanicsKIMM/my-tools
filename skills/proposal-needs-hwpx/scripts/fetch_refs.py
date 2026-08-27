# -*- coding: utf-8 -*-
"""수요조사서 근거 문헌 확보 유틸 (proposal-needs-hwpx Phase 3).

다운로드 우선순위 사다리를 명령 단위로 제공한다. 모든 네트워크 호출은
truststore(사내 프록시 인증서) + 브라우저 UA를 사용한다.

사용법:
  python fetch_refs.py local "remote epitaxy"          # 로컬 References 검색
  python fetch_refs.py get <URL> <저장경로>            # 직접 다운로드 (arXiv, 뉴스, HTML)
  python fetch_refs.py abstract "DOI:10.1063/1.4776707" <저장경로_초록.html>
  python fetch_refs.py abstract "제목 키워드 검색어" <저장경로_초록.html>
  python fetch_refs.py epmc 10.1126/sciadv.adz3605 <저장경로.pdf>
  python fetch_refs.py patent US11471871B2 <저장폴더>

퍼블리셔 직접 URL(AIP, OUP, Elsevier, science.org)은 403이 정상이다.
abstract(서지 API) 또는 epmc(OA 미러)로 우회할 것. 429는 30초 대기 후 재시도.
"""
import sys, io, json, re, time, html as H
import urllib.request, urllib.parse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 (research)'}
REFS_DIR = Path(r'D:\Zettelkasten\References')
S2 = 'https://api.semanticscholar.org/graph/v1'
FIELDS = 'title,year,abstract,venue,externalIds,openAccessPdf,authors'


def http_get(url, timeout=60, retries=1, wait=30):
    for i in range(retries + 1):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < retries:
                print(f'429 rate limit, {wait}s 대기 후 재시도...')
                time.sleep(wait)
                continue
            raise
    raise RuntimeError('unreachable')


def cmd_local(query):
    hits = [p.name for p in REFS_DIR.iterdir() if query.lower() in p.name.lower()]
    print(f'{len(hits)} hits in {REFS_DIR}:')
    for h in hits:
        print(' ', h)


def cmd_get(url, out):
    data = http_get(url)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    kind = 'PDF' if data[:4] == b'%PDF' else 'HTML/기타'
    print(f'saved {len(data)} bytes ({kind}) -> {out}')


def _write_abstract_html(meta, out):
    """meta: dict(title, year, venue, authors[list[str]], doi, abstract, oa)"""
    body = (f"<html><meta charset='utf-8'><h1>{H.escape(meta.get('title') or '')}</h1>"
            f"<p><b>{meta.get('year')}</b> | {H.escape(meta.get('venue') or '')}</p>"
            f"<p>{H.escape(', '.join(meta.get('authors') or []))}</p>"
            f"<p>DOI: {meta.get('doi')}</p><h2>Abstract</h2>"
            f"<p>{H.escape(meta.get('abstract') or '(초록 미제공)')}</p>"
            f"<p>OA PDF: {meta.get('oa')}</p>"
            f"<p>source: {meta.get('src')}, retrieved {time.strftime('%Y-%m-%d')}</p></html>")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(body, encoding='utf-8')


def _try_oa_pdf(oa_url, out_html):
    if not oa_url:
        return
    try:
        d = http_get(oa_url, timeout=90)
        if d[:4] == b'%PDF':
            pdf = str(out_html).replace('_초록.html', '.pdf').replace('.html', '.pdf')
            Path(pdf).write_bytes(d)
            print(f'  OA PDF saved -> {pdf}')
    except Exception as e:
        print('  OA PDF 실패:', str(e)[:70])


def cmd_abstract(ident, out):
    """Semantic Scholar 우선, 429/실패 시 OpenAlex."""
    try:
        if ident.upper().startswith('DOI:'):
            j = json.loads(http_get(f'{S2}/paper/{ident}?fields={FIELDS}', retries=1))
            papers = [j]
        else:
            j = json.loads(http_get(f'{S2}/paper/search?query={urllib.parse.quote(ident)}&fields={FIELDS}&limit=3', retries=1))
            papers = j.get('data', [])[:1]
        p = papers[0]
        meta = dict(title=p.get('title'), year=p.get('year'), venue=p.get('venue'),
                    authors=[a['name'] for a in p.get('authors', [])[:8]],
                    doi=(p.get('externalIds') or {}).get('DOI'), abstract=p.get('abstract'),
                    oa=(p.get('openAccessPdf') or {}).get('url'), src='Semantic Scholar API')
    except Exception as e:
        print('S2 실패, OpenAlex 폴백:', str(e)[:60])
        if ident.upper().startswith('DOI:'):
            w = json.loads(http_get(f'https://api.openalex.org/works/doi:{ident[4:]}'))
        else:
            w = json.loads(http_get(f'https://api.openalex.org/works?search={urllib.parse.quote(ident)}&per-page=3'))['results'][0]
        inv = w.get('abstract_inverted_index')
        absr = None
        if inv:
            pos = {p: word for word, ps in inv.items() for p in ps}
            absr = ' '.join(pos[i] for i in sorted(pos))
        meta = dict(title=w.get('title'), year=w.get('publication_year'),
                    venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                    authors=[a['author']['display_name'] for a in w.get('authorships', [])[:8]],
                    doi=w.get('doi'), abstract=absr,
                    oa=(w.get('best_oa_location') or {}).get('pdf_url'), src='OpenAlex API')
    _write_abstract_html(meta, out)
    print('abstract saved ->', out, '| title:', (meta.get('title') or '')[:70])
    _try_oa_pdf(meta.get('oa'), out)


def cmd_epmc(doi, out):
    q = urllib.parse.quote(f'DOI:"{doi}"')
    j = json.loads(http_get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json', retries=1))
    hits = j['resultList']['result']
    if not hits or not hits[0].get('pmcid'):
        print('PMC 미수록:', doi)
        return
    pmc = hits[0]['pmcid']
    print('PMC id:', pmc)
    d = http_get(f'https://europepmc.org/articles/{pmc}?pdf=render', timeout=120, retries=2)
    if d[:4] == b'%PDF':
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(d)
        print(f'PDF saved {len(d)} -> {out}')
    else:
        print('PDF 아님 (렌더 실패)')


def cmd_patent(patno, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    html = http_get(f'https://patents.google.com/patent/{patno}/en').decode('utf-8', 'replace')
    (outdir / f'{patno}.html').write_text(html, encoding='utf-8')
    m = re.search(r'https://patentimages\.storage\.googleapis\.com/[^"]+\.pdf', html)
    print('page saved. pdf link:', m.group(0) if m else None)
    if m:
        d = http_get(m.group(0), timeout=90)
        (outdir / f'{patno}.pdf').write_bytes(d)
        print(f'patent PDF saved {len(d)}')


if __name__ == '__main__':
    cmds = {'local': cmd_local, 'get': cmd_get, 'abstract': cmd_abstract,
            'epmc': cmd_epmc, 'patent': cmd_patent}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(1)
    cmds[sys.argv[1]](*sys.argv[2:])
