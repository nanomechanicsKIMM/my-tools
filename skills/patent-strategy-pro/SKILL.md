---
name: patent-strategy-pro
description: Advanced patent strategy report with sub-technology decomposition, gap analysis, Objective-Solution matrix, and IP creation strategy. Supports PDF or MD RFP input. Generates Obsidian-format report. Use when user asks for 특허 전략 보고서, 세부 기술 분석, 공백 기술, OS 매트릭스, IP 창출 전략, 특허 분석 보고서, patent strategy.
---

# Patent Strategy Pro Skill

PDF 또는 MD 형식의 RFP를 입력받아 세부 기술별 특허 분석, 공백 기술 분석, Objective-Solution Matrix, IP 창출 전략을 포함한 종합 특허 전략 보고서(Obsidian MD)를 생성한다. **기술 분야에 무관하게** 반도체, 배터리, 바이오, AI, 통신, 로봇, 소재 등 어떤 RFP에도 적용 가능하다.

## When to Use

- 사용자가 RFP(PDF 또는 MD)와 Google Patents CSV를 제공하고 특허 전략 보고서를 요청할 때
- 기존 `/patent-strategy-report` 보다 심층 분석이 필요한 경우: 세부 기술별 특허 분석, 공백 기술, OS 매트릭스, IP 창출 전략 포함
- "특허 전략 보고서", "세부 기술 분석", "공백 기술", "OS 매트릭스", "IP 창출 전략", "RFP 특허 검색", "Google Patents 분석" 언급 시

## Inputs

1. **RFP 파일** (필수): PDF 또는 MD 형식. PDF이면 자동으로 MD 변환 진행.
2. **메인 CSV** (필수): RFP 전체 범위 Google Patents 검색 결과 (사용자 직접 다운로드)
3. **세부 기술별 CSV** (필수): 세부 기술 도출 후 각 세부 기술별 검색 결과 CSV (사용자 직접 다운로드, 3~5개)
4. **옵션**: `--include-terms`, `--exclude-terms`, `--years` (기본 10년)

## Workflow (9단계)

### Phase 1: RFP 전처리

**Step 1 — RFP 변환 (PDF 입력 시)**
- `pdf_to_md.py <rfp.pdf> -o <rfp.md>` 실행
- pdfplumber 기반 구조 보존 변환 (제목, 표, 목록, 한글 텍스트)
- 출력: YAML 프론트매터 포함 Obsidian MD 파일

**Step 2-A — 세부 기술 자동 추출 (스크립트)**
- `extract_sub_technologies.py <rfp.md> -o sub_techs.json [--domain-dict domain.json]` 실행
- RFP의 과제목표·연구개발내용·성과지표에서 3~5개 세부 기술 추출
- 내장 도메인 사전(14개 분야 190+개 매핑) + 선택적 외부 사전(`--domain-dict`)
- 출력: JSON (name_ko, name_en, description, key_terms, exclude_terms, quality_warnings 포함)

**Step 2-B — Claude RFP 분석 보정 (필수)**

스크립트 자동 추출은 **초안**일 뿐이다. Claude는 반드시 다음 보정을 수행한다:

1. **RFP 원문 독해**: 과제목표·단계별 목표·연구개발내용·성과지표를 직접 분석
2. **스크립트 결과 대조**: 자동 추출 결과와 자체 분석을 비교하여 다음을 확인:
   - 중복된 세부 기술이 있는가? (있으면 합치거나 제거)
   - 빠진 핵심 기술 영역이 있는가? (있으면 추가)
   - key_terms가 세부 기술 간 충분히 차별화되는가? (Jaccard > 50% 시 재설정)
   - exclude_terms가 적절한가? (key_terms와 충돌하는 제외 단어 확인)
3. **보정된 sub_techs.json 작성**: Claude가 직접 수정하여 JSON 파일 업데이트
4. **품질 검증 결과 포함**: `quality_warnings`의 경고를 해결한 상태로 제시

> **근거**: 한국어 RFP의 불릿 구조·표 셀 병합·기술 용어 다양성 때문에 스크립트 단독으로는 세부 기술 분류 품질이 불안정하다. Claude의 RFP 독해 능력과 스크립트의 구조적 추출을 결합하면 정확도가 크게 향상된다.

**⛔ Step 2-B 완료 후 반드시 사용자 확인 — 승인 전 Phase 2 진행 금지**

Claude는 **보정 완료된** 결과를 아래 형식으로 제시하고, 명시적 승인을 받은 뒤에만 다음 단계로 진행한다:

```
## 세부 기술 자동 추출 결과 확인

| ID | 한국어 기술명 | Google Patents 검색 키워드 |
|----|--------------|--------------------------|
| sub1 | {name_ko} | {key_terms} |
| sub2 | {name_ko} | {key_terms} |
| ...  | ...         | ...                       |

**검토 포인트**
- [ ] 기술명이 RFP 연구개발내용 항목과 일치하는가?
- [ ] 중요한 세부 기술이 빠져 있지 않은가?
- [ ] key_terms가 Google Patents 검색에 적합한 영어 기술 용어인가?
- [ ] 세부 기술별 key_terms가 서로 다른가? (모두 동일하면 검색 품질 저하)

위 목록이 맞으면 **"확인"** 또는 수정 내용을 알려주세요.
수정이 필요하면 output/sub_techs.json을 직접 편집하거나 수정 사항을 말씀해 주세요.
```

승인 방식:
- 사용자가 "확인", "OK", "진행", "맞습니다" 등을 입력하면 Phase 2로 진행
- 수정 요청 시 Claude가 sub_techs.json을 직접 편집 후 재확인 요청
- 세부 기술명 교체, key_terms 수정, 항목 추가/삭제 모두 Claude가 즉시 반영

### Phase 2: 검색식 생성 및 CSV 수집

**Step 3 — 메인 검색식 생성**
- `generate_query.py <rfp.md> [--years 10] [--exclude-terms "..."]`
- 기존과 동일: RFP 전체 범위 AND 그룹 검색식 생성
- 사용자가 Google Patents에서 CSV 다운로드

**Step 4 — 세부 기술별 검색식 생성**
- `generate_query.py <rfp.md> --sub-tech-json sub_techs.json` 실행
- 각 세부 기술별 특화 검색식 + URL 생성
- 사용자가 세부 기술별 CSV를 각각 다운로드 (3~5개)

### Phase 3: 메인 CSV 통계 분석

**Step 5 — 제목 연관성 점수 (메인 CSV)**
- `score_title_relevance.py <main.csv> <rfp.md> -o v1_top10000.csv --top 10000`
- 상위 10,000건 추출 → 보고서 통계 기반 데이터
- `aggregate_csv_report.py` 로 연도별·출원인·국가별 집계

### Phase 4: 세부 기술별 심층 분석

**Step 6 — 세부 기술별 제목 연관성 점수**
- 각 세부 기술 CSV에 대해 `score_title_relevance.py` 실행 → 상위 100건

**Step 7 — 초록+대표청구항 수집**
- 각 세부 기술의 상위 100건에 대해 `fetch_abstracts.py` 실행
- 초록(abstract) + 대표청구항(representative_claim) 컬럼 추가
- `--resume` 옵션으로 중단 후 재개 가능

**Step 8 — 초록+대표청구항 연관성 점수**
- `score_abstract_relevance.py` 실행 → 상위 5건 핵심 특허 선정
- 세부 기술별 핵심 특허 5건 CSV 저장: `{sub_tech}_core5.csv`

### Phase 5: 분석 및 보고서 생성

**Step 9 — 종합 분석 및 보고서 작성**

Claude가 다음 항목을 순서대로 작성:

1. **통계 섹션** (§1~§4): 메인 10,000건 집계 데이터 기반
2. **세부 기술별 특허 분석** (§5): 각 세부 기술의 핵심 특허 5건 분석
   - 특허 개요 표 (번호, 출원인, 출원일, 제목)
   - 대표청구항 요지 요약
   - 기술적 특징 및 RFP 연관성
3. **공백 기술 분석** (§6): RFP 요구사항 vs 기존 특허 커버리지 비교
4. **Objective-Solution Matrix** (§7): RFP 목표 × 특허 솔루션 매핑
5. **IP 창출 전략** (§8): 세부 기술별 출원 방향, 회피 전략, 선점 기회
6. **종합 전략 시사점** (§9)

## 보고서 작성 규칙

### 출원인 표기
- compact 형태 통일: `Apple Inc. → Apple`, `Google LLC → Google`, `Samsung Electronics Co., Ltd. → Samsung Electronics`
- LLC, Inc., Ltd., Co., Ltd., GmbH, Corporation, Corp. 접미사 삭제
- 한·중·일·영문 변형 → 영어 통일명으로 합산

### 섹션별 규칙
- **§3.3 주요 출원인 전략**: 반드시 표(table) 형태만. 헤더: `출원인 | 강점·주요 포트폴리오 | RFP 연관성 | 차별화·선행 회피 포인트`
- **§5 세부 기술별 분석**: 각 세부 기술마다 개요 표 + 핵심 특허 분석 포함
- **§6 공백 기술**: 표 형태: `기술 요구사항 | 특허 커버리지 | 공백 여부 | 제안 방향`
- **§7 OS 매트릭스**: 행=RFP 목표, 열=특허 솔루션. ◎/○/△/× 표기
- **§8 IP 창출 전략**: 세부 기술별로 독립항 전략, 종속항 전략, 회피 포인트 제시

### 기술 단계 해석
- 최근 2~3년 출원 감소 → 성숙기로 단정하지 않음 (공개 지연 고려)
- 도입기 기술이면 "도입기"로 명시

### 국가별 표기
- 유럽 국가 통합 (EP, DE, GB, FR, ES, NL, DK, BE → "유럽")
- 한글 명칭 사용: 미국, 중국, 일본, 한국, 유럽, PCT 등

## Outputs

```
{output_dir}/
├── rfp.md                          # PDF 변환 결과 (PDF 입력 시)
├── sub_techs.json                  # 세부 기술 목록 (3~5개)
├── query_main.txt                  # 메인 검색식
├── queries_sub_techs.md            # 세부 기술별 검색식
├── v1_top10000.csv                 # 메인 통계용 상위 10,000건
├── aggregate_report_data.json      # 집계 데이터 JSON
├── {sub_tech_1}/
│   ├── top100_title_scored.csv
│   ├── top100_with_abstracts.csv
│   ├── top100_abstract_scored.csv
│   └── core5_patents.csv
├── {sub_tech_2}/
│   └── ...
├── analysis/
│   ├── gap_analysis.md             # 공백 기술 분석
│   ├── os_matrix.md                # Objective-Solution Matrix
│   └── ip_strategy.md             # IP 창출 전략
└── {YYYYMMDD}_{topic}_특허전략보고서.md  # 최종 보고서
```

## Files in This Skill

- [SKILL.md](SKILL.md) – 본 스킬 정의 (이 파일)
- [reference.md](reference.md) – 검색식 문법, 점수 알고리즘, 공백 분석·OS 매트릭스·IP 전략 방법론
- [templates/report-template.md](templates/report-template.md) – 최종 보고서 템플릿 (§1~§9)
- [templates/sub-tech-analysis-template.md](templates/sub-tech-analysis-template.md) – 세부 기술 분석 섹션 템플릿
- [scripts/](scripts/) – `pdf_to_md.py`, `extract_sub_technologies.py`, `generate_query.py`, `score_relevance_weighted.py`, `score_title_relevance.py`, `score_abstract_relevance.py`, `fetch_abstracts.py`, `aggregate_csv_report.py`, `fill_report.py`, `run_pipeline.py`
- [output/실행가이드.md](output/실행가이드.md) – 단계별 실행 가이드

## Dependencies

- Python 3.9+
- `pdfplumber` (PDF→MD 변환)
- `pandas` (집계)
- `scikit-learn` (TF-IDF 유사도)
- `requests`, `beautifulsoup4` (초록 수집)
- [scripts/requirements.txt](scripts/requirements.txt) 참고
