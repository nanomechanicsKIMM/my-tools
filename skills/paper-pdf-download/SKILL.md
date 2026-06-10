---
name: paper-pdf-download
description: "봇 차단·기관 구독 저널의 논문 PDF를 사용자 인증 브라우저 세션으로 다운로드하는 스킬. LLM이 직접 못 받는(WebFetch 차단) 저널 PDF를 dev-browser(실제 Chromium)로 받는다. '논문 PDF 다운로드', '저널 PDF', 'DOI로 논문 받기', '참고문헌 PDF 다운로드', 'paper pdf download', 'journal pdf', 'download paper', 'Optica/MDPI/PNAS/Nature/Wiley/ACS PDF', '봇 차단 논문', '기관 접근 논문', 'institutional access pdf', 'Cloudflare 논문 다운로드' 등의 키워드/요청 시 사용. 다른 스킬(예: paper-review)이나 에이전트가 참고문헌 PDF 수집 엔진으로 호출 가능."
---

# Paper PDF Download Skill

LLM은 저널 사이트의 봇 차단(Radware/Cloudflare 등) 때문에 논문 PDF를 직접 받지 못한다.
이 스킬은 **dev-browser(실제 Chromium + 사용자 인증 세션: 기관 IP + 로그인 쿠키)**로
PDF를 받아 디스크에 저장한다. **봇 차단을 "우회"하는 게 아니라, 정상 브라우저 + 정당한
기관 접근으로 받으므로 차단 대상이 아니게 된다. 합법적 구독/오픈액세스 범위에서만 동작하며,
진짜 페이월은 우회하지 않는다(Sci-Hub 등 불법 경로 사용 금지).**

## 전제조건

- **dev-browser CLI** 설치 필요 (QuickJS 샌드박스 + Playwright Chromium).
  - 위치: `C:\Users\JHKIM\AppData\Roaming\npm\node_modules\dev-browser` (v0.2.7), Chromium-1208
  - 미설치 시 README 참조: `npm i -g --ignore-scripts dev-browser` → 바이너리 수동 배치 → `dev-browser install`
- bash, `curl`(Unpaywall용), python(get_paper.sh의 JSON 파싱; 경로 `$PAPER_DL_PYTHON` 또는 miniconda 기본).

## 빠른 사용 (에이전트/스킬용 인터페이스)

### A. DOI/URL 한 방에 (resolve + download)
```bash
bash {skill_dir}/scripts/get_paper.sh <DOI-or-URL> [out.pdf] [-d <dest>] [-b papers] [-t 150] [--headless]
# 예: bash {skill_dir}/scripts/get_paper.sh 10.3390/cryst15030267 -d D:/Zettelkasten/References
```
- 기본 **헤드드(headed) + 브라우저 "papers"** — 봇 차단 출판사 통과에 필요(사용자가 PC 앞에 있어야 첫 로그인/captcha 처리).
- OA·비차단 일괄 다운로드는 `--headless`로 창 없이.

### B. PDF URL을 이미 알 때
```bash
bash {skill_dir}/scripts/dlpaper.sh <pdfUrl> [out.pdf] -l <landing> -b papers --login -t 120 -d <dest>
```

### C. PDF URL을 모를 때 (resolve만)
```bash
# resolve.json 작성 후 dev-browser로 실행 → {landing,title,pdfUrl,candidates,paywallHint}
printf '{"input":"%s"}\n' "10.1364/OE.525680" > ~/.dev-browser/tmp/resolve.json
dev-browser --browser papers --timeout 90 run {skill_dir}/scripts/resolve_pdf.js
```

기본 저장 폴더: 환경변수 `PAPER_DL_DEST`(미설정 시 현재 디렉터리).
KIMM 워크플로우는 `-d D:/Zettelkasten/References` (Obsidian References).

## 동작 원리 (핵심 설계 — 실측 검증됨)

PDF 바이트를 샌드박스 밖으로 빼내는 경로가 관건. dev-browser QuickJS는 `fs`/`fetch` 불가,
Playwright **다운로드 artifact(saveAs/readIntoBuffer)도 차단**. 따라서:

- **페이지 컨텍스트에서 `fetch`(credentials:include) → base64 → `writeFile`(~/.dev-browser/tmp)**
  채널만이 유일한 바이트 추출구. 래퍼가 tmp→목적지 이동 + `%PDF` 검증.
- 두 방식 자동 선택 (`download_paper.js`):
  - **direct**: 랜딩에서 PDF URL을 same-origin fetch (대부분 출판사).
  - **cdn**: direct가 CORS로 실패하면(출판사가 `/pdf`를 교차 출처 CDN으로 302; 예 MDPI→
    `mdpi-res.com`) → 브라우저 다운로드 트리거로 `download.url()`(최종 CDN URL) 캡처 →
    그 CDN 출처에 문서 로드 후 same-origin fetch. 출력 `method` 필드로 확인.

## 의사결정 트리

1. **DOI/URL 입력** → `get_paper.sh` (또는 resolve_pdf.js로 landing+pdfUrl 확보).
2. **결과가 PDF면** 완료. `%PDF` + 크기 검증, 가능하면 제목↔DOI 정합성 확인.
3. **결과가 HTML(비-PDF)이면** 원인 구분:
   - **봇 차단**(headless 탐지: Radware가 `HeadlessChrome` UA 차단) → **헤드드 재시도**
     (`-b papers --login`). 실제 창이 JS 챌린지 통과 후 세션 유지.
   - **진짜 페이월**("Buy or subscribe"/"access via your institution" + Unpaywall `is_oa:false`)
     → **우회 금지**. 합법 경로 안내: 기관 Shibboleth 로그인(헤드드 창에서 federation 로그인),
     도서관 ILL, 저자 요청. `paywallHint` 필드 + Unpaywall로 판정.
     - ⚠️ **단, Unpaywall `is_oa:false`는 "OA 사본 없음"일 뿐 "접근 불가"가 아니다.** KIMM이
       **구독**하는 타이틀(ACS·IOP·MDPI·일부 Wiley)은 기관 IP/SSO 세션(헤드드 `papers` 또는
       `--connect`)으로 **합법 접근 가능** → 페이월로 단정하기 전에 반드시 시도. 진짜 미구독
       closed(예: 로그인 게이트 Nature 비구독)만 ILL/저자요청으로 넘긴다.
4. **타임아웃**: dev-browser 스크립트 기본 30초 → 래퍼 기본 `-t 120`. 대용량(>5MB)은 `-t 150~180`.

## 출판사별 PDF URL 패턴

`references/publishers.md` 참조 (resolve_pdf.js에 내장된 유도 규칙 포함).
요약: arXiv `pdf/<id>` · Optica `viewmedia.cfm?uri=<jrnl-v-i-p>&seq=0` ·
PNAS/Atypon `/doi/pdf/<DOI>?download=true` · MDPI `<landing>/pdf`(→CDN) ·
Nature `/articles/<id>.pdf` · Wiley/ACS `/doi/pdf/<DOI>` · Springer `/content/pdf/<DOI>.pdf`.

## 트러블슈팅

| 증상 | 원인 | 조치 |
|------|------|------|
| `isPdf:false`, ct=text/html, magic=`<!DO` | 봇 차단 또는 페이월 HTML | 헤드드 재시도 → 그래도면 Unpaywall로 페이월 확인 |
| `Failed to fetch` | 교차 출처 CDN 리다이렉트 | 자동 cdn 폴백 동작(로그 `method:cdn:*`); 실패 시 토큰형 CDN(미지원) |
| `Radware Captcha Page` 제목 | headless 탐지 | `--login`(헤드드) 필수 |
| `Script timed out after 30s` | 기본 타임아웃 | `-t 150` 이상 |
| exit code 1인데 파일 정상 | QuickJS 대용량 teardown assertion | 정상. exit code 말고 stdout JSON+`%PDF`로 판정 |
| 제목 `잠시만 기다리십시오…`/`Just a moment` 스피너 무한반복 | **Cloudflare 관리형 챌린지가 자동화 Chromium 탐지** | **`--connect` 모드(아래) 사용** |

## Cloudflare 관리형 챌린지 → `--connect` (사용자 실제 Chrome)

PNAS·일부 사이트의 Cloudflare "사람인지 확인 중" 챌린지는 Playwright가 띄운 Chromium의
자동화 시그널(navigator.webdriver 등)을 탐지해 스피너에서 통과하지 않을 수 있다(간헐적;
cf_clearance 쿠키가 만료/플래그되면 발생). dev-browser의 managed Chromium으로는 한계.

**해결: 9222 포트의 Chrome 인스턴스에 attach** — 자동화 플래그가 없어 Cloudflare를 통과하고,
KIMM **기관 IP**(저널 구독이 IP 기반)와 SSO 세션을 그대로 사용한다.

> ⚠️ **Chrome 136+ 필수 주의 (검증됨 2026-06-09)**: **기본 프로필**(default user-data-dir)에서는
> `--remote-debugging-port`가 보안상 **무시**되어 9222가 바인딩되지 않는다 → attach 실패.
> 반드시 **격리 `--user-data-dir`** 로 별도 인스턴스를 띄운다(메인 Chrome/탭은 안 건드림).
> KIMM 저널 구독은 **IP 기반**이라 로그인 없는 새 프로필도 ACS·IOP(APEx)·MDPI는 통과하지만,
> **Nature(로그인 게이트)** 등은 새 프로필 실패 → 실제 로그인 세션이 필요하면 메인 프로필의
> 쿠키(`Local State` + `Default/Network/Cookies`)를 격리 디렉터리로 복사해 그 사본을 9222로 띄운다.
```powershell
# 1) PowerShell — 격리 프로필로 디버깅 Chrome 1회 기동 (메인 창과 독립)
Start-Process chrome.exe -ArgumentList `
  "--remote-debugging-port=9222","--user-data-dir=C:\Users\JHKIM\.dev-browser\chrome-connect","--no-first-run"
```
```bash
# 2) --connect 로 attach하여 다운로드
bash {skill_dir}/scripts/get_paper.sh 10.1073/pnas.1005828107 --connect -d D:/Zettelkasten/References
bash {skill_dir}/scripts/dlpaper.sh <pdfUrl> -l <landing> --connect
```
`--connect`는 `--browser/--login/--headless`를 무시하고 9222 포트의 Chrome을 쓴다.
(무인 자동화엔 부적합하나 가장 강건. 파일명은 Crossref `api.crossref.org/works/<doi>`로 첫저자·연도
조회 후 `(연도 첫저자) 제목.pdf`로 rename; crossref issue date가 online-first 연도와 다를 수 있음.)

## ScienceDirect (Elsevier) — `cra_js_challenge` → presigned CDN

ScienceDirect는 SPA라 resolver가 pdfft 앵커를 늦게 잡고, pdfft를 그냥 fetch하면 `cra_js_challenge`
HTML(~51KB)만 온다. **실제 Chrome 탭으로 navigate해야 JS 챌린지가 풀려** presigned S3 URL
(`pdf.sciencedirectassets.com`, 300초 만료·쿠키 불요)이 발급된다. 전용 헬퍼(`--connect` 필수):
```bash
# resolve: 대상 PII의 fresh pdfft 추출 (resolve.json {input: DOI-or-URL})
printf '{"input":"10.1016/j.nxnano.2025.100132"}\n' > ~/.dev-browser/tmp/resolve.json
dev-browser --connect --timeout 90 run {skill_dir}/scripts/sd_resolve.js
# resolve+download 통합 (job.json {article, pii, out}) — JS챌린지 통과 후 CDN 바이트 재fetch
dev-browser --connect --timeout 150 run {skill_dir}/scripts/sd_download.js
```
presigned URL을 직접 받을 땐 `curl --ssl-no-revoke -A <UA> -e <referer> -o out.pdf <cdnUrl>`.
✅ 검증: Kaçar OLEDoS 16.3 MB (2026-06-09). `download_paper.js`의 일반 same-origin/cdn 경로로는 실패가 정상.

## 다른 스킬/에이전트와의 연동

- **paper-review** 등 참고문헌 PDF 수집이 필요한 스킬은, 봇 차단·기관 구독 논문에 대해
  기존 requests/Sci-Hub 경로 대신 이 스킬의 `dlpaper.sh`/`get_paper.sh`를 호출하면
  **합법적·고성공률** 다운로드가 가능하다. (DOI 리스트 → 각 DOI에 get_paper.sh)
- 에이전트는 SKILL.md의 의사결정 트리를 따라 직접 오케스트레이션하거나, get_paper.sh를
  단일 진입점으로 사용한다. 결과는 항상 stdout JSON + 저장 파일 `%PDF`로 검증할 것.

## 검증 기록 (2026-06-09 ~ 06-10)

| 출판사 | 차단 유형 | 방식 | 결과 |
|--------|-----------|------|------|
| arXiv 1706.03762 | 없음 | direct | ✓ 2.2 MB |
| Optics Express 10.1364/OE.525680 | Radware captcha | direct(헤드드) | ✓ 5.3 MB |
| PNAS 10.1073/pnas.1005828107 | Cloudflare/Atypon | direct | ✓ 1.2 MB (PDF 워터마크에 KIMM IP 기록 → 기관 접근 입증) |
| MDPI 10.3390/cryst15030267 | Cloudflare + 교차출처 CDN | **cdn 폴백** | ✓ 9.0 MB |
| Wiley OA (SID) 10.1002/msid.1378·1522 | Cloudflare | **pdfdirect**(`sid.onlinelibrary`) 헤드드 | ✓ Ha·Eccles (2026-06-09) |
| ScienceDirect 10.1016/j.nxnano.2025.100132 | `cra_js_challenge` | **`--connect` + sd_download.js → presigned CDN** | ✓ Kaçar OLEDoS 16.3 MB (2026-06-09) |
| ACS 10.1021/acs.nanolett.0c03939 | 구독(IP) | **`--connect` 새 프로필** | ✓ Nano Lett (2026-06-10, KIMM IP 구독 — Unpaywall closed이나 접근 가능) |
| Nature 10.1038/s43586-022-00122-w | 구독 **로그인 게이트** | — | 자동 경로(IP 새 프로필) 거부 — 우회 안 함. (이후 사용자가 SSO 로그인 세션으로 수동 입수) |
