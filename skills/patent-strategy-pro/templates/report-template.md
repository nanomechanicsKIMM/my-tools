---
title: "{{REPORT_TITLE}}"
created: "{{REPORT_DATE}}"
tags: [특허분석, IP전략, {{TAG_TOPIC}}, 세부기술분석, 공백기술, OS매트릭스]
aliases: ["{{ALIAS}}"]
---

# {{REPORT_TITLE}}

> **분석 기준일**: {{ANALYSIS_DATE}}
> **데이터 출처**: Google Patents (`https://patents.google.com`)
> **메인 검색 쿼리**: `{{SEARCH_QUERY}}`
> **분석 대상 기간**: {{DATE_RANGE}}
> **총 특허 건수 (메인)**: {{TOTAL_COUNT}}건
> **세부 기술 수**: {{SUB_TECH_COUNT}}개
> **관련 RFP**: [[{{RFP_FILENAME}}]]

---

## 1. 개요

{{OVERVIEW_PARAGRAPH}}

> [!note] 분석 한계
> {{LIMITATION_NOTE}}

---

## 2. 연도별 출원 추이 분석

### 2.1 우선일(Priority Date) 기준 출원 건수

| 연도 | 출원 건수 | 비중 (%) | 전년 대비 증감 |
|------|-----------|----------|----------------|
{{TABLE_PRIORITY_BY_YEAR}}

```
우선일 기준 연도별 출원 건수
{{ASCII_CHART_PRIORITY}}
```

### 2.2 공개일(Publication Date) 기준 출원 건수

| 연도 | 공개 건수 | 비고 |
|------|-----------|------|
{{TABLE_PUBLICATION_BY_YEAR}}

### 2.3 해석: 기술 단계 및 공개 지연 효과

{{INTERPRETATION_PUBLAG}}

> [!info] 기술 발전 단계 판정
> {{CONCLUSION_PHASE}}

---

## 3. 주요 출원인 분석

### 3.1 통합 출원인 순위 (Top 10)

{{APPLICANT_INTRO}}

| 순위 | 출원인 | 국적 | 통합 건수 | 비중(%) |
|------|--------|------|-----------|---------|
{{TABLE_TOP_APPLICANTS}}

### 3.2 출원인 국적별 점유율 (상위 10개사 기준)

```
{{ASCII_CHART_APPLICANTS}}
```

### 3.3 주요 출원인 전략 특성

| 출원인 | 강점·주요 포트폴리오 | RFP 연관성 | 차별화·선행 회피 포인트 |
|--------|----------------------|------------|--------------------------|
{{TABLE_APPLICANT_STRATEGY}}

{{APPLICANT_STRATEGY_SUMMARY}}

---

## 4. 국가별 특허 출원 분포

### 4.1 출원 국가별 건수

| 국가/지역 | 건수 | 비중(%) | 전략적 특성 |
|----------|------|---------|------------|
{{TABLE_COUNTRY}}

```
국가별 특허 분포
{{ASCII_CHART_COUNTRY}}
```

### 4.2 국가별 전략 분석

{{COUNTRY_STRATEGY}}

---

## 5. 세부 기술별 특허 분석

> [!summary] 세부 기술 목록
> {{SUB_TECH_LIST}}

{{SUB_TECH_SECTIONS}}

<!-- 각 세부 기술은 아래 5.N 형식으로 반복 삽입 -->
<!-- 예시: sub-tech-analysis-template.md 참고 -->

---

## 6. 공백 기술 분석 (Gap Analysis)

> [!abstract] 분석 방법
> RFP 기술 요구사항과 기존 특허 커버리지를 비교하여 특허화 기회 영역을 도출한다.
> 커버리지: ◎ 완전 커버 / ○ 부분 커버 / △ 간접 커버 / × 공백

### 6.1 요구사항별 특허 커버리지

| 기술 요구사항 | RFP 항목 | 특허 커버리지 | 주요 선행 특허 | 공백 내용 |
|-------------|---------|------------|------------|---------|
{{TABLE_GAP_ANALYSIS}}

### 6.2 세부 기술별 주요 공백

{{GAP_BY_SUB_TECH}}

### 6.3 공백 기술 특허화 우선순위

| 우선순위 | 공백 기술 | 근거 | 예상 청구 방향 |
|---------|---------|------|-------------|
{{TABLE_GAP_PRIORITY}}

---

## 7. Objective-Solution Matrix (OS Matrix)

> [!abstract] 분석 방법
> RFP 기술 목표(행) × 핵심 특허 솔루션 접근법(열) 매핑
> ◎ 강한 대응 / ○ 대응 / △ 약한 대응 / × 미대응

### 7.1 OS Matrix

| RFP 목표 | {{OS_MATRIX_HEADERS}} |
|---------|{{OS_MATRIX_HEADER_SEP}}|
{{OS_MATRIX_ROWS}}

### 7.2 Matrix 해석

{{OS_MATRIX_INTERPRETATION}}

> [!tip] 주요 공백 영역
> {{OS_MATRIX_GAPS}}

---

## 8. IP 창출 전략

> [!abstract] 전략 방향
> 공백 기술 분석 및 OS Matrix 결과를 기반으로 세부 기술별 특허 창출 방향을 제시한다.

{{IP_STRATEGY_SECTIONS}}

<!-- 각 세부 기술별 IP 전략은 아래 형식으로 반복 -->
<!--
### 8.N {세부기술명} IP 창출 전략

| 전략 유형 | 청구 방향 | 우선순위 | 주의할 선행 특허 | 예상 청구항 범위 |
|---------|---------|---------|------------|------------|
| 핵심 독립항 | ... | 최우선 | ... | ... |
| 선점 전략 | ... | 높음 | ... | ... |
| 방어 전략 | ... | 중간 | ... | ... |

#### 권장 청구항 구조

독립항 예시:
> "{핵심 구성 요소}를 포함하는 [장치/방법/시스템]으로서, [차별화 특징]을 특징으로 하는 {명칭}."

종속항 방향: {종속항 확장 방향}

#### 출원 타이밍 및 전략

{출원 타이밍, 국가별 PCT 활용 전략, 영업비밀 대비 특허 선택 기준}
-->

---

## 9. 종합 전략 시사점

### 9.1 기술 발전 단계 평가

{{TECH_PHASE_SUMMARY}}

### 9.2 지정학적 IP 경쟁 구도

{{COMPETITION_LANDSCAPE}}

### 9.3 세부 기술별 경쟁 강도 요약

| 세부 기술 | 특허 건수 | 주요 경쟁사 | 공백 수준 | IP 창출 기회 |
|---------|---------|-----------|---------|-----------|
{{TABLE_SUB_TECH_SUMMARY}}

### 9.4 국내 R&D 과제 기획 시사점

{{RND_IMPLICATIONS}}

---

## 10. 참고 데이터

- **메인 검색 URL**: {{SEARCH_URL}}
- **분석 기반 RFP**: [[{{RFP_FILENAME}}]]
- **세부 기술별 검색 URL**: [[queries_sub_techs]]
- **핵심 특허 목록**: {{CORE_PATENT_LINKS}}
- **공백 기술 상세**: [[analysis/gap_analysis]]
- **OS Matrix 원본**: [[analysis/os_matrix]]
- **IP 전략 상세**: [[analysis/ip_strategy]]

---

*본 보고서는 Google Patents 데이터를 기반으로 Patent Strategy Pro 스킬에 의해 자동 분석·작성되었습니다. {{GENERATED_BY}}*
