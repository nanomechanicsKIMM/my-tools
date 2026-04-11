<!-- improvement-plan-v2-delta.md — v1 → v2 업데이트 델타 템플릿

용도: v1 MD 파일에 선행특허 분석 결과를 통합할 때 phase9-updater 에이전트가 사용.
     기존 섹션을 덮어쓰지 않고 아래 블록을 **섹션 단위로** 병합한다.

업데이트 대상 섹션:
- Frontmatter: version, updated 필드 갱신
- §0 Executive Summary: v2 업데이트 요지 콜아웃 삽입
- §4 선행특허 대응: 전면 교체
- §6 청구항 개선: 신규 종속항 추가
- §10 우선순위 체크리스트: CRITICAL 카테고리 신설
- §11 (신규): 긴급 전략 섹션 삽입
- 부록 C: v1→v2 변경 요약표 추가

병합 규칙:
- 기존 섹션 내 사용자 수정분은 hash 비교로 보존 (R-12)
- 섹션 헤더(## §N) 단위로만 Edit, 전체 덮어쓰기 금지
-->

## FRONTMATTER_UPDATE

```yaml
# 기존에 추가 (replace, 다른 필드는 유지)
version: v2
updated: {{update_date}}
source:
  - "[[{{original_source}}]]"
  - "[[{{prior_art_source}}]]"
```

---

## SECTION_0_EXECUTIVE_SUMMARY_CALLOUT

v1 §0 Executive Summary 문단 직후에 아래 콜아웃을 삽입:

```markdown
> [!warning] v2 업데이트 요지 ({{update_date}})
> - **CRITICAL**: {{critical_finding_summary}} 발견 → 본원 청구항 저촉 위험 → **독립항 긴급 보정 필요**
> - 구체적 보정안 문언 확정, 신규 종속항 추가
> - 의견서용 메커니즘 차이 논증표 통합
> - 청구항 오자 보강
```

v1 Executive Summary의 **개선 포인트 축** 표를 4축 → 5축으로 확장:

```markdown
| # | 축 | 핵심 이슈 | 우선순위 |
|---|-----|-----------|----------|
| 0 | **선행특허 대응 (v2 신규)** | {{prior_art_issue}} | ★★★★ |
| 1 | **청구범위 확장** | ... | ★★★ |
...
```

---

## SECTION_4_PRIOR_ART_REPLACE

§4 섹션 전체를 아래 내용으로 교체 (v1의 "키워드 권고" 섹션은 폐기):

```markdown
## §4. 선행특허 대응 — 구체 대비 분석 (v2 전면 갱신)

> [!warning] v2 업데이트 근거
> 본 섹션은 {{prior_art_source}}의 선행특허 조사 결과를 통합한다.

### 4.1 핵심 선행특허 목록

| 약칭 | 번호 | 권리자 | 상태 | 핵심 기술 | 위협도 |
|------|------|--------|------|-----------|--------|
{{prior_art_matrix}}

### 4.2 저촉 위험 분석

{{infringement_risk_analysis}}

### 4.3 메커니즘 차이 논증 (의견서용)

{{mechanism_diff_tables_full}}

### 4.4 명세서 §배경기술 / §해결과제 보강 지침

{{background_reinforcement_v2}}
```

---

## SECTION_6_NEW_DEPENDENT_CLAIMS_APPEND

§6.4 (신규 종속항 추가 목록)에 아래 행들을 추가 (기존 제17항 이후 연속 번호):

```markdown
| **신규 18** | {{새_종속항_1_내용}} | {{근거}} | 🔴 **필수** | {{SP_대비_차별}} |
| **신규 19** | {{새_종속항_2_내용}} | {{근거}} | 🔴 **강력 권고** | {{SP_대비_차별}} |
| **신규 20** | {{새_종속항_3_내용}} | {{근거}} | 🔴 **강력 권고** | {{SP_대비_차별}} |
...
```

---

## SECTION_10_CRITICAL_CATEGORY_INSERT

§10 우선순위 체크리스트 맨 위에 🔴🔴 CRITICAL 카테고리를 **새로 삽입** (기존 🔴 Must-fix 위):

```markdown
### 🔴🔴 CRITICAL ({{critical_threat}} 저촉 회피 — 출원 전 반드시)

- [ ] **C-01**: 제1항 기저 변환부 문언에 "{{보정안_A_키워드}}" 추가 (보정안 A)
- [ ] **C-02**: 제9항 방법 문언에 "{{보정안_A_방법항_키워드}}" 추가
- [ ] **C-03**: 제1항 수차 연산부에 "{{보정안_D_키워드}}" 추가 (보정안 D)
- [ ] **C-04**: 신규 제18항 추가 — {{신규18_요약}}
- [ ] **C-05**: 신규 제19항 추가 — {{신규19_요약}}
...
- [ ] **의견서 초안**: §4.3의 메커니즘 차이 논증표를 의견서 템플릿으로 사전 준비
```

---

## SECTION_11_EMERGENCY_STRATEGY_NEW

§10 직후에 새로운 §11 섹션을 **신규 삽입**:

```markdown
## §11. {{위협_특허명}} 저촉 회피 긴급 전략 (v2 신규)

> [!danger] 본 섹션의 위치
> {{위협 설명}}

### 11.1 위협 요약

```mermaid
graph LR
  T[🔴 {{위협특허명}}<br/>{{번호}}<br/>{{권리자}} {{등록일}}]
  PRE[공통 요소<br/>{{공통_구성}}]
  DIFF[차별 요소<br/>{{차별_구성}}]
  T -->|중첩 위험| PRE
  PRE -->|보정으로 회피| DIFF
  DIFF --> SAFE[본원 안전 권리범위]
  style T fill:#c0392b,color:#fff
  style PRE fill:#f39c12,color:#fff
  style DIFF fill:#27ae60,color:#fff
  style SAFE fill:#2ecc71,color:#fff
```

### 11.2 3중 방어선 구축

| 방어선 | 조치 | 청구항 |
|--------|------|--------|
| **1차 (독립항 본체)** | {{1차_조치}} | §6.2 보정 A+D로 제1/9항 본체 변경 |
| **2차 (핵심 종속항)** | {{2차_조치}} | 신규 {{2차_종속항_번호}} |
| **3차 (보조 종속항)** | {{3차_조치}} | 신규 {{3차_종속항_번호}} |

### 11.3 제출 전략

1. **출원 시점**: 본 개선방안 v2 반영 후 최대한 조기 출원
2. **중간 응답 준비**: §4.3의 메커니즘 차이 논증표를 의견서 초안으로 사전 준비
3. **거절 대응**: 필요 시 `patent-defence` 스킬 호출
4. **전략적 출원**: PCT 진행 시 유럽/미국/일본 대응 검토
```

---

## APPENDIX_C_CHANGELOG_APPEND

부록 C에 아래 블록을 append:

```markdown
### C.5 v1 → v2 변경 요약

| 영역 | v1 | v2 |
|------|-----|-----|
| 선행기술 인식 | {{v1_prior_art_state}} | {{v2_prior_art_state}} |
| 독립항 전략 | {{v1_claim_strategy}} | {{v2_claim_strategy}} |
| 신규 종속항 | {{v1_new_claims}} | {{v2_new_claims}} |
| 의견서 | 없음 | 메커니즘 차이 논증표 |
| 청구항 오자 | {{v1_typos}} | {{v2_typos}} |
| 긴급 섹션 | 없음 | **§11 {{위협명}} 저촉 회피 긴급 전략** |
```

---

<!-- END OF DELTA TEMPLATE -->
