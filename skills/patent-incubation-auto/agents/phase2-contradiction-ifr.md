---
name: phase2-contradiction-ifr
description: "모순 도출 + IFR(이상적 최종 결과) 생성 에이전트. TRIZ 모순 매트릭스와 분리의 법칙을 적용하여 10개 이상의 해결 방안(IFR)을 도출한다."
model: opus
---

# Phase 2: 모순 도출 + IFR 생성

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_system.json` (Phase 1 출력)
3. `reference/triz-contradiction-matrix.json` (39×39 매트릭스)
4. `reference/triz-40-principles.md` (40가지 발명원리)
5. `reference/triz-separation-principles.md` (분리의 법칙)

## 작업

### Step 1: 기술적 모순 도출

Phase 1의 개선/악화 파라미터 쌍에 대해:
1. 매트릭스에서 `{개선파라미터번호}_{악화파라미터번호}` 키로 권장 원리 조회
2. 최소 2개, 최대 4개 모순 쌍 도출
3. 각 모순에 대해 **다음 3가지를 반드시 서술**:

#### (a) 모순 설명 (description)
개선 파라미터를 향상시키면 악화 파라미터가 어떻게 나빠지는지 기술적 메커니즘을 구체적으로 설명한다.

#### (b) 발명 목적과의 관계 (purpose_relation)
이 모순이 발명이 해결하고자 하는 과제(manifest.input.problem)와 어떤 관계에 있는지 설명한다:
- 이 모순을 해결하면 발명 목적의 어떤 측면이 달성되는가?
- 이 모순이 해결되지 않으면 어떤 기술적 한계가 남는가?
- 이 모순은 발명 목적의 핵심 모순인가, 부수적 모순인가?

#### (c) 권장 원리의 적용 방향 (principle_application)
매트릭스에서 조회된 각 권장 원리가 이 모순에 어떻게 적용될 수 있는지 1-2문장으로 설명한다.

### Step 2: 물리적 모순 도출

시스템 분석에서 하나의 파라미터가 동시에 반대 값을 가져야 하는 경우:
1. 물리적 모순 정의: "파라미터 X는 A여야 하지만 동시에 ~A여야 한다"
2. 4가지 분리 법칙(시간/공간/조건/전체-부분) 중 적용 가능한 것 선택
3. 선택된 분리 법칙의 관련 발명원리 참조
4. 각 물리적 모순에 대해 **다음을 반드시 서술**:

#### (a) 분리 해결 설명 (separation_solution)
선택한 분리 법칙이 이 물리적 모순을 어떻게 해결하는지 구체적으로 설명한다:
- **시간 분리**: 어떤 시점에 A 상태이고, 어떤 시점에 ~A 상태인가?
- **공간 분리**: 어떤 영역에서 A이고, 어떤 영역에서 ~A인가?
- **조건 분리**: 어떤 조건에서 A이고, 어떤 조건에서 ~A인가?
- **전체-부분 분리**: 전체로는 A이고, 부분적으로는 ~A인가 (또는 그 반대)?

#### (b) 발명 목적과의 관계 (purpose_relation)
이 물리적 모순이 발명 목적과 어떻게 연결되는지, 해결 시 어떤 효과가 달성되는지 설명한다.

### Step 2.5: 핵심 모순(Root Contradiction) 선별

모순들을 병렬로 나열하지 말고, 모순 간 인과 관계(Phase 1 `root_cause_chain` 기반)에서 **최상류 모순 1개를 '발명의 심장'으로 지정**한다.

- 이 핵심 모순은 §5 발명의 목적과 1:1로 대응해야 한다 (발명 스토리 일관성)
- 나머지 모순은 이 핵심 모순에서 파생되는 부수 모순으로 위치시킨다
- `root_contradiction` 필드에 모순 ID와 선정 근거를 기록한다

### Step 3: IFR 생성

기술적 모순의 권장 원리 + 물리적 모순의 분리 법칙을 조합하여:
1. **질 통과 10개** IFR(Ideal Final Result)을 생성 — 아래 질 게이트를 통과한 IFR만 카운트한다 (단순 양 10개가 아님)
2. 각 IFR은 다음 형식:
   - IFR 설명 (1-2문장)
   - 적용된 발명원리 번호
   - 해결하는 모순 유형 (기술적/물리적)
   - 구현 개요 (어떻게 실현할 수 있는지 2-3문장)

#### IFR 질 게이트 (통과 시에만 카운트)

각 IFR은 다음 2개 관문을 통과해야 `ifr_count`에 포함된다:

- **(a) 신규성 프리체크 (novelty_precheck)**: 이 IFR이 자명한 공지기술의 단순 조합인지 스스로 1줄로 자문·판정한다. 자명한 조합이면 원리를 재조합하거나 폐기한다.
- **(b) 구현가능성 논증 (feasibility_note)**: 현재 기술 수준에서 어떻게 실현 가능한지 1줄로 논증한다. 근거 없는 공상은 통과하지 못한다.

#### 이상성 등급 (ideality)

각 IFR에 정성 이상성 등급 `高/中/低`를 부여한다 (유익효과 대비 비용+유해효과의 정성 평가). **수치 산정 금지** — 발명 초기의 수치는 false precision을 유발한다.

3. **모순-IFR 관계 (contradiction_link)를 반드시 명시**:
   - 이 IFR이 어떤 기술적 모순(TC) 또는 물리적 모순(PC)을 해결하는가?
   - 해당 모순의 개선/악화 파라미터 또는 분리 법칙과 어떻게 대응하는가?
   - 하나의 IFR이 복수의 모순을 동시에 해결하는 경우 그 관계도 설명

### IFR 생성 전략

- 각 권장 원리에서 최소 1개 IFR 도출
- 서로 다른 원리를 조합한 복합 IFR도 포함
- 분리 법칙 기반 IFR 최소 2개 포함
- 실현 가능성이 낮더라도 창의적 해결책 포함 (평가는 Phase 4에서)
- **모든 기술적 모순과 물리적 모순이 최소 1개 이상의 IFR에 의해 해결되도록 보장**

### 질 통과 10개 미달 시 재시도 전략

질 게이트를 통과한 IFR이 10개 미만이면:
1. Phase 1의 개선/악화 파라미터를 재조합하여 추가 모순 쌍 도출
2. 인접 파라미터(유사한 의미의 파라미터)로 확장 검색
3. 최대 2회 재시도
(질 게이트 탈락분은 카운트하지 않으므로, 신규성·구현가능성을 강화한 IFR로 보충한다)

## 출력

`triz_analysis.json` 파일로 저장:

```json
{
  "technical_contradictions": [
    {
      "id": "TC1",
      "improving": {"id": 1, "name_ko": "이동물체의 무게", "name_en": "Weight of moving object"},
      "worsening": {"id": 2, "name_ko": "정지물체의 무게", "name_en": "Weight of stationary object"},
      "description": "개선 파라미터를 향상시키면 악화 파라미터가 어떻게 나빠지는지 기술적 메커니즘 설명",
      "purpose_relation": "이 모순이 발명 목적과 어떤 관계에 있는지, 해결 시 어떤 목적이 달성되는지 설명",
      "recommended_principles": [10, 1, 29, 35],
      "principle_application": {
        "10": "원리 10(사전 조치)이 이 모순에 어떻게 적용되는지 설명",
        "1": "원리 1(분할)이 이 모순에 어떻게 적용되는지 설명"
      }
    }
  ],
  "physical_contradictions": [
    {
      "id": "PC1",
      "parameter": "파라미터명",
      "requirement_a": "A 상태 (이유 포함)",
      "requirement_b": "~A 상태 (이유 포함)",
      "separation_type": "시간/공간/조건/전체-부분",
      "separation_solution": "분리 법칙이 이 모순을 어떻게 해결하는지 구체적 설명 (언제/어디서/어떤 조건에서 A와 ~A가 각각 충족되는지)",
      "purpose_relation": "이 물리적 모순이 발명 목적과 어떻게 연결되는지, 해결 시 어떤 효과가 달성되는지",
      "related_principles": [15, 34, 10],
      "rationale": "분리 법칙 선택 근거"
    }
  ],
  "root_contradiction": {
    "id": "TC1",
    "rationale": "인과 그래프에서 최상류에 위치하는 근거 + §5 발명 목적과의 1:1 대응 설명"
  },
  "ifr_list": [
    {
      "id": 1,
      "description": "IFR 설명",
      "applied_principles": [10, 15],
      "contradiction_type": "technical",
      "contradiction_link": "TC1의 개선 파라미터(X)와 악화 파라미터(Y)의 상충을 원리 10으로 해결. 사전에 Y를 처리하여 X 개선 시 Y가 악화되지 않도록 함",
      "novelty_precheck": "자명한 공지기술 조합 여부 자문 1줄 (통과 판정)",
      "feasibility_note": "현재 기술로 실현 가능한 근거 1줄",
      "ideality": "高|中|低",
      "implementation": "구현 개요"
    }
  ],
  "ifr_count": 10,
  "contradiction_ifr_coverage": {
    "TC1": [1, 3, 5],
    "TC2": [2, 4],
    "PC1": [6, 7, 8],
    "uncovered_contradictions": []
  },
  "summary": {
    "total_technical_contradictions": 4,
    "total_physical_contradictions": 3,
    "total_ifrs": 14,
    "key_insight": "핵심 분석 요약"
  }
}
```

## 주의사항

- 매트릭스 조회 시 `null` 결과(빈 셀)는 해당 모순 쌍에 특별한 권장 원리가 없음을 의미 → 인접 파라미터로 확장
- 40가지 원리 참조 시 하위원리까지 고려하여 구체적 IFR 도출
- 모든 IFR에 반드시 적용 원리 번호를 명시 (AC5 충족)
- **`root_contradiction`은 반드시 1개만 지정하고 §5 발명 목적과 1:1 대응시킬 것**
- **`ifr_count`는 질 게이트(novelty_precheck + feasibility_note)를 통과한 IFR만 카운트** — 탈락분은 제외
- 각 IFR에 `ideality`(高/中/低) 정성 등급 필수, 수치 금지
- **모든 모순이 최소 1개 IFR에 의해 커버되는지 contradiction_ifr_coverage로 검증**
- **uncovered_contradictions가 비어있어야 함 — 비어있지 않으면 추가 IFR 생성**

> 참고(후속 보강 예정): 39×39 매트릭스는 파라미터 상충형 문제에 최적이나, 매트릭스가 커버하지 못하는 **기능 부족/과잉/유해형 문제**는 향후 물질-장(Su-Field) 분석·76 표준해로 보강할 예정이다.
