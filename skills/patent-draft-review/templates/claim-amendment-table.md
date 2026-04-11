<!-- claim-amendment-table.md — 청구항 보정안 비교표 템플릿

용도: phase3-claim-structure + phase4-prior-art-diff 에이전트가 본 템플릿을 사용하여
     독립항 보정안의 "현행 vs 보정안 A/B/C/D" 비교표를 생성한다.

출력 위치: 개선방안 MD §6.2 (독립항 보정안 블록)

보정안 분류:
- A: 기저 변환부 등 "기준면/위치" 관련 한정 추가 (최소 한정)
- B: 수차 연산부 등 "연산 방식" 관련 한정 추가
- C: A + 추가 한정 (독립항 A의 확장)
- D: 수차 연산부 등 "독립 연산" 관련 명시 (단일 패스와 구조적 분리)

권리범위 영향:
🟢 넓음 | 🟡 적정 | 🔴 좁음
-->

### 6.2 독립항 긴급 보정안 ({{reason_label}})

> [!danger] v{{version}} 결정
> {{rationale_paragraph}}

#### 6.2.1 보정안 A — {{amendment_A_name}} ({{priority_A}})

**제{{independent_system_claim_num}}항 (시스템) 문언 변경**:

| 구분 | 문언 |
|------|------|
| **현행** | "{{current_system_text}}" |
| **보정 A** | "{{amendment_A_system_text}}" |

**제{{independent_method_claim_num}}항 (방법) 문언 변경**:

| 구분 | 문언 |
|------|------|
| **현행** | "{{current_method_text}}" |
| **보정 A** | "{{amendment_A_method_text}}" |

**근거**: {{amendment_A_rationale}}

---

#### 6.2.2 보정안 B — {{amendment_B_name}} ({{priority_B}})

**제{{independent_system_claim_num}}항 (시스템) 문언 변경**:

| 구분 | 문언 |
|------|------|
| **현행** | "{{current_system_text_B}}" |
| **보정 B** | "{{amendment_B_system_text}}" |

**근거**: {{amendment_B_rationale}}

---

#### 6.2.3 보정안 C — {{amendment_C_name}} ({{priority_C}})

**제{{independent_system_claim_num}}항 (시스템) 문언 변경**:

| 구분 | 문언 |
|------|------|
| **현행** | "{{current_system_text_C}}" |
| **보정 C** | "{{amendment_C_system_text}}" |

**근거**: {{amendment_C_rationale}}

---

#### 6.2.4 보정안 D — {{amendment_D_name}} ({{priority_D}})

**제{{independent_system_claim_num}}항 (시스템) 문언 변경**:

| 구분 | 문언 |
|------|------|
| **현행** | "{{current_system_text_D}}" |
| **보정 D** | "{{amendment_D_system_text}}" |

**근거**: {{amendment_D_rationale}}

---

#### 6.2.5 보정안 조합 선택지

| 조합 | 문언 범위 | 진보성 | 권리범위 | 권고 |
|------|-----------|--------|----------|------|
| A만 | {{scope_A}} | {{inventiveness_A}} | 🟢 넓음 | 🟡 최소 필수 |
| B만 | {{scope_B}} | {{inventiveness_B}} | 🟡 적정 | 🟡 선택적 |
| C만 | {{scope_C}} | {{inventiveness_C}} | 🟡 적정 | 🟡 선택적 |
| D만 | {{scope_D}} | {{inventiveness_D}} | 🔴 좁음 | 🟡 선택적 |
| **{{recommended_combo}}** | {{recommended_scope}} | **강** | {{recommended_range}} | 🔴 **권고 (필수)** |

> [!tip] 권리범위 vs 진보성 트레이드오프
> - **넓은 권리범위**를 원한다면 보정안 A만 적용 (최소 한정)
> - **강한 진보성 방어**를 원한다면 {{recommended_combo}} 조합 (다층 방어)
> - 심사관의 인용 가능성이 높은 경우 **강한 조합 우선**

---

<!-- TEMPLATE USAGE NOTES

사용 예시 (P26057KR1 케이스 기반):
- amendment_A_name: "기저 변환부에 '장벽 근처 공액면' 명시"
- amendment_A_system_text:
    "상기 반사행렬을 개별 송신기저 및/또는 개별 수신기저로 변환하고,
     상기 대상체의 장벽 근처에 정의된 공액면을 기준으로 상기 반사행렬을
     공액면 기준 행렬로 변환하는 기저 변환부"
- amendment_D_name: "수차 연산부에 'Tx/Rx 독립 위상차' 명시"
- amendment_D_system_text:
    "상기 이미지 기반 행렬에 포함된 기저 이미지와 참조 이미지 사이의
     상관성으로부터, 송신기저에 대한 위상차와 수신기저에 대한 위상차를
     독립적으로 연산하는 수차 연산부"
- recommended_combo: "A + D"
- recommended_scope: "장벽 근처 공액면 + Tx/Rx 독립 연산"

priority 표기:
- 필수 긴급 = 🔴🔴
- 필수 = 🔴
- 강력 권고 = 🔴
- 권고 = 🟡
- 선택 = 🟢
-->
