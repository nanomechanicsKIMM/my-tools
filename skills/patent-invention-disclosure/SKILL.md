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

## Step 0: 입력 수집 및 검증

사용자에게 다음 3개 필드를 요청한다:

```
발명내용설명서를 작성합니다. 다음 정보를 입력해 주세요:

1. **기술분야**: 발명이 속하는 기술 분야 (예: "마이크로LED 디스플레이 제조")
2. **해결 과제**: 해결하고자 하는 기술적 문제 (예: "인터포저 제조 단계의 비용과 시간 절감")
3. **핵심 아이디어**: 문제를 해결하는 핵심 기술적 아이디어 (예: "가변 피치 레이저를 이용한 COC 직접 전사")

옵션:
- **발명자명** (기본: 미입력)
- **출력 디렉토리** (기본: 현재 작업 디렉토리의 output/)
```

입력을 받으면 `invention_manifest.json`을 생성한다:

```json
{
  "input": {
    "field": "사용자가 입력한 기술분야",
    "problem": "사용자가 입력한 해결 과제",
    "idea": "사용자가 입력한 핵심 아이디어",
    "inventor": "발명자명 (선택)",
    "date": "YYYY-MM-DD"
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

Phase 2 결과를 사용자에게 표시하고 검토를 요청한다:

```
## TRIZ 분석 결과

### 기술적 모순
{triz_analysis.technical_contradictions를 테이블로 표시}

### 물리적 모순
{triz_analysis.physical_contradictions를 테이블로 표시}

### IFR 목록 ({ifr_count}개)
{triz_analysis.ifr_list를 번호 목록으로 표시}

---

다음 중 선택해 주세요:
1. **자동 진행** — 현재 결과로 평가 및 발명내용설명서 작성을 계속합니다
2. **피드백 제공** — IFR 수정/추가/삭제 의견을 입력합니다
3. **재분석 요청** — 다른 관점에서 TRIZ 분석을 다시 수행합니다
```

- **자동 진행**: Phase 4로 바로 이동
- **피드백 제공**: 사용자 피드백을 반영하여 `triz_analysis.json` 수정 후 Phase 4
- **재분석**: Phase 2 재실행

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
# 방법 1: .env 파일에서 로드 (권장)
if [ -f "C:/Users/JHKIM/Claude_Work/Patents_EPO/.env" ]; then
  set -a
  eval "$(cat 'C:/Users/JHKIM/Claude_Work/Patents_EPO/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
  set +a
fi

# 방법 2: 환경변수 직접 확인
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

## Step 6: 발명내용설명서 최종 작성 (Phase 6)

**Agent**: `agents/phase6-disclosure-writer.md`
**Model**: opus

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read {SKILL_ROOT}/agents/phase6-disclosure-writer.md for instructions.
         Read {SKILL_ROOT}/templates/disclosure-report.md for MD template.

         Read all phase outputs from {output_dir}/:
         - triz_system.json (Phase 1)
         - triz_analysis.json (Phase 2)
         - evaluation.json (Phase 4)
         - prior_art.json (Phase 5, may be degraded)

         Input: {manifest.input}
         Output: {output_dir}/disclosure.md

         CRITICAL REQUIREMENTS:
         1. All 9 sections (§1~§9) must be filled
         2. Each section starts with '## §N' header (machine-parseable)
         3. Written in Korean
         4. If prior_art is degraded, mark §3/§4/§8 with [선행특허 수동 보완 필요]
         5. Adjust IFR rankings based on prior art novelty in §6"
)
```

### 출력 검증

생성된 `disclosure.md`에서 9개 섹션 존재 확인:

```python
import re
sections_found = re.findall(r'^## §(\d+)', md_text, re.MULTILINE)
missing = set(range(1, 10)) - set(int(s) for s in sections_found)
if missing:
    # 1회 재시도
    pass
```

manifest 업데이트:
```json
"phase6": {"status": "completed", "output": "disclosure.md"}
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

         REPLACEMENT STRATEGY:
         Use zip_replace() with unique key per section (NOT sequential).
         Keys from kimm-template-mapping.md '고유키' column.
         For §1, §2: simple single-text replacement.
         For §3~§8: replace first hp:t text with full section content.
         For §9: use XML-escaped key '&lt;기존 기술과 본 발명의 차이&gt;'.

         After replacement:
         1. Run fix_namespaces.py on output HWPX
         2. Run validate.py on output HWPX
         3. If validation fails, report error and keep MD as fallback"
)
```

### HWPX 치환 핵심 로직

```python
import zipfile, shutil
from xml.sax.saxutils import escape

def zip_replace(src_path, dst_path, replacements):
    """HWPX ZIP 내 모든 XML에서 텍스트 치환"""
    tmp = dst_path + ".tmp"
    with zipfile.ZipFile(src_path, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w') as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith('.xml') or item.filename.endswith('.hpf'):
                    text = data.decode('utf-8')
                    for old, new in replacements.items():
                        text = text.replace(old, new)
                    data = text.encode('utf-8')
                zout.writestr(item, data)
    shutil.move(tmp, dst_path)

# 치환 딕셔너리 (고유키 → 새 내용, XML escape 적용)
replacements = {
    "미소소자의 가변 피치 롤 전사 방법 및 장비": escape(sections["§1"]),
    "해당 없음.": escape(sections["§2"]),
    "장비 특허는 YTS를, 방법(공정)특허는 삼성 디스플레이를 수요기업으로 타겟한다. YTS는 롤 스탬프 장비와 레이저 장비에 특화된 기업이고, 삼성 디스플레이는 QD를 디스플레이에 응용하는 데에 관심이 많다.": escape(sections["§3"]),
    # ... §4~§8 동일 패턴
    "&lt;기존 기술과 본 발명의 차이&gt;": escape(sections["§9"]),
}
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
## 발명내용설명서 생성 완료

### 출력 파일
- 📄 `{output_dir}/{발명명칭}_발명내용설명서.md` — Obsidian 호환 마크다운
- 📋 `{output_dir}/{발명명칭}_발명내용설명서.hwpx` — KIMM 양식 한글 파일
- 🔍 `{output_dir}/{발명명칭}_선행특허분석.md` — EPO 선행특허 분석

### TRIZ 분석 요약
- 기술적 모순: {N}개 도출
- 물리적 모순: {N}개 도출
- IFR: {N}개 생성, 상위 3개 → 발명내용설명서 반영

### 다음 단계
1. HWPX 파일을 한/글에서 열어 서식과 내용 확인
2. §9(추가자료)에 도면/사진 직접 삽입
3. 필요 시 각 섹션 내용 보완
4. 발명심의위원회 제출
```

---

## Error Handling Summary

| Phase | 실패 모드 | 대응 |
|-------|-----------|------|
| Phase 2 | IFR < 10개 | 재시도 2회, 이후 현재 결과로 진행 |
| Phase 5 | EPO API 실패 | graceful degradation, 수동 보완 안내 |
| Phase 6 | 섹션 누락 | 1회 재생성, 이후 부분 결과 제공 |
| Phase 7 | HWPX 변환 실패 | MD fallback |
| Phase 7 | validate.py 실패 | MD fallback + 에러 로그 |
