---
description: FEM 해석 결과를 해석해·수렴·극한·평형으로 검증하고 검증표를 생성 (FEniCSx 전용)
---

# /fem-verify — FEM 검증

FEniCSx/dolfinx 해석 결과(`results/<단계>`)를 **fem-verify** 스킬과 **fem-verifier** 에이전트로 검증한다.

## 동작
1. `fem-verify` 스킬을 로드한다 (7항목 검증 체크리스트 + `references/analytic_solutions.md`).
2. 깊은 검증이 필요하면 **fem-verifier** 에이전트(별도 lane, opus)에 위임한다 — 구현과 같은 context에서 self-approve 금지.
3. 2~3개 독립 증거를 수집해 `templates/verification_table.md`로 검증표를 채운다.
4. 미수렴·미달·정정은 fail loud로 표기, 최종 판정(PASS/FAIL/추가검증필요).

> FEM/FEniCSx 해석 검증 전용. 일반 테스트는 OMC `verifier`를 사용.

입력: `$ARGUMENTS` (결과 dir 또는 검증 대상 양·단계 ID).
