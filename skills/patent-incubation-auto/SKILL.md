---
name: patent-incubation-auto
description: "TRIZ 기반 발명내용설명서 작성 스킬. 기술분야/해결과제/핵심아이디어를 입력받아 TRIZ 모순 분석, IFR 도출, 선행특허 조사를 거쳐 KIMM 직무발명내용설명서(HWPX)를 자동 생성한다."
---

# TRIZ 기반 발명내용설명서 작성 스킬

KIMM 연구원이 특허 아이디어를 입력하면, TRIZ 방법론으로 체계적 분석을 수행하고 KIMM 직무발명내용설명서 양식(HWPX)으로 출력한다.

## When to Use

- 사용자가 특허 아이디어로 발명내용설명서를 작성하고자 할 때
- "특허", "발명신고서", "발명내용설명서", "patent disclosure", "TRIZ", "직무발명" 언급 시
- KIMM 양식의 발명 관련 문서가 필요할 때

## Skill Constants

```
SKILL_ROOT = ~/.claude/skills/patent-incubation-auto
HWPX_SKILL = ~/.claude/skills/hwpx
HWPX_XML_SKILL = ~/.claude/skills/hwpx-xml
KIPRIS_ENV_FILE = ~/Claude_Work/.env
```

> [!note] OS별 경로 해석
> `~`는 홈 디렉토리로 해석한다 (Windows: `C:/Users/JHKIM`, macOS: `/Users/<user>`).
> `KIPRIS_ENV_FILE`이 존재하지 않으면 환경변수 `KIPRIS_API_KEY`/`KIPRIS_REST_ACCESS_KEY`를
> 직접 확인하고, 둘 다 없으면 Phase 5/6c는 degraded 모드로 진행한다.
> Python 실행은 `python3`(PATH 우선)를 사용한다 (Windows에서 미탐지 시 `~/miniconda3/python`).

---

## Obsidian 마크다운 및 다이어그램 규칙 (모든 출력 파일에 적용)

본 스킬이 생성하는 모든 `.md` 파일은 Obsidian 볼트에서 직접 사용할 수 있어야 한다.

### MD 파일 기본 규칙

1. **YAML 프론트매터 필수**: `title`, `created`, `tags` 최소 포함
2. **내부 링크**: `[[파일명]]` 또는 `[[파일명|표시텍스트]]` 문법 사용 가능
3. **태그**: `#태그명` 또는 프론트매터 `tags:` 배열
4. **콜아웃**: `> [!note]`, `> [!warning]`, `> [!info]` 등 Obsidian 콜아웃 사용 가능
5. **줄바꿈**: Obsidian 렌더링 기준 (빈 줄로 단락 구분)

### 다이어그램 정책

| 유형 | 도구 | 용도 |
|------|------|------|
| 코드화 가능한 도면 | **Mermaid** | 흐름도, 시스템 구성도, 상태 변화도, 비교표, 시퀀스 다이어그램 등 |
| 자유 형식 스케치 | **Excalidraw** | 아이디어 핸드라이팅, 개념 스케치 등 사용자가 직접 그리는 경우만 |
| HWPX 삽입용 | **PNG (matplotlib)** | convert_hwpx.py가 §9에 자동 삽입하는 이미지 |

### Mermaid 다이어그램 규칙

- 발명내용설명서 MD에 `\`\`\`mermaid` 코드 블록으로 **인라인 삽입**
- 지원 유형: `graph`, `flowchart`, `stateDiagram-v2`, `sequenceDiagram`, `pie`, `xychart-beta`, `quadrantChart`
- 한글 텍스트 사용 가능 (노드 라벨, 설명 등)
- Phase 6b에서 발명 구성에 맞는 Mermaid 다이어그램을 자동 생성하여 발명내용설명서 MD §6, §9에 삽입

### 도면 ↔ 설명 동기화 규칙 (규칙 C, 2026-07 신설 / 2026-07-13 개정)

도면이 신규 생성·교체·업데이트되면(특히 사용자 제공 원도 pptx/이미지를 삽입할 때) 각 도면의 실제 내용(라벨·구성요소·신호 흐름·좌표축)을 Read 또는 텍스트 추출(python-pptx 등)로 파악하여, §9의 도면 목록(내용 기반 제목)과 본문 참조를 그 내용에 맞게 일치시킨다. **도면 번호([도 N])별 설명 목록("도 1은 ~" 형식의 '도면의 간단한 설명')은 작성하지 않는다** — 아래 '도면 번호·부호 미사용 정책' 참조. 도면 개수·순서·주제가 바뀌면 제목 목록·순서도 일치시키고 관련 청구항 링크를 갱신한다. 사용자 원도 삽입 시 600 dpi PNG 변환(PowerPoint COM: 슬라이드 in×600 픽셀) 후 `diagrams/`에 배치하면 convert_hwpx.py가 §9에 삽입한다. Phase 6b(도면)와 Phase 6c(인용) 사이 산출물이 확정될 때 auto는 이 동기화를 자동 수행한다.

### 도면 번호·부호 미사용 정책 (2026-07-13 신설, NON-NEGOTIABLE)

출원용 정식 도면과 도면부호 체계는 **변리사가 별도로 작성**한다. 내부 신고 문서의 자체 번호가 남으면 변리사 작업과 충돌하여 오해를 일으킬 수 있으므로 다음을 지킨다:

1. **도면 내 부품 번호(참조 부호) 금지**: 도면(SVG·Mermaid·matplotlib)의 구성요소 라벨은 **부품 이름 텍스트만** 사용한다. "10", "100", "챔버(10)" 등 참조 부호 표기 금지.
2. **도면 번호 설명 삭제**: §9에 "[도 N]" 번호 부여 및 번호별 설명 목록("도 1은 ~를 나타낸다")을 작성하지 않는다. 각 도면은 내용 기반 제목(예: "전체 시스템 구성도")만 달아 삽입한다.
3. **본문·청구항 부호 병기 금지**: §6 본문·§8 청구항에서 구성요소는 이름으로만 지칭한다("챔버(10)" → "챔버"). §9 도면부호 목록 테이블은 작성하지 않는다. 구별이 필요하면 서수·수식어("제1 롤", "하부 기판")를 사용한다.
4. **파일·슬라이드 관리용 번호는 허용**: `fig1_*.svg`/`fig1_*.png` 파일명 접두사와 figures_deck.pptx 슬라이드 순서는 삽입 순서 관리용으로 유지하되, 문서·슬라이드 캡션에는 "[도 N]"을 노출하지 않는다(캡션은 제목만).

### TRIZ 용어 사용 규칙

TRIZ는 아이디어 도출 수단이며, 그 흔적은 최종 특허 문서에 남기지 않는다.

| 영역 | TRIZ 용어 | 설명 |
|------|----------|------|
| 발명내용설명서 MD §1~§9 | **금지** | 일반적 기술 용어로 변환하여 서술 |
| 발명내용설명서 MD 부록 A | **허용** | TRIZ 분석 과정을 상세 기록 (내부 참고용) |
| HWPX §1~§9 | **금지** | TRIZ, IFR, 모순 매트릭스, 원리 번호 등 일체 불포함 |

Phase 6 에이전트가 §1~§9 작성 시, TRIZ 분석 결과를 일반적인 기술 용어로 변환하여 서술한다. 예:
- "기술적 모순 TC1 해결" → "점진적 접촉과 변형 방지의 상충 관계를 해소"
- "IFR 3 적용" → "복합재료 챔버 구조를 도입하여"
- "원리 35(속성 변환)" → "형상기억합금의 온도 응답 특성을 활용하여"

### 도면 파이프라인 규칙 (HWPX 삽입용, 2026-07-06 개편)

- **SVG(컬러 벡터) 1차 생성 → figures_deck.pptx(슬라이드 N=도면 N 1:1, 캡션은 제목만 — [도 N] 번호 미표기) → 600 dpi PNG → HWPX** 순서를 표준으로 한다(상세: agents/phase6b-diagram-generator.md Step 3-2).
- **상세·실척 도면 모드 (matplotlib 계산 기반, 2026-07-16 신설)**: 발명이 물리 기하(광학·역학·열)로 정의되거나 정량 상충·한계가 논거의 중심이면, 손코딩 SVG 대신 **matplotlib 실척·계산 도면**을 1차 경로로 쓴다 — 실척 좌표계(실제 mm 치수), 광선·궤적의 물리 계산, 전 기능층 적층+재료 표기, 정량 차트(로그축+요구선+동작점), 렌더 후 Read 육안 검증 루프. `svg.fonttype='path'`로 SVG를 병행 저장하면 outline 단계 없이 COM AddPicture 덱 조립이 가능하다. 상세: `reference/detailed-figures.md` (Phase 6b Step 4-0).
- **PPTX 덱은 편집 가능해야 한다(2026-07-06 개정)**: PNG 래스터 삽입 금지. `outline_svg_text.py`로 텍스트를 path로 outline한 SVG를 PowerPoint COM `AddPicture`로 직접 삽입 — 슬라이드에서 "그래픽 도형으로 변환" 편집 가능 + 한글 텍스트 누락 버그(PowerPoint SVG 변환기) 회피. 조립 후 패키지 내 `ppt/media/*.svg` 파트 수 검증.
- 600 dpi PNG는 PowerPoint COM export(슬라이드 인치×600 픽셀) 우선, `svg2png.py --dpi 600` 폴백. 그래프형 도면의 matplotlib 폴백도 `dpi=600`.
- `{output_dir}/diagrams/*.png` 에 저장 → convert_hwpx.py의 `--diagrams` 옵션으로 §9에 자동 삽입
- **컬러 적극 사용**(내부 신고 문서 기준. 출원 도면화 시 흑백 변환 §9 부기), 흰색 배경, 한글 폰트(Malgun Gothic)
- 필수 3종 도면(특허 배경·종래기술 비교·활용/파급효과) 포함 최소 5매

---

## 워크플로우 전체 개요

```
Step 0: 입력 수집 ──────────────────── 사용자 상호작용
Step 1: TRIZ 시스템 분석 (Phase 1) ─── sonnet 에이전트
Step 2: 모순 + IFR 생성 (Phase 2) ──── opus 에이전트
Step 3: 사용자 검토 게이트 ──────────── 사용자 상호작용 (결과 표시 + 선택)
Step 4: 정량 평가 (Phase 4) ─────────── sonnet 에이전트
Step 5: 선행특허 조사 (Phase 5) ─────── sonnet 에이전트 (자기공지 논문 + 자기선행 특허 조사 포함)
Step 5.5: 특허성 재채점 ────────────── sonnet 에이전트 (Phase 5 반영 + 반대심문)
Step 5b: 중간 진행 보고 ────────────── 사용자에게 진행 상황 표시
Step 6: 발명내용설명서 작성 (Phase 6) ── opus 에이전트
Step 6.5: 청구항 하드닝 (자동 점검+수정) ─ 오케스트레이터 자동 처리
Step 6b: 도면 생성 (Phase 6b) ───────── sonnet 에이전트 (컬러 SVG → PPTX 덱 → 600dpi PNG)
Step 6c: 인용문헌 정합성 검증 & PDF (Phase 6c) ── sonnet 에이전트 + 강제 게이트
Step 6d: Critic 검증 게이트 ─────────── opus 에이전트 (출처·모순/IFR·청구항 특허성, PASS/FIX/BLOCK)
Step 6e: 사업화 Critic ──────────────── opus 에이전트 (삼성전자 전담 변리사 페르소나 — 회피설계·침해 입증·사업 판단, PASS/FIX/ADVISE)
Step 7: HWPX 변환 (Phase 7) ─────────── sonnet 에이전트
Step 8: 최종 출력 및 안내 ──────────── 사용자에게 결과 안내
```

---

## Step 0: 입력 수집 및 검증

### 입력 방법 A: 대화형 입력 (기본)

사용자에게 다음 메시지를 표시한다:

```
발명내용설명서를 작성합니다. 다음 정보를 입력해 주세요:

1. **기술분야**: 발명이 속하는 기술 분야 (예: "마이크로LED 디스플레이 제조")
2. **해결 과제**: 해결하고자 하는 기술적 문제 (예: "인터포저 제조 단계의 비용과 시간 절감")
3. **핵심 아이디어**: 문제를 해결하는 핵심 기술적 아이디어 (예: "가변 피치 레이저를 이용한 COC 직접 전사")

옵션:
- **발명자명** (기본: 미입력) — 공동발명자가 있으면 쉼표로 함께 입력(첫 항목=주발명자, `inventors[]`로 저장)
- **소속기관** (기본: 미입력, KIMM 발명이면 "한국기계연구원" 제안) — 자기선행 특허 조사(Phase 5 Step 0-B)의 출원인 검색에 사용
- **출력 디렉토리** (기본: 현재 작업 디렉토리의 output/)
- **참조 문서** (기본: 현재 디렉토리의 .md 파일 자동 탐색)

> 발명자 리스트·소속기관 정보가 없으면 자기선행 조사는 **사용자(주발명자) 1인 위주**로 수행한다.
```

> [!important] AskUserQuestion 도구를 사용하여 입력을 받아야 한다. 입력을 요청한 후 사용자 응답을 기다린다.

### 입력 방법 B: 문서 기반 입력 (자동 감지)

사용자가 "현재 폴더의 md 파일을 토대로" 등의 지시를 하거나, 발명 주제와 함께 실행을 요청한 경우:

1. 작업 디렉토리의 `.md` 파일을 Glob으로 탐색
2. 발명 관련 MD 파일을 읽어 기술분야/해결과제/핵심아이디어를 자동 추출
3. 추출된 정보를 사용자에게 확인 요청:

```
📋 다음 정보로 발명내용설명서를 작성합니다. 맞는지 확인해 주세요:

- **기술분야**: {추출된 기술분야}
- **해결 과제**: {추출된 해결과제}
- **핵심 아이디어**: {추출된 핵심아이디어}
- **참조 문서**: {발견된 MD 파일 목록}

진행할까요? (Y/수정사항 입력)
```

> [!important] 자동 추출 시에도 반드시 사용자 확인을 거쳐야 한다. 단, 사용자가 "자동으로 진행" 또는 "확인할 것 없으면 자동 진행"이라고 지시한 경우에는 확인 없이 바로 진행한다.

### manifest 생성

입력을 받으면 `invention_manifest.json`을 생성한다:

```json
{
  "input": {
    "field": "사용자가 입력한 기술분야",
    "problem": "사용자가 입력한 해결 과제",
    "idea": "사용자가 입력한 핵심 아이디어",
    "inventor": "주발명자명 (하위호환 키 = inventors[0])",
    "inventors": ["주발명자", "공동발명자1", "..."],
    "affiliation": "소속기관(출원인 예정, 선택) — Phase 5 Step 0-B 자기선행 특허 조사에 사용",
    "date": "YYYY-MM-DD",
    "references": ["참조 문서 경로 목록"],
    "source_files": ["원본 MD 파일 경로 목록"]
  },
  "output_dir": "출력 디렉토리 절대 경로",
  "phases": {}
}
```

---

## Step 1: TRIZ 시스템 분석 (Phase 1)

**Agent**: `agents/phase1-triz-system.md`
**Model**: sonnet

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase1-triz-system.md for instructions.
         Read {SKILL_ROOT}/reference/triz-contradiction-matrix.json for parameter list.
         Input: {manifest.input}
         Output: {output_dir}/triz_system.json"
)
```

완료 후 manifest 업데이트:
```json
"phase1": {"status": "completed", "output": "triz_system.json"}
```

---

## Step 2: 모순 도출 + IFR 생성 (Phase 2)

**Agent**: `agents/phase2-contradiction-ifr.md`
**Model**: opus

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase2-contradiction-ifr.md for instructions.
         Read {SKILL_ROOT}/reference/triz-contradiction-matrix.json for matrix lookup.
         Read {SKILL_ROOT}/reference/triz-40-principles.md for principle details.
         Read {SKILL_ROOT}/reference/triz-separation-principles.md for separation laws.
         Read {output_dir}/triz_system.json for Phase 1 output.
         Input: {manifest.input}
         Output: {output_dir}/triz_analysis.json

         CRITICAL: Generate at least 10 IFRs. Each IFR must cite applied principle numbers."
)
```

완료 후 manifest 업데이트:
```json
"phase2": {"status": "completed", "output": "triz_analysis.json"}
```

### IFR 수량 검증

생성된 `triz_analysis.json`의 `ifr_count`가 10 미만이면:
- 에이전트를 재호출하여 추가 모순 쌍 탐색 (최대 2회 재시도)
- 재시도 후에도 10개 미만이면 현재 결과로 진행 (사용자에게 안내)

---

## Step 3: 사용자 검토 게이트 (Phase 3)

Phase 2 결과를 사용자에게 **반드시 표시**하고 검토를 요청한다.

### 결과 표시 형식

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TRIZ 분석 결과 (Phase 1~2 완료)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 기술적 모순 ({N}개)

| ID | 개선 파라미터 | 악화 파라미터 | 권장 원리 |
|----|-------------|-------------|----------|
{triz_analysis.technical_contradictions를 테이블로}

각 기술적 모순에 대해:
- **모순 설명**: 개선 시 악화되는 메커니즘
- **발명 목적과의 관계**: 이 모순 해결이 발명 목적에 기여하는 바
- **원리 적용 방향**: 각 권장 원리의 구체적 적용 방법

### 물리적 모순 ({N}개)

| ID | 모순 내용 | 분리 법칙 | 분리 해결 방법 |
|----|----------|----------|--------------|
{triz_analysis.physical_contradictions를 테이블로}

각 물리적 모순에 대해:
- **분리 해결 설명**: 분리 법칙이 모순을 해결하는 구체적 방법
- **발명 목적과의 관계**: 해결 시 달성되는 효과

### 모순-IFR 관계 매핑

| 모순 ID | 관련 IFR | 해결 방식 요약 |
|---------|---------|--------------|
{contradiction_ifr_coverage를 테이블로}

### IFR 목록 ({ifr_count}개)

| # | 핵심 내용 (요약) | 적용 원리 | 해결 모순 |
|---|----------------|----------|----------|
{triz_analysis.ifr_list를 간결한 테이블로, contradiction_link 포함}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 중 선택해 주세요:
1️⃣ **자동 진행** — 현재 결과로 평가 및 발명내용설명서 작성을 계속합니다
2️⃣ **피드백 제공** — IFR 수정/추가/삭제 의견을 입력합니다
3️⃣ **재분석 요청** — 다른 관점에서 TRIZ 분석을 다시 수행합니다
```

### 사용자 응답 처리

- **자동 진행** (1, "자동", "진행", "OK", "Y" 등): Phase 4로 바로 이동
- **피드백 제공** (2, 또는 구체적 의견 텍스트): 사용자 피드백을 반영하여 `triz_analysis.json` 수정 후 Phase 4
- **재분석** (3, "재분석", "다시"): Phase 2 재실행

> [!important] 사용자가 이전에 "자동 진행" 또는 "확인할 것 없으면 자동 진행"이라고 지시한 경우에만 이 게이트를 건너뛸 수 있다. 그 외에는 반드시 사용자 응답을 기다린다.

manifest 업데이트:
```json
"phase3": {"status": "completed", "user_action": "approved|feedback|reanalysis"}
```

---

## Step 4: 정량 평가 & 순위화 (Phase 4)

**Agent**: `agents/phase4-evaluator.md`
**Model**: sonnet

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase4-evaluator.md for instructions.
         Read {output_dir}/triz_analysis.json for IFR list.
         Read {SKILL_ROOT}/templates/evaluation-matrix.md for scoring template.
         Input: {manifest.input}
         Output: {output_dir}/evaluation.json"
)
```

manifest 업데이트:
```json
"phase4": {"status": "completed", "output": "evaluation.json"}
```

---

## Step 5: 선행특허 조사 (Phase 5)

**Agent**: `agents/phase5-prior-art.md`
**Model**: sonnet

### KIPRIS API 키 로드

실행 전 KIPRIS API 키를 환경변수로 로드한다:

```bash
KIPRIS_ENV="$HOME/Claude_Work/.env"
if [ -f "$KIPRIS_ENV" ]; then
  set -a
  eval "$(cat "$KIPRIS_ENV" | sed 's/^[[:space:]]*//' | grep -v '^#')"
  set +a
fi

if [ -z "$KIPRIS_API_KEY" ] && [ -z "$KIPRIS_REST_ACCESS_KEY" ]; then
  echo "WARNING: KIPRIS API key not set. Phase 5 will run in degraded mode."
fi
```

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase5-prior-art.md for instructions.
         Read {output_dir}/triz_analysis.json for IFR list.
         Read {output_dir}/evaluation.json for top-ranked IFRs.

         KIPRIS search script: {SKILL_ROOT}/scripts/search_patents_kipris.py
         KIPRIS .env file: {KIPRIS_ENV_FILE}

         Before calling the KIPRIS script, load env vars:
         set -a && eval \"$(cat '{KIPRIS_ENV_FILE}' | sed 's/^[[:space:]]*//' | grep -v '^#')\" && set +a

         Input: {manifest.input}
         Output: {output_dir}/prior_art.json
         Also output: {output_dir}/{발명명칭}_선행특허분석.md

         MANDATORY (다국가 국제 검색 — 2026-07-06 필수 격상):
         - KIPRIS 국내 검색에 더해, 독립항 신규성 앵커 개념을 영문 키워드로 변환하여
           Google Patents WebFetch 3~5쿼리로 KR/US/JP/EP/WO 를 검색한다(agent 문서 S5 참조).
         - 국내 한정 조사로 novel 판정 금지. 국제 검색 불가 시 analysis_summary 에
           "국제 검색 미수행 — 국내 한정 결론" + ifr_coverage kr_only_caveat 명시.
         - 검출 문헌의 방식(투사형/직시형 등)은 원문 WebFetch 로 직접 확인(2차 요약 신뢰 금지).

         MANDATORY (자기선행 특허 조사 — 2026-07-06 신설, agent 문서 Step 0-B):
         - manifest input.inventors[](공동발명자)·input.affiliation(소속기관)으로
           KIPRIS 국내 중심 발명자·출원인 검색을 수행한다(정보 없으면 주발명자 1인 위주).
         - 검출 자기선행의 청구범위 + **배경기술·명세서 개시 요소**를 파싱하고 공지예외
           12개월 기한을 산정하여 prior_art.json self_prior_art[]에 기록한다.
         - disclosed_elements 는 Phase 6 독립항 설계의 금지 영역 + Step 6d critic 공격 재료.

         ADDITIONAL (자기공지·NPL 조사 — 연구기관 최다 무효사유 차단):
         - 발명자 본인·KIMM 소속 저자의 논문·학회 발표·보도자료를 CrossRef/OpenAlex 저자
           검색으로 조회하여 특허 출원 전 자기 선행공개 여부를 확인한다.
         - source_files로 입력된 발명자 자신의 논문은 자동으로 자기공지 후보로 검사한다.
         - 자기공개 발견 시 prior_art.json에 self_disclosure[]{title, date, venue, grace_deadline}
           를 기록한다. grace_deadline = 공개일 + 12개월(공지예외주장·신규성 의제 기한).
         - §2(논문발표 여부)에 반영할 실질 조사 결과로 활용한다."
)
```

> [!important] 자기공지(발명자 선공개) 경고
> KIMM은 연구기관으로, 발명자가 논문·학회 발표를 출원보다 먼저 공개하여 자기 공지로 신규성·진보성을 상실하는 것이 최다 무효 사유다. Phase 5가 자기공개를 발견하면 `prior_art.json`의 `self_disclosure[]`에 공개일과 공지예외주장 12개월 기한(`grace_deadline`)을 기록하고, Step 8 최종 안내에서 기한 경고를 표시한다.

### Graceful Degradation

KIPRIS 검색 실패 시:
- `prior_art.json`에 `{"status": "degraded", "reason": "KIPRIS API failure", "patents": []}` 기록
- 사용자에게 안내: "선행특허 자동 검색에 실패했습니다. §3, §4, §8 섹션은 수동 보완이 필요합니다."
- Phase 6는 degraded 상태로 계속 진행

### 선택: 상위 선행특허 원문 PDF 심화 분석

서지 기반 검색만으로 변별력이 부족할 때, 상위 1~3건의 원문 PDF를 받아 청구항 전문을 비교한다.

```bash
PYTHONUTF8=1 python3 \
  ~/.claude/skills/_shared/scripts/download_patent_pdf.py \
  --kr <applno1> <applno2> --out {output_dir}/prior_art_pdfs/ --verify
```

- KR 특허는 KIPRIS `getPubFullTextInfoSearch`/`getAnnFullTextInfoSearch`로 PDF 직접 수신
- 국외 특허는 `--gp <GooglePatentsID>`
- 다운로드 직후 `pdf-to-md`로 변환하여 청구항 섹션만 추출하여 비교
- 상세 절차: `~/.claude/skills/_shared/patent_pdf_download.md`

manifest 업데이트:
```json
"phase5": {"status": "completed|degraded", "output": "prior_art.json"}
```

---

## Step 5.5: 특허성 재채점 (Phase 5 반영)

**Model**: sonnet
**목적**: Phase 4가 특허성(0.20)을 선행특허 조사(Phase 5) **이전에** 채점했으므로, 조사 결과(신규성/진보성 실측)를 반영해 특허성 축을 재채점한다. 단일 평가자 + LLM 낙관 편향으로 인한 점수 인플레이션을 반대심문(devil's advocate) 레인으로 교정한다.

> [!note] degraded 시 스킵
> `prior_art.json`이 `status: degraded`이면 재채점 근거(ifr_coverage·rejection_combinations)가 없으므로 이 단계를 건너뛰고 Step 5b로 진행한다. manifest에 `"phase5_5": {"status": "skipped", "reason": "prior_art degraded"}` 기록.

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="특허성 재채점 및 반대심문을 수행한다.
         Read {output_dir}/evaluation.json for current patentability scores.
         Read {output_dir}/prior_art.json for ifr_coverage(novel/partial/disclosed) and rejection_combinations.

         TASK:
         1. evaluation.json의 각 IFR patentability 점수를 prior_art.json의 ifr_coverage와
            rejection_combinations에 근거해 재조정한다.
            - novel → 8~10, partial → 4~7, disclosed → 1~3 범위로 정합.
            - 대응 종속항/방어논거가 없는 rejection_combination이 있으면 감점.
         2. 상위 3개 IFR에 대해 '이 IFR이 특허성이 없는 이유를 논증하라'는 반대심문
            (devil's advocate)을 수행한다 — 자명한 공지기술 조합 여부, 결합 동기 존재,
            teaching away 부재 등을 적극적으로 반박 논거로 제시.
         3. 결과를 evaluation.json에 다음 필드로 기록한다:
            - patentability_recheck: IFR별 {before, after, reason}
            - patentability_devil_advocate: 상위 3개 IFR의 반론 요지
         재조정으로 상위 순위가 바뀌면 ranking도 갱신한다.

         Output: 업데이트된 {output_dir}/evaluation.json"
)
```

manifest 업데이트:
```json
"phase5_5": {"status": "completed|skipped", "recheck_count": N}
```

---

## Step 5b: 중간 진행 보고

Phase 4~5 완료 후, Phase 6 진입 전에 사용자에게 중간 진행 상황을 표시한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 중간 진행 보고 (Phase 4~5 완료)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### IFR 평가 결과 (상위 3건)

| 순위 | IFR# | 종합점수 | 핵심 내용 |
|------|------|---------|----------|
{evaluation.json에서 상위 3건}

### 선행특허 조사 결과

- 검색 건수: {총건수}건 → 상위 {분석건수}건 분석
- 위험 수준 '중간' 이상: {N}건
- 본 발명 차별 요소: {선행특허 미개시 IFR 요약}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ Phase 6 (발명내용설명서 작성)을 시작합니다...
```

> [!note] 이 보고는 표시만 하고 사용자 응답을 기다리지 않는다. 바로 Phase 6으로 진행한다.

---

## Step 6: 발명내용설명서 최종 작성 (Phase 6)

**Agent**: `agents/phase6-disclosure-writer.md`
**Model**: opus

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6-disclosure-writer.md for instructions.
         Read {SKILL_ROOT}/templates/disclosure-report.md for MD template.
         Read {SKILL_ROOT}/reference/user-philosophy.md for inventor philosophy.

         Read all phase outputs from {output_dir}/:
         - triz_system.json (Phase 1)
         - triz_analysis.json (Phase 2)
         - evaluation.json (Phase 4)
         - prior_art.json (Phase 5, may be degraded)

         Read original source documents: {manifest.input.source_files}

         Input: {manifest.input}
         Output: {output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md

         FILE NAMING RULE:
         - Format: (YYYYMMDD 발명자) 발명명칭vN.md
         - Check output_dir for existing files with same 발명명칭 to determine version N
         - If no existing file: v1. If v1 exists: v2. And so on.
         - Example: (20260331 김재현) 나노박막의 진공 대면적 전사 방법 및 장비v1.md

         CRITICAL REQUIREMENTS:
         1. All 9 sections (§1~§9) must be filled
         2. All 3 appendices (부록 A/B/C) must be filled
         3. Each section starts with '## §N' header (machine-parseable)
         4. Written in Korean
         5. If prior_art is degraded, mark §3/§4/§8 with [선행특허 수동 보완 필요]
         6. Adjust IFR rankings based on prior art novelty in §6
         7. Include ALL references with proper citations (DOI, patent numbers, URLs)
         8. Reflect inventor philosophy from user-philosophy.md
         9. After writing, update user-philosophy.md §4 with new patterns found
         10. 부록 A.4는 반드시 2단계 구성:
             - A.4.1 IFR 설명 테이블: 정량 평가 이전에 배치. 모든 IFR을 주제별 그룹으로
               분류하고, 각 IFR의 지향 방향/해결 모순/핵심 내용/기술적 효과/적용 원리를
               테이블로 정리. 모순→원리→IFR→효과의 논리적 체인이 명확해야 함.
             - A.4.2 IFR 정량 평가 테이블: A.4.1 이후에 배치. Phase 4 점수 기반 순위."
)
```

### 출력 검증

생성된 MD 파일에서 9개 섹션 + 3개 부록 존재 확인:

```python
import re, glob

# 파일명 형식 확인
md_files = glob.glob(f"{output_dir}/*v*.md")
# 버전 번호 파싱
versions = []
for f in md_files:
    m = re.search(r'v(\d+)\.md$', f)
    if m:
        versions.append(int(m.group(1)))
next_version = max(versions) + 1 if versions else 1

# 섹션/부록 검증
sections_found = re.findall(r'^## §(\d+)', md_text, re.MULTILINE)
appendices_found = re.findall(r'^## 부록 ([A-C])', md_text, re.MULTILINE)
missing_sec = set(range(1, 10)) - set(int(s) for s in sections_found)
missing_app = set(['A', 'B', 'C']) - set(appendices_found)
if missing_sec or missing_app:
    # 1회 재시도
    pass

# IFR 설명 테이블(A.4.1) 존재 검증 — 정량 평가 전에 배치되어야 함
has_ifr_desc = bool(re.search(r'A\.4\.1.*IFR 설명', md_text))
has_ifr_eval = bool(re.search(r'A\.4\.2.*IFR 정량', md_text))
if not has_ifr_desc or not has_ifr_eval:
    # A.4.1/A.4.2 누락 시 1회 재시도
    pass
```

manifest 업데이트:
```json
"phase6": {"status": "completed", "output": "(YYYYMMDD 발명자) 발명명칭vN.md"}
```

---

## Step 6.5: 청구항 하드닝 (자동 점검 + 자동 수정)

발명의 최고가치 산출물은 청구항이므로, 도면·HWPX 변환 이전에 §8 청구항을 법적 관점에서 점검한다. auto는 **사용자 게이트 없이** 자동 점검하고, 발견된 issue는 phase6 MD를 직접 보정한 뒤 최종 보고(Step 8)에 표시한다.

### 점검 항목 (§8 대상)

**필수 5항목**:

1. **112(b) antecedent basis**: 각 종속항 구성요소가 인용 독립항에 선행 기재됐는지. "상기 ~"의 선행어 존재 확인.
2. **청구항 트리 정합**: 독립항-종속항 인용 관계, 카테고리 일치(장치 종속항이 방법 독립항을 인용하지 않는지).
3. **권리범위 계층**: 독립항이 불필요하게 좁지 않은지(광역 유지), 종속항이 단계적 fallback 방어선을 형성하는지.
4. **거절조합 대응**: Phase 5 `rejection_combinations`의 각 예상 조합에 대응하는 한정 요소가 최소 하나의 종속항으로 준비됐는지.
5. **수치 한정 위치**: 독립항은 수치 무한정(광역), 수치 한정은 종속항으로 이동됐는지.

**SMART 자가진단 8항목** (Phase 6.5 통합, 2026-07-06 SMART5/KPAS 활용성·시장성 레버 3항목 확장):

6. **독립항 글자수 경고 신호**: 과도한 길이면 플래그(규칙이 아닌 **경고 신호** — SMART는 독립항이 길수록 감점하는 기계적 경향이 있음). 길이는 신규성 지탱 결합의 크기가 결정하는 것이지 점수 최적화 대상 아님.
7. **카테고리 병행**: 물건+방법 청구항이 병행되는지(최소), 소자·**시스템**(센서/제어 요소 있을 때) 추가 검토 — 최대 4축.
8. **종속항 계층 균형**: 독립항당 종속항 4~6개.
9. **활용성 서술 존재**: §7에 "본 발명은 [산업]에 적용되어 [분야]에 활용" 패턴이 존재하는지.
10. **실시예·도면 수 하한**: 실시예 ≥3, 도면 ≥5.
11. **도면 번호·부호 부재 검사 (2026-07-13 개정)**: §6 본문·§8 청구항에 도면 부호 괄호 병기("챔버(10)")가 없는지, §9에 도면부호 목록 테이블·"[도 N]" 번호별 설명 목록이 없는지, 도면 라벨이 부품 이름 기반인지 검사 — 출원용 도면·부호는 변리사가 별도 작성(도면 번호·부호 미사용 정책). 발견 시 부호 제거·이름 치환(자동 수정).
12. **파급/사업화 블록 존재**: §9에 적용 시장·후속출원(분할/연속) 구조·PCT/삼극 패밀리 플랜이 실질 내용으로 서술됐는지 (KPAS 시장성·SMART5 활용성 레버).
13. **안티게이밍 검사**: 12가 지표용 빈 문구가 아닌지 — 시장·패밀리 서술이 발명 내용과 무관하거나 근거 없는 과장이면 플래그. 자동점수 ≠ 실제 권리강도, 신규성·품질 우선.

**사업화 2항목 (2026-07-10 신설 — claim-drafting.md §11·§12 연동)**:

14. **회피설계 차단 매트릭스**: 각 독립항마다 경쟁사 회피 시나리오(치환·생략·공정변경·공급망 분리·실시주체 분산, E1~E5) 최소 2개가 상정되고, 각각 대응 차단 청구항(상위개념 문언/병렬 독립항/봉쇄 종속항)이 존재하는지. 부록 B.4에 매트릭스(`| 독립항 | 회피 시나리오 | 유형 | 차단 청구항 | 잔여 리스크 |`)가 기록됐는지. 부재 시 §8·§6 내용을 근거로 생성하여 추가(자동 수정).
15. **침해 검출성 등급**: 모든 청구항에 검출성 등급(A: 제품 관찰 / B: 리버스엔지니어링 / C: 내부 정보 필요)이 부여되고 **최소 1개 독립항이 등급 A/B**인지. 방법 발명은 공정 지문(제품에 남는 구조 흔적) 물건항 병행 여부. 부록 B.5에 검출성 테이블(`| 청구항 | 등급 | 입증 수단 | 비고 |`)이 기록됐는지. 테이블 부재는 자동 수정, 등급 A/B 독립항 부재는 reported issue(청구항 신설은 Phase 6e에서 문안 제안).

### 자동 처리 방식

- 각 항목을 점검하여 issue 목록을 수집한다.
- 자동 수정 가능한 issue(선행어 누락, 수치한정 위치, 활용성 서술 누락 등)는 **phase6 MD를 직접 보정**한다(버전 번호 유지).
- 자동 수정이 어려운 issue(카테고리 재설계 등)는 수정하지 않고 Step 8 보고에 명시한다.
- 참고: `patent-draft-review` 스킬을 이 단계에서 호출 가능.

### 에이전트 호출

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="§8 청구항을 자동 점검하고 phase6 MD를 직접 보정한다.
         Read the latest vN.md in {output_dir} for §8 청구범위 and §6/§7 및 부록 B.
         Read {output_dir}/prior_art.json for rejection_combinations and ifr_coverage.
         Read {SKILL_ROOT}/reference/claim-drafting.md §11(회피설계 차단)·§12(침해 검출성) for 사업화 2항목 판정 기준.

         점검 항목(필수 5 + SMART 8 + 사업화 2): 위 SKILL 정의 참조.
         자동 수정 가능한 issue는 MD를 직접 보정(버전 유지), 불가한 issue는 목록으로 반환.
         부록 B.4 회피설계 차단 매트릭스·B.5 검출성 테이블 부재 시 직접 생성하여 부록 B에 추가한다.
         Output: 보정된 phase6 MD + issues[]{item, severity, action(fixed/reported), detail}"
)
```

manifest 업데이트:
```json
"phase6_5": {"status": "completed", "issues_found": N, "auto_fixed": K, "reported": R}
```

---

## Step 6b: 도면 생성 (Phase 6b)

**Agent**: `agents/phase6b-diagram-generator.md`
**Model**: sonnet

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase6b-diagram-generator.md for instructions.
         Read the Phase 6 output MD file (the latest vN.md in {output_dir}) for §6 and §9 content.
         Read {output_dir}/triz_system.json for system components.
         Read {output_dir}/evaluation.json for top IFRs.

         Input: {manifest.input}
         Output directories: {output_dir}/figures/ (컬러 SVG 원본), {output_dir}/diagrams/ (600dpi PNG)
         Also output: {output_dir}/figures_deck.pptx (슬라이드 N = 도면 N 1:1, 캡션은 제목만 — [도 N] 번호 미표기, 표지 없음)
         Also update: the Phase 6 output MD file (latest vN.md in {output_dir}) §9 with diagram references

         Generate at minimum (필수 3종 포함 최소 5매, 컬러):
         1. 특허 배경 그림 (문제 상황·종래 한계 시각화) [필수]
         2. 종래기술 vs 본 발명 비교도 [필수]
         3. 활용 가능성·파급효과 그림 (적용 제품·시장·응용) [필수]
         4. 전체 시스템 구성도
         5. 공정 흐름도 또는 소자/장치 단면도

         PIPELINE (agent 문서 Step 3-2): 컬러 SVG 1차 생성 → outline_svg_text.py로
         텍스트→path outline(figures/pptx/) → figures_deck.pptx 조립(PowerPoint COM
         AddPicture로 outlined SVG 직접 삽입 — 편집 가능, PNG 래스터 삽입 금지,
         슬라이드 번호=도면 번호 일치) → 600 dpi PNG(svg2png.py --dpi 600, 원본 SVG
         기준) → diagrams/ 저장 → convert_hwpx.py가 §9 삽입.
         Korean font: Malgun Gothic. 종래=적색 계열 vs 본 발명=청색 계열 대비.

         MANDATORY (도면 번호·부호 미사용 — 2026-07-13 정책):
         - 도면 내 구성요소 라벨은 부품 이름 텍스트만 사용 — 참조 부호(10, 100 등) 표기 금지.
         - §9 업데이트 시 '[도 N]' 번호·번호별 설명 목록을 작성하지 않는다 — 각 도면은
           내용 기반 제목만 기재. 도면부호 목록 테이블 금지.
         - 슬라이드 캡션도 제목만(번호 미표기). 파일명 figN_ 접두사는 삽입 순서 관리용으로만 유지.
         - 사유: 출원용 정식 도면·부호 체계는 변리사가 별도 작성 — 내부 번호가 오해 유발."
)
```

manifest 업데이트:
```json
"phase6b": {"status": "completed", "output": "diagrams/", "diagram_count": N}
```

---

## Step 6c: 인용문헌 정합성 검증 & PDF 저장 (Phase 6c)

**Agent**: `agents/phase6c-reference-verifier.md`
**Model**: sonnet

발명내용설명서 MD에 기재된 모든 인용문헌(학술 논문·KR/외국 특허·DOI·보고서)을 외부 DB(KIPRIS Plus, CrossRef, OpenAlex, Semantic Scholar, Google Patents)로 직접 조회하여 번호·제목·저자·출원인의 정합성을 검증하고, **참고문헌 리스트를 검증된 실제 문헌의 순수 서지만 남도록 정리**(미검증·실재 불명 문헌 제거 + 본문 inline 인용을 gap 없이 재번호)하며, 검증 이력은 `reference_verification.json`에 기록하고, 원문 PDF를 `{output_dir}/reference/`에 저장한다.

> [!important] 클린 리스트 원칙 (NON-NEGOTIABLE, 2026-07)
> 참고문헌 리스트에는 **검증된 실제 문헌의 서지 정보만** 기재한다. `(정합 확인!)`·`[정정:...]`·`(삭제)`·`(정합 불일치)` 등 마커·편집문구를 리스트에 **절대 넣지 않는다.** 검증·정정·제거 이력은 `reference_verification.json`(audit trail)에만 남긴다.
>
> 배경: 실전 run에서 Phase 6c가 누락됐는데 작성 에이전트가 참고문헌 20건 전부에 `(정합 확인!)`을 임의 부착 → CrossRef 재검증 시 학술 DOI 6건이 404/무관논문/제목오류로 판명된 환각 사고가 있었다. 자동 모드일수록 사용자 검토가 없어 기계 게이트(verify_citations.py)가 더 절실하다.

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

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase6c-reference-verifier.md for instructions.
         Read the Phase 6 output MD file (the latest vN.md in {output_dir}) for citation extraction.
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
         7. 재번호로 바뀐 inline 인용을 §3~§8·표·부록 전체에서 일관 갱신(참고문헌 리스트 자체 제외)
         8. 모든 정리 완료 후 반드시 강제 게이트를 실행한다:
            PYTHONUTF8=1 python {SKILL_ROOT}/scripts/verify_citations.py --md <MD> --verification <reference_verification.json>
            exit!=0 이면 Phase 7로 진행 금지(편집문구 잔존/미검증 문헌/6c 미실행 차단)."
)
```

### 강제 게이트: verify_citations.py [기계 게이트, auto-skip 불가]

Phase 6c 에이전트 종료 후, 오케스트레이터가 직접 게이트를 실행한다. 이것은 기계 게이트이므로 auto 모드에서도 **자동 스킵 불가** — exit!=0이면 Phase 7(HWPX 변환)로 진행하지 않는다.

```bash
PYTHONUTF8=1 python {SKILL_ROOT}/scripts/verify_citations.py \
  --md "{output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md" \
  --verification "{output_dir}/reference_verification.json"
```

| exit | 의미 | 조치 |
|------|------|------|
| 0 | 리스트 클린(편집문구 없음) + 모든 참고문헌이 검증 문헌과 DOI/특허번호 매칭 | Phase 7 진행 |
| 1 | 편집문구 잔존 / 미검증 문헌 존재 / removed 문헌 재등장 | 리스트 정리(제거·재번호) 후 재실행 |
| 2 | reference_verification.json 부재 또는 참고문헌 미검출 | Phase 6c 재실행 (미실행 상태) |

> 이 게이트는 "리스트=검증된 순수 서지"를 결정적으로 보증한다. 단, 개수·매칭 검사는 **위조된 DOI**를 잡지 못한다 — 서지의 의미적 정확성(원문 대조)은 phase6c 에이전트의 책임이며, 기계 게이트가 환각을 완전 봉쇄하지는 않는다.

### Graceful Degradation

- KIPRIS API 실패 시: 해당 KR 특허는 `manual_review`, 다른 인용은 계속 처리
- Google Patents 봇 차단 시: WebFetch 폴백 → 그래도 실패 시 `manual_review`
- CrossRef/Semantic Scholar 실패 시: Zettelkasten 캐시만으로 PDF 확보 시도, 메타데이터는 `partial`
- Zettelkasten 접근 불가 시: 메타데이터 검증만 진행, PDF는 skipped

### 출력 MD 업데이트 규칙 (클린 리스트)

참고문헌 리스트를 다음 원칙으로 **재작성**한다 (마커 삽입 금지):

- 검증(verified/corrected) 문헌만 남긴다. 정정된 서지는 정정된 값으로 교체(정정 표기 없이).
- 미검증·실재 불명·중복 문헌은 삭제하고, 본문 inline `[N]` 인용을 gap 없이 재번호.
- 리스트 형식: `- [N] 저자, "제목", 저널 권(호), 페이지 (연도). DOI/KIPRIS` 순수 서지.
- KIMM 내부 자문(구두)은 리스트에 넣지 않는다.
- 검증/정정/제거 이력과 renumber_map은 reference_verification.json에만 기록(별도 검증요약 섹션 불필요).

### 검증 요약 표시 (자동 진행, 정보 표시)

강제 게이트 통과 후 Phase 7 진입 전에 결과를 화면에 표시한다:

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
▶ Phase 7 (HWPX 변환)을 시작합니다...
```

> `removed / total > 0.3`이면(다수 인용이 미검증으로 제거) Step 8 보고에 재조사 권고를 표시한다.

manifest 업데이트:
```json
"phase6c": {
  "status": "completed|degraded",
  "output": "reference_verification.json",
  "pdf_count": N,
  "verified": K, "removed": M, "final_reference_count": F
}
```

---

## Step 6d: Critic 검증 게이트 (2026-07-06 신설)

**Agent**: `agents/phase6d-critic.md`
**Model**: opus

verify_citations.py 게이트 통과 후, HWPX 변환 전에 **작성 lane과 분리된 독립 critic**이
산출물 전체를 적대적으로 재검증한다. 3개 레인: (A) 인용 문헌·근거 자료 출처 검증(핵심
문헌 ≥3건 원문 spot 재검증 + **성격 오규정 탐지** + 무근거 수치), (B) 핵심 모순·IFR
유효성(가짜 모순·물리 성립성·점수-coverage 정합), (C) 대표 청구항 특허성 모의 심사
(자기선행 배경기술 최우선 신규성 공격 + 조합 진보성 공격 → survive/needs_amendment/reject).

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6d-critic.md for instructions.
         Read {output_dir}/: invention_manifest.json, triz_analysis.json, evaluation.json,
         prior_art.json (self_prior_art 포함), reference_verification.json,
         그리고 최신 vN.md (§4/§7/§8·부록 A/B/C).
         Output: {output_dir}/critic_report.json (verdict: PASS|FIX|BLOCK + 레인별 issues)"
)
```

### 판정 처리 (오케스트레이터)

| verdict | 조치 |
|---------|------|
| **PASS** | Step 7(HWPX) 진행 |
| **FIX** | required_fixes를 해당 phase(6/6b/6c)가 **1회 자동 보정** → §8 변경 시 Step 6.5 하드닝 재적용 + verify_citations.py 재실행 → critic 재검(1회 한정) |
| **BLOCK** | critical(성격 오규정·미검증 인용·독립항 reject) — **auto 모드여도 자동 진행 중단**, 사용자에게 issue 목록 제시 후 판단 요청 |

manifest 업데이트:
```json
"phase6d": {"status": "completed", "verdict": "PASS|FIX->PASS|BLOCK", "critical": N, "major": M, "output": "critic_report.json"}
```

---

## Step 6e: 사업화 Critic — 삼성전자 전담 변리사 페르소나 (2026-07-10 신설)

**Agent**: `agents/phase6e-business-critic.md`
**Model**: opus

Phase 6d(등록 가능성 critic) 통과 후, HWPX 변환 전에 **등록 후 가치**를 검증하는 두 번째
독립 critic이다. 삼성전자 IP센터 전담 변리사 페르소나로 "이 특허가 등록돼도 우리는
회피/무시/협상/존중 중 무엇을 택할 것인가"를 적대적으로 분석하고, avoid/ignore가 나온
경로를 발명자 개선 재료(청구항 보정·신설 문안)로 되돌려준다. 3개 레인:
(D1) 회피설계 — 독립항별 회피 경로 5유형(치환·생략·공정변경·공급망 분리·주체 분산)과
회피 비용, 부록 B.4 매트릭스 검증, (D2) 침해 입증 — 청구항별 검출성 등급(A/B/C) 독립
재판정 + 공정 지문 후보 발굴, (D3) 사업 판단 — 침해 주체 정합·회피 vs 라이선스 비용·
독립항별 avoid/ignore/negotiate/respect.

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6e-business-critic.md for instructions.
         Read {SKILL_ROOT}/reference/claim-drafting.md §11·§12 for 판정 기준.
         Read {output_dir}/: invention_manifest.json, prior_art.json (ifr_coverage 포함),
         critic_report.json (Phase 6d 결과), 그리고 최신 vN.md (§6/§7/§8/§9 + 부록 B).
         Output: {output_dir}/business_critic_report.json
         (verdict: PASS|FIX|ADVISE + persona_memo + lane별 결과 + required_fixes[청구항 문안] + advisories)"
)
```

### 판정 처리 (오케스트레이터)

| verdict | 조치 |
|---------|------|
| **PASS** | Step 7(HWPX) 진행 |
| **FIX** | required_fixes(보정·신설 청구항 문안)를 phase6가 **1회 자동 보정** → Step 6.5 하드닝 재적용(선행어·트리) → **Phase 6d Lane C 모의 심사 재실행**(신설 청구항의 특허성 확인 — 선행 포섭 차단) → 6e 재검(1회 한정) |
| **ADVISE** | 보정으로 해소 불가한 전략 한계(원리적 회피 경로·등급 C 계열 유지 판단 등) — 진행은 계속하되 advisories를 Step 8 최종 보고에 **필수 표시** |

> [!note] Phase 6d와의 관계
> 6d = 등록 가능성(심사관 관점), 6e = 등록 후 가치(침해자 관점). 6e FIX로 청구항이
> 넓어지거나 신설되면 반드시 6d Lane C를 재실행하여 선행기술 포섭 여부를 확인한다 —
> 회피 차단을 위해 넓힌 문언이 선행을 밟으면 무효가 되기 때문이다.

manifest 업데이트:
```json
"phase6e": {"status": "completed", "verdict": "PASS|FIX->PASS|ADVISE", "fixes_applied": N, "advisories": M, "output": "business_critic_report.json"}
```

---

## Step 7: HWPX 변환 (Phase 7)

**Agent**: `agents/phase7-hwpx-converter.md`
**Model**: sonnet

```
Agent(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="Read {SKILL_ROOT}/agents/phase7-hwpx-converter.md for instructions.
         Read {SKILL_ROOT}/reference/kimm-template-mapping.md for cell mapping.
         Read the Phase 6 output MD file (the latest vN.md in {output_dir}) for content to insert.

         Template: {SKILL_ROOT}/assets/[KIMM]직무발명내용설명서_양식.hwpx
         fix_namespaces: {HWPX_SKILL}/scripts/fix_namespaces.py
         validate: {HWPX_XML_SKILL}/scripts/validate.py

         Output: {output_dir}/(YYYYMMDD 발명자) {발명명칭}v1.hwpx

         CRITICAL — MUST USE STRATEGY A (전체 셀 내용 교체):
         1. Parse section0.xml with xml.etree.ElementTree
         2. For each section: locate the target <hp:tc> cell by table/row/cell index
         3. Remove ALL existing <hp:p> elements from the cell
         4. Split new content by newline into individual <hp:p> elements
         5. Use correct paraPrIDRef and charPrIDRef per section
         6. Remove §9 template image (hp:pic and BinData/image1.bmp)
         7. DO NOT use zip_replace() — it causes text overlap bugs

         §8 특별 규칙 (청구범위):
         8. §8은 청구항 단위로 문단을 분할한다 (줄 단위가 아님)
         9. 각 청구항([청구항 N] 헤더 + 본문)을 하나의 hp:p 요소로 생성
         10. 청구항 내의 줄바꿈은 공백으로 치환하여 단일 문단에 합침

         §9 도면 삽입 규칙:
         11. diagrams/ 폴더의 PNG 파일을 BinData/에 fig1.png~figN.png로 저장
         12. content.hpf에 각 이미지 항목 등록
         13. §9 셀 맨 끝에 도면 제목(내용 기반, "[도 N]" 번호·부호 미표기) + hp:pic 문단을 삽입
         14. hp:pic에 hc: 네임스페이스 요소(transMatrix 등) 사용 금지 — validate 실패 원인
         15. content.hpf에서 BinData/image1.bmp 참조 반드시 제거 — 한/글 크래시 원인

         After replacement:
         1. Run fix_namespaces.py on output HWPX
         2. Run validate.py on output HWPX
         3. If validation fails, report error and keep MD as fallback"
)
```

### Fallback

validate.py 실패 시:
- 에러 내용 로그
- MD 파일만 최종 출력으로 제공
- 사용자에게 안내: "HWPX 변환에 실패했습니다. MD 파일을 수동으로 양식에 붙여넣기 해 주세요."

manifest 최종 업데이트:
```json
"phase7": {"status": "completed|failed", "output": "disclosure.hwpx"}
```

---

## Step 8: 최종 출력 및 안내

모든 Phase 완료 후 사용자에게 결과를 안내한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 발명내용설명서 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 출력 파일
- 📄 `{output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md` — Obsidian 호환 마크다운 (9개 섹션 + 부록 3개, 참고문헌은 검증된 순수 서지만)
- 📋 `{output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.hwpx` — KIMM 양식 한글 파일
- 🔍 `{output_dir}/{발명명칭}_선행특허분석.md` — KIPRIS 선행특허 분석
- 🎨 `{output_dir}/figures/` — 컬러 SVG 벡터 원본 {N}개 / `{output_dir}/figures_deck.pptx` — 도면 슬라이드 덱(슬라이드 N=[도 N])
- 🖼️ `{output_dir}/diagrams/` — 600 dpi 기술 도면 PNG {N}개
- 📚 `{output_dir}/reference/` — 인용문헌 원문 PDF {K}건 (학술 논문 + 선행특허)
- 🧾 `{output_dir}/reference_verification.json` — 인용문헌 정합성 검증 로그 (audit trail)
- 🧐 `{output_dir}/critic_report.json` — Critic 검증 결과 (verdict {PASS|FIX→PASS} + 레인별 issue {N}건)
- 💼 `{output_dir}/business_critic_report.json` — 사업화 Critic 결과 (verdict {PASS|FIX→PASS|ADVISE} + 독립항별 avoid/ignore/negotiate/respect)

### Critic 검증 결과 (Phase 6d)
- 판정: {verdict} — Lane A 출처 {issues}건 / Lane B 모순·IFR {issues}건 / Lane C 독립항 {survive/needs_amendment/reject 요약}
- (자기선행 특허 발견 시) self_prior_art: {number 목록 — 개시 요소·공지예외 기한}

### 사업화 Critic 결과 (Phase 6e — 삼성전자 전담 변리사 페르소나)
- 판정: {verdict} — 독립항별 {avoid/ignore/negotiate/respect 요약}
- 회피설계(D1): 최유력 회피 시나리오 {요약} / 차단 여부 / FIX로 신설·보정된 청구항 {N}건
- 침해 입증(D2): 등급 A/B 독립항 {유/무} / 공정 지문 청구 {유/무} / 등급 재판정 하향 {N}건
- 사업 판단(D3): 침해 주체 {요약} / 회피 vs 라이선스 {결론}
- **advisories (전략 한계·후속출원 권고 — 발명심의위 판단 재료)**: {목록 — ADVISE 판정 시 필수 표시}

> [!important] 파일명 규칙
> - MD와 HWPX 파일은 `(YYYYMMDD 발명자) 발명명칭vN` 형식으로 명명
> - 초판은 v1, 수정본이 생길 때마다 v2, v3 형태로 버전 번호를 증가
> - 버전 결정: output_dir에서 동일 발명명칭의 기존 파일을 검색하여 최대 버전 + 1
> - MD와 HWPX의 버전 번호는 항상 일치시킴

### TRIZ 분석 요약
- 기술적 모순: {N}개 도출
- 물리적 모순: {N}개 도출
- IFR: {N}개 생성, 상위 3개 → 발명내용설명서 반영

### 선행특허 차별성
- 분석 특허: {N}건
- 본 발명 미개시 요소: {핵심 차별 요소 요약}

### 특허성 재채점 (Phase 5.5)
- 재채점 IFR: {recheck_count}건 (선행특허 조사 결과 반영)
- 반대심문 상위 3개 IFR 반론 요지: {patentability_devil_advocate 요약}
- (degraded로 스킵된 경우: "선행특허 degraded로 재채점 미수행")

### 청구항 하드닝 결과 (Phase 6.5)
- 점검 issue: 발견 {issues_found}건 → 자동 수정 {auto_fixed}건, 수동 확인 필요 {reported}건
- 수동 확인 항목: {reported issues 목록 — 카테고리 재설계 등}

> [!warning] 자기공지 경고 (해당 시)
> 발명자 선공개 발견: {self_disclosure 목록 — 공개일·매체}
> **공지예외주장(신규성 의제) 기한: {grace_deadline} (공개일로부터 12개월)** — 이 기한 내 출원해야 자기공지에 의한 신규성·진보성 상실을 회피할 수 있음.

### 다음 단계
1. HWPX 파일을 한/글에서 열어 서식과 내용 확인
2. §9(추가자료)에 diagrams/ 폴더의 도면 삽입
3. 필요 시 각 섹션 내용 보완
4. 발명심의위원회 제출
```

---

## Error Handling Summary

| Phase | 실패 모드 | 대응 |
|-------|-----------|------|
| Phase 2 | IFR < 10개 | 재시도 2회, 이후 현재 결과로 진행 |
| Phase 5 | KIPRIS API 실패 | graceful degradation, 수동 보완 안내 |
| Phase 6 | 섹션/부록 누락 | 1회 재생성, 이후 부분 결과 제공 |
| Phase 6b | matplotlib 실패 | Mermaid만 발명내용설명서 MD에 포함 |
| Phase 5.5 | prior_art degraded | 재채점 스킵, Step 5b로 진행 |
| Phase 6.5 | 자동 수정 불가 issue | 수정하지 않고 Step 8 보고에 명시 |
| Phase 6c | KIPRIS/CrossRef API 실패 | 해당 인용은 manual_review, 나머지 계속 진행 |
| Phase 6c | 검증 실패/PDF 제목 불일치 | 해당 문헌 리스트에서 제거 + 본문 재번호 + json에 removed 기록 |
| Phase 6c | verify_citations.py exit!=0 | Phase 7 차단 — 리스트 정리 후 재실행(exit1) 또는 Phase 6c 재실행(exit2) |
| Phase 6d | verdict=FIX | 해당 phase 1회 자동 보정 → critic 재검(1회 한정) |
| Phase 6d | verdict=BLOCK (critical) | auto 모드여도 진행 중단, 사용자 판단 요청 |
| Phase 6d | 네트워크 불가(spot check 불능) | Lane A degraded 표기, 정합성 대조만 수행 후 진행 |
| Phase 6e | verdict=FIX | phase6 1회 자동 보정 → 6.5 하드닝 재적용 → 6d Lane C 재실행 → 6e 재검(1회 한정) |
| Phase 6e | verdict=ADVISE | 진행 계속 + Step 8 보고에 advisories 필수 표시 |
| Phase 6e | prior_art degraded (ifr_coverage 부재) | 신설 청구항의 선행 포섭 확인 불가 — required_fixes에 "추가 선행조사 필요" 플래그, D1/D2 분석은 계속 |
| Phase 7 | HWPX 변환 실패 | MD fallback |
| Phase 7 | validate.py 실패 | MD fallback + 에러 로그 |

---

## 사용자 상호작용 규칙

### 반드시 사용자 응답을 기다리는 시점

1. **Step 0**: 입력 수집 (방법 B의 자동 추출 확인 포함)
2. **Step 3**: TRIZ 분석 결과 검토 게이트

### 사용자 응답 없이 자동 진행하는 시점

1. Phase 1 → Phase 2 전환
2. Phase 4 → Phase 5 → Phase 5.5 전환
3. Step 5b 중간 진행 보고 (표시만)
4. Phase 6 → Phase 6.5(자동 점검·자동 수정) → Phase 6b → Phase 6c → Phase 6d(critic) → Phase 6e(사업화 critic) → Phase 7 전환

> [!important] 단, 두 게이트는 auto-skip 불가다. (1) Phase 6c 후 강제 게이트(verify_citations.py)는 **기계 게이트** — exit!=0이면 Phase 7로 진행하지 않는다. (2) Phase 6d critic의 **BLOCK 판정** — critical issue(성격 오규정·미검증 인용·독립항 reject) 발견 시 자동 진행 모드에서도 중단하고 사용자 판단을 요청한다.

### 자동 진행 모드 활성화 조건

사용자가 다음과 같이 지시한 경우, Step 3 검토 게이트도 건너뛰고 전체 자동 진행:
- "자동으로 진행"
- "확인할 부분 없으면 자동 진행"
- "매 phase 자동으로 진행"
- "전부 자동"
- 영어: "auto", "proceed automatically"

이 경우 Step 0의 입력 확인도 간소화한다 (자동 추출 후 바로 진행).
