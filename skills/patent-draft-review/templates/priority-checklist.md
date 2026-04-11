<!-- priority-checklist.md — 4단계 우선순위 체크리스트 템플릿

용도: phase7-report-writer 에이전트가 본 템플릿을 사용하여 개선방안 MD §10
     우선순위 체크리스트를 생성한다.

4단계:
- 🔴🔴 CRITICAL   : 선행특허 저촉 회피 — 출원 전 반드시 (v2 전용)
- 🔴   Must-fix    : 오탈자/부호/치명 오류 — 출원 전 반드시
- 🟡   Should-fix  : 진보성/권리범위 강화 — 출원 전 권장
- 🟢   Nice-to-have: 장기 포트폴리오 — 차기 출원/확장 가능

출력 위치: 개선방안 MD §10
-->

## §10. 우선순위 체크리스트 (출원 전 액션)

{{#if has_critical_items}}
### 🔴🔴 CRITICAL ({{critical_context}} — 출원 전 반드시)

{{#each critical_items}}
- [ ] **{{id}}**: {{description}} ({{section_ref}})
{{/each}}

{{#if has_opinion_draft_task}}
- [ ] **의견서 초안**: §4.3의 메커니즘 차이 논증표를 의견서 템플릿으로 사전 준비
{{/if}}

{{/if}}

### 🔴 Must-fix (오탈자·부호 — 출원 전 반드시)

{{#each must_fix_items}}
- [ ] **{{id}}**: {{description}}{{#if location}} ({{location}}){{/if}}
{{/each}}

### 🟡 Should-fix (진보성·권리범위 강화)

{{#each should_fix_items}}
- [ ] **{{id}}**: {{description}}
{{/each}}

### 🟢 Nice-to-have (장기 권리 포트폴리오)

{{#each nice_to_have_items}}
- [ ] **{{id}}**: {{description}}
{{/each}}

---

<!-- TEMPLATE USAGE NOTES

### 항목 ID 네이밍 규칙

| 카테고리 | 접두사 | 예시 |
|---------|--------|------|
| CRITICAL (선행특허 저촉 회피) | C-01 ~ C-99 | C-01: 제1항에 "장벽 근처 공액면" 추가 |
| Must-fix (오탈자·부호) | E-01 ~ E-99 | E-01: `position-dependetn` → `position-dependent` |
| Must-fix (용어 일관성) | T-01 ~ T-99 | T-01: `conjugate surface` ↔ `conjugate plane` 통일 |
| Should-fix (청구항 구조) | 신규 18 ~ | 신규 18: 공액면 점진 정밀화 종속항 |
| Should-fix (본문 강화) | B-01 ~ | B-01: 배경기술에 선행특허 선제 인용 |
| Nice-to-have (포트폴리오) | N-01 ~ | N-01: 3D 볼륨 실시예 종속항 |

### 체크박스 상태

- `[ ]` — 미처리 (기본)
- `[x]` — 완료 (사용자 수기 체크)
- `[~]` — 부분 완료
- `[?]` — 검토 필요

### Context 라벨 예시 (critical_context 필드)

- "KR-SP1 등록특허 저촉 회피"
- "SP1+SP2 유사성 회피"
- "IMPACT 모델 기반 수차 보정 차별화"
- "선제적 진보성 방어"

### 생성 규칙

1. CRITICAL 카테고리는 **Phase 4 선행특허 비교가 있을 때만** 렌더링
2. Must-fix에는 **반드시** Phase 5 오탈자 결과 + Phase 3 청구항 형식 결과 모두 포함
3. Should-fix의 신규 종속항 제안은 §6.4와 번호 일치
4. 각 항목은 관련 섹션(§N.M) 참조를 괄호로 표시
5. 총 항목 수 상한: CRITICAL 15, Must-fix 15, Should-fix 20, Nice-to-have 10 (초과 시 병합)

-->
