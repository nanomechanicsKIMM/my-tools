# patent-incubation: 사용자 주도형 발명 워크플로우

사용자와 긴밀하게 소통하며 발명 아이디어를 체계적으로 발전시키는 스킬. TRIZ 분석 → 모순 도출 → IFR 생성 → 평가 → 선행특허 → 발명내용설명서(KIMM 양식)까지, 모든 단계에서 사용자가 판단하고 선택한다.

## When to Use

- 사용자가 발명 아이디어를 함께 발전시키고 싶을 때
- "발명 인큐베이션", "patent incubation", "발명 같이 하자", "아이디어 발전" 언급 시
- 기존 `patent-incubation-auto`의 자동화 모드 대신, 각 단계를 직접 검토하며 진행하고 싶을 때

## Skill Constants

```
SKILL_ROOT = ~/.claude/skills/patent-incubation-interactive
SHARED_SKILL_ROOT = ~/.claude/skills/patent-incubation-auto
HWPX_SKILL = ~/.claude/skills/hwpx
HWPX_XML_SKILL = ~/.claude/skills/hwpx-xml
KIPRIS_ENV_FILE = ~/Claude_Work/.env
```

> [!note] OS별 경로 해석
> `~`는 홈 디렉토리로 해석한다 (Windows: `C:/Users/JHKIM`, macOS: `/Users/<user>`).
> `KIPRIS_ENV_FILE`이 존재하지 않으면 환경변수 `KIPRIS_API_KEY`/`KIPRIS_REST_ACCESS_KEY`를
> 직접 확인하고, 둘 다 없으면 Phase 5/6c는 degraded 모드로 진행한다.
> Python 실행은 `python3`(PATH 우선)를 사용한다 (Windows에서 미탐지 시 `~/miniconda3/python`).

### 공유 자원 (patent-incubation-auto에서 참조)

```
reference/   → {SHARED_SKILL_ROOT}/reference/
templates/   → {SHARED_SKILL_ROOT}/templates/
scripts/     → {SHARED_SKILL_ROOT}/scripts/   (convert_hwpx.py·search_patents_kipris.py — auto의 assets/ 의존)
assets/      → {SHARED_SKILL_ROOT}/assets/
```

> [!note] SVG 도면 변환 스크립트 예외
> `svg2png.py`·`svg2emf.py`·`outline_svg_text.py`는 assets 의존이 없는 독립 변환기로
> **interactive/scripts/에 로컬 번들**되어 `{SKILL_ROOT}/scripts/`로 참조한다.
> 반면 `convert_hwpx.py`는 auto의 `assets/` 양식 템플릿(`TEMPLATE_PATH=SKILL_ROOT/assets/...`)에
> 의존하므로 반드시 `{SHARED_SKILL_ROOT}/scripts/`(=auto)에서 실행한다.

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
| 기술 단면도·구조도·schematic | **손코딩 SVG** ⭐ | figures/*.svg → svg2png.py로 PNG 변환, EMF/outlined로 PowerPoint (Phase 6b Step 3) |
| 물리 기하·정량 상충 중심 발명 | **matplotlib 실척·계산 도면** ⭐ (2026-07-16) | 실척 좌표계 + 물리 계산 광선 + 재료 적층 + 정량 차트. PNG(300 dpi)+SVG(fonttype=path) 동시 저장 — `reference/detailed-figures.md` (Phase 6b Step 4-0) |
| HWPX 삽입용 | **PNG (SVG→PNG 우선, matplotlib는 데이터 플롯)** | diagrams/*.png를 convert_hwpx.py가 §9에 자동 삽입 |

> [!important] Phase 6b 도면 필수 규칙 (상세: agents/phase6b-diagram-generator.md)
> - **규칙 A (원본 재활용)**: 사용자 제공 자료(제안서 HWPX BinData·선행 등록공보 PDF 도면·기획서)의 그림을 먼저 추출·Read하여 근거로 삼고, 신규 발명에 맞게 깨끗한 SVG로 재작도한다. 원본의 부품 번호(참조 부호)는 제거하고 **부품 이름 라벨로 대체**한다(규칙 D).
> - **규칙 B (텍스트 절대 비겹침)**: 모든 텍스트는 도형과 절대위치로 겹치지 않는다. 제목=상단 밴드, 설명=예약 legend 박스, 구성요소 라벨=부품 이름 텍스트(여백+leader line, 부품 위 직접표기 금지). 생성 후 Read로 육안 검증 필수.
> - **규칙 C (도면 ↔ 설명 동기화, 2026-07 신설 / 2026-07-13 개정)**: 도면이 신규·교체·업데이트되면(특히 사용자 제공 원도 pptx/이미지를 삽입할 때) 각 도면의 실제 내용(라벨·구성요소·신호 흐름·좌표축)을 Read 또는 텍스트 추출(python-pptx 등)로 파악하여, §9의 도면 목록(내용 기반 제목)과 본문 참조를 그 내용에 맞게 일치시킨다. **도면 번호([도 N])별 설명 목록("도 1은 ~" 형식)은 작성하지 않는다**(규칙 D). 도면 개수·순서·주제가 바뀌면 제목 목록·순서도 일치시키고 관련 청구항 링크를 갱신한다. 사용자 원도 삽입 시 600 dpi PNG 변환(PowerPoint COM: 슬라이드 in×600 픽셀) 후 `diagrams/`에 배치하면 convert_hwpx.py가 §9에 삽입한다.
> - **규칙 D (도면 번호·부호 미사용, 2026-07-13 신설, NON-NEGOTIABLE)**: 도면 내 구성요소 라벨은 **부품 이름 텍스트만** 사용(참조 부호 10·100 등 금지). 문서·슬라이드 캡션에 "[도 N]" 번호를 노출하지 않고, §9에 도면부호 목록 테이블·번호별 설명을 작성하지 않으며, §6·§8에서 부호 괄호 병기("챔버(10)")를 하지 않는다. 사유: 출원용 정식 도면·부호 체계는 변리사가 별도 작성 — 내부 번호가 오해 유발. 파일명 `figN_` 접두사는 삽입 순서 관리용으로만 유지.

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

### 참고문헌 정합 검증 규칙 (필수, 2026-07 개정 — 클린 리스트 원칙)

> [!important] 클린 리스트 원칙 (NON-NEGOTIABLE)
> 발명신고서 §9 참고문헌 리스트에는 **검증된 실제 문헌의 서지 정보만** 기재한다.
> `(정합 확인!)`·`[정정:...]`·`(삭제)`·`(정합 불일치)` 등 마커·편집문구를 리스트에
> **절대 넣지 않는다.** 무엇을 정정·삭제했는지의 검증 이력은 `reference_verification.json`
> (audit trail)에만 남긴다. 리스트는 순수 서지만 남는다.

§9 참고문헌 및 본문 인용의 모든 외부 문헌(논문·특허)은:

1. **DOI 링크 기재** (논문): `https://doi.org/10.XXXX/...` 형식
2. **KIPRIS 링크 또는 특허번호 기재** (한국 특허): `https://doi.org/10.8080/10YYYYNNNNNNN` 또는 `KR 10-XXXXXXX`
3. **CrossRef/KIPRIS API로 번호·제목·저자·연도 실제 검증**(Phase 6c). 결과는 reference_verification.json에 status(verified/corrected/removed)로 기록.
4. **검증 실패·실재 불명 문헌은 리스트에서 제거**하고, 본문 inline 인용을 gap 없이 `[1]~[N]` 순차로 **재번호**한다. 제거·정정 이력은 json에만 기록.
5. 최종 리스트에는 마커·주석·정정표기가 없어야 한다.

**강제 게이트**: `{SKILL_ROOT}/scripts/verify_citations.py` 가 (1) 리스트에 편집문구가 없는지, (2) 각 참고문헌이 json 검증 항목과 DOI/특허번호로 매칭되는지, (3) removed 문헌이 재등장하지 않는지 검사. exit!=0 이면 Phase 7 차단.

**KIPRIS API 키**: `{KIPRIS_ENV_FILE}`의 `KIPRIS_REST_AccessKey` 사용.

**잘못된 인용 탐지 패턴**: 저자·제목·저널·연도 조합이 실제 논문과 다르거나, 같은 PII가 서로 다른 참고문헌에 중복 사용되면 **환각 의심** → 재검증 또는 제거.

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
Phase 6.5: 청구항 하드닝 ────────── (112b·트리·권리범위·거절대응 점검)
  ├─ Gate 6.5: 청구항 확정 ──────── 사용자 판단 [필수]
  │
Phase 6b: 도면 생성 ─────────────── sonnet 에이전트 (컬러 SVG → PPTX 덱 → 600dpi PNG, Background 결과 활용)
Phase 6c: 인용문헌 정합성 검증 ──── sonnet 에이전트 (KIPRIS + CrossRef + OpenAlex + Zettelkasten)
  └─ 강제 게이트: verify_citations.py (exit!=0 → Phase 7 차단)
Phase 6d: Critic 검증 게이트 ────── opus 에이전트 (출처·모순/IFR·청구항 특허성)
  └─ Gate 6d: critic 판정 처리 ──── PASS 자동 진행 / FIX 1회 보정 / BLOCK 사용자 판단 [BLOCK은 auto-skip 불가]
Phase 6e: 사업화 Critic ─────────── opus 에이전트 (삼성전자 전담 변리사 페르소나 — 회피설계·침해 입증·사업 판단)
  └─ Gate 6e: 사업화 판정 처리 ──── PASS 자동 진행 / FIX 1회 보정 / ADVISE 사용자 판단 [ADVISE는 auto-skip 불가]
Phase 7: HWPX 변환 ──────────────── sonnet 에이전트 (정합 반복 최대 3회)
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
    "inventor": "주발명자명 (하위호환 키 = inventors[0])",
    "inventors": ["주발명자", "공동발명자1", "..."],
    "affiliation": "소속기관(출원인 예정, 선택) — Phase 5 Step 0-B 자기선행 특허 조사에 사용. 정보 없으면 사용자 1인 위주 조사",
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
    "phase6e": {"status": "pending", "output": null},
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
| Gate 6.5 | **조건부** (issue 0건 시 skip) | 청구항은 핵심 자산 — issue 1건 이상이면 확인 필수 |
| (Phase 6c 강제 게이트) | **불가** | verify_citations.py exit!=0 이면 Phase 7 차단 (기계적 게이트, auto-skip 불가) |
| Gate 6d | **조건부** (PASS 시 skip, FIX는 1회 자동보정) | critic **BLOCK**(critical: 성격 오규정·미검증 인용·독립항 reject)은 auto-skip 불가 — 사용자 판단 필수 |
| Gate 6e | **조건부** (PASS 시 skip, FIX는 1회 자동보정) | 사업화 critic **ADVISE**(보정 불가한 전략 한계 — 원리적 회피 경로·등급 C 계열 유지 판단)는 auto-skip 불가 — 수용 여부는 발명자 판단 |
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
KIPRIS_ENV="$HOME/Claude_Work/.env"
if [ -f "$KIPRIS_ENV" ]; then
  set -a
  eval "$(cat "$KIPRIS_ENV" | sed 's/^[[:space:]]*//' | grep -v '^#')"
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
         Also output: {output_dir}/{발명명칭}_선행특허분석.md

         MANDATORY (다국가 국제 검색 — 2026-07-06 필수 격상):
         - 독립항 신규성 앵커 개념을 영문 키워드로 변환하여 Google Patents WebFetch
           3~5쿼리로 KR/US/JP/EP/WO 검색 (agent 문서 S5 참조). 국내 한정 조사로
           novel 판정 금지. 검출 문헌의 방식은 원문 WebFetch 로 직접 확인.

         MANDATORY (자기선행 특허 조사 — 2026-07-06 신설, agent 문서 Step 0-B):
         - manifest input.inventors[](공동발명자)·input.affiliation(소속기관)으로
           KIPRIS 국내 중심 발명자·출원인 검색(정보 없으면 사용자 1인 위주).
         - 자기선행의 청구범위 + 배경기술·명세서 개시 요소 파싱, 공지예외 12개월 기한
           산정 → prior_art.json self_prior_art[] 기록. Gate 5 표시에 포함."
)
```

#### 선택: 위험 등급 선행특허 원문 PDF 확보

Gate 5 제시 전, 위험도 '중간' 이상 선행특허의 원문 PDF를 내려받아 청구항 전문으로 차별화 포인트를 재검증할 수 있다.

```bash
PYTHONUTF8=1 python3 \
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

### 예상 거절 조합 (필수, 단일 유사도만으로 판단 금지)

> 단일 선행문헌 유사도가 낮아도 심사관은 2~3건 조합으로 진보성을 공격한다.
> 각 독립항마다 최소 1개의 가상 조합 거절 시나리오와 방어 논거를 제시한다.

| 독립항 | 예상 조합 (주인용 + 부인용) | 결합 동기 유무 | 방어 논거(요지) |
|--------|--------------------------|--------------|----------------|
| 독립항 N | {main_ref} + {secondary_ref} | 없음/약함/있음 | teaching away / 결합 곤란 / 상승효과 |

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
         6. After writing, update user-philosophy.md §4 with new patterns
         7. 참고문헌 리스트에는 (정합 확인!)·[정정]·(삭제) 등 마커/편집문구를 절대 넣지
            말 것. 검증되지 않은 문헌은 애초에 넣지 않는다(추정 인용 금지). 검증·정정·제거는
            Phase 6c가 수행하고 이력은 reference_verification.json에만 기록한다.
         8. 참고문헌은 '- [N] 저자, \"제목\", 저널, 연도. DOI/KIPRIS' 형식의 순수 서지 리스트로
            기재(마커 없음). Phase 6c 파서(verify_citations.py)가 DOI/특허번호로 검증 매칭한다."
)
```

> [!warning] 클린 리스트 / 마커 위조 방지 (2026-07)
> 실제 run에서 Phase 6c가 누락됐는데 작성 에이전트가 참고문헌 20건 전부에
> (정합 확인!)을 임의 부착 → CrossRef 재검증 시 학술 DOI 6건이 404/무관논문/제목오류로
> 판명된 사고가 있었다. 대책: (a) 리스트에는 검증된 서지만, 마커·편집문구 금지, (b) Phase 6c가
> 검증·정정·제거·재번호를 수행하고 이력은 reference_verification.json에만 기록, (c) 강제 게이트
> verify_citations.py로 재발 차단.

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

## Phase 6.5: 청구항 하드닝 + Gate 6.5 [필수]

Gate 6 승인 직후, 도면·HWPX 변환 이전에 청구항 자체를 법적 관점에서 점검한다.
발명의 최고가치 산출물은 청구항이므로 서식(HWPX)보다 먼저 확정한다.

### 점검 항목 (§8 대상)

1. **112(b) antecedent basis**: 각 종속항의 구성요소가 인용 독립항에 선행 기재됐는지. "상기 ~"의 선행어 존재 확인.
2. **청구항 트리 정합**: 독립항-종속항 인용 관계, 카테고리 일치(장치 종속항이 방법 독립항을 인용하지 않는지).
3. **권리범위 계층**: 독립항이 불필요하게 좁지 않은지(광역 유지), 종속항이 fallback 방어선을 단계적으로 형성하는지.
4. **선행특허 회피 반영**: Gate 5의 예상 거절 조합에 대응하는 한정 요소가 최소 하나의 종속항으로 준비됐는지.
5. **수치 한정 위치**: 독립항은 수치 무한정(광역), 수치 한정은 종속항으로 이동됐는지(변리사 메모 반영).
6. **카테고리 포트폴리오 (2026-07-06)**: 물건+방법 병행(필수) + 소자·시스템(센서/제어 요소 있을 때) 추가 검토 — 최대 4축.
7. **SMART5/KPAS 활용성·시장성 레버 (2026-07-06 / 2026-07-13 개정)**: §9에 파급/사업화 블록(적용 시장·후속출원 구조·PCT/삼극 패밀리 플랜)이 실질 내용으로 존재하는지. (도면부호 목록 테이블은 2026-07-13 폐지 — 규칙 D 도면 번호·부호 미사용 정책.)
8. **안티게이밍 검사 (2026-07-06)**: 6·7이 자동등급(SMART5/KPAS) 지표용 빈 문구·부풀리기가 아닌지 — 발명사상이 지지하지 않는 카테고리·근거 없는 시장 서술이면 issue 플래그. 자동점수 ≠ 실제 권리강도, 신규성·품질 우선.
9. **회피설계 차단 매트릭스 (사업화, 2026-07-10 — claim-drafting.md §11)**: 각 독립항마다 경쟁사 회피 시나리오(치환·생략·공정변경·공급망 분리·실시주체 분산, E1~E5) 최소 2개가 상정되고, 각각 대응 차단 청구항(상위개념 문언/병렬 독립항/봉쇄 종속항)이 존재하는지. 부록 B.4 매트릭스 기록 여부 — 부재 시 §8·§6 근거로 생성하여 추가.
10. **침해 검출성 등급 (사업화, 2026-07-10 — claim-drafting.md §12)**: 전 청구항에 검출성 등급(A: 제품 관찰 / B: 리버스엔지니어링 / C: 내부 정보 필요) 부여 + **최소 1개 독립항이 등급 A/B**인지. 방법 발명은 공정 지문 물건항 병행 여부. 부록 B.5 테이블 기록 여부 — 테이블 부재는 생성, 등급 A/B 독립항 부재는 issue(청구항 신설 문안은 Phase 6e가 제안).
11. **도면 번호·부호 부재 검사 (2026-07-13 신설 — 규칙 D)**: §6 본문·§8 청구항에 도면 부호 괄호 병기("챔버(10)")가 없는지, §9에 도면부호 목록·"[도 N]" 번호별 설명이 없는지, 도면 라벨이 부품 이름 기반인지. 발견 시 부호 제거·이름 치환.

### Gate 6.5 표시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
청구항 하드닝 점검 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 점검 | 결과 | 조치 필요 |
|------|------|----------|
| antecedent basis | {pass/issue N건} | ... |
| 청구항 트리 정합 | ... | ... |
| 권리범위 계층 | ... | ... |
| 거절 조합 대응 | ... | ... |
| 회피설계 차단(B.4) | {독립항별 시나리오/차단 요약} | ... |
| 침해 검출성(B.5) | {등급 A/B 독립항 유무} | ... |

선택:
1. 청구항 확정 → 도면·HWPX 변환 진행
2. 특정 청구항 수정 → 번호 + 의견
3. 선행특허 재검토 (Gate 5)
```

> 참고: 기존 `patent-draft-review` / `review-claims` 스킬을 이 단계에서 호출 가능.
> auto-proceed 지시가 있어도 issue가 1건 이상이면 1회 사용자 확인을 요청한다.

manifest 업데이트: `phase6_5: {status, issues_found, resolved}`

---

## Phase 6b + 6c + 6d + 6e + 7: 도면 생성, 인용 검증, Critic 2단(등록 가능성·사업화), HWPX 변환

Gate 6.5 승인 후 자동 진행 (단, 6d BLOCK·6e ADVISE는 사용자 판단).

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
         
         Output directories: {output_dir}/diagrams/ (HWPX 임베드용 PNG 취합), {output_dir}/figures/ (SVG 벡터 원본 + emf/pptx)
         Also update: the MD file §9 with diagram references

         도면 유형별 도구 (phase6b 정책표 — 한 도면에 혼용 금지):
         - 흐름도·구성도·상태도·비교표 → Mermaid (MD 인라인 삽입)
         - 기술 단면도·구조도·schematic → 손코딩 컬러 SVG(figures/*.svg)
         - 물리 기하·정량 상충 중심 발명 → matplotlib 실척·계산 도면 1차 경로
           (reference/detailed-figures.md, Step 4-0 — 실척 치수·물리 계산 광선·재료 적층·정량 차트,
           PNG 300dpi + SVG(svg.fonttype=path) 병행 저장, Read 육안 검증 루프)
         - 데이터 플롯 → matplotlib(dpi=600) → {output_dir}/diagrams/

         MANDATORY (2026-07-06 개편 — agent 문서 Step 1·3-2):
         - 필수 3종 포함 최소 5매, 컬러: 특허 배경 그림 + 종래기술 비교도 +
           활용 가능성·파급효과 그림 (+ 시스템 구성도·단면도 등). 종래=적색 vs 본 발명=청색 대비.
         - PIPELINE: 컬러 SVG 1차 생성 → 'python {SKILL_ROOT}/scripts/outline_svg_text.py
           --src {output_dir}/figures/ --dst {output_dir}/figures/pptx/' 로 텍스트→path
           outline → {output_dir}/figures_deck.pptx 조립(PowerPoint COM AddPicture로
           outlined SVG 직접 삽입 — 편집 가능, PNG 래스터 삽입 금지, 슬라이드 번호 =
           도면 번호 1:1, 표지 없음, 패키지 ppt/media/*.svg 파트 수 검증) →
           600 dpi PNG('python {SKILL_ROOT}/scripts/svg2png.py --src {output_dir}/figures/
           --dst {output_dir}/diagrams/ --dpi 600', 원본 SVG 기준) → diagrams/ 취합.
         모든 PNG는 diagrams/로 취합되어 convert_hwpx.py가 알파벳순으로 §9에 삽입한다. 파일명은 fig1_, fig2_ … 접두사.
         Use matplotlib Korean font: plt.rcParams['font.family'] = 'Malgun Gothic'"
)
```

### Phase 6c 에이전트 호출

발명내용설명서 MD의 모든 인용문헌(학술 논문·KR/외국 특허·DOI·보고서)을 외부 DB(KIPRIS Plus, CrossRef, OpenAlex, Semantic Scholar, Google Patents)로 직접 조회하여 번호·제목·저자·출원인의 정합성을 검증하고, **참고문헌 리스트를 검증된 실제 문헌의 순수 서지만 남도록 정리(미검증·실재 불명 문헌 제거 + 본문 inline 인용을 gap 없이 재번호)** 하며, 검증 이력은 `reference_verification.json`에 기록하고, 원문 PDF를 `{output_dir}/reference/` 에 저장한다. **리스트에는 (정합 확인!)·[정정]·(삭제) 등 마커·편집문구를 넣지 않는다.**

#### KIPRIS API 키 로드

```bash
KIPRIS_ENV="$HOME/Claude_Work/.env"
if [ -f "$KIPRIS_ENV" ]; then
  set -a
  eval "$(cat "$KIPRIS_ENV" | sed 's/^[[:space:]]*//' | grep -v '^#')"
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
         Zettelkasten 로컬 캐시: D:/Zettelkasten/References/ (Windows) 또는 ~/Zettelkasten/References/ (macOS) — 학술 논문 1차 조회 경로, 미존재 시 skip
         
         Before calling download scripts, load env vars:
         set -a && eval \"$(cat '{KIPRIS_ENV_FILE}' | sed 's/^[[:space:]]*//' | grep -v '^#')\" && set +a
         
         Input: {manifest.input}
         Outputs:
           (1) {output_dir}/reference/ (다운로드된 PDF 모음)
           (2) {output_dir}/reference_verification.json (검증 audit: status verified/corrected/removed + renumber_map)
           (3) 정리된 Phase 6 MD (vN 유지): 참고문헌=검증 서지만, 마커 없음, 미검증 제거 후 gap 없이 재번호
         
         CRITICAL REQUIREMENTS:
         1. KR 특허는 download_patent_pdf.py --kr --verify 로 출원번호-제목 자동 대조
         2. 학술 논문은 CrossRef DOI 확인 → OpenAlex OA URL → Zettelkasten 캐시 순으로 PDF 확보
         3. 참고문헌 위치 비의존: §9 또는 부록 어디에 있든 '- [N] ...' 리스트를 모두 찾아 검증
         4. KIMM 내부 자문(구두)은 검증 대상 아님 — 스킵(리스트에 넣지 않음)
         5. 검증 실패·실재 불명·중복 문헌은 리스트에서 제거하고, 본문 inline [N] 인용을 gap 없이 재번호.
            제거·정정 이력은 reference_verification.json(citations[].status, renumber_map)에만 기록
         6. 최종 리스트에는 마커·편집문구((정합 확인!)/[정정]/(삭제)/(불일치)) 금지 — 순수 서지만
         7. 재번호로 바뀐 inline 인용을 §3~§8·표·부록 전체에서 일관 갱신(단, 참고문헌 리스트 자체 제외)
         8. 모든 정리 완료 후 반드시 강제 게이트를 실행한다:
            python {SKILL_ROOT}/scripts/verify_citations.py --md <MD> --verification <reference_verification.json>
            exit!=0 이면 Phase 7로 진행 금지 (편집문구 잔존/미검증 문헌/6c 미실행 차단)."
)
```

#### 강제 게이트: verify_citations.py [필수, auto-skip 불가]

Phase 6c 에이전트 종료 후, 오케스트레이터가 직접 게이트를 실행한다:

```bash
PYTHONUTF8=1 python {SKILL_ROOT}/scripts/verify_citations.py \
  --md "{output_dir}/{발명명칭}vN.md" \
  --verification "{output_dir}/reference_verification.json"
```

| exit | 의미 | 조치 |
|------|------|------|
| 0 | 리스트 클린(편집문구 없음) + 모든 참고문헌이 검증 문헌과 DOI/특허번호 매칭 | Phase 7 진행 |
| 1 | 편집문구 잔존 / 미검증 문헌 존재 / removed 문헌 재등장 | 리스트 정리(제거·재번호) 후 재실행 |
| 2 | reference_verification.json 부재 또는 참고문헌 미검출 | Phase 6c 재실행 (미실행 상태) |

> 이 게이트는 "리스트=검증된 순수 서지"를 결정적으로 보증한다. 스킬 자기검증 테스트는
> `{SKILL_ROOT}/scripts/` 에서 클린/편집문구/미검증/미실행 fixture로 exit 0/1/1/2 를 확인했다.

#### 검증 요약 표시 (Gate 없음, 정보 표시)

Phase 6c 완료 직후, Phase 7 진입 전에 결과를 화면에 표시한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 인용문헌 정합성 검증 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 구분 | 건수 |
|------|------|
| 원 인용 | {total} |
| ✅ 검증(verified/corrected) | {verified} |
| ✂️ 제거(removed·미검증·실재불명) | {removed} |
| 🔢 최종 리스트(재번호) | {final_count} |
| 📄 PDF 확보 | {pdf_count} |

> 제거·정정 이력은 reference_verification.json에 기록됨(리스트에는 마커·편집문구 없음).
> 미검증으로 제거된 문헌은 본문 inline 인용도 함께 정리·재번호됨.
> 원문 PDF: {output_dir}/reference/
> 상세 로그: {output_dir}/reference_verification.json

▶ Phase 7 (HWPX 변환)을 시작합니다...
```

> 이 표시는 Gate가 아니다 — 바로 Phase 7로 진행한다. 단, `removed / total > 0.3` 이면 한 번 사용자 확인을 요청한다(다수 인용이 미검증으로 제거되면 재조사 필요).

#### Graceful Degradation

- KIPRIS API 실패: 해당 KR 특허는 `manual_review`, 다른 인용은 계속 처리
- Google Patents 봇 차단: WebFetch 폴백 → 그래도 실패 시 `manual_review`
- CrossRef/Semantic Scholar 실패: Zettelkasten 캐시만으로 PDF 확보 시도, 메타데이터는 `partial`
- Zettelkasten 접근 불가: 메타데이터 검증만 진행, PDF는 skipped
- MD 부록 C 미존재: Phase 6c 스킵, 사용자에게 "인용문헌 수동 검증 필요" 안내

#### 출력 MD 업데이트 규칙 (클린 리스트)

참고문헌 리스트를 다음 원칙으로 **재작성**한다 (마커 삽입 금지):

- 검증(verified/corrected) 문헌만 남긴다. 정정된 서지는 정정된 값으로 교체(정정 표기 없이).
- 미검증·실재 불명·중복 문헌은 삭제하고, 본문 inline `[N]` 인용을 gap 없이 재번호.
- 리스트 형식: `- [N] 저자, "제목", 저널 권(호), 페이지 (연도). DOI/KIPRIS` 순수 서지.
- KIMM 내부 자문(구두)은 리스트에 넣지 않는다.
- 검증/정정/제거 이력과 renumber_map 은 reference_verification.json에만 기록(별도 검증요약 섹션 불필요).

manifest 업데이트:
```json
"phase6c": {
  "status": "completed|degraded",
  "output": "reference_verification.json",
  "pdf_count": N,
  "verified": K, "removed": M, "final_reference_count": F
}
```

### Phase 6d: Critic 검증 게이트 + Gate 6d (2026-07-06 신설)

verify_citations.py 게이트 통과 후, HWPX 변환 전에 **작성 lane과 분리된 독립 critic**
(`{SKILL_ROOT}/agents/phase6d-critic.md`, opus)이 3개 레인으로 적대적 재검증한다:
(A) 인용·근거 출처 검증(핵심 문헌 ≥3건 원문 spot 재검증 + 성격 오규정 탐지 + 무근거 수치),
(B) 핵심 모순·IFR 유효성(가짜 모순·물리 성립성·점수-coverage 정합),
(C) 대표 청구항 특허성 모의 심사(자기선행 배경기술 최우선 공격 → survive/needs_amendment/reject).

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6d-critic.md for instructions.
         Read {output_dir}/: invention_manifest.json, triz_analysis.json, evaluation.json,
         prior_art.json (self_prior_art 포함), reference_verification.json, 최신 vN.md.
         Output: {output_dir}/critic_report.json (verdict: PASS|FIX|BLOCK + 레인별 issues)"
)
```

#### Gate 6d: critic 판정 처리

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧐 Critic 검증 결과 (Phase 6d)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
판정: {PASS|FIX|BLOCK}
| Lane | issue | 심각도 |
|------|-------|--------|
| A 출처 | {요약} | {critical/major/minor} |
| B 모순·IFR | {요약} | ... |
| C 청구항 | {독립항별 verdict} | ... |
```

- **PASS**: Phase 7 자동 진행 (게이트 표시만).
- **FIX**: required_fixes를 해당 phase가 1회 자동 보정(§8 변경 시 하드닝 체크 재적용 +
  verify_citations.py 재실행) → critic 재검(1회 한정) → 결과 표시 후 진행.
- **BLOCK**: critical(성격 오규정·미검증 인용·독립항 reject) — **auto-proceed 지시가 있어도
  중단**하고 사용자 판단을 요청한다. 선택: 1. 보정 지시 / 2. 해당 issue 수용하고 진행 /
  3. Gate 5(선행 재조사)로 회귀.

manifest 업데이트: `"phase6d": {"status": "completed", "verdict": "...", "critical": N, "major": M}`

### Phase 6e: 사업화 Critic + Gate 6e (2026-07-10 신설)

Gate 6d 통과 후, HWPX 변환 전에 **삼성전자 IP센터 전담 변리사 페르소나의 두 번째 독립 critic**
(`{SKILL_ROOT}/agents/phase6e-business-critic.md`, opus)이 **등록 후 가치**를 적대적으로 분석한다.
6d(등록 가능성, 심사관 관점)와 달리 침해자 관점에서 "등록돼도 회피/무시/협상/존중 중 무엇을
택할 것인가"를 판정하고, avoid/ignore가 나온 경로를 청구항 보정·신설 문안으로 되돌려준다. 3개 레인:
(D1) 회피설계 — 독립항별 회피 경로 5유형(치환·생략·공정변경·공급망 분리·주체 분산)·회피 비용·부록 B.4 매트릭스 검증,
(D2) 침해 입증 — 청구항별 검출성 등급(A/B/C) 독립 재판정·등급 인플레이션 탐지·공정 지문 후보 발굴,
(D3) 사업 판단 — 침해 주체 정합·회피 vs 라이선스 비용·독립항별 avoid/ignore/negotiate/respect.

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6e-business-critic.md for instructions.
         Read {SHARED_SKILL_ROOT}/reference/claim-drafting.md §11·§12 for 판정 기준.
         Read {output_dir}/: invention_manifest.json, prior_art.json (ifr_coverage 포함),
         critic_report.json (Phase 6d 결과), 최신 vN.md (§6/§7/§8/§9 + 부록 B).
         Output: {output_dir}/business_critic_report.json
         (verdict: PASS|FIX|ADVISE + persona_memo + lane별 결과 + required_fixes[청구항 문안] + advisories)"
)
```

#### Gate 6e: 사업화 판정 처리

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 사업화 Critic 결과 (Phase 6e — 삼성전자 전담 변리사 페르소나)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
판정: {PASS|FIX|ADVISE}

### 페르소나 메모 (요약)
{persona_memo}

| 독립항 | D1 회피설계 | D2 검출성(주장→재판정) | D3 판정 |
|--------|------------|----------------------|---------|
| 청구항 N | {회피 용이/곤란 + 최유력 시나리오} | {B→C 등} | {avoid/ignore/negotiate/respect} |

### 보정 제안 (required_fixes)
{proposed_claim_text 목록 + 선행 포섭 확인 결과}

### 전략 한계 (advisories)
{보정 불가 항목 — 원리적 회피 경로·후속출원 권고 등}

선택:
1. 보정안 전체 수용 → FIX 자동 적용
2. 특정 보정만 선택 적용 → 번호 지정
3. 현재 청구항 유지하고 진행 → advisories만 기록
4. §8 집중 검토 모드로 직접 수정 (Gate 6 선택 4와 동일)
```

- **PASS**: 결과 표시 후 Phase 7 자동 진행.
- **FIX**(보정 적용 시): phase6가 required_fixes 반영 → Phase 6.5 하드닝 체크 재적용(선행어·트리) →
  **Phase 6d Lane C 모의 심사 재실행**(신설·확장 청구항의 선행 포섭 확인 — 회피 차단용으로 넓힌
  문언이 선행기술을 밟으면 무효) → 6e 재검(1회 한정).
- **ADVISE**: auto-proceed 지시가 있어도 사용자 확인 — 전략 한계 수용 여부는 발명자 판단.
  수용 시 advisories를 Gate 7 최종 보고에 필수 표시.

manifest 업데이트: `"phase6e": {"status": "completed", "verdict": "...", "fixes_applied": N, "advisories": M, "output": "business_critic_report.json"}`, `current_gate: "gate_7"`

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

### HWPX 정합 반복 상한 (S2, 2026-07 신설)

> MD가 source of truth, HWPX는 best-effort 산출물이다. 서식 정합에 세션을 소진하지 않는다.

- HWPX 렌더링 정합(bullet/내어쓰기/paraPr) 재시도는 **최대 3회**로 제한한다.
- 3회 내 validate.py 통과 실패 또는 사용자 육안 불일치가 남으면, 현재 최선본 HWPX + MD를 최종 제공하고 남은 정합은 사용자 한/글 후처리로 넘긴다.
- 사용자 한/글 편집본이 있으면 v11_user diff 분석처럼 **일반화 가능한 규칙 1~2건만** convert_hwpx.py에 반영하고, 미적 선택(§6 heading 평탄화 등)은 규칙화하지 않는다.
- 내용(§1~§9, 청구항) 변경은 HWPX가 아니라 반드시 MD에서 수행 후 재변환한다.

---

## Gate 7: 최종 확인 [auto-skip 가능]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
발명내용설명서 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 출력 파일
- {filename}.md — Obsidian 호환 마크다운 (9개 섹션 + 부록 3개, 참고문헌은 검증된 순수 서지만)
- {filename}.hwpx — KIMM 양식 한글 파일
- 선행특허분석.md — KIPRIS 분석
- diagrams/ — 기술 도면 {N}개
- reference/ — 인용문헌 원문 PDF {K}건 (학술 논문 + 선행특허)
- reference_verification.json — 인용문헌 정합성 검증 로그
- critic_report.json — Critic 검증 결과 (Phase 6d, 등록 가능성)
- business_critic_report.json — 사업화 Critic 결과 (Phase 6e, 삼성전자 전담 변리사 페르소나 — 독립항별 avoid/ignore/negotiate/respect + advisories)

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
| Gate 6d | critic {verdict} | {gates.gate_6d 요약} |
| Gate 6e | 사업화 critic {verdict} — {독립항별 판정 요약} | {gates.gate_6e 요약} |

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
| Phase 6c | 검증 실패/PDF 제목 불일치 | 해당 문헌 리스트에서 제거 + 본문 재번호 + json에 removed 기록 |
| Phase 6c | MD 부록 C 미존재 | Phase 6c 스킵 + 사용자에게 수동 검증 안내 |
| Phase 6e | verdict=FIX | phase6 1회 보정 → 6.5 재적용 → 6d Lane C 재실행 → 6e 재검(1회 한정) |
| Phase 6e | verdict=ADVISE | 사용자 확인(auto-skip 불가) → 수용 시 advisories를 Gate 7 보고에 표시 |
| Phase 6e | prior_art degraded (ifr_coverage 부재) | 신설 청구항 선행 포섭 확인 불가 — "추가 선행조사 필요" 플래그, D1/D2 분석은 계속 |
| Phase 7 | HWPX 변환/validate 실패 | MD fallback |
| Background | prefetch 실패 | Phase 5에서 정상 검색 실행 (성능 저하만) |
