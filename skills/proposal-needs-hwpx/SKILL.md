---
name: proposal-needs-hwpx
description: 정부 R&D 기술수요조사서를 근거 기반으로 작성하는 end-to-end 파이프라인 스킬. 사업정보(공고문·양식 hwpx) 파악, 사용자 자료(LLM_wiki vault)·웹·문헌 근거 수집(원문 PDF/HTML 다운로드 저장), 근거 정합성 검증, 초안 MD 작성, 핵심 아이디어 개념도(matplotlib) 생성, hwpx 양식 채움·포맷 맞추기까지 수행한다. '기술수요조사서 작성', '수요조사서 파이프라인', 'KEIT 수요조사', '산업부 수요조사', '수요조사서 hwpx', 'proposal needs', '수요조사서 초안' 등의 요청 시 사용. NRF 미래개척융합 전용 양식은 nrf-tech-survey 사용.
---

# proposal-needs-hwpx — 기술수요조사서 근거 기반 작성 파이프라인

임의 부처·사업의 기술수요조사서(HWPX 양식)를 "근거 수집 → 검증 → 초안 MD → 개념도 → 양식 채움" 순서로 작성한다.
2026-08 첨단나노상용화(KEIT) 수요조사서 2건 작성 세션에서 검증된 절차의 일반화판.

- 적용: 배포된 hwpx 양식을 채워 제출하는 모든 수요조사·사전기획류 문서 (KEIT, 산업부, KIAT 등)
- 제외: NRF 미래개척융합 전용 양식(→ `nrf-tech-survey`), 발명신고서(→ `patent-incubation-*`)
- 의존: `hwpx-xml` 스킬(unpack/pack/validate), lxml, matplotlib, (vault 세션이면) Explore 서브에이전트·qmd

## 산출물 구조 (task 폴더 기준)

```
to-do/<task>/
├── [양식] ... .hwpx / 공고문 .hwpx / 설명자료 .pdf   # 입력 (사용자 제공)
├── (YYYYMMDD) <주제> 수요조사서 초안.md               # Phase 4: 사용자 검토용 초안 (근거 인용 포함)
├── (YYYYMMDD)(기술수요조사서) <주제>_<성명>.hwpx      # Phase 6: 최종 산출물
├── refs/<주제별 폴더>/                                # Phase 3: 근거 원문 (PDF·HTML) + README.md 매핑표
├── figures/fig_<주제>.png                             # Phase 5: 개념도
└── .omc/                                              # 스크래치 (언팩본, 스크립트, content JSON)
```

## Phase 0 — 사업정보 확보

1. **주제 출처 확인**: 사용자 지시에 메일이 언급되면 Gmail MCP(`search_threads` → `get_thread` PLAIN_TEXT)로 원문을 읽고 주제 후보를 추출한다. 주제가 복수면 각각 별도 문서로 진행.
2. **공고문·양식·설명자료 텍스트 추출**:
   - PDF: `pypdf`로 텍스트 추출. 콘솔 인코딩이 한글을 깨뜨리므로 **UTF-8 파일로 덤프 후 Read** (print 직접 확인 금지).
   - HWPX: zipfile로 `Contents/section0.xml`에서 `<hp:t>` 추출. 정규식 `<hp:t[^>]*>([^<]*)</hp:t>`는 **lineBreak 포함 문단을 놓친다**는 점을 인지하고, 전체 확인은 lxml itertext로.
3. **사업 구조 표 작성**: 내역사업 구분, 제안기술 유형(TRL 종료 기준), 3대 분야 등 택1 항목, 예산 단위·연차 규칙(1차년도 개월수), TRL 시작/종료 허용범위, 제출 마감·경로. 이 표가 이후 모든 선택의 기준.

## Phase 1 — 양식 구조 분석 (HWPX)

`hwpx-xml` 스킬 로드 후:

```bash
python <hwpx-xml>/scripts/office/unpack.py "양식.hwpx" .omc/form_unpacked/
```

pretty-print된 section0.xml에서 다음을 **모두 매핑**한다 (grep으로 hp:t 라인번호 스캔 → 필요 구간만 Read):

| 대상 | 식별 방법 | 기록할 것 |
|---|---|---|
| 값 입력 셀 | 라벨 셀(tc)의 같은 tr 다음 tc | 라벨 텍스트 (정규화: 공백 제거) |
| 체크박스 셀 | 빈 run 셀. 라벨 배치와 cellAddr 대조 | (colAddr, rowAddr) + 소속 tbl id |
| placeholder 문단 | `ㅇ `, ` - `, `  * ` 텍스트 | paraPrIDRef (계층 스타일 ID) |
| 예시 문구 | `(예) ...`, `ex. ...` | 전체 문자열 (치환 anchor) |
| 안내 박스 | `<참고 사항 - 작성 시 삭제>` 류 중첩 tbl | **tbl id** (문단 검색으로 지우면 상위 표를 통째 날린다) |
| 견본 체크 잔존 | 체크리스트 문자열 repr 확인 | U+F0FC(Wingdings 체크) 등 비가시 문자 위치 |

⚠️ 실증 함정: 배포 양식에 이미 견본 체크(예: 중소기업(\uf0fc), 서울(\uf0fc))가 박혀 있을 수 있다. **반드시 repr로 확인**하고 지운 뒤 올바른 항목에 체크한다. 체크 문자는 양식이 쓰는 문자를 그대로 재사용.

## Phase 2 — 사용자 자료(핵심 아이디어 근거) 수집

주제당 **Explore 서브에이전트 1개를 병렬 위임** (very thorough). 프롬프트에 반드시 포함:

- 검색 키워드 세트 (국문+영문, 동의어·약어 포함)
- 탐색 대상 폴더: `LLM_work/active|report|archive`, `brain/`, `human/`, `to-do/`, `sample_exchange/`
- 요구 산출: ① **기존 유사 제안서·수요조사서 제출본** (최우선 재활용 소스) ② 정량 성과 수치(출처 파일 경로 포함) ③ 보유기술·특허 ④ 국내외 동향 ⑤ 협력 기업·인물
- "수요조사서(목표/개요/지원 필요성/기대효과/동향/보유기술) 작성에 쓸 수준의 상세"

결과 회수 후 원칙:
- **선행 제출본의 선례를 따른다**: 산업기술분류(예: 세라믹 > 나노, 융복합소재 > 저차원나노소재 800501), 예산 규모, TRL, 공개 수위(정밀 공정 수치는 "약 800도급"처럼 완화).
- 선행 제출본에 `인용문헌 정합성 검증` 노트가 있으면 그 검증 결과를 승계한다.

## Phase 3 — 문헌 확보 (refs/)

문서별 하위 폴더에 근거 원문을 저장한다. **다운로드 우선순위 사다리** (스크립트: `scripts/fetch_refs.py`):

1. **로컬 보유분**: `D:\Zettelkasten\References`를 저자·키워드로 grep → 작업용 사본을 refs/로 복사 (원본 이동 금지).
2. **직접 다운로드** (`truststore.inject_into_ssl()` + urllib + 브라우저 UA): arXiv, Europe PMC(`europepmc.org/articles/PMC...?pdf=render`, 429 시 30초 대기 재시도), patentimages(구글 특허 페이지 HTML에서 PDF 링크 추출), 뉴스·기업 페이지 HTML.
3. **퍼블리셔 403** (AIP, OUP, Elsevier, science.org, WebFetch도 403): 서지 API로 **초록 HTML 생성** — Semantic Scholar(`/graph/v1/paper/DOI:...`) → 429 시 OpenAlex(`/works/doi:...`, abstract_inverted_index 복원). openAccessPdf 링크가 있으면 PDF도 시도.
4. **끝내 미확보**: refs/README.md의 미확보 목록에 기재 (KIMM 구내망 브라우저 + `paper-pdf-download`로 사용자가 수령 가능).

`refs/README.md` (frontmatter + `LLM_work` 태그) 필수 구성:
- 파일 ↔ 본문 주장 매핑표 + 검증 상태(✅ 정합 / 🔁 정정 / ⚠️ 본문 수치는 원문 열람 필요)
- 내부 근거(vault 정본) 목록: 다운로드 대상이 아닌 자체 실험·과제 데이터의 출처 노트 경로
- 미확보 목록과 사유

대용량 PDF는 **커밋 제외** (README·HTML·개념도만 커밋).

## Phase 4 — 정합성 검증 + 초안 MD 작성

**검증 규칙** (세션 실증 사례):
- 시장 수치는 반드시 최신 전망으로 웹 재검증한다. 오래된 CAGR(예: 2023년 전망)은 폐기하고 최신 기관 전망으로 교체.
- 기업·정책 뉴스는 **상태 변화**를 확인한다 (예: "투자 진행 중" → 실제로는 이미 준공).
- 재확인 불가한 수치는 **완화하거나 삭제** (예: "누적 4,000개" → "수직통합 파운드리 운영").
- 자체 성과 수치는 vault 정본 노트와 대조하고, 공개 문서라면 공개 수위를 선행 제출본에 맞춘다.

**초안 MD** `(YYYYMMDD) <주제> 수요조사서 초안.md`: hwpx에 들어갈 **모든 내용**을 양식 항목 순서로 담고, 정량 주장마다 근거를 `[refs/...]` 또는 `[vault: ...]`로 병기한다. 구성:

1. 사업·마감 요약, 선택 주제와 출처(메일 등)
2. 제안자 정보 (휴대전화 등 모르는 값은 **빈칸 + 사용자 확인 표기**)
3. 제안 기술명(정량 지표 포함 한 줄), 최종 산출물, 산업기술분류, 유형/내역/분야 선택 + **선택 이유**
4. 적용 대상 한 줄 (적용 대상 → 필요사항 → 개발기술 순)
5. 개발기간·연차 예산·TRL
6. 기술개발 목표 / 개요 / 주요내용 / 지원 필요성 / 기대효과 (ㅇ/-/* 계층 그대로)
7. 국내외 동향, 보유기술, 공통기술·지원 필요사항
8. 개념도 기획: 비유 한 줄, 구성 요소, 강조 수치
9. **사용자 확인 필요 항목** 목록 (분야 매핑, 예산, 분류 등 판단이 갈리는 결정)

문체: em-dash(—)와 가운데점(·) 미사용, 짧은 명사형 종결. 초안 MD 단계에서 사용자 검토를 받을 수 있으면 받고, 자율 세션이면 그대로 진행하되 확인 필요 항목을 최종 보고에 포함한다.

## Phase 5 — 핵심 아이디어 개념도 (문서당 1장)

matplotlib(폰트 `Malgun Gothic`, 없으면 Noto Sans KR)로 **일반인 눈높이** 개념도를 그린다. figsize 13.4x6.6, dpi 150, `figures/fig_<주제>.png`.

디자인 원칙 (세션 검증):
- **비유 한 줄**을 부제로 (예: "포스트잇처럼 떼어내는 반도체 박막", "신문 인쇄하듯 롤로 뽑는 그래핀")
- 번호 스텝(①②③) 좌→우 흐름 + 순환 구조(재사용 등)는 되돌아가는 화살표로
- 강조 수치 박스 1~2개 (핵심 목표: "재사용 5회 이상 → 원가 1/10")
- 미래지향 요소(파일롯 스케일, AI/디지털 트윈, 친환경 순환)를 명시적 구성요소로
- 팔레트: 네이비 #1B3A6B, 틸 #0E8C7F, 오렌지 #E8762C, 경고 적 #C6403D, 배경 #EEF2F8

**겹침 검사 루프 필수**: 저장 후 Read로 이미지를 직접 보고, 화살표·점선이 라벨을 관통하면 좌표를 수정해 재생성한다 (보통 1~2회 반복).

## Phase 6 — HWPX 채움 및 포맷

`scripts/fill_survey_template.py`(검증 구현)를 해당 양식에 맞게 수정해 사용한다. content JSON(초안 MD에서 전환) → 채움 → pack → 검증.

**핵심 규칙** (vault [[HWPX 수정 패턴]] + [[(20260416) hwpx format_변환_insights]] §4 준수):

1. **계층 bullet 문단(음수 intent paraPr)은 linesegarray 명시 필수.** 제거하면 한글이 재계산하지 않아 **모든 줄이 같은 좌표에 겹쳐 그려진다** (세션 실증). 생성 규칙:
   - 줄 수 추정: 가중 길이(한글 1.0, ASCII 0.55, 기타 0.6) ÷ (horzsize / textheight)
   - textpos 균등 분할, vertpos는 셀 안에서 문단 간 누적, step = vertsize + spacing
   - flags: 첫 줄 393216, 연속 줄 1441792. **2490368 금지**
   - horzsize = cellSz.width - cellMargin(left+right)
2. **긴 텍스트 치환도 lineseg 재생성** (짧은 치환은 방치 가능).
3. **셀 높이 자동 확장**: 내용 높이 > cellSz.height면 같은 tr의 rowSpan=1 셀들과 tbl sz height를 함께 키운다.
4. **안내 박스 제거는 중첩 tbl id로 타겟**: "참고 사항 포함 문단 검색 삭제"는 상위 표 전체를 날린다 (실증 사고).
5. **체크박스는 cellAddr 좌표로 기입**하고, 완료 후 좌표를 역검증한다 (텍스트 덤프는 빈 셀이 안 보여 위치 구분 불가).
6. **그림 삽입**: PNG를 `BinData/imageN.png`로 복사, `Contents/content.hpf` manifest에 `<opf:item id="imageN" ... isEmbeded="1"/>` 등록, 대상 셀에 hp:pic 문단 추가. 치수: orgSz = px×30, imgDim = px×75, 표시폭 = cell_horzsize-200, scaMatrix = 표시/orgSz. 삽입 위치 기본값은 "기술개발 개요" 셀 하단.
7. pack은 hwpx-xml `pack.py`(mimetype first, ZIP_STORED) 사용.

**검증 스택** (모두 수행):
- `validate.py` 구조 검증
- 텍스트 덤프로 전 항목 반영 확인 (예시·안내문 잔존 여부 포함)
- 체크박스 cellAddr 역검증
- lineseg 정합: 전 문단 `max(textpos) < len(text)` (초과 시 한글이 파일 거부), 금지 flag 부재. 원본 양식 유래 경고는 원본과 개수 비교로 무해 판정
- (선택) 한글 COM 무인 열기: 보안모듈 대화상자로 **hang 가능** — 반드시 타임아웃 + 잔류 Hwp.exe 정리

## 마무리

- 최종 hwpx와 개념도를 SendUserFile로 전송 (hwpx는 attach, 그림은 render)
- to-do 세션 커밋 규칙: 자기 작업분 pathspec 커밋 (`git add -A` 금지), 대용량 PDF 제외, push는 루트 wrap-up
- 최종 보고에 반드시 포함: 정정·완화 이력, 사용자 확인 필요 항목, 미확보 문헌, 한글에서의 최종 육안 확인 요청

## Gotchas 요약 (세션 실증)

| 증상 | 원인 | 대응 |
|---|---|---|
| 셀 안 글자 전부 겹침 | 계층 bullet 문단 linesegarray 제거 | 명시적 lineseg 재생성 (규칙 1) |
| 값 셀·체크가 통째로 사라짐 | 안내 박스 제거가 상위 표 문단을 삭제 | 중첩 tbl id로 타겟 (규칙 4) |
| 엉뚱한 항목에 체크된 채 제출 위험 | 양식에 견본 체크(U+F0FC) 잔존 | 체크 문자열 repr 확인 후 정리 |
| 콘솔 한글 전부 깨짐 | Windows 콘솔 cp949 | UTF-8 파일 덤프 후 Read, `python -X utf8` |
| 퍼블리셔 다운로드 403 | 스크립트 차단 (WebFetch 포함) | 서지 API 초록 → OA 미러(EPMC, arXiv) 사다리 |
| 시장 수치 구식 인용 | 과거 vault 노트 재활용 | 웹 재검증 후 최신 전망으로 교체 |
| COM 검증 무한 대기 | 한글 보안모듈 승인 대화상자 | 타임아웃 + taskkill, 구조 검증으로 대체 |
