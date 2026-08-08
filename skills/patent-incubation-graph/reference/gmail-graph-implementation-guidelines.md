---
title: Gmail 기반 Graph 구현 지침 및 평가 기준
created: 2026-08-06
tags:
  - graph-engineering
  - agent-workflow
  - patent-incubation-graph
  - evaluation
source:
  - gmail:4594
  - gmail:4505
  - gmail:4483
  - gmail:4432
  - gmail:4433
  - gmail:4532
---

# Gmail 기반 Graph 구현 지침 및 평가 기준

## 요약

Gmail의 graph 관련 자료는 공통적으로 "모델 성능보다 작업 구조가 먼저"라는 관점을 제시한다. 단일 agent loop는 작은 작업에는 충분하지만, 다단계 연구·코드 검토·문서 생성·특허 도출처럼 많은 근거와 판단을 오래 유지해야 하는 작업에서는 context, 검증, 재시작성, 비용 문제가 누적된다. 해결책은 작업을 node와 edge로 나누고, 독립 작업은 병렬화하며, 판단이 필요한 지점에는 verifier와 judge를 배치하는 것이다.

`patent-incubation-graph`에는 이 관점을 그대로 적용한다. 기술문서·선행특허·아이디어를 하나의 긴 프롬프트로 처리하지 말고, 기술요소-문제-효과-선행문헌-청구항 요소를 typed graph로 저장한 뒤 후보 경로를 탐색하고 검증한다.

## 핵심 원칙

### 1. Node는 하나의 작업이어야 한다

각 node는 한 문장으로 설명 가능한 단일 작업만 수행한다. 예를 들어 "문서에서 기술요소 추출", "선행특허와 claim element 매핑", "후보 청구항 검증"은 각각 별도 node다. "분석하고 정리하고 평가하고 작성"처럼 여러 판단을 섞은 node는 병렬화와 검증이 어렵다.

구현 기준:

- 모든 node는 명시적 input과 output을 가진다.
- node output은 JSON schema 또는 표준 markdown 구조로 고정한다.
- 다음 node가 실제로 이전 node의 output을 읽지 않으면 edge를 만들지 않는다.
- agent가 필요 없는 변환, flatten, dedupe, sorting은 code edge에서 처리한다.

### 2. Edge는 순서가 아니라 데이터 계약이다

메일 자료에서 반복되는 가장 중요한 테스트는 "다음 단계가 이전 단계의 결과 변수를 실제로 소비하는가?"이다. 소비하지 않으면 dependency가 아니며, 병렬 실행 대상이다.

`patent-incubation-graph` 적용:

- `corpus -> graph extraction`: 실제 문서 내용이 graph node/edge로 변환되므로 real edge.
- `graph extraction -> gap mining`: graph를 입력으로 쓰므로 real edge.
- `prior-art search`와 `market actor extraction`: 같은 corpus를 읽지만 서로 output 의존성이 작으므로 병렬 가능.
- `candidate scoring -> disclosure drafting`: 선택 후보와 점수를 직접 사용하므로 real edge.

### 3. Fan-out은 독립성에서 시작한다

여러 문서, 여러 선행특허, 여러 후보, 여러 검증 렌즈는 독립 node로 fan-out한다. fan-out 결과는 barrier에서 모으되, barrier는 전체 결과가 필요한 경우에만 둔다.

권장 fan-out:

- corpus 파일별 기술 주장 추출
- 선행특허별 claim chart 작성
- 후보별 신규성·진보성·검출성 평가
- critic lens별 검증: correctness, prior-art overlap, enforceability, business value

주의:

- 단순 concat/dedupe는 agent에게 맡기지 않는다.
- fan-in node는 "전체 후보를 비교해 rank"처럼 cross-item 판단이 필요한 경우에만 agent로 둔다.

### 4. Router는 판단 node와 deterministic edge를 분리한다

분류 자체는 agent가 할 수 있지만, 분류 후 어느 경로를 탈지는 code로 고정한다.

예시:

- graph coverage가 충분하면 후보 생성으로 진행
- `claim_element_count < 8`이면 corpus 부족 경고 또는 degraded mode
- prior-art risk가 critical이면 candidate revise/drop 경로
- selected candidate가 detectability C only이면 business critic 강화 경로

### 5. Verifier는 edge 위에 둔다

검증은 최종 보고 직전에 한 번 하는 것이 아니라, downstream으로 넘어가기 전에 edge gate로 배치한다.

권장 verifier:

- graph schema validation: node/edge 필수 필드, source_refs, confidence 확인
- source verifier: graph node가 실제 corpus 근거를 갖는지 spot check
- prior-art verifier: `overlaps`와 `distinguishes` 엣지가 선행문헌 내용과 맞는지 확인
- claim verifier: 독립항 핵심 요소가 graph node에서 추적되는지 확인
- citation verifier: 최종 참고문헌이 실제 DOI/특허번호와 일치하는지 확인

fresh-context verifier 원칙:

- 작성 node와 같은 reasoning transcript를 그대로 공유하지 않는다.
- verifier는 output, rulebook, source만 본다.
- 자기승인을 막기 위해 공격적 관점으로 "틀렸다는 가설"을 먼저 세운다.

### 6. State는 context가 아니라 disk와 graph에 둔다

장시간 실행은 conversation context에 의존하면 재시작과 오류 추적이 어렵다. 모든 phase output은 파일로 저장하고, graph는 공유 memory layer로 취급한다.

필수 저장물:

- `invention_manifest.json`: 전체 phase 상태
- `technology_graph.json`: typed graph
- `candidate_paths.json`: 후보 경로
- `portfolio_evaluation.json`: 평가 결과
- `prior_art.json`: 선행문헌 매핑
- `claim_graph_map.json`: claim과 graph node 연결
- `critic_report.json`: 검증 결과

### 7. Loop는 수렴 조건이 있을 때만 쓴다

반복 탐색은 "새 후보가 더 이상 나오지 않음" 같은 종료 조건이 있어야 한다. rejected 후보도 `seen`에 넣어야 같은 후보를 반복 생성하지 않는다.

권장 종료 조건:

- 연속 2회 gap mining에서 new candidate 없음
- 후보 5개 이상 확보 후 점수 상위 1~2개가 안정
- critic FIX가 1회 보정 후에도 재발하면 사용자 판단 요청

### 8. Model tiering을 설계에 넣는다

반복 extraction/classification node는 저비용 모델에, synthesis/critic/rule writing node는 고성능 모델에 배치한다. graph의 장점은 node별로 model tier를 다르게 줄 수 있다는 점이다.

권장 배치:

- extraction, normalization, routing: low/fast model
- gap mining, candidate generation: mid/high model
- final disclosure, claim drafting, critic: high model
- deterministic judge, schema validation, dedupe: no model

## Patent-Incubation-Graph 구현 지침

### Graph schema

최소 node type:

- `need`: 해결 과제, 미충족 요구
- `function`: 시스템/공정/제어 기능
- `component`: 물리 구성요소, 소재, 모듈
- `parameter`: 정량 변수
- `effect`: 기술 효과와 검출 가능한 제품 흔적
- `constraint`: 비용, 공정성, 신뢰성, 규제, 양산 제약
- `prior_art`: 특허, 논문, 발표, 제품, 자기공지
- `principle`: TRIZ 원리, 물리 효과, 설계 패턴
- `claim_element`: 청구항 구성요소
- `market_actor`: 실시 주체와 침해 입증 대상

최소 edge type:

- 기술 관계: `causes`, `blocks`, `improves`, `degrades`, `requires`, `replaces`, `combines_with`
- 선행문헌 관계: `discloses`, `overlaps`, `distinguishes`, `teaches_away`
- 청구항 관계: `maps_to_claim`, `supports_effect`, `detectable_by`, `enables_design_around`

모든 node/edge에는 `source_refs[]`, `confidence`, `origin`, `notes`를 둔다.

### Workflow topology

권장 topology는 diamond와 verifier gate의 조합이다.

1. Scope: manifest와 corpus 확정
2. Fan-out: 문서별 graph extraction
3. Reduce: node canonicalization, dedupe, confidence aggregation
4. Fan-out: gap mining lens별 탐색
5. Synthesize: candidate path 생성
6. Fan-out: 후보별 scoring과 prior-art mapping
7. Verify: graph-source, prior-art, claim support 검증
8. Select: 사용자 선택 또는 최고점 자동 선택
9. Draft: 발명내용설명서 작성
10. Critic: 등록 가능성, 회피설계, 침해 입증 검증
11. Convert: HWPX 변환

### Rulebook-first 운영

메일 자료의 Anthropic method에서 가장 중요한 운영 원칙은 "결과물을 손으로 고치지 말고, 결과물을 만든 rule을 고친다"이다. graph 스킬도 동일하게 운영한다.

반복적으로 발견되는 오류 예:

- claim element가 source_refs 없이 생성됨
- 효과가 선행문헌과 구분되지 않음
- `distinguishes`라고 표기했지만 실제로는 `overlaps`
- 도면 설명과 §6 구성 순서 불일치
- 침해 검출성이 C인데 사업성 점수가 과대평가됨

처리 방식:

- 개별 문장만 수정하지 않는다.
- `reference/graph-schema.md`, `reference/graph-evaluation.md`, agent 지시문에 규칙을 추가한다.
- 영향 받은 phase를 재실행한다.

## 평가 기준

### 후보 발명 평가

| 축 | 가중치 | 평가 질문 |
|---|---:|---|
| 신규성/차별성 | 0.25 | close prior art가 공개하지 않은 claim element가 명확한가? |
| 진보성/결합곤란성 | 0.20 | 선행문헌 조합 동기가 약하거나 teaching away가 있는가? |
| 청구항 강도 | 0.20 | 독립항이 compact하고 fallback 종속항이 충분한가? |
| 침해 검출성 | 0.15 | 제품 관찰 또는 리버스엔지니어링으로 확인 가능한가? |
| 사업 활용성 | 0.10 | 경쟁사 회피 경로를 막거나 실제 제품/공정에 걸리는가? |
| 그래프 근거 신뢰도 | 0.10 | high-confidence source-backed path인가? |

판정:

- `go`: 총점 7.5 이상, critical prior-art risk 없음
- `revise`: 총점 6.2 이상이나 claim/evidence 보강 필요
- `hold`: 아이디어는 있으나 출처·시장·구현 근거 부족
- `drop`: 선행문헌 포섭, 낮은 검출성, 또는 구현 불명확

### Graph 품질 평가

| 항목 | 통과 기준 |
|---|---|
| Coverage | node 30개 이상, edge 40개 이상, claim-ready element 8개 이상 |
| Provenance | 핵심 node/edge의 80% 이상이 source_refs 보유 |
| Canonicalization | 같은 기술요소가 중복 node로 분산되지 않음 |
| Edge correctness | order edge가 아니라 data/technical relation edge로 구성됨 |
| Confidence hygiene | 추정 node/edge는 confidence 0.55 이하로 표시 |
| Traceability | claim element -> graph node -> source까지 추적 가능 |

### Workflow 품질 평가

| 항목 | 통과 기준 |
|---|---|
| Node contract | 각 node input/output schema 존재 |
| Parallelism | 독립 작업이 불필요하게 chain으로 묶이지 않음 |
| Barrier discipline | 전체 집합 판단이 필요한 곳에만 fan-in barrier 사용 |
| Verifier placement | downstream 전 edge gate에 검증 node 존재 |
| Failure isolation | fan-out node 실패가 전체 run을 중단하지 않음 |
| Resumability | phase output이 disk에 저장되어 중단 후 재개 가능 |
| Cost control | deterministic edge와 model node가 분리됨 |

### 최종 신고서 품질 평가

| 항목 | 통과 기준 |
|---|---|
| 방법론 은닉 | §1~§9와 HWPX에 graph/TRIZ 용어 없음 |
| 청구항 추적성 | 독립항 핵심 요소가 graph에서 추적됨 |
| 선행문헌 차별성 | `distinguishes` edge가 §4/§7/§8 논거로 반영됨 |
| 효과 근거 | §7 효과가 graph effect node 또는 검증 근거에 연결됨 |
| 도면 정합성 | §6 구성, §8 청구항, §9 도면이 같은 요소명을 사용함 |
| 인용 정합성 | `reference_verification.json`과 최종 참고문헌이 일치함 |
| 사업성 방어 | 회피설계·침해 입증 critic 결과가 반영됨 |

## 구현 시 금지 사항

- 순서만 있다는 이유로 edge를 만들지 않는다.
- agent에게 단순 dedupe/flatten/sort를 맡기지 않는다.
- verifier가 worker의 전체 reasoning transcript를 읽게 하지 않는다.
- source_refs 없는 추정을 최종 차별점으로 쓰지 않는다.
- critic FIX를 문서에만 손수 반영하고 rule/schema에는 반영하지 않는 운영을 금지한다.
- graph가 작은데도 충분한 근거가 있는 것처럼 최종 문서를 단정적으로 쓰지 않는다.

## 바로 반영할 개선안

`patent-incubation-graph` 초안에는 다음을 우선 반영한다.

1. `technology_graph.json`에 `quality` 블록을 필수화한다.
2. `candidate_paths.json`에 `path_nodes`, `path_edges`, `core_claim_elements`, `fallback_claim_elements`를 필수화한다.
3. `claim_graph_map.json`을 최종 disclosure writer의 필수 산출물로 둔다.
4. Phase G2 후 graph coverage gate를 둔다.
5. Phase G5 후 후보별 devil's-advocate 공격문을 필수화한다.
6. Phase 9 critic에서 graph traceability 검사를 추가한다.
7. 반복 수정은 개별 문서 patch보다 rule/reference/agent 지시문 업데이트를 우선한다.

