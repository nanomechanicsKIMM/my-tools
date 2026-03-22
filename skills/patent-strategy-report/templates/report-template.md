---
title: "{{REPORT_TITLE}}"
date: "{{REPORT_DATE}}"
tags: [특허분석, {{TAG1}}, {{TAG2}}, IP전략]
aliases: [{{ALIAS}}]
---

# {{REPORT_TITLE}}

> **분석 기준일**: {{ANALYSIS_DATE}}  
> **데이터 출처**: Google Patents (`https://patents.google.com`)  
> **검색 쿼리**: `{{SEARCH_QUERY}}`  
> **분석 대상 기간**: {{DATE_RANGE}}  
> **총 특허 건수**: {{TOTAL_COUNT}}건

---

## 1. 개요

{{OVERVIEW_PARAGRAPH}}

> **⚠️ 분석 한계 주의**: {{LIMITATION_NOTE}}

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

### 2.3 해석: 특허 공개 지연 효과(Publication Lag)

{{INTERPRETATION_PUBLAG}}

> **결론**: {{CONCLUSION_PHASE}}

---

## 3. 주요 출원인 분석

### 3.1 통합 출원인 순위 (Top 10)

{{APPLICANT_INTRO}}

| 순위 | 출원인 | 국적 | 통합 건수 | 비고 |
|------|--------|------|-----------|------|
{{TABLE_TOP_APPLICANTS}}

### 3.2 출원인 국적별 점유율 (상위 N개사 기준)

```
{{ASCII_CHART_APPLICANTS}}
```

### 3.3 주요 출원인 전략 특성

초록·대표청구항이 수집된 상위 500건 특허를 출원인별로 정리하고, RFP 및 해당 기술 목표 관점에서 전략을 **표**로 정리한다.

| 출원인 | 강점·주요 포트폴리오 | RFP 연관성 | 차별화·선행 회피 포인트 |
|--------|----------------------|------------|--------------------------|
{{TABLE_APPLICANT_STRATEGY}}

※ `{{TABLE_APPLICANT_STRATEGY}}` 는 상위 10개 출원인에 대해 **각 한 행씩** 채운다(예: `| 출원인명 | 강점·대표 특허 요지 | RFP 연관성 | 차별화·선행 회피 포인트 |`). 출원인(영문 통일명), 강점·주요 포트폴리오(대표 특허·청구 요지), RFP 연관성(높음/중간/제한적·참고), 차별화·선행 회피 포인트(1~2문장). 집계 데이터만으로 자동 생성이 어려우면 LLM/에이전트가 초록·대표청구항 기반으로 표 행을 작성한다. 표 하단에 **요약** 문단 1개를 둘 수 있다.

---

## 4. 국가별 특허 출원 분포

### 4.1 출원 국가별 건수

| 국가/지역 | 건수 | 비중 | 특성 |
|----------|------|------|------|
{{TABLE_COUNTRY}}

```
국가별 특허 분포
{{ASCII_CHART_COUNTRY}}
```

### 4.2 국가별 전략 분석

{{COUNTRY_STRATEGY}}

---

## 5. 종합 전략적 시사점

### 5.1 기술 발전 단계

{{TECH_PHASE}}

### 5.2 지정학적 IP 경쟁 구도

{{COMPETITION_DIAGRAM}}

### 5.3 국내 R&D 과제 기획 시 시사점

{{RND_IMPLICATIONS}}

---

## 6. 참고 데이터

- **검색 URL**: {{SEARCH_URL}}
- **관련 국내 RFP**: {{RFP_REFERENCE}}
- **관련 심층 분석 문서**: {{RELATED_DOCS}}

---

*본 보고서는 {{GENERATED_BY}}.*
