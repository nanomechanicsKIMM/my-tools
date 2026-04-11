---
title: "{{invention_id}} 명세서 개선 방안 — TRIZ 기반 분석"
created: {{date}}
tags: [특허, 개선방안, TRIZ, {{tech_field}}, patent-draft-review]
source: "[[{{source_md}}]]"
applied_skill: patent-draft-review
---

# {{invention_id}} 명세서 개선 방안

> [!info] 본 문서의 목적
> `{{spec_file}}` 특허 명세서 초안을 **patent-draft-review** 스킬의 TRIZ 분석 방법론으로 재점검하여, (1) 청구범위 확장 방향, (2) 명세서 논리/실시예 보강, (3) 오탈자·부호·용어 수정, (4) 도면/요약 보완을 통합적으로 도출한다.

---

## §0. Executive Summary

| 항목 | 내용 |
|------|------|
| 발명 명칭 | {{invention_title}} |
| 출원번호 | {{invention_id}} (초안) |
| 기술분야 | {{tech_field}} |
| 핵심 기술 | {{core_tech_summary}} |
| 독립 청구항 | {{n_independent}}개 |
| 종속 청구항 | {{n_dependent}}개 (총 {{n_total_claims}}개 청구항) |
| 도면 | {{n_figures}}개 |

### 개선 포인트 축

| # | 축 | 핵심 이슈 | 우선순위 |
|---|-----|-----------|----------|
| 1 | **청구범위 확장** | {{claim_issue_summary}} | ★★★ |
| 2 | **실시예 보강** | {{example_issue_summary}} | ★★★ |
| 3 | **오탈자/부호 정비** | {{proofread_issue_summary}} | ★★★ |
| 4 | **요약·도면 보완** | {{abstract_issue_summary}} | ★★ |

---

## §1. TRIZ 시스템 분석 (Phase 1 등가)

### 1.1 시스템 구성요소

```mermaid
graph TB
  {{system_map_mermaid}}
```

### 1.2 유용 기능 vs 유해 작용

| 측면 | 내용 |
|------|------|
| **유용 기능** | {{useful_functions}} |
| **유해 작용** | {{harmful_effects}} |

### 1.3 현행 명세서의 시스템 기술 커버리지

| 구성 | 본문 서술 | 청구항 반영 | 평가 |
|------|-----------|-------------|------|
{{coverage_table_rows}}

---

## §2. 기술적 모순과 물리적 모순 (Phase 2 등가)

### 2.1 기술적 모순 (Technical Contradictions)

| ID | 개선 파라미터 | 악화 파라미터 | 해결 아이디어 |
|----|---------------|---------------|---------------|
{{technical_contradictions}}

### 2.2 물리적 모순 (Physical Contradictions)

| ID | 모순 진술 | 분리 원리 |
|----|-----------|-----------|
{{physical_contradictions}}

---

## §3. IFR(Ideal Final Result) 및 청구범위 확장 후보

> [!note] TRIZ 용어는 부록 A에만 사용한다. 본 섹션은 일반 기술 용어로 서술.

### 3.1 IFR 리스트

| # | IFR 요지 | 해결 모순 | 청구화 제안 |
|---|----------|-----------|-------------|
{{ifr_list}}

### 3.2 청구범위 강화 권고

{{claim_strengthening_recommendations}}

---

## §4. 선행특허 대응 — 구체 대비 분석

{{#if has_prior_art}}
### 4.1 핵심 선행특허 목록

| 약칭 | 번호 | 권리자 | 상태 | 핵심 기술 | 위협도 |
|------|------|--------|------|-----------|--------|
{{prior_art_matrix}}

### 4.2 저촉 위험 분석

| 본원 청구항 | 저촉 위험 | 분석 |
|-------------|-----------|------|
{{infringement_risk_matrix}}

### 4.3 메커니즘 차이 논증 (의견서용)

{{mechanism_diff_tables}}

### 4.4 명세서 §배경기술 / §해결과제 보강 지침

{{background_reinforcement}}
{{else}}
> [!note] 선행특허 분석 미제공
> 본 검토는 선행특허 비교 없이 수행되었다. 출원 전 아래 외부 도구로 검색 후 `--prior-art` 플래그로 재실행을 권장한다:
> - KIPRIS: `http://kpat.kipris.or.kr/kpat/searchLogina.do?next=MainSearch` (한국 특허)
> - Google Patents: `https://patents.google.com` (국제 특허)
> - WIPO PatentScope: `https://patentscope.wipo.int` (PCT 출원)
>
> 또한 Phase 8(참고문헌 섹션)은 본원 §선행기술문헌에 인용된 특허만 [R1]/[R2] 형식으로 자동 생성하며, B(선행특허) 섹션은 비어 있다.
{{/if}}

---

## §5. 명세서 상세설명 논리 강화 포인트

### 5.1 §해결과제 보강

{{problem_statement_improvements}}

### 5.2 §과제의 해결 수단 재구성

{{solution_restructure}}

### 5.3 §발명의 효과 정량화

> [!tip] 정량적 효과 기술 추가 권고
> {{quantification_suggestions}}

### 5.4 실시예 확장

| 주제 | 현재 | 개선안 |
|------|------|--------|
{{example_expansion_table}}

---

## §6. 청구항 개별 검토와 개선안

### 6.1 청구항 구조 진단

```mermaid
graph LR
  {{claim_tree_mermaid}}
```

### 6.2 항별 개선 권고

| 항 | 현 상태 평가 | 개선안 |
|----|--------------|--------|
{{claim_recommendations}}

### 6.3 신규 종속항 추가 목록

| 번호 | 내용 | 근거 | 우선순위 |
|------|------|------|----------|
{{new_dependent_claims}}

### 6.4 청구항 전문부(Preamble) 및 형식 개선

{{preamble_form_improvements}}

---

## §7. 오탈자·부호·용어 수정 목록 (Proofreading)

> [!error] 치명적 오류 (출원 전 반드시 수정)

### 7.1 치명적 오류

| # | 위치 | 현재 | 수정 | 비고 |
|---|------|------|------|------|
{{critical_typos}}

### 7.2 용어 일관성

| # | 위치 | 이슈 | 수정 방향 |
|---|------|------|-----------|
{{terminology_inconsistencies}}

### 7.3 부호의 설명 보완

| 부호 | 구성요소 | 현재 등재 | 조치 |
|------|----------|-----------|------|
{{reference_number_table}}

### 7.4 경미한 표현 개선

| # | 위치 | 현재 | 개선 |
|---|------|------|------|
{{minor_improvements}}

---

## §8. 요약서(Abstract) 및 대표도 개선

### 8.1 현재 요약 진단

{{current_abstract_diagnosis}}

### 8.2 요약 개선안

> {{improved_abstract}}

### 8.3 대표도 권고

{{representative_figure_recommendation}}

---

## §9. 도면 점검

| 도면 | 확인 포인트 | 조치 |
|------|-------------|------|
{{figure_checklist}}

---

## §10. 우선순위 체크리스트 (출원 전 액션)

### 🔴 Must-fix (출원 전 반드시)

{{must_fix_checklist}}

### 🟡 Should-fix (진보성·권리범위 강화)

{{should_fix_checklist}}

### 🟢 Nice-to-have (장기 권리 포트폴리오)

{{nice_to_have_checklist}}

---

## 부록 A. TRIZ 분석 상세 (내부 참고용)

> [!note] 본 부록은 patent-draft-review 스킬 규칙에 따라 **내부 참고용**이며, 실제 청구항/상세설명에는 TRIZ 용어(모순 매트릭스, IFR, 원리 번호 등)를 일체 포함하지 않는다.

### A.1 분석 대상 매핑

| TRIZ 파라미터 | 본 발명 대응 |
|---------------|---------------|
{{triz_parameter_mapping}}

### A.2 모순 매트릭스 추천 원리

{{contradiction_matrix_lookup}}

### A.3 적용된 40 발명 원리

| 원리 # | 명칭 | 본 발명 적용 |
|--------|------|--------------|
{{applied_40_principles}}

### A.4 IFR → 청구화 가능성 검토

{{ifr_claimability_analysis}}

---

## 부록 B. 수정 반영 시 버전 관리 권고

- **v1 (현재)**: `{{invention_id}}-초안.{{ext}}`
- **v2 제안**: `{{invention_id}}-초안_v2_오탈자수정.{{ext}}` (§7 Must-fix 반영)
- **v3 제안**: `{{invention_id}}-초안_v3_청구범위확장.{{ext}}` (§6 Should-fix 반영)
- **최종**: `{{invention_id}}.{{ext}}` (출원 제출본)

---

## 부록 C. 참고 — 분석에 적용된 방법론

본 개선 방안은 **patent-draft-review** 스킬의 TRIZ 분석 프레임워크를 기존 명세서 **진단 모드**로 적용한 결과이다.

```
Phase 1 (시스템 분석) → 현행 구성요소 추출 및 기능 맵
Phase 2 (모순/IFR)     → 기술적·물리적 모순 도출
Phase 3 (청구항 구조)   → 독립/종속 트리 + 매몰 차별 요소 탐지
Phase 4 (선행특허 대비) → (옵션) 저촉 위험 매트릭스 + 메커니즘 차이
Phase 5 (오탈자/부호)   → korean-patent-typo-patterns 기반 스캔
Phase 6 (요약/도면)     → 독립 청구항과의 정합성 점검
Phase 7 (리포트 작성)   → 본 MD 파일 생성
Phase 8 (참고문헌)      → DOI/Google Patents 링크 자동 삽입
```

> [!info] 관련 파일
> - 원본: [[{{source_md}}]]
> - 본 문서: [[{{invention_id}}_개선방안]]

---

{{references_section_placeholder}}

---

<!-- TEMPLATE USAGE NOTES
- 플레이스홀더 문법: {{variable_name}} — Phase 7 (report-writer) 에이전트가 치환
- 조건 블록: {{#if has_prior_art}} ... {{else}} ... {{/if}} — Phase 4 여부에 따라 렌더링
- §11 긴급 전략 섹션은 v2 업데이트 시 improvement-plan-v2-delta.md 에서 추가됨
- 참고문헌 섹션은 Phase 8 이 references-section.md 템플릿을 사용하여 append
- Mermaid 다이어그램은 구성요소 수에 따라 동적 생성 (assets/mermaid-snippets.md 참조)
-->
