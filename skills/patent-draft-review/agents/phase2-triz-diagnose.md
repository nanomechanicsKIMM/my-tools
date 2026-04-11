---
name: phase2-triz-diagnose
description: |
  Patent-draft-review 스킬의 Phase 2 에이전트 (opus 모델).
  이미 작성된 특허 명세서를 TRIZ 진단 관점에서 분석하여 본 발명이 해결한 모순,
  남은 모순, 추가 IFR 후보를 도출한다. TRIZ 용어는 부록 A로 격리하여 본문에는
  일반 기술 용어만 사용한다.
model: opus
tools: Read, Write
---

# Phase 2 — TRIZ Diagnose Agent (진단 모드)

## 역할

이 에이전트는 **TRIZ 방법론을 진단 도구로 사용**하여 이미 작성된 특허 명세서를 분석한다. `patent-incubation-auto` 스킬의 **생성 모드**와 정반대 방향으로 작동한다:

| 구분 | 생성 모드 (patent-incubation-auto) | 진단 모드 (본 에이전트) |
|------|-----------------------------------|-------------------------|
| 방향 | 아이디어 → TRIZ 분석 → 새 발명 | 기존 발명 → TRIZ 진단 → 개선 방향 |
| 목표 | 신규 발명내용설명서 생성 | 명세서의 TRIZ 완결성 점검 |
| IFR | 신규 발명 컨셉 도출 | 이미 해결한 모순 vs 남은 모순 분리 |

## 입력

```json
{
  "spec_structure": "C:/.../output/spec_structure.json",
  "output_dir": "C:/.../output/",
  "triz_references": {
    "principles": "C:/Users/JHKIM/.claude/skills/patent-draft-review/reference/triz-40-principles.md",
    "contradiction_matrix": "C:/.../reference/triz-contradiction-matrix.json",
    "separation_principles": "C:/.../reference/triz-separation-principles.md"
  }
}
```

## 출력

### triz_diagnosis.json 스키마

```json
{
  "source": "<spec_structure.json 경로>",
  "invention_id": "P26057KR1_TB26021K",
  "analyzed_at": "2026-04-11T00:00:00",
  "system_components": {
    "mermaid_map": "graph TB\n  A[초음파 프로브 200] --> B[대상체 100]\n  ...",
    "components": [
      {"name": "초음파 프로브", "ref": "200", "role": "송수신"},
      ...
    ]
  },
  "useful_functions": [
    "장벽 투과 초음파 영상 획득",
    "위치 의존적 수차 정밀 추정",
    ...
  ],
  "harmful_effects": [
    "위상 wrapping으로 인한 누적 지연 손실",
    "송·수신 수차 상호 오염",
    ...
  ],
  "technical_contradictions": [
    {
      "id": "TC1",
      "improving_parameter": "복원 가능 영역",
      "worsening_parameter": "장벽 투과 경로 왜곡",
      "description": "복원 영역을 확장하려면 장벽 투과 경로가 증가하여 왜곡 증대",
      "already_solved": true,
      "solution_in_spec": "공액면을 장벽 근처로 이동 (§구체적 내용, §청구항 4)",
      "applied_principle_numbers": [24, 15],
      "applied_principle_names": ["매개체", "역동성"]
    },
    {
      "id": "TC5",
      "improving_parameter": "참조 이미지 SNR",
      "worsening_parameter": "초기 장벽 수차로 흐림",
      "already_solved": false,
      "solution_candidate": "참조 이미지 반복 갱신 (본문 line 158에만 언급, 청구항 누락)",
      "applied_principle_numbers": [15, 23]
    }
  ],
  "physical_contradictions": [
    {
      "id": "PM1",
      "statement": "수차 계산 기준면은 장벽에 있어야 한다 vs 프로브는 장벽에 있을 수 없다",
      "separation_principle": "공간 분리",
      "already_solved": true,
      "solution_in_spec": "가상의 공액면 도입"
    },
    ...
  ],
  "ifr_list": [
    {
      "id": "IFR-1",
      "summary": "공액면이 장벽 형상에 자기 적응하여 최적 위치 자동 결정",
      "solves_contradictions": ["TC1", "PM1"],
      "applied_principles": [15, 24],
      "claimability": "high",
      "claim_proposal": "반복 과정에서 복원 이미지 품질 지표 변화를 피드백하여 공액면 위치/형상을 자동 갱신하는 종속항",
      "present_in_spec": false
    },
    ...
  ],
  "diagnosis_summary": {
    "solved_contradictions_count": 4,
    "remaining_contradictions_count": 2,
    "ifr_count": 10,
    "ifr_present_in_spec": 4,
    "ifr_missing_from_spec": 6,
    "recommended_new_dependent_claims": 6
  }
}
```

## 작업 단계

### Step 1: 입력 로드

1. `spec_structure.json` 을 Read 도구로 로드
2. 아래 섹션을 추출:
   - `sections.tech_field` — 기술분야
   - `sections.problem` — 해결과제 (해결해야 할 모순의 단서)
   - `sections.solution` — 해결수단 (이미 해결된 모순의 증거)
   - `sections.effect` — 발명의 효과 (이미 해결된 모순의 결과)
   - `sections.detailed` — 구체적 내용 (시스템 구성요소 맵 추출 소스)
   - `claims_parsed` — 청구항 (이미 청구된 구성요소)
3. TRIZ 레퍼런스 3종 (40 원리, 모순 매트릭스, 분리 원리) 로드

### Step 2: 시스템 구성요소 맵 추출

`sections.detailed` 에서 도면 설명과 부호의 설명을 결합하여 시스템 구성요소 그래프 구축:

- 각 구성요소(구성요소명, 부호, 역할) 추출
- 구성요소 간 관계 (입력→처리→출력) 식별
- Mermaid `graph TB` 로 시각화 가능한 형태로 변환

### Step 3: 유용 기능 vs 유해 작용 분리

- 유용 기능: `sections.effect` 에서 "~할 수 있다", "~개선된다" 등 긍정 효과 문장 추출
- 유해 작용: `sections.problem` 에서 "~문제", "~한계" 등 부정 효과 문장 추출 + `sections.effect` 에서 언급되지 않은 남은 부작용 식별

### Step 4: 기술적 모순 도출 (최소 4건)

**진단 포인트**: 본 발명이 **이미 해결한** 모순 + **여전히 남은** 모순을 구분.

1. `sections.problem` 의 문제 진술에서 개선 파라미터 / 악화 파라미터 추출
2. TRIZ 모순 매트릭스(`triz-contradiction-matrix.json`)와 매칭하여 권장 40 원리 번호 추출
3. `sections.solution` + `claims_parsed` 에서 해당 모순이 해결되었는지 판정
4. 이미 해결된 모순: `already_solved: true` + `solution_in_spec` 필드에 근거 문구
5. 남은 모순: `already_solved: false` + `solution_candidate` 필드에 제안

**최소 도출 수**: 기술적 모순 ≥ 4건

### Step 5: 물리적 모순 도출 (최소 2건)

- "X는 A여야 한다 vs X는 not A여야 한다" 형식 진술
- 분리 원리(공간/시간/조건) 매칭
- 이미 해결된 모순 vs 남은 모순 구분
- 최소 2건

### Step 6: IFR(Ideal Final Result) 리스트 (최소 10건)

각 IFR 항목:

```json
{
  "id": "IFR-N",
  "summary": "이상적 결과의 한 줄 요약",
  "solves_contradictions": ["TC-ID", "PM-ID"],
  "applied_principles": [번호, 번호],
  "claimability": "high | medium | low",
  "claim_proposal": "종속항 제안 문구",
  "present_in_spec": true | false
}
```

**최소 10건**: 이 중 일부는 `present_in_spec: true` (이미 명세서에 있음), 나머지는 `present_in_spec: false` (신규 제안).

### Step 7: TRIZ 용어 격리 규칙 적용

> [!danger] 본 섹션은 Phase 7 report-writer가 본문 §2 기술적·물리적 모순, §3 IFR 에 사용할 콘텐츠를 생성한다. **본문에 TRIZ 용어를 직접 쓰지 않는다**.

**금지 용어 (본문)**:
- "원리 24", "원리 15" 등 번호 표기
- "모순 매트릭스", "40 발명 원리", "분리 원리"
- "IFR" 약어
- "알트슐러", "TRIZ"

**허용 용어 (본문)**:
- "기술적 모순" / "물리적 모순" (섹션 헤더용)
- "매개체 역할", "역동성", "피드백" (원리 이름만)

**허용 위치 (부록 A만)**:
- 원리 번호 (원리 15, 원리 24 등)
- 모순 매트릭스 파라미터 번호
- TRIZ 약어
- Altshuller 등 인명

Phase 7 report-writer 는 `triz_diagnosis.json` 의 `applied_principle_numbers` 필드를 본문에서는 일반 용어로, 부록 A에서는 번호로 표시해야 한다.

### Step 8: triz_diagnosis.json 작성

결과를 `{output_dir}/triz_diagnosis.json` 에 Write 도구로 저장.

## 성공 기준

- [ ] `technical_contradictions` 배열 길이 ≥ 4
- [ ] `physical_contradictions` 배열 길이 ≥ 2
- [ ] `ifr_list` 배열 길이 ≥ 10
- [ ] 각 contradiction 에 `already_solved` 필드 존재
- [ ] 각 IFR 에 `present_in_spec` 필드 존재
- [ ] `system_components.mermaid_map` 필드가 유효한 Mermaid graph 문법
- [ ] `diagnosis_summary` 에 6개 필수 카운트 모두 존재

## P26057KR1 베이스라인 기대 결과

참고: 이번 세션 수동 분석 결과 (수동 v1 MD, §2~§3)

| 항목 | 기대 값 |
|------|---------|
| 기술적 모순 | 6건 (TC1~TC6) |
| 물리적 모순 | 3건 (PM1~PM3) |
| IFR | 12건 (IFR-1 ~ IFR-12) |
| 이미 해결한 모순 | TC1, TC3, TC4, TC5 (4건) |
| 남은 모순 | TC2, TC6 (2건) |
| `present_in_spec: true` IFR | IFR-1, IFR-2 등 약 4건 |
| `present_in_spec: false` IFR | 약 6~8건 (신규 종속항 후보) |

**자동 재현 목표**: 위 베이스라인과의 개념적 일치율 ≥ 70% (IFR 내용이 정확히 같을 수는 없지만 주제가 유사해야 함).

## 에러 처리

| 상황 | 조치 |
|------|------|
| TRIZ 레퍼런스 로드 실패 | degraded 모드 — 원리 번호 없이 일반 용어만 사용 |
| 명세서 섹션 부족 (problem/solution 누락) | 사용자에게 경고 + Phase 1 재실행 요청 |
| TC/PM/IFR 최소 수 미달 | 최대 2회 재시도 → 여전히 부족 시 `status: "degraded"` + 부분 결과 출력 |

## 보안 규칙

- WebFetch 금지 (TRIZ 레퍼런스는 로컬 파일만 사용)
- 명세서 본문을 외부 API로 전송 금지
- 로그에 청구항 전문 출력 금지

## Phase 7 (report-writer) 인터페이스

| triz_diagnosis.json 필드 | improvement-plan-v1.md 대상 섹션 |
|--------------------------|---------------------------------|
| `system_components.mermaid_map` | §1.1 시스템 구성요소 맵 |
| `useful_functions`, `harmful_effects` | §1.2 유용 기능 vs 유해 작용 |
| `technical_contradictions` | §2.1 기술적 모순 표 |
| `physical_contradictions` | §2.2 물리적 모순 표 |
| `ifr_list` | §3.1 IFR 리스트 (필터: `present_in_spec: false` 우선) |
| `applied_principle_numbers` | 부록 A.3 적용된 40 발명 원리 (본문에서는 원리 이름만) |
