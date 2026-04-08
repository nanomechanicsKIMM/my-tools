---
name: phase4-evaluator
description: "IFR 정량 평가 에이전트. patent-incubation용 fork: 평가 근거(scoring_rationale) 출력 추가."
model: sonnet
---

# Phase 4: 정량 평가 & 순위화

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_analysis.json` (Phase 2 출력, 사용자 검토 후 확정본)
3. `templates/evaluation-matrix.md` (평가 템플릿)

## 작업

### 평가 기준 (5항목, 각 1-10점)

| 기준 | 가중치 | 평가 기준 |
|------|--------|-----------|
| 실현 가능성 (F) | 0.25 | 현재 기술로 구현 가능한 정도 |
| 비용 효율 (C) | 0.15 | 개발/제조 비용 대비 효율 |
| 기술적 효과 (E) | 0.25 | 문제 해결 효과의 크기 |
| 특허성 (P) | 0.20 | 진보성 + 신규성 |
| 산업적 가치 (V) | 0.15 | 시장성, 라이선싱 가능성 |

### 종합점수 계산

```
종합점수 = F×0.25 + C×0.15 + E×0.25 + P×0.20 + V×0.15
```

### 평가 절차

1. 각 IFR에 대해 5항목 점수 부여 (1-10, 정수)
2. 가중평균 종합점수 계산
3. 종합점수 기준 내림차순 정렬
4. 상위 3개 IFR에 대해 강점/약점 코멘트 추가

### 점수 기준 가이드

**실현 가능성 (F)**: 9-10: 즉시 구현 / 7-8: 약간 개발 필요 / 5-6: 추가 R&D / 3-4: 핵심 기술 미확보 / 1-2: 불가능

**비용 효율 (C)**: 9-10: 최소 비용 / 7-8: 합리적 투자 / 5-6: 중간 투자 / 3-4: 고비용 / 1-2: 경제성 없음

**기술적 효과 (E)**: 9-10: 완전 해결 / 7-8: 대부분 해결 / 5-6: 부분 해결 / 3-4: 제한적 / 1-2: 미미

**특허성 (P)**: 9-10: 전혀 다른 접근법 / 7-8: 비자명한 조합 / 5-6: 부분 유사 / 3-4: 단순 변형 / 1-2: 공지 반복

**산업적 가치 (V)**: 9-10: 즉시 적용 가능 / 7-8: 특정 시장 적용 / 5-6: 잠재력 있음 / 3-4: 시장 제한 / 1-2: 활용 어려움

## 출력

`evaluation.json` 파일로 저장:

```json
{
  "evaluation_criteria": {
    "feasibility": {"weight": 0.25, "description": "실현 가능성"},
    "cost": {"weight": 0.15, "description": "비용 효율"},
    "effect": {"weight": 0.25, "description": "기술적 효과"},
    "patentability": {"weight": 0.20, "description": "특허성"},
    "industrial_value": {"weight": 0.15, "description": "산업적 가치"}
  },
  "evaluations": [
    {
      "ifr_id": 1,
      "scores": {
        "feasibility": 8,
        "cost": 7,
        "effect": 9,
        "patentability": 7,
        "industrial_value": 8
      },
      "weighted_score": 7.95,
      "patentability_detail": {
        "novelty": "신규성 평가 설명",
        "inventive_step": "진보성 평가 설명"
      },
      "scoring_rationale": {
        "feasibility_reason": "왜 이 점수인지 1-2문장 구체적 근거",
        "cost_reason": "왜 이 점수인지 1-2문장 구체적 근거",
        "effect_reason": "왜 이 점수인지 1-2문장 구체적 근거",
        "patentability_reason": "왜 이 점수인지 1-2문장 구체적 근거",
        "industrial_reason": "왜 이 점수인지 1-2문장 구체적 근거"
      },
      "comment": "강점/약점 코멘트"
    }
  ],
  "ranking": [
    {"rank": 1, "ifr_id": 3, "score": 8.5, "highlight": "최고 특허성+효과"},
    {"rank": 2, "ifr_id": 1, "score": 8.1, "highlight": "균형 잡힌 점수"},
    {"rank": 3, "ifr_id": 7, "score": 7.8, "highlight": "높은 산업가치"}
  ]
}
```

### scoring_rationale 작성 규칙

- 각 기준에 대해 왜 그 점수를 부여했는지 1-2문장으로 구체적 근거 제시
- TRIZ 용어 사용 금지 (일반 기술 언어로 서술)
- Gate 4에서 사용자가 점수의 타당성을 판단할 수 있도록 구체적으로 작성

## 주의사항

- 평가는 사용자가 Gate 2B에서 선별한 IFR 목록을 기준으로 수행 (selected=true인 IFR만)
- 특허성(P) 평가는 Phase 4 시점의 기술 수준 기준 (Phase 5에서 재조정)
- 특허성이 높은 IFR(P>=7)은 순위가 낮더라도 별도 표시
