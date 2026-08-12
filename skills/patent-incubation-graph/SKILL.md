---
name: patent-incubation-graph
description: "그래프 기반 특허 도출 스킬. 기술문서·아이디어·선행특허를 typed graph로 구조화하고, 그래프 공백·브리지·회피설계 경로를 탐색·검증하여 특허 후보 포트폴리오와 KIMM 직무발명내용설명서(HWPX)를 생성한다. 사용자가 그래프 기반 특허 도출, 기술 그래프에서 발명 후보 생성, claim graph, knowledge graph patent, 공백 기술 도출, 회피설계 경로, 특허 포트폴리오 후보, 다문서 기반 발명 인큐베이션을 요청할 때 사용한다."
---

# 그래프 기반 특허 도출 스킬

기술 아이디어를 단일 TRIZ 후보로 바로 밀어붙이지 않고, 기술요소·기능·문제·효과·선행문헌·청구항 요소 사이의 관계 그래프를 만든 뒤 특허 가능성이 높은 발명 후보를 도출한다. 최종 출력은 원본 `patent-incubation-auto`와 같은 KIMM 발명내용설명서 MD/HWPX이지만, 전반부 분석 단위가 `IFR 후보`가 아니라 `graph-derived invention path`이다.

## Skill Constants

```
SKILL_ROOT = ~/.claude/skills/patent-incubation-graph
AUTO_SKILL_ROOT = ~/.claude/skills/patent-incubation-auto
HWPX_SKILL = ~/.claude/skills/hwpx
HWPX_XML_SKILL = ~/.claude/skills/hwpx-xml
KIPRIS_ENV_FILE = ~/Claude_Work/.env
```

레포 개발본에서 실행할 때는 `SKILL_ROOT`를 현재 스킬 폴더 절대경로로 해석한다. `KIPRIS_ENV_FILE`이 없으면 환경변수 `KIPRIS_API_KEY`/`KIPRIS_REST_ACCESS_KEY`를 확인하고, 둘 다 없으면 선행특허 단계는 degraded 모드로 진행한다.

## Output Contract

기본 출력 디렉토리는 현재 작업 디렉토리의 `output/patent_graph_{YYYYMMDD_HHMM}/`이다.

필수 산출물:

- `invention_manifest.json`: 입력, 파일, 단계 상태, 선택 후보 기록
- `technology_graph.json`: 노드·엣지·출처·신뢰도 포함 그래프
- `graph_gap_report.md`: 그래프 공백, 브리지, 병목, 회피설계 기회
- `candidate_paths.json`: 발명 후보 경로 3~10개
- `portfolio_evaluation.json`: 후보별 특허성·차별성·검출성·사업성 점수
- `prior_art.json`: 선행특허/NPL 조사와 후보별 포섭 위험
- `claim_graph_map.json`: 독립항/종속항 핵심 요소와 그래프 노드/출처 연결
- `graph_qa_report.json`: graph-source, prior-art, claim-support edge gate 검증 결과
- `selected_invention.md`: 최종 선택 후보의 발명내용설명서 MD
- `figures_deck.pptx`, `diagrams/*.png`: HWPX 삽입용 도면
- `reference_verification.json`: 인용 검증 로그
- `*.hwpx`: KIMM 직무발명내용설명서

각 phase가 끝날 때 `invention_manifest.json.phases`에 `status`, `inputs`, `outputs`, `degraded`, `notes`를 기록한다. 대화 context를 상태 저장소로 쓰지 말고, 중단 후 재개할 수 있도록 phase 산출물을 disk에 남긴다.

## Obsidian and Patent Drafting Rules

원본 `patent-incubation-auto`의 다음 규칙을 그대로 따른다.

- 모든 `.md` 파일은 YAML frontmatter(`title`, `created`, `tags`)를 포함한다.
- 최종 발명내용설명서 §1~§9와 HWPX에는 TRIZ, IFR, contradiction matrix 등 방법론 용어를 남기지 않는다. 방법론 기록은 부록에만 둔다.
- 도면 내 참조부호와 "[도 N]"식 설명은 금지한다. 도면 제목은 내용 기반 제목만 사용한다.
- 도면 파이프라인은 SVG 또는 matplotlib 계산 도면 -> 편집 가능한 `figures_deck.pptx` -> 600 dpi PNG -> HWPX 삽입 순서를 기본으로 한다.
- 참고문헌은 Phase 6c 검증을 통과한 실제 문헌만 최종 리스트에 남긴다.

## Graph Model

`reference/graph-schema.md`를 필요 시 읽고, 최소한 아래 노드/엣지 타입을 사용한다.

노드 타입:

- `need`: 해결 과제, 미충족 요구, 성능 병목
- `function`: 시스템 기능, 공정 기능, 제어 기능
- `component`: 물리 구성요소, 소재, 계층, 모듈
- `parameter`: 치수, 속도, 온도, 전압, 압력, 수율 등 정량 변수
- `effect`: 기술 효과, 검출 가능한 결과, 제품 흔적
- `constraint`: 비용, 양산성, 공정 호환성, 법규, 안전, 신뢰성 제약
- `prior_art`: 특허, 논문, 표준, 제품, 자기공지
- `principle`: TRIZ 원리, 분리 원리, 물리 효과, 설계 패턴
- `claim_element`: 독립항/종속항으로 옮길 수 있는 구성요소 또는 단계
- `market_actor`: 실시 주체, 구매자, 침해 입증 대상

엣지 타입:

- `causes`, `blocks`, `improves`, `degrades`, `requires`, `replaces`, `combines_with`
- `discloses`, `teaches_away`, `overlaps`, `distinguishes`, `detectable_by`
- `maps_to_claim`, `supports_effect`, `enables_design_around`, `owned_by`

각 노드와 엣지는 `source_refs[]`, `confidence`, `notes`를 가진다. 출처 없는 추정은 `confidence <= 0.55`로 표시하고 최종 문서의 확정 근거로 쓰지 않는다.

`technology_graph.json`에는 `quality` 블록을 반드시 포함한다. 최소 항목은 `node_count`, `edge_count`, `claim_element_count`, `unsupported_inference_count`, `degraded`, `notes`이다. `claim_element -> graph node -> source_ref` 추적이 끊긴 요소는 최종 독립항의 핵심 차별점으로 쓰지 않는다.

## Graph Workflow Rules

Graph는 순서도가 아니라 데이터 계약이다. edge는 downstream 단계가 upstream output을 실제로 읽고 사용할 때만 만든다. 단순히 시간상 먼저 실행된다는 이유로 dependency를 만들지 않는다.

운영 원칙:

- 각 phase node는 명시적인 input file과 output file을 가진다.
- 문서별 추출, 후보별 평가, 선행문헌별 claim chart, critic lens별 검증은 가능한 경우 fan-out한다.
- fan-in barrier는 전체 집합 비교·랭킹·정규화처럼 cross-item 판단이 필요한 지점에만 둔다.
- dedupe, flatten, sorting, schema validation 같은 deterministic edge는 agent 판단이 아니라 코드나 명시 규칙으로 처리한다.
- verifier는 downstream으로 넘기기 전 edge gate로 둔다. verifier에는 worker의 reasoning transcript가 아니라 산출물, rulebook, source만 제공한다.
- 반복 수정은 개별 문장 손수 보정이 아니라 schema/reference/agent 지시문 보강 후 해당 phase 재실행을 우선한다.

권장 topology:

```
Scope -> document fan-out extraction -> reduce/canonicalize -> gap lens fan-out
-> candidate synthesis -> candidate/prior-art fan-out -> edge verification
-> selection -> disclosure draft -> claim/figure/citation/critic gates -> HWPX
```

## Model Routing (2026-08-12 신설)

에이전트 호출 시 phase별 기본 모델 배치. fan-out 물량 단계는 저비용 모델, 창의 핵심·적대 검증은 고성능 모델로 비대칭 배치하여 품질을 유지하면서 비용·시간을 절감한다. `Agent(model=...)` 파라미터로 지정한다.

| 단계 | 작업 | model |
|------|------|-------|
| G1 스키마 | 노드/엣지 타입·동의어 사전·claim_element 규칙 정의 | sonnet |
| G2 추출 (fan-out) | 문서별 1차 원자 주장 추출 — corpus 문서 수만큼 병렬 | haiku |
| G2 정규화 (reduce) | canonicalize·중복 병합·coverage gate 판정 | sonnet |
| G3 공백 탐색 | gap/브리지/회피설계 기회 발굴 | opus |
| G4 후보 생성 | 발명 후보 경로 창출 — 창의 핵심 단계 | **fable** |
| G5 포트폴리오 평가 | 6축 채점 + devil's advocate 문단 | opus |
| G6 선행조사 병합 | KIPRIS/Google Patents 검색·그래프 병합 | sonnet |
| Step 7 QA gates | edge gate 검증 (schema/ID 무결성 등 결정적 검사는 코드로 처리) | sonnet |
| D1 명세 작성 | 발명내용설명서 + claim_graph_map — 청구항 포함 최고가치 산출물 | **fable** |
| Step 10 하드닝/도면/인용 | Phase 6.5·6b·6c 재사용 | sonnet |
| Step 10 critic 2단 | Phase 6d(등록 가능성)·6e(사업화) 재사용 | opus |
| Step 11 HWPX | convert_hwpx.py 변환 | sonnet |

## Workflow

```
Step 0: 입력 수집 및 corpus 확정
Step 1: 그래프 스키마 구축 (Phase G1)
Step 2: 기술 그래프 추출·정규화 (Phase G2)
Step 3: 그래프 공백/브리지/회피설계 탐색 (Phase G3)
Step 4: 발명 후보 경로 생성 (Phase G4)
Step 5: 후보 포트폴리오 정량 평가 (Phase G5)
Step 6: 선행특허·자기공지 조사 및 그래프 병합 (Phase G6)
Step 7: Graph QA edge gates
Step 8: 선택 게이트 또는 자동 선택
Step 9: 발명내용설명서 작성 (Phase D1)
Step 10: 청구항 하드닝, 도면, 인용 검증, critic
Step 11: HWPX 변환 및 최종 보고
```

## Step 0: Input

대화형 입력이 필요한 경우 다음을 요청한다.

```
그래프 기반 특허 도출을 시작합니다. 다음 정보를 주세요.

1. 기술분야:
2. 분석 대상 문서/폴더:
3. 해결하고 싶은 큰 문제 또는 제품/공정 목표:
4. 후보 수: 기본 5개
5. 최종 HWPX 작성 여부: 기본 예

선택: 발명자명, 소속기관, 제외할 공개자료, 우선 사업자/시장, 출력 디렉토리
```

문서 기반 요청이면 현재 폴더의 `.md`, `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv` 중 관련 파일을 탐색한다. PDF 변환이 필요하면 별도 PDF-to-MD 도구/스킬을 사용해 텍스트를 확보한 뒤 그래프 구축에 투입한다.

`invention_manifest.json`에는 다음 키를 포함한다.

```json
{
  "input": {
    "field": "",
    "goal": "",
    "corpus": [],
    "inventors": [],
    "affiliation": "",
    "candidate_count": 5,
    "final_hwpx": true,
    "date": "YYYY-MM-DD"
  },
  "output_dir": "",
  "phases": {}
}
```

## Step 1: Graph Schema (Phase G1)

`agents/phase-g1-graph-schema.md`를 읽고 `graph_schema.json`을 작성한다. 사용자의 기술분야에 맞춰 필수 노드 타입, 금지 관계, 동의어 사전, 정량 파라미터 단위를 정의한다.

완료 조건:

- 노드/엣지 타입이 누락 없이 정의됨
- 동의어/약어가 정규화됨
- 최종 청구항으로 전환 가능한 `claim_element` 규칙이 있음

## Step 2: Graph Extraction (Phase G2)

`agents/phase-g2-graph-builder.md`를 읽고 corpus에서 `technology_graph.json`을 생성한다.

추출 원칙:

- 문서 문장을 그대로 복사하지 말고, 원자 단위의 기술 주장으로 분해한다.
- 하나의 주장에는 출처와 근거 문장 위치를 붙인다.
- 선행기술과 사용자 아이디어는 같은 그래프에 넣되 `origin`으로 구분한다.
- 자기공지 가능성이 있는 논문/발표/보고서는 `prior_art` 후보로 별도 표시한다.

그래프가 너무 작으면(노드 < 30 또는 `claim_element` < 8) 사용자에게 corpus 부족을 알리고, 그래도 진행하라는 지시가 있으면 degraded 모드로 계속한다.

Coverage gate:

- `node_count >= 30`
- `edge_count >= 40`
- `claim_element_count >= 8`
- 핵심 node/edge의 80% 이상이 `source_refs[]`를 가짐
- 추정 node/edge는 `origin: inference` 및 `confidence <= 0.55`

gate를 통과하지 못하면 `technology_graph.json.quality.degraded = true`로 표시하고 `invention_manifest.json`에 부족 항목을 기록한다.

## Step 3: Gap and Bridge Mining (Phase G3)

`agents/phase-g3-gap-miner.md`를 읽고 `graph_gap_report.md`와 `graph_opportunities.json`을 작성한다.

탐색할 기회:

- `need -> constraint` 병목을 우회하는 새 `function/component` 브리지
- 선행문헌이 각각 따로 공개하지만 결합 동기가 약한 엣지 조합
- 성능 파라미터를 개선하면서 핵심 제약을 악화시키지 않는 Pareto 경로
- 침해 검출성이 높은 제품 흔적(`effect`)과 연결되는 claim path
- 타사가 쉽게 설계변경할 수 있는 약한 claim path의 보강 노드

## Step 4: Candidate Path Generation (Phase G4)

`agents/phase-g4-candidate-paths.md`를 읽고 `candidate_paths.json`을 만든다. 각 후보는 그래프 경로 하나가 아니라, 청구항으로 전환 가능한 문제-수단-효과 묶음이어야 한다.

각 후보 필수 필드:

- `candidate_id`, `title`, `one_sentence_invention`
- `path_nodes[]`, `path_edges[]`
- `core_claim_elements[]`, `fallback_claim_elements[]`
- `distinguishing_features[]`
- `technical_effects[]`
- `detectability_grade`
- `known_prior_art_risks[]`
- `source_refs[]`

최소 3개, 기본 5개, 최대 10개 후보를 만든다. 후보가 3개 미만이면 Phase G3를 1회 재실행한다.

## Step 5: Portfolio Evaluation (Phase G5)

`agents/phase-g5-portfolio-evaluator.md`를 읽고 `portfolio_evaluation.json`을 작성한다.

평가 축:

- 신규성/차별성 0.25
- 진보성/결합곤란성 0.20
- 청구항 강도 0.20
- 침해 검출성 0.15
- 사업 활용성 0.10
- 그래프 근거 신뢰도 0.10

후보별 `go`, `revise`, `hold`, `drop` 판정을 부여한다. 최종 HWPX는 `go` 최상위 후보 1건을 기본 대상으로 한다.

각 `go` 후보에는 반드시 devil's-advocate 문단을 포함한다. 침해 검출성이 C뿐인 후보는 사업 활용성 점수를 보수적으로 제한하고, 독립항에 검출 가능한 `effect` 또는 `detectable_by` 경로가 없으면 기본 판정을 `revise` 이하로 둔다.

## Step 6: Prior Art Graph Merge (Phase G6)

원본 `patent-incubation-auto`의 `agents/phase5-prior-art.md`와 `scripts/search_patents_kipris.py`를 재사용한다. 조사 결과는 단순 리스트가 아니라 기존 그래프에 병합한다.

필수:

- KIPRIS 국내 검색, 자기선행 특허, 자기공지/NPL 조사
- Google Patents 해외 패밀리 확인 가능 시 수행
- 후보별 포섭 위험을 `prior_art -> overlaps -> claim_element` 엣지로 기록
- `teaches_away`, `distinguishes` 엣지를 별도로 표시

`prior_art.json`이 degraded이면 Step 5 점수 중 신규성/진보성은 provisional로 표기한다.

## Step 7: Graph QA Edge Gates

`graph_qa_report.json`을 작성하고, 아래 gate를 통과한 뒤에만 선택 또는 drafting으로 넘어간다.

필수 검사:

- Graph schema: 모든 node/edge 필수 필드, ID 참조 무결성, confidence 범위
- Source support: 핵심 node/edge의 `source_refs` 실재 여부 spot check
- Prior-art mapping: `overlaps`, `distinguishes`, `teaches_away` 엣지가 선행문헌 내용과 일치하는지 확인
- Claim support: `core_claim_elements[]`가 graph node와 출처로 추적되는지 확인
- Evaluation integrity: 점수와 verdict가 `reference/graph-evaluation.md` 기준과 일치하는지 확인

gate 결과는 `PASS`, `FIX`, `ADVISE`, `BLOCK` 중 하나로 둔다. `BLOCK`이면 자동 진행을 멈추고 사용자 판단을 요청한다. `FIX`는 1회 보정 후 재검증하고, 같은 문제가 반복되면 사용자에게 리스크를 보고한다.

## Step 8: Selection Gate

자동 진행 모드가 아니면 후보 요약을 사용자에게 표시하고 선택을 기다린다.

```
그래프 기반 발명 후보 {N}개를 도출했습니다.

| 후보 | 한 줄 요약 | 점수 | 강점 | 주요 리스크 |
|---|---|---:|---|---|

진행할 후보 번호를 선택해 주세요. 기본값은 1위 후보입니다.
```

사용자가 "자동", "알아서", "초안까지"라고 지시한 경우 `go` 판정 중 최고점 후보를 선택한다.

## Step 9: Disclosure Draft (Phase D1)

선택 후보를 원본 `patent-incubation-auto`의 Phase 6 형식으로 변환한다. `agents/phase-d1-graph-disclosure-writer.md`를 읽고 `selected_invention.md`를 작성한다.

작성 규칙:

- §1~§9는 일반 특허 문서 언어만 사용하고 graph/TRIZ 용어를 숨긴다.
- §6 발명의 구성은 `claim_element` 순서와 일치시킨다.
- §7 효과는 `effect` 노드와 근거 출처가 있는 항목만 단정적으로 쓴다.
- §8 청구범위는 graph path를 독립항 1~2개와 종속항 8~15개로 변환한다.
- 부록 A에는 그래프 도출 로그, 부록 B에는 선행특허 대비표, 부록 C에는 검증 참고문헌을 둔다.
- `claim_graph_map.json`을 함께 작성해 각 청구항 요소가 graph node ID, source_ref, prior_art 대비 edge와 연결되게 한다.

## Step 10: Hardening, Figures, Verification, Critics

원본 `patent-incubation-auto`의 다음 단계를 재사용한다.

- Phase 6.5 청구항 하드닝: `reference/claim-drafting.md`, `reference/smart-index-checklist.md`
- Phase 6b 도면 생성: `agents/phase6b-diagram-generator.md`, `reference/detailed-figures.md`, `reference/svg-figure-creation.md`
- Phase 6c 인용 검증: `agents/phase6c-reference-verifier.md`, `scripts/verify_citations.py`
- Phase 6d critic: 등록 가능성, 인용 의미 검증, 대표 청구항 모의 심사
- Phase 6e business critic: 회피설계, 침해 입증, 사업 활용성

그래프 버전 추가 점검:

- 모든 독립항 핵심 구성요소가 `technology_graph.json`의 `claim_element` 또는 `component/function` 노드에서 추적되는지
- 차별점이 `prior_art.overlaps`가 아니라 `distinguishes` 엣지로 설명되는지
- 침해 검출성 등급 A/B 요소가 최소 하나 이상 독립항에 포함되는지
- 그래프 근거 없는 효과가 §7에 남지 않았는지
- §6 구성, §8 청구범위, §9 도면 설명이 같은 요소명과 같은 계층 구조를 쓰는지
- critic `FIX`를 문서에만 반영하지 말고 필요한 경우 `reference/graph-schema.md`, `reference/graph-evaluation.md`, 관련 agent 지시문까지 보강했는지

## Step 11: HWPX and Final Report

원본 `patent-incubation-auto`의 Phase 7 HWPX 변환 절차와 `scripts/convert_hwpx.py`를 사용한다. 템플릿은 `assets/[KIMM]직무발명내용설명서_양식.hwpx`이다.

최종 응답에는 다음을 간결히 보고한다.

- 선택 후보명과 점수
- 생성된 MD/HWPX 경로
- 그래프 기반 차별점 3개
- 선행특허 리스크와 공지예외 기한이 있으면 날짜
- critic PASS/FIX/ADVISE/BLOCK 결과

## Error Handling

| 단계 | 실패 모드 | 대응 |
|---|---|---|
| G1 | 스키마가 기술분야와 맞지 않음 | 스키마 1회 재작성 |
| G2 | 노드 < 30 또는 claim_element < 8 | corpus 부족 경고 후 degraded 진행 |
| G3 | 후보 기회 < 3 | gap miner 1회 재실행 |
| G4 | 후보 < 3 | 후보 생성 1회 재실행, 그래도 부족하면 현재 후보로 진행 |
| G6 | KIPRIS/API 실패 | prior_art degraded, 수동 보완 안내 |
| D1 | §1~§9 누락 | 1회 재작성 |
| 6c | verify_citations.py 실패 | HWPX 변환 차단 후 정리/재검증 |
| 6d | BLOCK | 자동 진행 중단, 사용자 판단 요청 |
| HWPX | 변환 실패 | MD와 도면 패키지를 fallback 산출물로 제공 |

## Reference Loading

- 그래프 JSON 구조가 필요하면 `reference/graph-schema.md`를 읽는다.
- 후보 평가 기준이 필요하면 `reference/graph-evaluation.md`를 읽는다.
- graph 구현 지침과 workflow 평가 기준이 필요하면 `reference/gmail-graph-implementation-guidelines.md`를 읽는다.
- 청구항 문안, SMART 지수, 도면, HWPX 변환은 복사된 원본 reference 파일을 필요 시 읽는다.
