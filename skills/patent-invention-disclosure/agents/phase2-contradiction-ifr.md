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
2. 각 모순 쌍에 대해 `{개선 파라미터, 악화 파라미터, 권장 원리 번호[]}` 형태로 기록
3. 최소 2개, 최대 4개 모순 쌍 도출

### Step 2: 물리적 모순 도출

시스템 분석에서 하나의 파라미터가 동시에 반대 값을 가져야 하는 경우:
1. 물리적 모순 정의: "파라미터 X는 A여야 하지만 동시에 ~A여야 한다"
2. 4가지 분리 법칙(시간/공간/조건/전체-부분) 중 적용 가능한 것 선택
3. 선택된 분리 법칙의 관련 발명원리 참조

### Step 3: IFR 생성

기술적 모순의 권장 원리 + 물리적 모순의 분리 법칙을 조합하여:
1. **최소 10개** IFR(Ideal Final Result)을 생성
2. 각 IFR은 다음 형식:
   - IFR 설명 (1-2문장)
   - 적용된 발명원리 번호
   - 해결하는 모순 유형 (기술적/물리적)
   - 구현 개요 (어떻게 실현할 수 있는지 2-3문장)

### IFR 생성 전략

- 각 권장 원리에서 최소 1개 IFR 도출
- 서로 다른 원리를 조합한 복합 IFR도 포함
- 분리 법칙 기반 IFR 최소 2개 포함
- 실현 가능성이 낮더라도 창의적 해결책 포함 (평가는 Phase 4에서)

### 10개 미달 시 재시도 전략

만약 도출된 IFR이 10개 미만이면:
1. Phase 1의 개선/악화 파라미터를 재조합하여 추가 모순 쌍 도출
2. 인접 파라미터(유사한 의미의 파라미터)로 확장 검색
3. 최대 2회 재시도

## 출력

`triz_analysis.json` 파일로 저장:

```json
{
  "technical_contradictions": [
    {
      "improving": {"id": 1, "name_ko": "이동물체의 무게", "name_en": "Weight of moving object"},
      "worsening": {"id": 2, "name_ko": "정지물체의 무게", "name_en": "Weight of stationary object"},
      "recommended_principles": [10, 1, 29, 35]
    }
  ],
  "physical_contradictions": [
    {
      "parameter": "파라미터명",
      "requirement_a": "A 상태",
      "requirement_b": "~A 상태",
      "separation_type": "시간/공간/조건/전체-부분",
      "related_principles": [15, 34, 10]
    }
  ],
  "ifr_list": [
    {
      "id": 1,
      "description": "IFR 설명",
      "applied_principles": [10, 15],
      "contradiction_type": "technical",
      "implementation": "구현 개요"
    }
  ],
  "ifr_count": 10
}
```

## 주의사항

- 매트릭스 조회 시 `null` 결과(빈 셀)는 해당 모순 쌍에 특별한 권장 원리가 없음을 의미 → 인접 파라미터로 확장
- 40가지 원리 참조 시 하위원리까지 고려하여 구체적 IFR 도출
- 모든 IFR에 반드시 적용 원리 번호를 명시 (AC5 충족)
