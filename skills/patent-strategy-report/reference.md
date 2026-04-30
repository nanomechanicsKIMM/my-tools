# Patent Strategy Report Skill – Reference

## Google Patents query syntax

- **Boolean**: `AND`, `OR`, `NOT` (uppercase). Group with parentheses: `(A OR B) AND C NOT D`.
- **Phrases**: double quotes, e.g. `"light emitting"`, `"rigid substrate"`.
- **Wildcard**: `*` for suffix only, e.g. `stretch*` → stretch, stretchable, stretching.
- **Date filters** (query params, not in search box):
  - `after=priority:YYYYMMDD` – priority date on or after.
  - `before=priority:YYYYMMDD` – priority date on or before.
  - Full URL form: `https://patents.google.com/?q=QUERY&after=priority:20160101&before=priority:20251231`.
- **Encoding**: When building URL, encode the `q` value (e.g. spaces → `+`, quotes → `%22`).

Example query string (for search box):
```
(stretchable OR deformable OR "shape-variable") AND (display OR panel) AND (sensor OR sensing) NOT ("rigid substrate")
```

### 초기 검색식 알고리즘 (검색 건수 5000건 이하 목표)

- **목표**: 초기 검색식만으로 10만 건 이상이 나오지 않도록, **AND로 표현되는 필수 개념**을 사용해 검색 건수를 5000건 이하 수준으로 줄인다.
- **동작** (`generate_query.py`, 기본값 `use_and_groups=True`):
  - RFP·기술분류에서 **필수 개념 그룹**을 추출한다. 예: (1) 디스플레이 관련어 (display, panel, flexible, stretchable, …), (2) 센서/변형 관련어 (sensor, sensing, deformation, transformable, …).
  - 검색식을 **`(그룹1 OR …) AND (그룹2 OR …)`** 형태로 만든다. 각 그룹에서 최소 1개 이상 히트해야 하므로 결과 건수가 크게 줄어든다.
  - 그룹은 RFP 본문·RFP명·영문 키워드와 기술분류(도메인)로 판단한다. 영문 키워드는 그룹2에 없는 것만 그룹1에 보강해, 그룹1이 지나치게 넓어지지 않게 한다.
- **기존 동작(단일 OR 블록)** 이 필요하면: `--no-and-groups` 옵션을 사용한다. 이 경우 10만 건 이상이 나올 수 있다.
- **용어 수**: 그룹당 최대 `MAX_TERMS_PER_GROUP`(기본 10)개로 제한해 URL 길이를 관리한다.

### 사용자 제공 핵심 키워드(필수 단어)

- 검색 결과가 여전히 많을 때, 사용자에게 **핵심 키워드**를 받아 필수 AND 블록으로 추가한다.
- **방법 1**: `--required-terms "term1,term2,term3"` (또는 `-r`) — 쉼표 구분 문자열로 전달.
- **방법 2**: `--ask-required` — 실행 시 `핵심 키워드(필수 단어, 쉼표 구분):` 프롬프트를 띄우고 stdin에서 입력받음.
- 생성 검색식: `(term1 OR term2 OR term3) AND (기존 개념 그룹들...)` 형태로, 사용자 필수 블록이 맨 앞에 AND로 붙는다.

### 필수 제외 단어 (빼야 할 단어)

- **방법 1**: `--exclude-terms "phrase1,phrase2,word"` (또는 `-e`) — 쉼표 구분으로 제외할 단어/구문 전달. 검색식에 `NOT ("phrase1" OR "phrase2" OR "word")` 형태로 붙는다.
- **방법 2**: `--ask-exclude` — 실행 시 `빼야 할 단어(제외 단어, 쉼표 구분):` 프롬프트로 stdin에서 입력받음.
- 예: 디스플레이·센서 RFP에서 `--exclude-terms "rigid substrate,drug"` 로 노이즈 구문을 제외할 수 있다.
- **도메인별 권장**: 특정 기술을 RFP 범위에서 제외할 때(예: 디스플레이 RFP에서 OLED·LCD 제외) 검색식 생성 시 `--exclude-terms "OLED,LCD"` 를 사용하면, 수집 단계부터 NOT이 적용된 URL이 생성된다. 이후 연관성 필터·핵심 특허 선정에서도 동일 키워드로 제목/초록 필터를 적용하는 것이 정합성에 유리하다(아래 "제외 키워드(연관성 필터·핵심 특허)" 참고).

### 제외 키워드(연관성 필터·핵심 특허)

RFP 범위에서 **특정 키워드(예: OLED, LCD)를 제외**하고 싶을 때, 다음 세 단계에서 일관되게 적용할 수 있다.

1. **검색식** (`generate_query.py`): `--exclude-terms "OLED,LCD"` → 쿼리에 `NOT ("OLED" OR "LCD")` 추가. 사용자가 해당 URL로 다운로드한 CSV에는 원천적으로 해당 용어가 제목에 적은 건만 포함될 수 있다.
2. **제목 연관성 필터** (`filter_title_top_n.py`): `--exclude-terms "OLED,LCD"` — **제목**에 해당 단어(대소문자 무관)가 포함된 행은 **점수 계산 전에 제거**한 뒤, 남은 행만으로 TF-IDF 점수를 매겨 상위 N건을 출력. 수집 CSV에 제외 대상이 섞여 들어온 경우를 보정한다.
3. **핵심 특허 선정**(예: 상위 10건): 초록–RFP 점수순으로 정렬한 CSV에서, **제목 또는 초록**에 제외 키워드가 포함된 행을 제거한 뒤 상위 N건을 핵심 특허로 저장. (파이프라인 스크립트에서 `EXCLUDE_CORE = ["OLED", "LCD"]` 등으로 설정 후 필터 적용.)

동일한 제외 키워드 목록을 검색식·제목 필터·핵심 특허 선정에 공통으로 두면, 보고서와 목록 간 정합성이 유지된다.

### 기술 분야별 용어 (Technology domain vocabulary)

- **용도**: 사용자가 기술 대분류를 제시한 경우, 검색식 확장 시 해당 분야의 표준 용어·동의어를 참고한다. **특정 분야에 한정되지 않도록** 필요 시 아래 표에 다른 분야를 추가하여 사용한다.
- **예시** (다양한 연구 분야 확장 가능):

| Domain (한글) | English / synonyms (for query) |
|---------------|----------------------------------|
| 디스플레이 | display, panel, screen, OLED, LED, flexible, stretchable, foldable, rollable, backplane, TFT |
| 반도체 | semiconductor, wafer, transistor, CMOS, process, lithography |
| 배터리 | battery, cell, electrode, electrolyte, lithium, solid-state |
| 센서 | sensor, sensing, strain, deformation, touch, embedded |
| 바이오/의료 | drug, therapeutic, biomarker, diagnostic, clinical trial |
| 인공지능/소프트웨어 | machine learning, neural network, algorithm, model, training |

- Exclusions: 분야별로 off-topic 구문이 있으면 `NOT (...)` 에 추가 (예: 디스플레이에서 "rigid substrate"). RFP와 무관한 일반 용어는 검색식에 넣지 않는다.

## 국가별 집계(보고서용)

보고서 §4 국가별 분포는 **한글 명칭 통일** 및 **유럽 국가 통합**을 적용한다.

- **함수**: `aggregate_csv_report.aggregate_countries_for_report(rows)` — 원시 국가 코드별 건수 집계 후, 유럽 국가 코드(EP, ES, DE, GB, FR, NL, DK, BE)를 하나의 **"유럽"** 항목으로 합산하고, 각 항목에 **한글 명칭(name_ko)** 를 부여한다 (미국, 중국, 일본, 한국, 대만, 호주, PCT, 러시아, 캐나다, 브라질, 유럽 등).
- **보고서 표·차트**: `fill_report.table_country()` 는 `name_ko` 가 있으면 한글만 표시; ASCII 차트도 `(name_ko, pct)` 로 생성하면 한글로 표기된다.
- **파이프라인**: 집계 후 보고서를 채울 때 `aggregate_countries_for_report()` 를 사용하고, `ascii_countries` 에 `(c.get("name_ko", c["code"]), c["pct"])` 를 넘기면 된다.

### v1 → v2 노이즈 필터 파이프라인 (연관성 점수 기반)

- **목표**: v1 CSV에서 제목–RFP 연관성으로 상위 5000건 추린 뒤, 초록을 추가하고 초록–RFP 연관성으로 상위 2500건을 점수순 정렬해 v2로 저장.
- **Step 1** (`filter_title_top_n.py`): v1에서 **title**과 RFP의 TF-IDF 코사인 유사도로 점수화 → 상위 5000건 CSV 저장 (기본 `--top 5000`).
- **Step 2** (`fetch_abstracts.py`): 위 CSV의 result link로 크롤링해 **abstract** 컬럼 추가. `--resume`으로 재개 가능.
- **Step 3** (`filter_abstract_top_n.py`): **abstract**과 RFP의 TF-IDF 코사인으로 점수화 → 상위 2500건을 **점수 내림차순**으로 정렬해 **v2.csv** 저장 (기본 `--top 2500`).
- **일괄 실행**: `run_relevance_pipeline.py <v1_csv> <rfp_path> -o output` (상관성 점수: 제목 10k → 상위 100 초록 → 초록 점수 → 핵심 10건). 상세는 `output/실행가이드_상관성_파이프라인.md` 참고.
- **(구) v1→v2**: `run_v1_to_v2_pipeline.py` 및 `filter_title_top_n.py`/`filter_abstract_top_n.py`는 레거시. 현재 기본은 포함/제외 가중치를 쓰는 `score_title_relevance.py`·`score_abstract_relevance.py`이다.

## Noise criteria and LLM prompt

> **전략 요약·의견 요청**: 경로 A(노이즈 필터 루프)와 경로 B(연관성 상위 N건+제외 키워드)를 정리한 문서는 [output/노이즈_필터링_전략_요약.md](output/노이즈_필터링_전략_요약.md) 에 있습니다. 기준·파라미터 수정 의견이 있으면 해당 문서를 참고해 요청해 주세요.

**Noise**: A patent is noise if its title and abstract are not relevant to the RFP’s technical goals (e.g. different application field, different technology, or only tangentially related).

**Judgment**:
- Preferred: LLM with (patent title + abstract) and (RFP summary or key objectives). Output: relevant Y/N or 0–1 score; threshold e.g. 0.5.
- Alternative: Keyword overlap score (RFP keywords present in title/abstract) then LLM for borderline cases.

**Prompt example (for LLM)**:
```
RFP summary: [paste 2–3 sentences from RFP describing the technology goal]

Patent title: [title]
Abstract: [abstract]

Is this patent relevant to the RFP’s technology area? Answer YES or NO. Brief reason in one line.
```

**Stopping condition**: In each round, compute `removed_count / total_count`. If this ratio ≤ 10%, stop and proceed to aggregation/report. Otherwise the script **derives an improved search query** from the noise:

- **NOT terms**: Frequent words in the **removed** (noise) rows that are relatively rare in the **kept** rows (and not already in the RFP or current query) are suggested as NOT candidates.
- **IMPROVED_QUERY_SUGGESTION**: `current_query + " NOT (term1 OR term2 OR ...)"`.
- The user opens the improved search URL in a browser, downloads a new CSV, and runs the filter (or full pipeline) again. This loop is repeated until REMOVAL_RATIO ≤ 10%.

When running the pipeline (`run_full_pipeline.py`), pass `--search-query` and `--search-url` so that when REMOVAL_RATIO > 10% the script can output IMPROVED_QUERY_SUGGESTION and IMPROVED_SEARCH_URL and stop before aggregation; the user then re-downloads and re-runs with the new query/URL.

## 노이즈·NOT 개선 워크플로우 (초록 기반)

CSV에 특허 초록이 없을 때, **초록 크롤링 → RFP와 상관성 점수 → 노이즈에서 NOT 키워드 추출** 순서로 NOT 선택 품질을 높일 수 있다.

### 1단계: 특허 초록 크롤링 (`fetch_abstracts.py`)

- **입력**: Google Patents CSV (`result link` 컬럼 필수).
- **동작**: 각 행의 result link를 GET하여 HTML에서 초록(abstract) 추출 후 `abstract` 컬럼 추가.
- **옵션**: `--limit N`(처리 건수 제한), `--delay 1.5`(요청 간격), `--resume abstracts.json`(이미 수집한 id→abstract로 재개).
- **출력**: `abstract` 컬럼이 추가된 CSV.

### 2단계: 초록–RFP 상관성 점수 및 노이즈 분류 (`score_relevance.py`)

- **입력**: 초록이 추가된 CSV, RFP 마크다운 경로.
- **동작**: TF-IDF 벡터화 후 각 특허 초록과 RFP 본문의 **코사인 유사도** 계산. 점수가 **threshold 미만**인 행을 노이즈로 분류.
- **옵션**: `--threshold 0.12`(기본), `--no-abstract-use-title`(초록 없을 때 제목 사용).
- **출력**: `relevance_score`, `is_noise` 컬럼이 추가된 CSV.

### 3단계: 노이즈에서 NOT 키워드 추출 (`extract_not_from_noise.py`)

- **입력**: 2단계 출력 CSV, RFP 경로, 현재 검색식·검색 URL.
- **동작**: `is_noise == true`인 행의 초록(또는 제목)에서 단어 빈도 산출. 유지(keep) 행 대비 **노이즈에서 상대적으로 많이 나온 단어**만 후보로 선택. RFP·현재 쿼리에 포함된 단어 및 일반 특허 용어(stopword)는 제외.
- **출력**: `SUGGESTED_NOT_TERMS`, `IMPROVED_QUERY_SUGGESTION`, `IMPROVED_SEARCH_URL`.

### 한 번에 실행 (`run_noise_pipeline_with_abstracts.py`)

```bash
python run_noise_pipeline_with_abstracts.py <input_csv> <rfp_path> --current-query "..." --search-url "..." [-o output_dir] [--fetch-limit 100] [--skip-fetch]
```

- `--skip-fetch`: 이미 `abstract` 컬럼이 있는 CSV를 쓸 때 1단계 생략.
- `--fetch-limit 100`: 테스트 시 100건만 크롤링.

## Report section template (summary)

1. **YAML**: `title`, `date`, `tags`, `aliases`.
2. **Opening block**: 분석 기준일, 데이터 출처, 검색 쿼리, 분석 대상 기간, 총 특허 건수.
3. **§1 개요**: One paragraph; data source and purpose.
4. **§2 연도별 출원 추이**: 2.1 우선일 기준 표 + ASCII bar chart; 2.2 공개일 기준 표; 2.3 해석 (공개 지연, 성장기/성숙기).
5. **§3 주요 출원인**: 3.1 통합 출원인 Top 10 표; 3.2 국적별 점유율 (ASCII bar); **3.3 전략 특성** — **표(table) 형태만** 사용. 컬럼: 출원인 | 강점·주요 포트폴리오 | RFP 연관성 | 차별화·선행 회피 포인트. 상위 10개 출원인당 한 행, 표 하단에 요약 1문단. (불릿 목록·장문 서술은 사용하지 않음.)
6. **§4 국가별 분포**: 4.1 국가별 건수 표; ASCII bar; 4.2 국가별 전략 분석.
7. **§5 종합 전략 시사점**: 기술 단계, 경쟁 구도, R&D 기획 시사점.
8. **§6 참고 데이터**: 검색 URL, 관련 RFP, 관련 문서 링크.
9. **Footer**: "본 보고서는 … 에 의해 자동 분석·작성되었습니다."

## Report file naming

- Pattern: `{YYYYMMDD}_{topic}_세계특허현황_분석보고서.md`
- Topic: short slug from RFP title (any research/technology field).
- Example: `20260306_센서융합디스플레이_세계특허현황_분석보고서.md` (display example; replace with RFP-specific slug).

## 품질 검토 및 수정보완 (Skill 실행 후)

- **보고서 검토**: 생성된 보고서를 샘플과 비교하여 섹션 순서, 표 형식, ASCII 차트, 누락된 항목이 없는지 확인.
- **수치 검증**: 연도별 건수 합계 = 총 건수, 출원인/국가 비중 합계 = 100% 근처인지 확인.
- **노이즈 판단**: 제거율이 반복 후에도 10% 초과이면 검색식 NOT 조건 추가; 제거가 과도하면 threshold 완화 또는 LLM 판단 기준 완화.

## CSV: 사용자 제공

- **기본 방식**: CSV는 **사용자가 Google Patents에서 검색 후 직접 다운로드**하여 경로를 제공한다. 스킬은 이 CSV 경로를 입력으로 받아 필터·집계·보고서 생성에 사용한다.
- **다운로드 방법**: Step 1에서 생성한 검색 URL을 브라우저에서 연 뒤, 결과 페이지 상단의 **Download (CSV)** 버튼을 클릭해 저장. (최대 1,000건 등 제한은 Google Patents 정책에 따름.)
- 특정 기술에 한정하지 않으며, 어떤 연구 분야의 RFP·검색 결과 CSV도 동일한 워크플로로 처리할 수 있다.

## Playwright 자동 다운로드 (보류)

- **상태**: Playwright를 이용한 CSV 자동 다운로드는 **보류**. 현재 워크플로에서는 사용자가 CSV를 제공하는 방식만 사용한다.
- **참고용**: `scripts/google_patents_download.py`는 실험용으로 남겨 두었을 수 있으나, UI 변경 등으로 동작하지 않을 수 있음. 필요 시 선택자 등은 직접 확인하여 수정한다.
- **의존성**: 메인 워크플로에는 Playwright가 필요하지 않다. pandas만 있으면 집계·보고서 생성이 가능하다.

## CSV columns (typical Google Patents export)

Expect columns such as: title, publication number, priority date, publication date, assignee(s), country/office. Column names may be in English. Use "priority date" and "publication date" for 연도별; "assignee" or "applicant" for 출원인; country code (e.g. US, CN, KR) for 국가별. Normalize date formats (YYYY-MM-DD or similar) and extract year for aggregation.

---

## 출원인 집계 (Assignee normalization)

집계 시 **출원인(applicant/assignee)** 은 아래 규칙으로 정규화하여 **영어 통일명**으로 합산하고, **보고서 표시 시에는 compact** 형태로 쓴다.

### 법인 접미사 처리

- **Ltd.**, **Inc.**, **Llc**, **Co., Ltd.** 등은 **단독 토큰으로 세지 않는다**. 셀을 `,`, `;`, `|` 로 나눈 뒤, 접미사만 있는 토큰은 **이전 토큰에 붙여** 하나의 출원인으로 인식한다 (`_parse_assignee_cell`, `LEGAL_SUFFIXES`).
- 예: `"Samsung Electronics Co., Ltd."` → `Samsung Electronics Co., Ltd.` (한 덩어리), `"Apple Inc."` → `Apple Inc.` (한 덩어리).

### Compact 표시명 (보고서용)

- **규칙**: 보고서·표·ASCII 차트에는 출원인명을 **compact**로 표기한다. LLC, Inc., Ltd., Co., Ltd., Gmbh, Corporation, Corp. 등 일반적 법인 접미사를 **삭제**한다.
- **구현**: `aggregate_csv_report.compact_applicant_display(name)` — 끝부분 접미사 제거; 중간의 "Gmbh"(예: Cilag Gmbh International)도 제거. `_canonical_assignee_english()` 반환값에 이 함수를 적용하므로, 집계 결과(JSON·표·ASCII)에 이미 compact 명이 나온다.
- **예**: Apple Inc. → Apple, Intel Corporation → Intel, Google LLC → Google, Semiconductor Energy Laboratory Co., Ltd. → Semiconductor Energy Laboratory, Microsoft Technology Licensing, LLC → Microsoft Technology Licensing, Cilag Gmbh International → Cilag International.

### 영어 통일명 및 동일 회사 합산

- 한글·중국어·일본어 표기와 영문 변형을 **하나의 영어 통일명**으로 매핑하고, **동일 회사**로 건수를 합산한다.
- **CANONICAL_APPLICANT_EN** 및 **\_canonical_assignee_english()**: 삼성 디스플레이/전자, Apple, BOE, Semiconductor Energy Laboratory, Daiichi Shoji, Huawei, LG 등. LG/BOE는 대소문자 통일, 苹果公司·三星电子·Semiconductor Energy Laboratory 접두사 등 변형을 하나로 통합.
- **확장**: 새 회사/그룹을 통일하려면 `aggregate_csv_report.py` 내 `CANONICAL_APPLICANT_EN` 딕셔너리와 `_canonical_assignee_english()` 로직에 항목을 추가한다.

### 보고서 서술

- 보고서 §3.1에서는 “출원인은 영어 통일명으로 통합하였으며, 동일 회사(한·중·일·영문 변형)는 합산하였다”는 문구를 넣어 독자가 이해할 수 있게 한다. **§3.3**에서는 주요 출원인 전략을 **표(table)** 로만 제시하고, 불릿 목록 등 중복 서술을 하지 않는다. 출원인명은 compact 표시명을 사용한다.

---

## 기술 단계 해석 (도입기·성장기·성숙기)

연도별 추이 해석 시 **기술 수명주기**를 RFP·도메인에 맞게 판단한다.

- **도입기**: 출원이 서서히 증가하거나 최근까지 유지. **최근년도 감소**가 있으면 **공개 지연(18개월 등)·표본 한계** 때문인지 먼저 고려하고, “성숙기”로 단정하지 않는다.
- **성장기**: 연도별 건수가 뚜렷이 증가.
- **성숙기**: 피크 이후 감소가 기술 쇠퇴·대체 기술로 해석 가능한 경우.

**주의**: 우선일 기준 최근 2~3년 감소만으로 “기술 성숙”이라고 쓰지 말고, 해당 기술이 실제로 **도입기**라면 보고서에 “도입기”로 명시하고, 최근 감소는 “공개 지연 및 표본 한계에 따른 것으로 해석할 수 있다” 등으로 서술한다.

---

## RFP → Search query generation (Step 1 spec)

### Inputs

- RFP markdown file path (required).
- Optional: technology_domain (e.g. "디스플레이", "반도체", "배터리") for synonym expansion.

### Extraction from RFP (in order)

1. **사업명** – Look for "사업명" or "**사업명**" followed by text on same or next line.
2. **RFP명** – Look for "RFP명" or "**RFP명**" (often the main technical scope sentence).
3. **키워드** – "키워드" / "한글:" / "영문:" lists; use both for query (prefer English terms for Google Patents).
4. **추진배경 / 과제목표** – Section "1. 추진배경", "2. 과제목표"; extract noun phrases and technical terms (e.g. "형태 가변", "센서 융합", "변형 인식", "백플레인").
5. **성과지표** – From "3. 성과지표" or "연구개발내용": extract domain-relevant terms that can narrow the search (do not assume a specific field; use whatever the RFP contains).

### Query construction rules

- **Core block**: Build `(term1 OR term2 OR ...) AND (term3 OR ...)` from RFP명 + 키워드(영문) + 추진배경/과제목표 derived terms (transliterate or use existing English).
- **Domain expansion**: If technology_domain given, add synonyms from the "Technology domain vocabulary" table (OR with existing terms).
- **Exclusions**: Add `NOT ("obvious exclusion")` for known off-topic phrases in the relevant domain. Optionally derive from first-round noise later.
- **Date range**: Default **10 years**: `after=priority:(YYYY-10)0101`, `before=priority:YYYY1231`. 사용자가 `--years N`을 지정하면 그 값이 우선(예: `--years 12` → 12년, `--years 15` → 15년).
- **보고서 분석 기간**: 집계 스크립트는 **CSV에 포함된 모든 행**을 사용하며, 연도별 표는 CSV 내 우선일/공개일 기준 **실제 존재하는 연도 전부**를 반영한다. 따라서 **검색 시 입력한 기간**(URL의 after/before)과 동일한 기간이 보고서에 나오려면, 검색식 생성 시 원하는 `--years`(기본 10년, 사용자 지정 우선)로 URL을 만들고, 그 URL로 다운로드한 CSV를 사용해야 한다.
- **Final string**: Single line, no extra newlines; use double quotes for phrases; parentheses for grouping.

### Output

- `query_string`: the text to paste in Google Patents search box (or use in URL as `q=` value).
- `search_url`: `https://patents.google.com/?q=` + urlencoded(query_string) + `&after=priority:YYYYMMDD&before=priority:YYYYMMDD`.

### Example (일반적인 RFP)

- RFP에 키워드(영문)와 목표 기술이 있으면, 그에 맞춰 OR/AND/NOT 조합을 만든다. 예: 키워드가 Display, Sensor, Deformation 이고 목표가 "형태 가변·센서 융합"이면, `(display OR panel) AND (sensor OR sensing OR deformation) NOT ("rigid substrate")` 등. 날짜는 RFP 지원기간 또는 `--years` 인자로 설정 (기본 10년, `--years 12`·`--years 15` 등 사용자 지정 우선).
