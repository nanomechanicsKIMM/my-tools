---
name: patent-strategy-report
description: Generates patent strategy reports from RFP markdown and user-provided Google Patents CSV. Builds search queries from RFP; scores patents by title–RFP relevance with must-include/must-exclude term weights; keeps top 10k for statistics, top 100 for abstracts, top 10 by abstract score as core patents; then aggregation and Obsidian-format report. Applies to any research/technology domain.
---

# Patent Strategy Report Skill

Generates a patent strategy report (Obsidian MD) from an **RFP markdown file** and **user-provided CSV** (downloaded from Google Patents). **Main workflow**: **relevance-based pipeline** — title–RFP 상관성 점수(반드시 포함 단어 가산, 반드시 제외 단어 감점)로 상위 1만 건 저장 → 통계용 집계·보고서 작성; 상위 100건에 초록 수집 → 초록 기준 상관성 점수 → 상위 10건 핵심 특허 저장 → 핵심 특허 분석을 보고서에 반영. Applicable to **any research or technology domain**.

## When to Use

- User has an RFP in markdown and wants a patent strategy or landscape report.
- User has (or will obtain) a CSV export from Google Patents for the same topic and wants structured analysis.
- User mentions "특허 전략 보고서", "RFP 특허 검색", "Google Patents 분석", "특허 CSV 분석" in Claude Code.

## Inputs

- **Required**: (1) Path to RFP markdown file (`.md`). (2) Path to CSV file from Google Patents (user downloads manually and provides).
- **Optional**: Technology domain (e.g. 디스플레이, 반도체) for query vocabulary; **current-folder RFP**: run `generate_query.py` with first argument `.` to auto-detect `*RFP*.md` in the current directory.

## Workflow: Relevance-based pipeline (상관성 점수 알고리즘)

1. **Generate query** from RFP (`generate_query.py`). Optionally `--exclude-terms`, `--required-terms`. User downloads CSV (v1).
2. **Title relevance score** (`score_title_relevance.py`): RFP 부합성(TF-IDF 코사인) + **반드시 포함 단어**는 높은 양의 가중치, **반드시 제외 단어**는 높은 음의 가중치로 계량화. 상위 **10,000건**을 별도 파일로 저장 → 이 파일을 기준으로 특허 전략 보고서의 **통계적 부분** 작성.
3. **Top 100 by title score** → **초록 수집** (`fetch_abstracts.py`) → 초록 컬럼 추가.
4. **Abstract relevance score** (`score_abstract_relevance.py`): 동일한 포함/제외 가중치로 초록–RFP 상관성 점수 산출 → 상위 **10건**을 핵심 특허로 저장 (`핵심특허_상위10건_목록.csv`).
5. **핵심 특허 분석** 진행 후 특허 전략 보고서에 추가(관련 문서 링크 등).
6. **Aggregate** 10k CSV (연도별·출원인·국가별) → **Fill report** (`fill_report.py`) → LLM narrative.

**일괄 실행**: `run_relevance_pipeline.py <v1_csv> <rfp_path> -o output [--include-terms "A,B"] [--exclude-terms "C,D"]`. 상세는 `output/실행가이드_상관성_파이프라인.md` 참고.

### 보고서 작성 규칙 (사용자 요구사항 반영, 모든 분야 공통)

다양한 연구·기술 분야의 RFP에 공통 적용되는 최종 보고서 규칙이다. **도메인별로** RFP 키워드·기술 목표만 치환하면 된다.

- **§3.3 주요 출원인 전략 특성**: 반드시 **표(table)** 형태로만 제시한다. 불릿 목록이나 장문 서술로 중복 기술하지 않는다.
  - 표 헤더: `출원인 | 강점·주요 포트폴리오 | RFP 연관성 | 차별화·선행 회피 포인트`
  - 상위 10개 출원인당 한 행씩 채운다. 표 하단에 **요약** 문단 1개만 둔다.
  - 집계만으로 채우기 어려우면 LLM/에이전트가 초록·대표청구항 기반으로 표 행을 작성한다. ([reference.md](reference.md) Report section template 참고)
- **출원인 표시명(영문)**: **compact** 형태로 통일한다. LLC, Inc., Ltd., Co., Ltd., Gmbh, Corporation, Corp. 등 일반적 법인 접미사는 **삭제**하여 간결하게 표기한다.
  - 예: Apple Inc. → Apple, Intel Corporation → Intel, Google LLC → Google, Semiconductor Energy Laboratory Co., Ltd. → Semiconductor Energy Laboratory, Cilag Gmbh International → Cilag International
  - 집계 스크립트 `aggregate_csv_report.py`의 `compact_applicant_display()` 및 `_canonical_assignee_english()` 반환값에 이미 적용되어, JSON·표·ASCII 차트에 compact 명이 나온다.
- **출원인 통일**: 한·중·일·영문 변형은 하나의 **영어 통일명**으로 매핑 후 건수 합산. 통일명도 위 compact 규칙을 적용해 표시한다.
- **핵심 특허(§6)**: 상위 10건 선정 후 **개요 표**, **대표청구항 요지**, **공백 기술**, **OS 매트릭스**, **특허 창출 전략 요약**을 보고서 본문에 포함하고, 상세 문서는 링크로 참조한다.

### Common: Aggregate and report

- **Aggregate** (`aggregate_csv_report.py`): 연도별·출원인·국가별 집계. **출원인**은 **영어 통일** 및 **동일 회사 합산** (한·중·일·영문 변형 → 하나의 영어 통일명, 건수 합산). 표시 시 **compact** 적용(LLC, Inc., Ltd., Co., Ltd., Gmbh, Corporation, Corp. 제거). **국가별** 보고서용 집계는 **유럽 국가 통합**(EP·ES·DE·GB·FR·NL·DK·BE → "유럽") 및 **한글 명칭(name_ko)** 사용(`aggregate_countries_for_report`); 표·차트는 한글만 표기.
- **Fill report** (`fill_report.py`): [templates/report-template.md](templates/report-template.md) 기반으로 표·차트 채움. 국가 표는 `name_ko`가 있으면 한글만 사용.
- **Narrative**: 개요, 연도별 해석, **기술 단계**(도입기/성장기/성숙기)는 RFP·도메인에 맞게 해석. 우선일 기준 최근년도 감소가 **공개 지연·표본 한계** 때문인지, 기술 성숙인지 구분하여 서술 (도입기 기술이면 “도입기”로 명시).

## Outputs

- Search query string and URL (for user to download CSV).
- Filtered or top-N CSV path (path-dependent).
- One Obsidian-format report: `{topic}_세계특허현황_분석보고서.md` (또는 날짜 접두사 포함). **분야 무관**: RFP 제목·키워드만 해당 도메인에 맞게 치환하면 동일 템플릿·규칙으로 반도체, 배터리, 바이오, AI 등 어떤 기술 분야에도 적용 가능하다.

## Files in This Skill

- [reference.md](reference.md) – Query syntax, **상관성 점수 알고리즘(포함/제외 가중치)**, 제외 키워드, 기술 용어, **국가별 집계(유럽 통합·name_ko)**, **출원인 통일·compact 표시·§3.3 표 형태**, 보고서 템플릿 요약.
- [templates/report-template.md](templates/report-template.md) – Report structure and placeholders. §3.3은 표(table) 전용, 출원인명은 compact 규칙 적용.
- [scripts/](scripts/) – **Core**: `generate_query.py`, `score_relevance_weighted.py`, `score_title_relevance.py`, `score_abstract_relevance.py`, `fetch_abstracts.py`, `aggregate_csv_report.py`, `fill_report.py`. **Pipeline**: `run_relevance_pipeline.py` (10k by title → top 100 → abstracts → abstract score → top 10 core → aggregate & report). Legacy: `filter_noise.py`, `filter_title_top_n.py`, `filter_abstract_top_n.py`, `run_v1_to_v2_pipeline.py`, `run_10k_500_core_pipeline.py`.
- [output/](output/) – 실행가이드: `실행가이드_상관성_파이프라인.md`, `실행가이드_v1_to_v2_파이프라인.md`, `워크플로_요약.md`.

## Dependencies

- Python 3.9+.
- **pandas** (aggregation). **scikit-learn** (filter_title_top_n, filter_abstract_top_n, score_relevance). **requests**, **beautifulsoup4** (fetch_abstracts). See [scripts/requirements.txt](scripts/requirements.txt).
