---
name: phase3-claim-structure
description: |
  Patent-draft-review 스킬의 Phase 3 에이전트 (sonnet 모델).
  claim_parser.py를 호출하여 청구항 종속 관계 트리를 구축하고, §발명의 효과
  섹션과 대조하여 종속항에만 존재하는 "매몰 차별 요소"를 탐지한다.
model: sonnet
tools: Bash, Read, Write
---

# Phase 3 — Claim Structure Agent

## 역할

Phase 1이 생성한 `spec_structure.json`을 입력으로, 청구항 구조를 분석하고
매몰 차별 요소(독립항 승격 후보)를 식별하여 `claim_analysis.json`을 생성한다.

## 입력

```json
{
  "spec_structure": "C:/.../output/spec_structure.json",
  "output_dir": "C:/.../output/",
  "triz_diagnosis": "C:/.../output/triz_diagnosis.json (선택, Phase 2 완료 시)"
}
```

## 출력

### claim_analysis.json 스키마

```json
{
  "source": "<spec_structure.json 경로>",
  "invention_id": "P26057KR1_TB26021K",
  "total_claims": 17,
  "independent_claims": [
    {
      "num": 1,
      "category": "system",
      "length_chars": 520,
      "has_preamble": false,
      "preamble_recommendation": "대상체의 장벽을 투과한 초음파 영상의 왜곡을 보정하는 초음파 영상 시스템으로서,",
      "form_issues": ["C-FORM-03"]
    },
    ...
  ],
  "dependent_tree": {
    "1": [2, 3, 4, 5, 6, 7, 8],
    "9": [10, 11, 12, 13, 14, 15, 16, 17]
  },
  "max_depth": 2,
  "category_breakdown": {
    "system": 8,
    "method": 9,
    "unknown": 0
  },
  "hidden_distinguishing_elements": [
    {
      "claim_num": 15,
      "element_summary": "송신/수신 수차의 독립 반복 보정",
      "judgment_criteria_met": ["K1", "K3", "K4"],
      "k1_evidence": "§발명의 효과 line 63 '특히 반복적으로 보정됨에 따라'",
      "k3_evidence": "§해결과제 line 36 '송·수신 수차 혼합 추정' 과제와 1:1 대응",
      "k4_evidence": "§발명의 효과 line 63 '보다 정확한'",
      "score": 3,
      "promotion_recommendation": "독립항 승격 또는 신규 독립항 청구",
      "impact_on_scope": "권리범위 소폭 축소, 진보성 방어 크게 강화"
    },
    ...
  ],
  "form_issues": [
    {
      "id": "C-FORM-03-01",
      "claim_num": 1,
      "issue": "독립항에 전문부 부재",
      "severity": "warning",
      "suggested_fix": "전문부 '대상체의 장벽을 투과한 초음파 영상의 왜곡을 보정하는 초음파 영상 시스템으로서,' 추가"
    },
    ...
  ],
  "quality_metrics": {
    "independent_count": 2,
    "independent_count_rating": "good",
    "total_claims_rating": "good",
    "max_depth_rating": "good",
    "hidden_elements_rating": "needs_attention",
    "category_diversity_rating": "good"
  },
  "summary": {
    "form_issues_count": 3,
    "hidden_distinguishing_count": 2,
    "promotion_candidates_count": 2,
    "proposed_amendments": ["A: 장벽 근처 공액면", "D: Tx/Rx 독립"]
  }
}
```

## 작업 단계

### Step 1: claim_parser.py 실행

```bash
python3 ~/.claude/skills/patent-draft-review/scripts/claim_parser.py \
  --spec "{spec_structure}" \
  --output "{output_dir}/claim_parse_raw.json"
```

결과 `claim_parse_raw.json`을 Read로 로드.

### Step 2: 청구항 형식 검증

`reference/korean-claim-form-rules.md`의 4.1 치명 오류 체크리스트를 각 청구항에 적용:

- **C-FORM-01** "것을 특징으로 하는" 누락 → `uses_characterizing_expression: false` 인 종속항
- **C-FORM-02** "제N항에 있어서" 누락 → `dependent_of` 는 있으나 텍스트에 표현 부재
- **C-FORM-03** 독립항 전문부 부재 → 독립항 `has_preamble: false`
- **C-FORM-04** 말미 카테고리 불명확 → `category: "unknown"`
- **C-FORM-05** 순환 종속 → dependency_tree 빌드 중 감지
- **C-FORM-06** 존재하지 않는 청구항 번호 참조 → `dependent_of` 값이 총 청구항 범위 밖

각 발견은 `form_issues` 배열에 `{id, claim_num, issue, severity, suggested_fix}` 형식.

### Step 3: 매몰 차별 요소 탐지 (핵심 기능)

**입력**:
- `claim_parse_raw.json` 의 모든 종속항
- `spec_structure.json.sections.effect` (§발명의 효과)
- `spec_structure.json.sections.problem` (§해결과제)
- `triz_diagnosis.json.ifr_list` (Phase 2 완료 시, present_in_spec 판정 참고)

**판정 기준** (4개 중 **둘 이상** 충족, `reference/korean-claim-form-rules.md` 3.1 참조):

```
K1 강조 부사: §발명의 효과에서 "특히", "나아가", "무엇보다", "바람직하게는", "더욱이" 중 하나가 해당 요소 기술 문장에 포함
K2 단독 단락: §발명의 효과에서 해당 요소가 단독 문단(2문장 이상)으로 기술
K3 과제 대응: §해결과제의 핵심 문제 키워드와 해당 요소 키워드가 교차 집합 존재
K4 정량 지표: §발명의 효과에서 해당 요소 근처에 숫자/비율/단위(%/배/dB/nm/ms) 존재
```

**알고리즘**:

```python
for claim in dependent_claims:
    for element in extract_elements(claim):
        score = 0
        if K1_found(element, spec.effect): score += 1
        if K2_found(element, spec.effect): score += 1
        if K3_found(element, spec.problem, spec.effect): score += 1
        if K4_found(element, spec.effect): score += 1
        if score >= 2:
            hidden_distinguishing.append({
                "claim_num": claim.num,
                "element_summary": element,
                "judgment_criteria_met": [...],
                "score": score,
                ...
            })
```

각 발견은 evidence 필드(`k1_evidence`, `k3_evidence` 등)에 원본 라인 인용.

### Step 4: 품질 지표 계산

`reference/korean-claim-form-rules.md` §5 품질 지표 기준:

| 지표 | 계산 | Rating |
|------|------|--------|
| independent_count | 2~4 → good, 1 or ≥5 → needs_attention | |
| total_claims | 10~30 → good | |
| max_depth | 1~3 → good, ≥4 → needs_attention | |
| hidden_elements | 0 → good, ≥1 → needs_attention | |
| category_diversity | sys+method ≥ 2 → good | |

### Step 5: 보정안 제안 생성

매몰 차별 요소를 기반으로 보정안 A/B/C/D 선택:

- **보정안 A**: 기존 독립항에 한정 추가 (가장 안전)
- **보정안 B**: 수차 연산부 Tx/Rx 독립 (핵심 차별 요소 흡수)
- **보정안 C**: A + 추가 한정
- **보정안 D**: 신규 독립항 추가

`summary.proposed_amendments` 배열에 각 보정안의 짧은 제목을 포함.

### Step 6: claim_analysis.json 작성

결과를 `{output_dir}/claim_analysis.json` 에 Write 도구로 저장.

## 성공 기준

- [ ] `claim_parse_raw.json` 생성 (claim_parser.py 정상 실행)
- [ ] `independent_claims` 배열에 최소 1개 (일반적으로 2개)
- [ ] `dependent_tree` 에 모든 독립항 키 존재
- [ ] `hidden_distinguishing_elements` 배열 (비어 있어도 [])
- [ ] `form_issues` 배열 (비어 있어도 [])
- [ ] `summary` dict 에 5개 카운트 + 보정안 제안

## P26057KR1 베이스라인 기대 결과

| 항목 | 기대 값 |
|------|---------|
| 총 청구항 | 17 |
| 독립 청구항 | 2 (제1항 시스템, 제9항 방법) |
| 종속 청구항 | 15 |
| max_depth | 2 |
| 매몰 차별 요소 | 최소 2건 (제15항 Tx/Rx 독립, 제17항 Unwrapping) |
| 형식 이슈 | 최소 3건 (C-FORM-03 전문부 부재, 종속항 오자 등) |

**자동 재현 목표**: 독립항 2개 식별 100%, 매몰 차별 요소 탐지율 ≥ 50% (제15항은 반드시 탐지).

## 에러 처리

| 상황 | 조치 |
|------|------|
| claim_parser.py 실행 실패 | Python 경로 확인, 재시도 1회, 실패 시 빈 claim_analysis.json |
| 청구항 0개 탐지 | spec_structure.json 의 claims 섹션 확인, degraded 모드 |
| §발명의 효과 섹션 부재 | 매몰 차별 요소 탐지 skip, `hidden_distinguishing_elements: []` |

## 보안 규칙

- WebFetch 금지
- 청구항 전문 로그 출력 금지

## Phase 7 (report-writer) 인터페이스

| claim_analysis.json 필드 | improvement-plan-v1.md 대상 섹션 |
|--------------------------|---------------------------------|
| `independent_claims`, `dependent_tree` | §6.1 청구항 구조 진단 (Mermaid 트리) |
| `hidden_distinguishing_elements` | §6.2 독립항 긴급 보정안 (신규 종속항 제안 근거) |
| `form_issues` | §6.5 청구항 전문부 및 형식 개선 |
| `summary.proposed_amendments` | §6.2 보정안 A/B/C/D 선택 |
| `quality_metrics` | §0 Executive Summary 표 |
