# patent-incubation: 사용자 주도형 발명 워크플로우

사용자와 긴밀하게 소통하며 발명 아이디어를 체계적으로 발전시키는 스킬. TRIZ 분석 → 모순 도출 → IFR 생성 → 평가 → 선행특허 → 발명내용설명서(KIMM 양식)까지, 모든 단계에서 사용자가 판단하고 선택한다.

## When to Use

- 사용자가 발명 아이디어를 함께 발전시키고 싶을 때
- "발명 인큐베이션", "patent incubation", "발명 같이 하자", "아이디어 발전" 언급 시
- 기존 `patent-incubation-auto`의 자동화 모드 대신, 각 단계를 직접 검토하며 진행하고 싶을 때

## Skill Constants

```
SKILL_ROOT = C:/Users/JHKIM/.claude/skills/patent-incubation-interactive
SHARED_SKILL_ROOT = C:/Users/JHKIM/.claude/skills/patent-incubation-auto
HWPX_SKILL = C:/Users/JHKIM/.claude/skills/hwpx
HWPX_XML_SKILL = C:/Users/JHKIM/.claude/skills/hwpx-xml
KIPRIS_ENV_FILE = C:/Users/JHKIM/Claude_Work/.env
```

### 공유 자원 (patent-incubation-auto에서 참조)

```
reference/   → {SHARED_SKILL_ROOT}/reference/
templates/   → {SHARED_SKILL_ROOT}/templates/
scripts/     → {SHARED_SKILL_ROOT}/scripts/
assets/      → {SHARED_SKILL_ROOT}/assets/
```

---

## Obsidian 마크다운 및 다이어그램 규칙

본 스킬이 생성하는 모든 `.md` 파일은 Obsidian 볼트에서 직접 사용할 수 있어야 한다.

### MD 파일 기본 규칙

1. **YAML 프론트매터 필수**: `title`, `created`, `tags` 최소 포함
2. **내부 링크**: `[[파일명]]` 문법 사용 가능
3. **콜아웃**: `> [!note]`, `> [!warning]` 등 Obsidian 콜아웃 사용 가능

### 다이어그램 정책

| 유형 | 도구 | 용도 |
|------|------|------|
| 코드화 가능한 도면 | **Mermaid** | 흐름도, 시스템 구성도, 상태 변화도, 비교표 |
| HWPX 삽입용 | **PNG (matplotlib)** | convert_hwpx.py가 §9에 자동 삽입하는 이미지 |

### TRIZ 용어 사용 규칙

| 영역 | TRIZ 용어 | 설명 |
|------|----------|------|
| 발명내용설명서 MD §1~§9 | **금지** | 일반적 기술 용어로 변환 |
| 발명내용설명서 MD 부록 A | **허용** | TRIZ 분석 과정 상세 기록 |
| HWPX §1~§9 | **금지** | TRIZ, IFR, 모순 매트릭스, 원리 번호 등 불포함 |
| **Gate 표시** | **번역 필수** | 모든 Gate에서 TRIZ 용어를 일반 기술 언어로 번역하여 제시 |

### 문서 스타일 규칙 (본문 전 섹션 공통)

- **개조식 문체 필수 (§1 제외)**: 모든 문장을 `~함.`, `~있음.`, `~필요함.`, `~됨.`, `~임.`, `~가능함.` 등으로 종결한다. `~이다/~한다/~였다` 평서체 **금지**.
- **상세 설명 동반**: 짧게 자르지 말고 한 문장 안에 조건·수치·재료·메커니즘·인과를 충분히 담는다. "상세한 설명이 추가된 개조식"이 핵심.
- **§6 계층적 글머리기호 필수**: `6.1 / 6.2 / 6.1.1` 숫자 하위섹션 **금지**. markdown `- ` + 공백 2칸 = 1 레벨(최대 3레벨) 사용. convert_hwpx.py가 HWPX 변환 시 ●/○/▪/- 계층 bullet + 내어쓰기(hanging indent)로 자동 렌더링.

### 참고문헌 정합 검증 규칙 (필수)

§9.4 참고문헌 및 본문 인용의 모든 외부 문헌(논문·특허)은:

1. **DOI 링크 기재** (논문): `https://doi.org/10.XXXX/...` 형식
2. **KIPRIS 링크 기재** (한국 특허): `https://doi.org/10.8080/10YYYYNNNNNNN` 형식
3. **Google Scholar 또는 KIPRIS API로 내용 검증 후** 문헌 설명 끝에 **"(정합 확인!)"** 부착
4. 검증 불가(내부 메모 등)는 `외부 공개 DOI 없음 — 정합 확인 대상 아님` 표기

**KIPRIS API 키**: `{KIPRIS_ENV_FILE}`의 `KIPRIS_REST_AccessKey` 사용.

**잘못된 인용 탐지 패턴**: 저자·제목·저널·연도 조합이 실제 논문과 다르거나, 같은 PII가 서로 다른 참고문헌에 중복 사용되면 **환각 의심** → 재검증 필수.

---

## 워크플로우 전체 구조

```
Phase 0: 발명 씨앗 대화 ─────────── 사용자 주도 (반복 가능)
  ├─ Gate 0: 입력 확정 ──────────── 사용자 승인
  │
Phase 1: 시스템 분석 ────────────── sonnet 에이전트
  ├─ Gate 1: 시스템 모델 검토 ───── 사용자 판단 [auto-skip 가능]
  │
Phase 2: 모순 도출 + IFR 생성 ──── opus 에이전트
  ├─ Gate 2A: 모순 검토 ─────────── 사용자 판단 [필수]
  │  └─ Background: KIPRIS 예비 검색 시작
  ├─ Gate 2B: IFR 선별 ──────────── 사용자 선택 [필수]
  │  └─ Background: KIPRIS 정밀 검색 시작
  │
Phase 4: IFR 정량 평가 ──────────── sonnet 에이전트
  ├─ Gate 4: 평가 결과 검토 ─────── 사용자 판단 [auto-skip 가능]
  │
Phase 5: 선행특허 조사 ──────────── sonnet 에이전트 (Background 결과 활용)
  ├─ Gate 5: 차별성 전략 결정 ───── 사용자 판단 [필수]
  │
Phase 6: 발명내용설명서 초안 ────── opus 에이전트
  ├─ Gate 6: 섹션별 검토 ────────── 사용자 판단 [필수]
  │  └─ Background: 도면 선행 생성
  │
Phase 6b: 도면 생성 ─────────────── sonnet 에이전트 (Background 결과 활용)
Phase 6c: 인용문헌 정합성 검증 ──── sonnet 에이전트 (KIPRIS + CrossRef + OpenAlex + Zettelkasten)
Phase 7: HWPX 변환 ──────────────── sonnet 에이전트
  └─ Gate 7: 최종 확인 ──────────── 사용자 확인 [auto-skip 가능]
```

---

## Manifest 상태 추적 스키마

`invention_manifest.json`:

```json
{
  "input": {
    "field": "기술분야",
    "problem": "해결 과제",
    "idea": "핵심 아이디어",
    "inventor": "발명자명",
    "date": "YYYY-MM-DD",
    "references": [],
    "source_files": []
  },
  "output_dir": "/absolute/path",
  "current_gate": "gate_0",
  "phases": {
    "phase1": {"status": "pending", "output": null},
    "phase2": {"status": "pending", "output": null},
    "phase4": {"status": "pending", "output": null},
    "phase5": {"status": "pending", "output": null},
    "phase6": {"status": "pending", "output": null},
    "phase6b": {"status": "pending", "output": null},
    "phase6c": {"status": "pending", "output": null},
    "phase7": {"status": "pending", "output": null}
  },
  "gates": {},
  "backtrack_log": [],
  "background_tasks": {}
}
```

### 세션 중단/재개

1. `current_gate` 필드로 마지막 위치를 추적한다.
2. 세션 재개 시: manifest를 읽고 `current_gate`에 해당하는 Gate부터 재시작.
3. 해당 Gate의 입력 데이터(이전 Phase JSON)가 존재하면 에이전트 재실행 없이 Gate 제시.
4. 입력 데이터가 없으면 해당 Phase 에이전트부터 재실행.

---

## 자동 진행(Auto-Proceed) 정책

사용자가 "자동으로 진행", "전부 자동", "auto" 등을 지시한 경우:

| Gate | 자동 진행 | 이유 |
|------|----------|------|
| Gate 0 | **불가** | 발명 입력은 항상 사용자 확인 필요 |
| Gate 1 | **가능** (skip) | 정보 표시 성격 |
| Gate 2A | **불가** | 모순 정의는 발명 핵심 방향 |
| Gate 2B | **불가** | IFR 선별은 핵심 의사결정 |
| Gate 4 | **가능** (skip) | 정보 표시 성격 |
| Gate 5 | **불가** | 선행특허 대응 전략은 등록 가능성에 직결 |
| Gate 6 | **불가** | 발명내용설명서 내용 확인은 발명자 책임 |
| (Phase 6c 요약) | **가능** (정보 표시) | Gate 아님 — 단, 불일치 비율 > 30% 시 1회 확인 |
| Gate 7 | **가능** (skip) | 이전 Gate에서 이미 승인됨 |

> auto-skip 시에도 Gate 결과는 화면에 표시한다 (응답을 기다리지 않을 뿐).

---

## Phase 0: 발명 씨앗 대화

### 진행 방식

**라운드 1 — 문제 이해**

사용자에게 질문:
```
어떤 기술적 문제를 겪고 계신가요?
현재 그 문제가 왜 해결되지 않고 있는지도 함께 알려주세요.
```
→ 기술분야(field)와 해결 과제(problem)를 추출

**라운드 2 — 아이디어 탐색**

```
그 문제를 해결할 수 있다고 생각하시는 아이디어가 있으신가요?
아직 구체화되지 않은 단계라도 괜찮습니다.
```
→ 핵심 아이디어(idea) 추출. 막연한 경우 추가 질문으로 구체화

**라운드 3 — 맥락 확인**

```
관련된 참조 문서(논문, 메모, 기존 특허)가 있다면 경로를 알려주세요.
현재 폴더의 .md 파일도 자동 탐색합니다.
```
→ 참조 문서 확보. 현재 작업 디렉토리의 `.md` 파일을 Glob으로 자동 탐색.

### 입력 방법 B: 문서 기반 입력

사용자가 "현재 폴더의 md 파일을 토대로" 등의 지시를 하면:
1. 작업 디렉토리의 `.md` 파일 탐색
2. 발명 관련 내용 자동 추출
3. 추출 결과를 Gate 0에서 확인 요청

### Gate 0: 입력 확정

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
발명 입력 정보 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 항목 | 내용 |
|------|------|
| 기술분야 | {field} |
| 해결 과제 | {problem} |
| 핵심 아이디어 | {idea} |
| 참조 문서 | {references} |

선택:
1. 확정하고 분석 시작
2. 수정할 부분이 있음
3. 아이디어를 더 고민하고 싶음 → 추가 대화
```

> AskUserQuestion 도구를 사용하여 입력을 받는다.

→ 승인 시 `invention_manifest.json` 생성, `current_gate: "gate_1"` 설정

---

## Phase 1: TRIZ 시스템 분석 + Gate 1

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase1-triz-system.md for instructions.
         Read {SHARED_SKILL_ROOT}/reference/triz-contradiction-matrix.json for parameter list.
         Input: {manifest.input}
         Output: {output_dir}/triz_system.json"
)
```

### Gate 1: 시스템 모델 검토 [auto-skip 가능]

`triz_system.json`의 `gate_summary`를 사용하여 표시:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기술 시스템 분석 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 시스템 주 기능
"{gate_summary.main_function_display}"

### 5요소 분석 요약

| 요소 | 분석 결과 | 발명과의 관련성 |
|------|----------|---------------|
{gate_summary.five_element_table를 테이블로}

### 문제점 진단

| 유형 | 내용 |
|------|------|
| 유해 기능 | {gate_summary.problem_diagnosis.harmful} |
| 불충분 기능 | {gate_summary.problem_diagnosis.insufficient} |

### 개선/악화 파라미터 후보

| 개선 대상 | 악화 우려 | 상충 메커니즘 |
|----------|----------|-------------|
{gate_summary.parameter_candidates를 테이블로}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 분석이 적절함 → 모순 분석으로 진행
2. 수정/보완 의견이 있음 → 의견 입력 후 재분석
3. 개선/악화 파라미터를 조정하고 싶음 → 파라미터 변경
```

- **수정 의견 시**: 의견 반영하여 `triz_system.json` 수정 후 Gate 1 재제시
- **파라미터 조정 시**: 39개 TRIZ 파라미터 중 관련 항목 제시

manifest 업데이트: `current_gate: "gate_2a"`, `gates.gate_1: {iterations, decision, history}`

---

## Phase 2: 모순 도출 + IFR 생성

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase2-contradiction-ifr.md for instructions.
         Read {SHARED_SKILL_ROOT}/reference/triz-contradiction-matrix.json for matrix lookup.
         Read {SHARED_SKILL_ROOT}/reference/triz-40-principles.md for principle details.
         Read {SHARED_SKILL_ROOT}/reference/triz-separation-principles.md for separation laws.
         Read {output_dir}/triz_system.json for Phase 1 output.
         Input: {manifest.input}
         Output: {output_dir}/triz_analysis.json
         CRITICAL: Generate at least 10 IFRs. Each IFR must cite applied principle numbers."
)
```

### Gate 2A: 모순 검토 [필수]

모순 분석 결과를 제시. **IFR은 아직 보여주지 않음.**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
모순 분석 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 기술적 모순 ({N}개)

각 모순 카드:
┌─────────────────────────────────────┐
│ TC{n}: {개선 파라미터} vs {악화 파라미터}     │
│                                              │
│ 왜 모순인가:                                  │
│   {description — 일반 기술 언어}               │
│                                              │
│ 발명 목적과의 관계:                            │
│   {purpose_relation}                          │
│   중요도: 핵심/부수적                          │
│                                              │
│ 해결 실마리:                                   │
│   - {원리를 일반 기술 언어로 번역한 설명}       │
│   - {원리를 일반 기술 언어로 번역한 설명}       │
└─────────────────────────────────────┘

### 물리적 모순 ({N}개)

각 모순 카드:
┌─────────────────────────────────────┐
│ PC{n}: "{파라미터}는 {A}여야 하지만           │
│         동시에 {~A}여야 한다"                  │
│                                              │
│ 분리 해결 방향:                                │
│   {분리 법칙} — {구체적 설명}                  │
│                                              │
│ 발명 목적과의 관계:                            │
│   {purpose_relation}                          │
└─────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 모순 분석이 적절함 → IFR(해결 아이디어) 검토로 진행
2. 놓친 모순이 있음 → 추가 모순 제안
3. 특정 모순이 부적절함 → 수정/삭제 지정
4. 모순의 중요도 순서를 조정하고 싶음
5. 시스템 분석으로 되돌아가기 (Gate 1) → 파라미터 변경
```

**피드백 반영**: 모순 추가/수정/삭제 → `triz_analysis.json` 업데이트. 모순 변경 시 해당 IFR도 재생성.

#### Background Prefetch: KIPRIS 예비 검색

Gate 2A 제시 **직후**, 사용자 검토 중에 KIPRIS 예비 검색을 background로 실행:

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="KIPRIS 예비 검색. manifest.input의 기술분야/아이디어에서 핵심 키워드 3-5개를 추출하여 검색.
         Script: {SHARED_SKILL_ROOT}/scripts/search_patents_kipris.py
         .env: {KIPRIS_ENV_FILE}
         Output: {output_dir}/kipris_prefetch.json
         이 결과는 Phase 5에서 시간 절약 목적으로 활용됨.",
  run_in_background=True
)
```

### Gate 2B: IFR 선별 [필수]

사용자가 모순을 승인한 후, IFR 목록을 `ifr_groups` 기준으로 그룹별 제시:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IFR(이상적 해결 방안) 목록 — {N}개 생성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 그룹: {group_name} — {group_description}

| # | 핵심 내용 | 해결하는 모순 | 구현 개요 |
|---|----------|-------------|----------|
| IFR-{id} | {description} | {contradiction_link} | {implementation} |

(각 그룹별 반복)

### 모순-IFR 커버리지

| 모순 | 해결하는 IFR | 커버리지 |
|------|------------|---------|
| TC1 | IFR-1, IFR-2, IFR-5 | {summary} |
| PC1 | IFR-3, IFR-6 | {summary} |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 전체 유지 → 모든 IFR을 정량 평가로 진행
2. 선택적 채택 → 번호 지정 (예: "1,3,5,7,9 유지")
3. IFR 수정/합치기 → 구체적 의견 (예: "IFR-2와 IFR-5를 합쳐서...")
4. 새 아이디어 추가 → 사용자가 직접 IFR 제안
5. 모순 단계로 되돌아가기 (Gate 2A)
```

**피드백 유형별 처리**:
- **선택적 채택**: 선택된 IFR만 `triz_analysis.json`에 `selected: true` 표시
- **수정/합치기**: opus 에이전트에 수정 지시 → IFR 업데이트
- **새 아이디어 추가**: 사용자 아이디어를 IFR 형식으로 변환
- **되돌아가기**: Gate 2A로 복귀, `triz_analysis.json` IFR 부분 무효화

#### Background Prefetch: KIPRIS 정밀 검색

Gate 2B 제시 **직후**, 확정된 모순 기반으로 정밀 검색 시작:

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="KIPRIS 정밀 검색. 확정된 모순의 핵심 키워드 + IFR 키워드로 검색.
         이전 예비 검색 결과: {output_dir}/kipris_prefetch.json (있으면 참조)
         Script: {SHARED_SKILL_ROOT}/scripts/search_patents_kipris.py
         Output: {output_dir}/kipris_refined.json",
  run_in_background=True
)
```

> 사용자가 IFR을 변경하면 이 결과는 폐기하고 재검색.

---

## Phase 4: IFR 정량 평가 + Gate 4

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase4-evaluator.md for instructions.
         Read {output_dir}/triz_analysis.json for IFR list.
         Read {SHARED_SKILL_ROOT}/templates/evaluation-matrix.md for scoring template.
         IMPORTANT: Only evaluate IFRs with selected=true (or all if no selection was made).
         Input: {manifest.input}
         Output: {output_dir}/evaluation.json"
)
```

### Gate 4: 평가 결과 검토 [auto-skip 가능]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IFR 정량 평가 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 종합 순위

| 순위 | IFR | 종합점수 | 실현가능성 | 비용효율 | 기술효과 | 특허성 | 산업가치 |
|------|-----|---------|----------|---------|---------|-------|---------|
{evaluation.json ranking을 테이블로}

### 평가 근거 (상위 3건)

IFR-{n} (종합 {score}):
| 기준 | 점수 | 근거 |
|------|------|------|
| 실현가능성 | {s}/10 | {scoring_rationale.feasibility_reason} |
| 비용효율 | {s}/10 | {scoring_rationale.cost_reason} |
| 기술효과 | {s}/10 | {scoring_rationale.effect_reason} |
| 특허성 | {s}/10 | {scoring_rationale.patentability_reason} |
| 산업가치 | {s}/10 | {scoring_rationale.industrial_reason} |

### 가중치
현재: 실현가능성(0.25), 비용효율(0.15), 기술효과(0.25), 특허성(0.20), 산업가치(0.15)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 결과 수용 → 선행특허 조사로 진행
2. 특정 IFR의 점수를 조정하고 싶음 → 번호와 이유 입력
3. 가중치를 변경하고 싶음 → 새 가중치 입력
4. 발명에 포함할 IFR를 직접 지정 → 최종 IFR 목록 결정
5. IFR 선별로 되돌아가기 (Gate 2B) → evaluation.json 무효화
```

---

## Phase 5: 선행특허 조사 + Gate 5

### KIPRIS API 키 로드

```bash
if [ -f "C:/Users/JHKIM/Claude_Work/.env" ]; then
  set -a
  eval "$(cat 'C:/Users/JHKIM/Claude_Work/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
  set +a
fi
```

### 에이전트 호출

Background Prefetch 결과가 있으면 활용:

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase5-prior-art.md for instructions.
         Read {output_dir}/triz_analysis.json for IFR list.
         Read {output_dir}/evaluation.json for top-ranked IFRs.
         
         Background search results (use if available, skip re-search for matching keywords):
         - {output_dir}/kipris_prefetch.json
         - {output_dir}/kipris_refined.json
         
         KIPRIS script: {SHARED_SKILL_ROOT}/scripts/search_patents_kipris.py
         .env: {KIPRIS_ENV_FILE}
         
         Input: {manifest.input}
         Output: {output_dir}/prior_art.json
         Also output: {output_dir}/{발명명칭}_선행특허분석.md"
)
```

#### 선택: 위험 등급 선행특허 원문 PDF 확보

Gate 5 제시 전, 위험도 '중간' 이상 선행특허의 원문 PDF를 내려받아 청구항 전문으로 차별화 포인트를 재검증할 수 있다.

```bash
PYTHONUTF8=1 C:/Users/JHKIM/miniconda3/python \
  ~/.claude/skills/_shared/scripts/download_patent_pdf.py \
  --kr <applno...> --gp <GooglePatentsID...> \
  --out {output_dir}/prior_art_pdfs/ --verify
```

- KR 특허: KIPRIS `getPubFullTextInfoSearch`/`getAnnFullTextInfoSearch` 사용(출원번호 입력)
- 국외 특허: Google Patents ID 직접 사용
- `--verify` 옵션으로 첫 페이지 서지와 검색 결과가 일치하는지 자동 확인
- 상세 규칙: `~/.claude/skills/_shared/patent_pdf_download.md`

### Gate 5: 차별성 전략 결정 [필수]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
선행특허 조사 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 관련 선행특허 ({total_found}건 중 상위 {analyzed_count}건)

| # | 특허번호 | 명칭 | 출원인 | 유사도 | 위험도 |
|---|---------|------|-------|-------|-------|
{patents를 테이블로, risk_level 컬러 표시}

### 위험 특허 상세 분석 (위험도 '중간' 이상)

특허 {patent_no}:
  - 핵심 청구항: {representative_claim 요약}
  - 본 발명과 겹치는 부분: {similarity_points}
  - 차별화 가능 포인트: {difference_points}

### IFR별 선행특허 커버리지

| IFR | 개시 여부 | 차별화 요소 | 권장 조치 |
|-----|----------|-----------|----------|
{ifr_coverage를 테이블로}

### 회피설계 전략 요약
{design_around_strategy.summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 분석 결과 수용 → 발명내용설명서 작성 진행
2. 특정 IFR을 제외하고 싶음 → 번호 지정
3. 회피설계 방향을 논의하고 싶음 → 대화 진행
4. 검색 키워드/범위를 변경하여 재조사 → 키워드 입력
5. IFR 목록으로 되돌아가기 (Gate 2B) → evaluation + prior_art 무효화
6. 평가 결과로 되돌아가기 (Gate 4) → prior_art 무효화
```

**회피설계 논의 (선택 3)**: 위험 특허에 대해 사용자와 대화하며 차별화 전략 수립.
결과를 `prior_art.json`의 `design_around_strategy` 필드에 기록.

---

## Phase 6: 발명내용설명서 초안 + Gate 6

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6-disclosure-writer.md for instructions.
         Read {SHARED_SKILL_ROOT}/templates/disclosure-report.md for MD template.
         Read {SHARED_SKILL_ROOT}/reference/user-philosophy.md for inventor philosophy.
         
         Read all phase outputs from {output_dir}/:
         - triz_system.json (Phase 1)
         - triz_analysis.json (Phase 2)
         - evaluation.json (Phase 4)
         - prior_art.json (Phase 5, may be degraded)
         
         Read original source documents: {manifest.input.source_files}
         
         Input: {manifest.input}
         Output: {output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md
         
         CRITICAL REQUIREMENTS:
         1. All 9 sections (§1~§9) must be filled
         2. All 3 appendices (부록 A/B/C) must be filled
         3. section_summary in YAML frontmatter must be populated
         4. Written in Korean
         5. If prior_art is degraded, mark §3/§4/§8 with [선행특허 수동 보완 필요]
         6. After writing, update user-philosophy.md §4 with new patterns"
)
```

### Gate 6: 섹션별 검토 [필수]

`section_summary`를 사용하여 핵심 요약 먼저 제시:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
발명내용설명서 초안 완성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 핵심 섹션 요약

#### §5 발명의 목적
> {section_summary.s5.summary}

#### §6 발명의 구성 (핵심 섹션)
> {section_summary.s6.summary}

#### §8 청구범위 (초안)
> {section_summary.s8.summary}

### 전체 섹션 상태

| 섹션 | 제목 | 분량 | 상태 |
|------|------|------|------|
| §1 | 발명의 명칭 | {s1.chars}자 | 완료 |
| §2 | 논문발표 여부 | {s2.chars}자 | 완료 |
| §3 | 배경(동기) | {s3.chars}자 | 완료 |
| §4 | 종래기술 및 문제점 | {s4.chars}자 | 완료 |
| §5 | 발명의 목적 | {s5.chars}자 | 완료 |
| §6 | 발명의 구성 | {s6.chars}자 | 완료 |
| §7 | 발명의 효과 | {s7.chars}자 | 완료 |
| §8 | 청구범위 | {s8.chars}자 | 완료 |
| §9 | 추가자료 | {s9.chars}자 | 도면 삽입 예정 |

전체 파일: {output_dir}/{filename}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

선택:
1. 전체 승인 → 도면 생성 및 HWPX 변환으로 진행
2. 특정 섹션을 상세히 보고 싶음 → 섹션 번호 입력 (예: "6", "8")
3. 특정 섹션을 수정하고 싶음 → 섹션 번호 + 수정 의견
4. 청구범위를 함께 다듬고 싶음 → §8 집중 검토 모드
5. 전체 재작성 → 방향성 피드백 입력
6. 선행특허 분석으로 되돌아가기 (Gate 5) → MD 무효화
7. IFR 선별로 되돌아가기 (Gate 2B) → evaluation + prior_art + MD 무효화
```

### §8 집중 검토 모드 (선택 4)

청구항을 하나씩 표시하며 사용자와 다듬기:

```
§8 집중 검토 모드:

[독립항 1] ─────────────────────────
{청구항 전문}
────────────────────────────────────

선택:
1. 이 청구항은 적절함 → 다음 청구항으로
2. 수정할 부분이 있음 → 수정 의견 입력
3. 이 청구항을 삭제하고 싶음
4. 검토 중단 → 나머지 청구항은 현재 상태로 유지
```

#### Background Prefetch: 도면 선행 생성

Gate 6 제시 **직후**, 시스템 구성도와 공정 흐름도를 background로 선행 생성:

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase6b-diagram-generator.md for instructions (Step 1-2 only).
         Read {output_dir}/triz_system.json for system components.
         Generate system overview diagram and process flow diagram only.
         These are independent of §6 content details.
         Output: {output_dir}/diagrams/ (fig1_system_overview.png, fig2_process_flow.png)",
  run_in_background=True
)
```

> 사용자가 §6을 수정하면 §6 의존 도면만 재생성 (시스템 구성도는 유지).

---

## Phase 6b + 6c + 7: 도면 생성, 인용 검증, HWPX 변환

Gate 6 승인 후 자동 진행.

### Phase 6b 에이전트 호출

Background에서 선행 생성된 도면이 있으면 활용:

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase6b-diagram-generator.md for instructions.
         Read the Phase 6 output MD file for §6 and §9 content.
         Read {output_dir}/triz_system.json for system components.
         Read {output_dir}/evaluation.json for top IFRs.
         
         Pre-generated diagrams (if available): {output_dir}/diagrams/
         Skip regeneration for diagrams that already exist and don't depend on §6 changes.
         
         Output directory: {output_dir}/diagrams/
         Also update: the MD file §9 with diagram references
         Use matplotlib Korean font: plt.rcParams['font.family'] = 'Malgun Gothic'"
)
```

### Phase 6c 에이전트 호출

발명내용설명서 MD의 모든 인용문헌(학술 논문·KR/외국 특허·DOI·보고서)을 외부 DB(KIPRIS Plus, CrossRef, OpenAlex, Semantic Scholar, Google Patents)로 직접 조회하여 번호·제목·저자·출원인의 정합성을 검증하고, 부록 C 각 항목에 `(정합 확인!)` 마커를 삽입하며, 원문 PDF를 `{output_dir}/reference/` 에 저장한다.

#### KIPRIS API 키 로드

```bash
if [ -f "C:/Users/JHKIM/Claude_Work/.env" ]; then
  set -a
  eval "$(cat 'C:/Users/JHKIM/Claude_Work/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
  set +a
fi
```

#### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase6c-reference-verifier.md for instructions.
         Read the Phase 6 output MD file (latest vN.md in {output_dir}, with Phase 6b diagrams inserted) for citation extraction.
         Read {output_dir}/prior_art.json for Phase 5 patent metadata.
         
         KIPRIS .env file: {KIPRIS_ENV_FILE}
         Patent PDF downloader: ~/.claude/skills/_shared/scripts/download_patent_pdf.py
         Zettelkasten 로컬 캐시: D:/Zettelkasten/References/ (학술 논문 1차 조회 경로)
         
         Before calling download scripts, load env vars:
         set -a && eval \"$(cat '{KIPRIS_ENV_FILE}' | sed 's/^[[:space:]]*//' | grep -v '^#')\" && set +a
         
         Input: {manifest.input}
         Outputs:
           (1) {output_dir}/reference/ (다운로드된 PDF 모음)
           (2) {output_dir}/reference_verification.json
           (3) 업데이트된 Phase 6 MD (vN 유지, (정합 확인!) 마커 + 부록 C.5 요약 추가)
         
         CRITICAL REQUIREMENTS:
         1. KR 특허는 download_patent_pdf.py --kr --verify 로 출원번호-제목 자동 대조
         2. 학술 논문은 CrossRef DOI 확인 → OpenAlex OA URL → Zettelkasten 캐시 순으로 PDF 확보
         3. PDF 첫 페이지 제목 불일치 시 PDF 폐기, (정합 불일치) 마커 삽입
         4. KIMM 내부 자문(구두)은 검증 대상 아님 — 스킵
         5. 부록 C.5 섹션 새로 추가하여 검증 요약표 작성
         6. §1~§9 본문은 수정하지 않음 (inline 인용 번호는 부록에서 검증된 것을 참조)"
)
```

#### 검증 요약 표시 (Gate 없음, 정보 표시)

Phase 6c 완료 직후, Phase 7 진입 전에 결과를 화면에 표시한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 인용문헌 정합성 검증 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 구분 | 건수 |
|------|------|
| 총 인용 | {total} |
| ✅ 완전 확인 | {verified} |
| ⚠️ 부분 확인 | {partial} |
| ❌ 불일치 | {mismatch} |
| 🔍 수동 검토 | {manual_review} |
| 📄 PDF 확보 | {pdf_count} |

> 수동 검토 필요 항목은 부록 C에 (정합 불일치 — 수동 확인 필요) 또는 (정합 부분 확인 — 수동 재검토 필요) 마커로 표시됨.
> 원문 PDF: {output_dir}/reference/
> 상세 로그: {output_dir}/reference_verification.json

▶ Phase 7 (HWPX 변환)을 시작합니다...
```

> 이 표시는 Gate가 아니다 — 사용자 응답 없이 바로 Phase 7로 진행한다. 단, `(mismatch + manual_review) / total > 0.3` 이면 한 번 사용자 확인을 요청한다 (Phase 7 진행 vs 수동 보완 후 재개 선택).

#### Graceful Degradation

- KIPRIS API 실패: 해당 KR 특허는 `manual_review`, 다른 인용은 계속 처리
- Google Patents 봇 차단: WebFetch 폴백 → 그래도 실패 시 `manual_review`
- CrossRef/Semantic Scholar 실패: Zettelkasten 캐시만으로 PDF 확보 시도, 메타데이터는 `partial`
- Zettelkasten 접근 불가: 메타데이터 검증만 진행, PDF는 skipped
- MD 부록 C 미존재: Phase 6c 스킵, 사용자에게 "인용문헌 수동 검증 필요" 안내

#### 출력 MD 업데이트 규칙

부록 C의 각 항목 **뒤에** 마커를 삽입한다 (기존 텍스트는 수정하지 않음):

- 완전 검증 + PDF 확보: `... (정합 확인!) — [PDF](reference/xxx.pdf)`
- 완전 검증 + PDF 미확보: `... (정합 확인! — PDF 미확보)`
- 부분 일치: `... (정합 부분 확인 — 수동 재검토 필요)`
- 불일치: `... (정합 불일치 — 수동 확인 필요)`
- KIMM 내부 자문(C.2): 마커 삽입하지 않음

부록 C 하단에 새 하위 섹션 `### C.5 정합성 검증 요약` 을 추가한다 (`{SKILL_ROOT}/agents/phase6c-reference-verifier.md` 스펙 참조).

manifest 업데이트:
```json
"phase6c": {
  "status": "completed|degraded",
  "output": "reference_verification.json",
  "pdf_count": N,
  "verified": K, "mismatch": M, "manual_review": R
}
```

### Phase 7 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase7-hwpx-converter.md for instructions.
         Read {SHARED_SKILL_ROOT}/reference/kimm-template-mapping.md for cell mapping.
         Read the Phase 6 output MD file.
         
         Template: {SHARED_SKILL_ROOT}/assets/[KIMM]직무발명내용설명서_양식.hwpx
         fix_namespaces: {HWPX_SKILL}/scripts/fix_namespaces.py
         validate: {HWPX_XML_SKILL}/scripts/validate.py
         
         Output: {output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.hwpx
         
         MUST USE STRATEGY A (전체 셀 내용 교체).
         After replacement: run fix_namespaces.py, then validate.py."
)
```

### HWPX 변환 특성 (v15 기준)

`convert_hwpx.py`는 다음 규칙으로 bullet/내어쓰기를 렌더링한다:

1. **paraPrIDRef 순차 ID**: header.xml의 기존 `paraPr(0..max)` 뒤에 순차 ID로 새 paraPr 추가. paraPrIDRef는 배열 인덱스로 조회되므로 건너뛴 ID(예: 100)는 `paraPr[0]` fallback되어 intent 무시됨.
2. **paraPr.margin.intent 음수**: L1=-3072(case)/-6144(default), L2=-4572/-9144, L3=-6072/-12144. case(2016 HwpUnitChar) : default(legacy HWPUNIT) = 1:2 비율.
3. **snapToGrid="1"**: intent 렌더링 활성화 필수.
4. **lineseg flags**: 첫줄 `393216`, 연속줄 `1441792`. `2490368`(wrap 없음 신호) 사용 금지.
5. **텍스트 전각 공백**: 테이블 셀 내 paraPr.left가 무시되므로 U+3000으로 시각적 계층 들여쓰기.

상세 규칙: `{SHARED_SKILL_ROOT}/reference/hwpx-format-insights.md` 참조.

### Fallback

validate.py 실패 시: MD 파일만 최종 출력 제공.

---

## Gate 7: 최종 확인 [auto-skip 가능]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
발명내용설명서 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 출력 파일
- {filename}.md — Obsidian 호환 마크다운 (9개 섹션 + 부록 3개, 부록 C에 (정합 확인!) 마커 포함)
- {filename}.hwpx — KIMM 양식 한글 파일
- 선행특허분석.md — KIPRIS 분석
- diagrams/ — 기술 도면 {N}개
- reference/ — 인용문헌 원문 PDF {K}건 (학술 논문 + 선행특허)
- reference_verification.json — 인용문헌 정합성 검증 로그

### 워크플로우 히스토리

| 단계 | 결과 | 사용자 결정 |
|------|------|-----------|
| Gate 0 | 입력 확정 | {gates.gate_0 요약} |
| Gate 1 | 시스템 모델 | {gates.gate_1 요약} |
| Gate 2A | 모순 {N}개 | {gates.gate_2a 요약} |
| Gate 2B | IFR {N}개 → {M}개 선별 | {gates.gate_2b 요약} |
| Gate 4 | 평가 상위 3 | {gates.gate_4 요약} |
| Gate 5 | 선행특허 {N}건 | {gates.gate_5 요약} |
| Gate 6 | 초안 완성 | {gates.gate_6 요약} |
| Phase 6c | 인용 검증 {verified}/{total} 정합 | (Gate 없음, 자동 진행) |

### TRIZ 분석 요약
- 기술적 모순: {N}개 도출
- 물리적 모순: {N}개 도출
- IFR: {N}개 생성, 상위 3개 → 발명내용설명서 반영

### 다음 단계
1. HWPX 파일을 한/글에서 열어 서식과 내용 확인
2. 필요 시 각 섹션 내용 보완
3. 발명심의위원회 제출
```

---

## 되돌림(Backtrack) 규칙

### 되돌림 경로와 무효화 체인

| 현재 Gate | 되돌림 대상 | Gate 선택지 번호 | 무효화되는 하류 출력 |
|----------|-----------|----------------|-------------------|
| Gate 1 | Gate 0 | 선택 2 | triz_system → triz_analysis → evaluation → prior_art → MD |
| Gate 2A | Gate 1 | 선택 5 | triz_system 수정 → triz_analysis → evaluation → prior_art |
| Gate 2B | Gate 2A | 선택 5 | triz_analysis IFR 재생성 → evaluation → prior_art |
| Gate 4 | Gate 2B | 선택 5 | evaluation → prior_art |
| Gate 5 | Gate 2B | 선택 5 | evaluation → prior_art → MD |
| Gate 5 | Gate 4 | 선택 6 | prior_art (검색 키워드 변경 시만) |
| Gate 6 | Gate 5 | 선택 6 | MD 재작성 |
| Gate 6 | Gate 2B | 선택 7 | evaluation → prior_art → MD |

### 무효화 규칙

1. **모순 변경** (Gate 2A): 변경된 모순에 연결된 IFR만 재생성. 사용자가 "전체 재생성" 요청 시 모든 IFR 재생성.
2. **IFR 변경** (Gate 2B): evaluation.json 전체 무효화. prior_art.json도 무효화.
3. **평가만 변경** (Gate 4): 순위만 재계산. prior_art.json은 유효 (IFR 집합 불변 시).
4. **선행특허만 변경** (Gate 5): MD만 무효화.

### Background Prefetch 무효화

| 사용자 행동 | 무효화 대상 | 처리 |
|------------|-----------|------|
| Gate 2A에서 모순 수정 | KIPRIS 예비 검색 결과 | 폐기, 새 키워드로 재검색 |
| Gate 2B에서 IFR 변경 | KIPRIS 정밀 검색 결과 | 폐기, 새 IFR 키워드로 재검색 |
| Gate 2B 되돌림 → Gate 2A | 모든 백그라운드 결과 | 전체 폐기 |
| Gate 6에서 §6 수정 | 선행 생성된 도면 | §6 의존 도면만 재생성 (시스템 구성도는 유지) |

### 되돌림 시 manifest 기록

```json
"backtrack_log": [
  {"from": "gate_4", "to": "gate_2b", "reason": "IFR-3 재검토", "invalidated": ["evaluation.json"], "timestamp": "..."}
]
```

---

## user-philosophy.md 통합

- Phase 6 에이전트가 `{SHARED_SKILL_ROOT}/reference/user-philosophy.md`를 읽어 발명 스타일에 반영
- Phase 6 완료 후 `user-philosophy.md` §4(발명 패턴)을 새 발견사항으로 업데이트
- Gate 6에서 사용자가 §6/§8을 수정하면, 수정 패턴도 user-philosophy.md에 반영

---

## Error Handling Summary

| Phase | 실패 모드 | 대응 |
|-------|-----------|------|
| Phase 2 | IFR < 10개 | 재시도 2회, 이후 현재 결과로 진행 |
| Phase 5 | KIPRIS API 실패 | graceful degradation, 수동 보완 안내 |
| Phase 6 | 섹션/부록 누락 | 1회 재생성, 이후 부분 결과 제공 |
| Phase 6b | matplotlib 실패 | Mermaid만 MD에 포함 |
| Phase 6c | KIPRIS/CrossRef API 실패 | 해당 인용은 manual_review, 나머지 계속 진행 |
| Phase 6c | PDF 첫 페이지 제목 불일치 | PDF 폐기 + (정합 불일치) 마커 삽입 |
| Phase 6c | MD 부록 C 미존재 | Phase 6c 스킵 + 사용자에게 수동 검증 안내 |
| Phase 7 | HWPX 변환/validate 실패 | MD fallback |
| Background | prefetch 실패 | Phase 5에서 정상 검색 실행 (성능 저하만) |
