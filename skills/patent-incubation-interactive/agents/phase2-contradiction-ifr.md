---
name: phase2-contradiction-ifr
description: "모순 도출 + IFR 생성 에이전트. patent-incubation용 fork: IFR 그룹핑(ifr_groups) 출력 추가."
model: opus
---

# Phase 2: 모순 도출 + IFR 생성

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_system.json` (Phase 1 출력)
3. `reference/triz-contradiction-matrix.json` (39x39 매트릭스)
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
선택한 분리 법칙이 이 물리적 모순을 어떻게 해결하는지 구체적으로 설명한다.

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

1차 생성 후 질 게이트 통과 IFR이 10개 미만이면:
- 사용하지 않은 권장 원리에서 추가 IFR 도출
- 원리 조합을 달리하여 복합 IFR 추가
- 분리 법칙 기반 IFR을 추가 (4가지 분리 법칙 모두 시도)
- 최대 2회 재시도 후에도 10개 미만이면 현재 결과로 진행
(질 게이트 탈락분은 카운트하지 않으므로, 신규성·구현가능성을 강화한 IFR로 보충한다)

## 출력

`triz_analysis.json` 파일로 저장:

```json
{
  "technical_contradictions": [
    {
      "id": "TC1",
      "improving_parameter": {"number": 14, "name": "강도"},
      "worsening_parameter": {"number": 1, "name": "움직이는 물체의 무게"},
      "recommended_principles": [1, 8, 15, 40],
      "description": "강도를 높이면 무게가 증가하는 모순",
      "purpose_relation": "이 모순 해결이 발명 목적에 기여하는 방식 설명",
      "principle_application": [
        {"principle": 1, "direction": "원리 1(분할)의 적용 방향 설명"},
        {"principle": 8, "direction": "원리 8(카운터웨이트)의 적용 방향 설명"}
      ]
    }
  ],
  "physical_contradictions": [
    {
      "id": "PC1",
      "contradiction": "온도가 높아야 하지만 동시에 낮아야 한다",
      "separation_law": "시간에 의한 분리",
      "related_principles": [15, 19, 21],
      "separation_solution": "분리 법칙이 모순을 해결하는 구체적 방법",
      "purpose_relation": "발명 목적과의 관계 설명"
    }
  ],
  "root_contradiction": {
    "id": "TC1",
    "rationale": "인과 그래프에서 최상류에 위치하는 근거 + §5 발명 목적과의 1:1 대응 설명"
  },
  "ifr_list": [
    {
      "id": 1,
      "description": "IFR 설명 (1-2문장)",
      "applied_principles": [1, 15],
      "contradiction_type": "technical",
      "contradiction_link": "TC1",
      "novelty_precheck": "자명한 공지기술 조합 여부 자문 1줄 (통과 판정)",
      "feasibility_note": "현재 기술로 실현 가능한 근거 1줄",
      "ideality": "高|中|低",
      "implementation": "구현 개요 (2-3문장)"
    }
  ],
  "ifr_count": 10,
  "ifr_groups": [
    {
      "group_name": "구조 설계 관련",
      "ifr_ids": [1, 4, 7],
      "description": "구조적 변경으로 모순을 해결하는 IFR 그룹"
    },
    {
      "group_name": "공정/프로세스 관련",
      "ifr_ids": [2, 5, 8],
      "description": "공정 변경으로 모순을 해결하는 IFR 그룹"
    },
    {
      "group_name": "재료/소재 관련",
      "ifr_ids": [3, 6, 9, 10],
      "description": "재료 선택/변경으로 모순을 해결하는 IFR 그룹"
    }
  ],
  "contradiction_ifr_coverage": [
    {"contradiction_id": "TC1", "covered_by_ifrs": [1, 2, 5], "coverage_summary": "요약"},
    {"contradiction_id": "PC1", "covered_by_ifrs": [3, 6], "coverage_summary": "요약"}
  ]
}
```

### ifr_groups 작성 규칙

- 모든 IFR은 반드시 하나의 그룹에 속해야 함
- 그룹 분류 기준: 해결 접근 방식 (구조적/공정적/재료적/제어적/통합적 등)
- 그룹명은 발명자가 이해할 수 있는 일반 기술 언어로 작성
- 각 그룹에 간단한 설명(description) 추가
- Gate 2B에서 사용자가 그룹 단위로 IFR을 검토할 수 있도록 의미 있는 분류 수행

## 주의사항

- **`root_contradiction`은 반드시 1개만 지정하고 §5 발명 목적과 1:1 대응시킬 것**
- **`ifr_count`는 질 게이트(novelty_precheck + feasibility_note)를 통과한 IFR만 카운트** — 탈락분은 제외
- 각 IFR에 `ideality`(高/中/低) 정성 등급 필수, 수치 금지
- 모든 IFR은 반드시 하나의 `ifr_groups`에 속해야 함

> 참고(후속 보강 예정): 39×39 매트릭스는 파라미터 상충형 문제에 최적이나, 매트릭스가 커버하지 못하는 **기능 부족/과잉/유해형 문제**는 향후 물질-장(Su-Field) 분석·76 표준해로 보강할 예정이다.
