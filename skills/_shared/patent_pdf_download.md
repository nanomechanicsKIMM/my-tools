# 특허 원문 PDF 다운로드 표준 절차

특허 스킬 공용 참조 문서. 인용발명·선행특허 원문을 **내용 정합성이 보장된 방식**으로 내려받기 위한 절차를 정리한다.

## 핵심 원칙

1. **번호 체계 구분**: 출원번호(10-YYYY-NNNNNNN)와 공개번호(10-YYYY-NNNNNNN)는 형식이 동일하지만 **전혀 다른 문헌을 가리킨다**. 출원번호를 공개번호 자리에 넣어 다운로드하면 우연히 번호가 같은 무관 문헌이 수신된다(실제 사례: "KR 10-2023-0164912 KIMM 임피던스 메타구조체"로 알고 내려받으면 동일 번호의 "닭꼬치 제조방법"이 수신).
2. **제목 검증 필수**: 다운로드 직후 첫 페이지 제목·출원인을 텍스트 추출하여 기대값과 일치 확인. 불일치 시 폐기하고 재조회.
3. **DOI·특허번호 사전 확인**: `claude.md` 프로젝트 규약에 따라, 번호가 실제 존재하는지 CrossRef / KIPRIS / Google Patents로 **먼저** 검증한 뒤 기재한다.

## 한국 특허 (KIPRIS Plus OpenAPI) — 권장

`$HOME/Claude_work/.env`의 `KIPRIS_REST_AccessKey` 사용.

### 서지정보 조회 (출원번호 기반)

```
GET http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/applicationNumberSearchInfo
     ?applicationNumber=<13자리 출원번호, 하이픈 제거>
     &accessKey=<KIPRIS_REST_AccessKey>
```

응답(XML) `<PatentUtilityInfo>` 노드에서 확인:
- `Applicant`, `InventionName`, `OpeningNumber`(공개번호), `RegistrationNumber`(등록번호), `RegistrationStatus`

### 원문 PDF URL 조회

```
GET http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getPubFullTextInfoSearch   # 공개공보
GET http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAnnFullTextInfoSearch   # 공고/등록공보
     ?applicationNumber=<13자리>
     &ServiceKey=<KIPRIS_REST_AccessKey>   ← 주의: 파라미터명이 ServiceKey
```

응답의 `<path>` 값을 바로 GET하면 PDF 바이너리(`%PDF-` 시작) 수신.
등록된 특허는 `Ann` 우선, 공개 상태면 `Pub`.

### 한계

- KIPRIS는 한국 특허 전용. CN/US/WO/EP는 별도 경로 사용.
- 상용 요금제 외 월 1,000회 제한(학술·개인 용도는 충분).

## 국외 특허 (Google Patents) — 보조

`patents.google.com/patent/<ID>/en` 페이지 HTML에서 `https://patentimages.storage.googleapis.com/...pdf` URL을 정규식으로 추출 후 GET.

### 공식 ID 형식

| 국가 | 형식 | 예시 |
|------|------|------|
| WO (PCT) | `WOYYYYNNNNNNAK` | `WO2020016250A1` |
| US (공개) | `USYYYYMMDDDDAK` | `US20240041429A1` |
| US (등록) | `US<no>BK` | `US8088067B2` |
| CN | `CN<no>AK` | `CN112823283A` |
| KR (공개) | `KRYYYYNNNNNNNA` | `KR20240139518A` |
| KR (등록) | `KR<no>BK` | `KR102889440B1` |

### 봇 차단 주의

Google Patents는 Python/curl 기반 대량 요청을 `HTTP 503`으로 차단한다. 대응:
- 요청 간 3~5초 지연
- `User-Agent`를 최신 Chrome으로, `Referer: https://www.google.com/` 포함
- 실패 지속 시 Claude Code의 WebFetch 도구로 전환(Anthropic 프록시 경유)
- **한국 특허는 Google Patents 대신 KIPRIS 사용**(우회로 불필요, 속도 빠름)

## 학술 논문

`paper-review` 스킬의 `scripts/download_refs.py` 또는 다음 오픈액세스 경로 사용:
- PubMed Central: `https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/pdf/`
- arXiv: `https://arxiv.org/pdf/<id>.pdf`
- PNAS: `https://www.pnas.org/doi/pdf/<doi>`
- Nature: `https://www.nature.com/articles/<slug>.pdf`
- Science/Science Advances: `https://www.science.org/doi/pdf/<doi>`
- Elsevier: `https://www.sciencedirect.com/science/article/pii/<id>/pdfft`

IEEE 논문은 기본 paywall. 대체로 저자의 arXiv 프리프린트, PMC 사본, Semantic Scholar OA 링크, 또는 저자 소속 기관(예: Stanford Radiology) 홈페이지에서 제공.

## 내용 검증 절차

다운로드 후 `pdf-to-md` 스킬로 첫 2페이지를 MD 변환하고 다음을 확인:
1. **공보번호**(`공개특허 10-YYYY-NNNNNNN` 또는 `US20YYYYNNNNNN A1`)가 기대값과 일치
2. **발명의 명칭** 또는 **제목**이 인용 사유와 부합
3. **출원인/저자**가 인용한 권리자와 일치

이미지 스캔 PDF로 텍스트 추출이 안 되는 경우(Google Patents 커버페이지 등) PyMuPDF로 1페이지를 PNG 렌더링 후 시각 확인.

## 재사용 스크립트

`$HOME/.claude/skills/_shared/scripts/download_patent_pdf.py` — KIPRIS + Google Patents 통합 다운로더. CLI 사용법:

```bash
# KR 출원번호 기반 (가장 안전)
PYTHONUTF8=1 python download_patent_pdf.py \
  --kr 1020230164912 1020230191689 \
  --out ./references/

# 국외 특허 (Google Patents ID 직접)
PYTHONUTF8=1 python download_patent_pdf.py \
  --gp WO2020016250A1 US8088067B2 \
  --out ./references/

# 다운로드 후 첫 페이지 자동 검증
PYTHONUTF8=1 python download_patent_pdf.py \
  --kr 1020217003587 \
  --out ./references/ \
  --verify
```

## 실패 대응

| 증상 | 원인 | 조치 |
|------|------|------|
| KIPRIS XML에 `<path>` 비어있음 | 공개 전 상태 또는 등록 전 상태 | 다른 엔드포인트(`Ann`/`Pub`) 시도 |
| Google Patents `HTTP 503` | 봇 차단 | 지연 증가, WebFetch로 전환 |
| PDF 수신되나 내용 이상 | 번호 오인(출원 vs 공개) | KIPRIS 서지로 공개번호 재확인 |
| `HTTP 429` | 쿼터 초과 | KIPRIS는 분당 호출 제한 — 호출 간 1~2초 지연 |
| 한글 깨짐 | Windows 콘솔 인코딩 | `PYTHONUTF8=1` 환경변수 또는 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` |
