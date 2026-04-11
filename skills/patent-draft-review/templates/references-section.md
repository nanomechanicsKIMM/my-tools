<!-- references-section.md — 참고문헌 섹션 템플릿

용도: phase8-references-generator 에이전트가 본 템플릿을 사용하여 개선방안 MD 말미에
     참고문헌 섹션을 자동 생성한다.

입력:
- phase4 의 선행특허 분석 결과 (prior_art_diff.json)
- 명세서 본문에서 추출한 인용 (spec_structure.json의 references 필드)

인용 규약 (prior-art-citation-format.md 참조):
- [P{n}] = Paper (논문)
- [X{n}] = eXternal prior patent (선행특허)
- [R{n}] = Reference (본원 기존 인용)
- [K{n}] = KIMM (내부 포트폴리오, 조직별 확장 가능)
-->

---

## 참고문헌 (References)

> [!info] 표기 원칙
> - **논문**: 저자, 연도, 제목, 학술지, 권/호, 페이지, **DOI 링크** (클릭 가능한 `https://doi.org/...`)
> - **특허**: 권리자, 제목, 공보/등록번호, 출원일/공개일/등록일, **Google Patents 링크** (클릭 가능)
> - 심사 과정에서 인용될 가능성이 높은 순서로 정렬

### A. 학술 논문 (Journal Articles)

{{#each papers}}
#### [P{{index}}] {{first_author}} et al. ({{year}}) — {{short_title}}

> {{authors}} ({{year}}). **{{title}}.** *{{journal}}*, {{volume}}({{issue}}), {{pages}}.
>
> **DOI**: <https://doi.org/{{doi}}>

- **관련성**: {{relevance_note}}

{{/each}}

---

### B. 선행특허 (Prior Patents)

{{#if has_critical_prior_art}}
> [!warning] CRITICAL — {{critical_patent_name}} 한국 등록 상태
> 아래 {{critical_patent_ref}}는 한국에서 **등록** 완료되어 권리가 확정된 상태이다. 본원 출원 시 반드시 저촉 회피 전략 적용 필요.
{{/if}}

{{#each prior_patents}}
#### [X{{index}}] {{short_name}} — {{description}} {{threat_emoji}}

> **{{title_ko}}** ({{title_en}})
>
> - 권리자: {{assignee}}
> - 공보번호: **{{pub_number}}**
{{#if registration_number}}
> - 등록번호: **{{registration_number}}**
{{/if}}
> - 출원일: {{filing_date}}{{#if publication_date}} | 공개일: {{publication_date}}{{/if}}{{#if registration_date}} | **등록일: {{registration_date}}**{{/if}}
{{#if n_claims}}
> - 청구항: {{n_claims}}항
{{/if}}
> - **Google Patents**: <https://patents.google.com/patent/{{pub_number}}>
{{#if is_pct}}
> - **WIPO PatentScope**: <https://patentscope.wipo.int/search/en/detail.jsf?docId={{pub_number}}>
{{/if}}
{{#if is_kr_registered}}
> - **KIPRIS 검색**: <http://kpat.kipris.or.kr/kpat/searchLogina.do?next=MainSearch>
{{/if}}

- **관련성**: {{relevance_note}}

{{/each}}

---

### C. 본원 명세서 기존 인용 선행기술

{{#each existing_references}}
#### [R{{index}}] {{pub_number}}

> **{{description}}** — 초안 line {{spec_lines}} 인용
>
> - 공보번호: **{{pub_number}}**
> - **Google Patents**: <https://patents.google.com/patent/{{pub_number}}>

{{/each}}

---

{{#if has_org_portfolio}}
### D. {{org_name}} 내부 참고 특허 (관련 포트폴리오)

> [!note] 본원과 직접 관련은 없으나 {{org_name}} 관련 포트폴리오 참고

{{#each org_patents}}
#### [K{{index}}] {{title}}

> - 출원번호: **{{pub_number}}**
> - 출원일: {{filing_date}}
> - 출원인: {{org_name}}
> - **Google Patents**: <https://patents.google.com/patent/{{pub_number}}>

{{/each}}

---
{{/if}}

### E. 참고문헌 인용 규약 (내부 사용)

| 약칭 | 풀네임 | 용도 |
|------|--------|------|
{{#each citation_code_rows}}
| {{code}} | {{full_name}} | {{usage}} |
{{/each}}

> [!tip] 의견서 작성 시
> 위 [X1]~[X{{n_prior}}], [P1]~[P{{n_papers}}] 번호를 의견서에 그대로 사용하면 본 개선방안과의 참조 추적이 용이하다. 특히 **CRITICAL** 선행특허는 **저촉 회피 논증**을 최우선으로 서술.

---

<!-- TEMPLATE USAGE NOTES
- Handlebars-style 문법: {{#each}} ... {{/each}}, {{#if}} ... {{/if}}
- Phase 8 에이전트(phase8-references-generator)가 prior_art_diff.json을 입력받아 치환
- 논문/특허 구분 자동 판단: DOI 존재 = 논문, Patent number = 특허
- 등록특허 vs 공개특허: registration_date 존재 여부로 판단
- PCT 여부: pub_number가 WO로 시작하면 is_pct: true
- KR 등록 여부: pub_number 또는 registration_number가 KR로 시작 + registration_date 존재
- threat_emoji: CRITICAL=🔴, HIGH=🟡, MEDIUM=🟢, LOW/참고=없음
-->
