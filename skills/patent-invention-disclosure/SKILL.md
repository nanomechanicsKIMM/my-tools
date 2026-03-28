---
name: patent-invention-disclosure
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
SKILL_ROOT = C:/Users/JHKIM/.claude/skills/patent-invention-disclosure
HWPX_SKILL = C:/Users/JHKIM/.claude/skills/hwpx
HWPX_XML_SKILL = C:/Users/JHKIM/.claude/skills/hwpx-xml
PATENT_STRATEGY_SKILL = C:/Users/JHKIM/.claude/skills/patent-strategy-pro
EPO_ENV_FILE = C:/Users/JHKIM/Claude_Work/Patents_EPO/.env
```

---

## 워크플로우 전체 개요

```
Step 0: 입력 수집 ──────────────────── 사용자 상호작용
Step 1: TRIZ 시스템 분석 (Phase 1) ─── sonnet 에이전트
Step 2: 모순 + IFR 생성 (Phase 2) ──── opus 에이전트
Step 3: 사용자 검토 게이트 ──────────── 사용자 상호작용 (결과 표시 + 선택)
Step 4: 정량 평가 (Phase 4) ─────────── sonnet 에이전트
Step 5: 선행특허 조사 (Phase 5) ─────── sonnet 에이전트
Step 5b: 중간 진행 보고 ────────────── 사용자에게 진행 상황 표시
Step 6: 발명내용설명서 작성 (Phase 6) ── opus 에이전트
Step 6b: 도면 생성 (Phase 6b) ───────── sonnet 에이전트
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
- **발명자명** (기본: 미입력)
- **출력 디렉토리** (기본: 현재 작업 디렉토리의 output/)
- **참조 문서** (기본: 현재 디렉토리의 .md 파일 자동 탐색)
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
    "inventor": "발명자명 (선택)",
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

### 물리적 모순 ({N}개)

| ID | 모순 내용 | 분리 법칙 |
|----|----------|----------|
{triz_analysis.physical_contradictions를 테이블로}

### IFR 목록 ({ifr_count}개)

| # | 핵심 내용 (요약) | 적용 원리 |
|---|----------------|----------|
{triz_analysis.ifr_list를 간결한 테이블로}

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

### EPO API 키 로드

실행 전 EPO API 키를 환경변수로 로드한다:

```bash
if [ -f "C:/Users/JHKIM/Claude_Work/Patents_EPO/.env" ]; then
  set -a
  eval "$(cat 'C:/Users/JHKIM/Claude_Work/Patents_EPO/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
  set +a
fi

if [ -z "$EPO_OPS_KEY" ]; then
  echo "WARNING: EPO_OPS_KEY not set. Phase 5 will run in degraded mode."
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

         EPO search script: {PATENT_STRATEGY_SKILL}/scripts/search_patents_epo.py
         EPO .env file: {EPO_ENV_FILE}

         Before calling the EPO script, load env vars:
         set -a && eval \"$(cat '{EPO_ENV_FILE}' | sed 's/^[[:space:]]*//' | grep -v '^#')\" && set +a

         Input: {manifest.input}
         Output: {output_dir}/prior_art.json
         Also output: {output_dir}/{발명명칭}_선행특허분석.md"
)
```

### Graceful Degradation

EPO 검색 실패 시:
- `prior_art.json`에 `{"status": "degraded", "reason": "EPO API failure", "patents": []}` 기록
- 사용자에게 안내: "선행특허 자동 검색에 실패했습니다. §3, §4, §8 섹션은 수동 보완이 필요합니다."
- Phase 6는 degraded 상태로 계속 진행

manifest 업데이트:
```json
"phase5": {"status": "completed|degraded", "output": "prior_art.json"}
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
         Output: {output_dir}/disclosure.md

         CRITICAL REQUIREMENTS:
         1. All 9 sections (§1~§9) must be filled
         2. All 3 appendices (부록 A/B/C) must be filled
         3. Each section starts with '## §N' header (machine-parseable)
         4. Written in Korean
         5. If prior_art is degraded, mark §3/§4/§8 with [선행특허 수동 보완 필요]
         6. Adjust IFR rankings based on prior art novelty in §6
         7. Include ALL references with proper citations (DOI, patent numbers, URLs)
         8. Reflect inventor philosophy from user-philosophy.md
         9. After writing, update user-philosophy.md §4 with new patterns found"
)
```

### 출력 검증

생성된 `disclosure.md`에서 9개 섹션 + 3개 부록 존재 확인:

```python
import re
sections_found = re.findall(r'^## §(\d+)', md_text, re.MULTILINE)
appendices_found = re.findall(r'^## 부록 ([A-C])', md_text, re.MULTILINE)
missing_sec = set(range(1, 10)) - set(int(s) for s in sections_found)
missing_app = set(['A', 'B', 'C']) - set(appendices_found)
if missing_sec or missing_app:
    # 1회 재시도
    pass
```

manifest 업데이트:
```json
"phase6": {"status": "completed", "output": "disclosure.md"}
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
         Read {output_dir}/disclosure.md for §6 and §9 content.
         Read {output_dir}/triz_system.json for system components.
         Read {output_dir}/evaluation.json for top IFRs.

         Input: {manifest.input}
         Output directory: {output_dir}/diagrams/
         Also update: {output_dir}/disclosure.md §9 with diagram references

         Generate at minimum:
         1. 전체 시스템 구성도
         2. 공정 흐름도
         3. 종래기술 vs 본 발명 비교도

         Use matplotlib for technical drawings, Mermaid for flowcharts.
         Korean font: plt.rcParams['font.family'] = 'Malgun Gothic'"
)
```

manifest 업데이트:
```json
"phase6b": {"status": "completed", "output": "diagrams/", "diagram_count": N}
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
         Read {output_dir}/disclosure.md for content to insert.

         Template: {SKILL_ROOT}/assets/[KIMM]직무발명내용설명서_양식.hwpx
         fix_namespaces: {HWPX_SKILL}/scripts/fix_namespaces.py
         validate: {HWPX_XML_SKILL}/scripts/validate.py

         Output: {output_dir}/{발명명칭}_발명내용설명서.hwpx

         CRITICAL — MUST USE STRATEGY A (전체 셀 내용 교체):
         1. Parse section0.xml with xml.etree.ElementTree
         2. For each section: locate the target <hp:tc> cell by table/row/cell index
         3. Remove ALL existing <hp:p> elements from the cell
         4. Split new content by newline into individual <hp:p> elements
         5. Use correct paraPrIDRef and charPrIDRef per section
         6. Remove §9 template image (hp:pic and BinData/image1.bmp)
         7. DO NOT use zip_replace() — it causes text overlap bugs

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
- 📄 `{output_dir}/disclosure.md` — Obsidian 호환 마크다운 (9개 섹션 + 부록 3개)
- 📋 `{output_dir}/{발명명칭}_발명내용설명서.hwpx` — KIMM 양식 한글 파일
- 🔍 `{output_dir}/{발명명칭}_선행특허분석.md` — EPO 선행특허 분석
- 🎨 `{output_dir}/diagrams/` — 기술 도면 {N}개

### TRIZ 분석 요약
- 기술적 모순: {N}개 도출
- 물리적 모순: {N}개 도출
- IFR: {N}개 생성, 상위 3개 → 발명내용설명서 반영

### 선행특허 차별성
- 분석 특허: {N}건
- 본 발명 미개시 요소: {핵심 차별 요소 요약}

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
| Phase 5 | EPO API 실패 | graceful degradation, 수동 보완 안내 |
| Phase 6 | 섹션/부록 누락 | 1회 재생성, 이후 부분 결과 제공 |
| Phase 6b | matplotlib 실패 | Mermaid만 disclosure.md에 포함 |
| Phase 7 | HWPX 변환 실패 | MD fallback |
| Phase 7 | validate.py 실패 | MD fallback + 에러 로그 |

---

## 사용자 상호작용 규칙

### 반드시 사용자 응답을 기다리는 시점

1. **Step 0**: 입력 수집 (방법 B의 자동 추출 확인 포함)
2. **Step 3**: TRIZ 분석 결과 검토 게이트

### 사용자 응답 없이 자동 진행하는 시점

1. Phase 1 → Phase 2 전환
2. Phase 4 → Phase 5 전환
3. Step 5b 중간 진행 보고 (표시만)
4. Phase 6 → Phase 6b → Phase 7 전환

### 자동 진행 모드 활성화 조건

사용자가 다음과 같이 지시한 경우, Step 3 검토 게이트도 건너뛰고 전체 자동 진행:
- "자동으로 진행"
- "확인할 부분 없으면 자동 진행"
- "매 phase 자동으로 진행"
- "전부 자동"
- 영어: "auto", "proceed automatically"

이 경우 Step 0의 입력 확인도 간소화한다 (자동 추출 후 바로 진행).
