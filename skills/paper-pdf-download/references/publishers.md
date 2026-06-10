# 출판사별 PDF URL 패턴 / 다운로드 메모

`resolve_pdf.js`에 일부 유도 규칙이 내장됨. `<DOI>`는 `10.xxxx/...` 전체.
랜딩 페이지에서 same-origin으로 PDF를 받는 것이 원칙(교차 출처 CDN은 cdn 폴백이 처리).

| 출판사 | DOI prefix | 랜딩 패턴 | PDF URL 패턴 | 방식 | 비고 |
|--------|-----------|-----------|--------------|------|------|
| arXiv | (DOI 아님) | `arxiv.org/abs/<id>` | `arxiv.org/pdf/<id>` | direct | 봇 차단 없음, headless OK |
| Optica (OSA) | 10.1364 | `opg.optica.org/abstract.cfm?URI=<jrnl-v-i-p>` 또는 `/<jrnl>/fulltext.cfm?uri=` | `opg.optica.org/viewmedia.cfm?uri=<jrnl-v-i-p>&seq=0` | direct | **Radware 봇차단 → 헤드드 필수**. `<jrnl>`=oe/ol/boe/prj 등. DOI→uri는 resolve 필요 |
| PNAS | 10.1073 | `www.pnas.org/doi/<DOI>` | `www.pnas.org/doi/pdf/<DOI>?download=true` | direct | Cloudflare/Atypon. PDF에 기관 IP 워터마크 |
| MDPI | 10.3390 | `www.mdpi.com/<ISSN>/<vol>/<iss>/<art>` | `<landing>/pdf` (→ `mdpi-res.com` CDN로 302) | **cdn 폴백** | Cloudflare + 교차출처 CDN. direct는 CORS 실패가 정상 |
| Nature / Springer Nature | 10.1038 | `www.nature.com/articles/<id>` | `www.nature.com/articles/<id>.pdf` | direct | 구독 타이틀은 **로그인 게이트**(IP-only 새 프로필 `--connect` 실패) → SSO 로그인된 실제 세션 필요. 미구독 closed면 ILL/저자요청. `.pdf`가 HTML 반환 시 미licensed |
| Springer | 10.1007 | `link.springer.com/article/<DOI>` | `link.springer.com/content/pdf/<DOI>.pdf` | direct | |
| Wiley | 10.1002 | `onlinelibrary.wiley.com/doi/<DOI>` | OA: **`<sub>.onlinelibrary.wiley.com/doi/pdfdirect/<DOI>`** (`/doi/pdf/`는 HTML 뷰어) | direct(헤드드/--connect) | **정확한 서브도메인 필수**(예 SID=`sid.onlinelibrary`)로 same-origin fetch. ✅ Ha·Eccles msid OA(2026-06-09) |
| ACS | 10.1021 | `pubs.acs.org/doi/<DOI>` | `pubs.acs.org/doi/pdf/<DOI>` | direct(헤드드/--connect) | **KIMM IP 구독 → 로그인 없는 새 프로필 `--connect`도 성공**. ✅ Nano Lett 0c03939(2026-06-10) |
| RSC | 10.1039 | `pubs.rsc.org/en/content/articlelanding/...` | `pubs.rsc.org/en/content/articlepdf/...` | direct | article id는 resolve 필요(landing 스크랩) |
| Taylor & Francis | 10.1080 | `tandfonline.com/doi/<DOI>` | `tandfonline.com/doi/pdf/<DOI>` | direct | |
| Elsevier/ScienceDirect | 10.1016 | `sciencedirect.com/science/article/pii/<PII>` | `/pii/<PII>/pdfft` → presigned `pdf.sciencedirectassets.com` | **✅ `--connect` + `sd_resolve.js`/`sd_download.js`** | pdfft를 그냥 fetch하면 `cra_js_challenge` HTML(~51KB). **실제 Chrome 탭으로 navigate**해야 JS 챌린지가 풀려 presigned S3 URL(300s·쿠키불요) 발급 → `curl --ssl-no-revoke -A <UA> -e <referer>`. ✅ Kaçar OLEDoS 16.3MB(2026-06-09). 단순 same-origin fetch는 실패가 정상 |
| IEEE | 10.1109 | `ieeexplore.ieee.org/document/<num>` | `/stampPDF/getPDF.jsp?...arnumber=<num>` | direct(헤드드) | iframe viewer, arnumber resolve 필요 |

## 일반 규칙
- DOI prefix → 출판사 식별. 위 표에 없으면 resolve_pdf.js가 랜딩 페이지의 PDF 앵커를 스크랩.
- **헤드드 필요 판단**: 결과가 HTML/`Radware Captcha`/`Just a moment`(Cloudflare)면 `-b papers --login`.
- **교차 출처 판단**: `Failed to fetch` + (redirect:manual 시 `opaqueredirect`) → cdn 폴백.
- **페이월 판단**: 페이지에 "Buy or subscribe"/"access via your institution" + Unpaywall `is_oa:false`
  → 우회 금지, 합법 경로 안내.

## Unpaywall (합법 OA 확인 — 항상 우선 점검 가능)
```bash
curl -s -k "https://api.unpaywall.org/v2/<DOI>?email=<your-email>" \
  | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('is_oa'),d.get('oa_status'),(d.get('best_oa_location') or {}).get('url_for_pdf'))"
```
`is_oa:true`면 OA URL로 바로 받을 수 있어 봇 차단 자체를 회피.
