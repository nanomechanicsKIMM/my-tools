---
name: patent-strategy-pro
description: Advanced patent strategy report with sub-technology decomposition, gap analysis, Objective-Solution matrix, and IP creation strategy. Supports PDF or MD RFP input. Generates Obsidian-format report. Use when user asks for 특허 전략 보고서, 세부 기술 분석, 공백 기술, OS 매트릭스, IP 창출 전략, 특허 분석 보고서, patent strategy.
---

# Patent Strategy Pro – Orchestrator

PDF 또는 MD 형식의 RFP를 입력받아 세부 기술별 특허 분석, 공백 기술 분석, Objective-Solution Matrix, IP 창출 전략을 포함한 종합 특허 전략 보고서(Obsidian MD)를 생성한다. **기술 분야에 무관하게** 반도체, 배터리, 바이오, AI, 통신, 로봇, 소재 등 어떤 RFP에도 적용 가능하다.

## When to Use

- 사용자가 RFP(PDF 또는 MD)와 특허 전략 보고서를 요청할 때
- "특허 전략 보고서", "세부 기술 분석", "공백 기술", "OS 매트릭스", "IP 창출 전략", "RFP 특허 검색", "Google Patents 분석" 언급 시
- 기존 `/patent-strategy-report` 보다 심층 분석이 필요한 경우

## Inputs

1. **RFP 파일** (필수): PDF 또는 MD 형식
2. **옵션**: `--include-terms`, `--exclude-terms`, `--years` (기본 10년)

## Skill Constants

```
SKILL_ROOT = ~/.claude/skills/patent-strategy-pro/
SCRIPTS_DIR = SKILL_ROOT/scripts/
AGENTS_DIR = SKILL_ROOT/agents/
```

## Output Directory

Ask the user for an output directory or default to a `output/` subdirectory next to the RFP file.
Create it if it doesn't exist.

---

## Step 0-A: Patent Database Selection

Present this to the user **before launching any agent**:

```
**특허 검색 DB를 선택하세요:**

1. Google Patents (수동 CSV 다운로드)
   - 브라우저에서 검색 URL 열기 → CSV 다운로드 → 파일 경로 제공
   - EPO 계정 불필요

2. EPO OPS (자동 검색, API 키 필요)
   - 검색부터 초록 수집까지 자동 실행
   - 사전 준비: https://developers.epo.org 에서 Consumer Key/Secret 발급
   - 환경변수: EPO_OPS_KEY, EPO_OPS_SECRET
```

Wait for user selection. Set `db_mode = "google"` or `db_mode = "epo"`.

## Step 0-B: Input Collection

Immediately after DB selection, collect:

```
다음 정보를 입력해 주세요:

1. RFP 파일 경로 (PDF 또는 MD):
2. 보고서 주제명 (한국어 슬러그, 예: "센서융합디스플레이"):
3. 출력 디렉토리 경로 (기본: RFP 파일 옆 output/):
4. 필수 포함 단어 (쉼표 구분, 선택): 예) "flexible display, OLED"
5. 제외 단어 (쉼표 구분, 선택): 예) "lighting, signage"
6. 검색 기간 (기본 10년): 5 / 10 / 15
```

Store collected values:
- `rfp_input`: path to RFP file
- `topic`: Korean slug (used in output filename)
- `output_dir`: absolute path to output directory
- `include_terms`: comma-separated string (empty string if none)
- `exclude_terms`: comma-separated string (empty string if none)
- `years`: integer
- `date`: today's date as YYYYMMDD

---

## Agent Model Assignment

각 에이전트는 작업 복잡도에 따라 모델이 지정되어 있다. Agent 호출 시 `model` 파라미터를 반드시 명시한다.

| Phase | Agent | Model | 근거 |
|-------|-------|-------|------|
| Phase 1 | phase1-rfp-prep | **haiku** | PDF→MD 단순 변환 |
| Phase 2A | phase2a-sub-tech-extract | **sonnet** | 세부 기술 도출·보정 (분석 판단) |
| Phase 2B | phase2b-query-gen | **sonnet** | 검색식 생성·Playwright 건수 조정 (반복 판단) |
| Phase 3 | phase3-main-stats | **haiku** | CSV 통계 집계 (스크립트 실행·수치 처리) |
| Phase 4 | phase4-sub-tech-analysis | **sonnet** | 세부 기술별 특허 분석 (핵심 특허 선별) |
| Phase 5 | phase5-report-writer | **opus** | 전략 보고서 작성 (공백 분석·OS 매트릭스·IP 전략) |

---

## Orchestration Sequence

### Phase 1 (serial)

Launch Agent with `agents/phase1-rfp-prep.md`:

```
Task: Prepare RFP markdown
Agent: phase1-rfp-prep
Inputs:
  rfp_input: {rfp_input}
  output_dir: {output_dir}
  scripts_dir: {SCRIPTS_DIR}
```

Wait for completion. Verify `{output_dir}/rfp.md` exists. On failure, stop and report error to user.

---

### Phase 2A (serial)

Launch Agent with `agents/phase2a-sub-tech-extract.md`:

```
Task: Extract and correct sub-technologies
Agent: phase2a-sub-tech-extract
Inputs:
  rfp_md: {output_dir}/rfp.md
  output_dir: {output_dir}
  scripts_dir: {SCRIPTS_DIR}
  include_terms: {include_terms}
  exclude_terms: {exclude_terms}
```

Wait for completion. The agent returns the approval table markdown.

---

### ⏱️ USER APPROVAL GATE (1분 타임아웃)

Present the approval table returned by the Phase 2A agent verbatim to the user, with the following notice:

```
> [!warning] 1분 내 수정 요청이 없으면 자동으로 다음 단계로 진행합니다.
```

Then use `AskUserQuestion` to request approval. **Wait up to 60 seconds.**

- If user approves ("확인", "OK", "ok", "진행", "맞습니다", "좋아요") → proceed immediately
- If user requests corrections → apply changes to `{output_dir}/sub_techs.json`, re-present, and wait again (60초 타이머 리셋)
- **If 60초 경과 후 응답 없음** → 현재 세부 기술 그대로 확정하고 Phase 2B로 자동 진행. 진행 시 다음 메시지를 출력:
  ```
  ⏱️ 1분 타임아웃 — 세부 기술을 현재 상태로 확정하고 Phase 2B를 진행합니다.
  ```

---

### Phase 2B (serial)

Launch Agent with `agents/phase2b-query-gen.md`:

```
Task: Generate queries, auto-adjust counts, open browser tabs, acquire CSVs
Agent: phase2b-query-gen
Inputs:
  rfp_md: {output_dir}/rfp.md
  sub_techs_json: {output_dir}/sub_techs.json
  output_dir: {output_dir}
  scripts_dir: {SCRIPTS_DIR}
  db_mode: {db_mode}
  years: {years}
  include_terms: {include_terms}
  exclude_terms: {exclude_terms}
  topic: {topic}
  date: {date}
```

**Google Patents mode** (3단계 자동화):
1. **검색식 생성** → 구문 규칙 자동 검증/수정
2. **Playwright 자동 건수 조정** → 각 검색식별 목표 건수(MAIN ~5,000 / SUB ~1,000) 도달까지 최대 5회 반복
3. **브라우저 탭 오픈** → MAIN + SUB1~N 전체 URL을 Playwright로 동시에 탭 열기
4. 사용자가 각 탭에서 CSV 수동 다운로드 후 확인 대기
5. CSV 경로 확인 → `acquisition_manifest.json` 작성

**EPO mode**: The agent runs fully automatically. Wait for completion.

Verify `{output_dir}/acquisition_manifest.json` exists after completion.

---

### Phase 3 + Phase 4 (PARALLEL — launch all in a single message)

Read `{output_dir}/sub_techs.json` to get the list of sub-tech IDs.

Launch the following agents simultaneously in a single message (one Agent tool call per agent):

**Agent 1: Phase 3 — Main Statistics**
```
Task: Compute main CSV statistics
Agent: phase3-main-stats
Inputs:
  manifest_path: {output_dir}/acquisition_manifest.json
  scripts_dir: {SCRIPTS_DIR}
  include_terms: {include_terms}
  exclude_terms: {exclude_terms}
```

**Agent 2..N+1: Phase 4 — Sub-Tech Analysis (one per sub-tech)**

For each sub-tech with id `sub_id` at index `i` (0-based):
```
Task: Analyze sub-technology {sub_id}
Agent: phase4-sub-tech-analysis
Inputs:
  manifest_path: {output_dir}/acquisition_manifest.json
  sub_tech_id: {sub_id}
  sub_tech_json_path: {output_dir}/sub_techs.json
  scripts_dir: {SCRIPTS_DIR}
  include_terms: {include_terms}
  exclude_terms: {exclude_terms}
  db_mode: {db_mode}
  sub_index: {i}
```

Wait for ALL parallel agents to complete before proceeding.

Verify:
- `{output_dir}/aggregate_report_data.json` exists (Phase 3)
- `{output_dir}/{sub_id}/core5_patents.csv` exists for every sub_id (Phase 4)
- `{output_dir}/{sub_id}/analysis_complete.flag` exists for every sub_id (Phase 4)

---

### Phase 5 (serial, last)

Launch Agent with `agents/phase5-report-writer.md`:

```
Task: Write complete patent strategy report
Agent: phase5-report-writer
Inputs:
  manifest_path: {output_dir}/acquisition_manifest.json
  sub_tech_json_path: {output_dir}/sub_techs.json
  skill_root: {SKILL_ROOT}
```

Wait for completion. Verify the report file exists:
`{output_dir}/{date}_{topic}_특허전략보고서.md`

---

## Final Status Report

After Phase 5 completes, present to the user:

```
## 특허 전략 보고서 생성 완료

**최종 보고서**: {output_dir}/{date}_{topic}_특허전략보고서.md

**생성된 파일 목록**:
- rfp.md — RFP 변환본
- sub_techs.json — 세부 기술 정의 ({N}개)
- queries_sub_techs.md — 검색식
- acquisition_manifest.json — CSV 경로 매니페스트
- v1_top10000.csv — 메인 상위 10,000건
- aggregate_report_data.json — 통계 집계
- sub1/core5_patents.csv ~ subN/core5_patents.csv — 세부 기술별 핵심 특허
- analysis/gap_analysis.md — 공백 기술 분석
- analysis/os_matrix.md — OS 매트릭스
- analysis/ip_strategy.md — IP 창출 전략
- {date}_{topic}_특허전략보고서.md — **최종 보고서 (§1~§9)**
```

---

## Files in This Skill

- [SKILL.md](SKILL.md) — 오케스트레이터 (이 파일)
- [agents/phase1-rfp-prep.md](agents/phase1-rfp-prep.md) — Phase 1 에이전트
- [agents/phase2a-sub-tech-extract.md](agents/phase2a-sub-tech-extract.md) — Phase 2A 에이전트
- [agents/phase2b-query-gen.md](agents/phase2b-query-gen.md) — Phase 2B 에이전트
- [agents/phase3-main-stats.md](agents/phase3-main-stats.md) — Phase 3 에이전트 (병렬)
- [agents/phase4-sub-tech-analysis.md](agents/phase4-sub-tech-analysis.md) — Phase 4 에이전트 (병렬, N 인스턴스)
- [agents/phase5-report-writer.md](agents/phase5-report-writer.md) — Phase 5 에이전트
- [reference.md](reference.md) — 방법론, 알고리즘, 정규화 규칙
- [templates/report-template.md](templates/report-template.md) — §1~§9 보고서 템플릿
- [templates/sub-tech-analysis-template.md](templates/sub-tech-analysis-template.md) — §5 세부 기술 템플릿
- [scripts/](scripts/) — Python 스크립트 (변경 없음)
- [output/실행가이드.md](output/실행가이드.md) — 단계별 실행 가이드

## Inter-Phase Handoff Contract

`output/acquisition_manifest.json` is the single source of truth for CSV paths:

```json
{
  "rfp_md": "output/rfp.md",
  "topic": "string",
  "date": "YYYYMMDD",
  "db_mode": "google | epo",
  "main_csv": "output/gp-search-{date}_main.csv",
  "sub_tech_csvs": {
    "sub1": "output/gp-search-{date}_sub1.csv",
    "sub2": "output/gp-search-{date}_sub2.csv"
  }
}
```

Phase 3 and all Phase 4 agents read ONLY from this manifest — they never accept CSV paths as direct arguments.

## Dependencies

- Python 3.9+
- `pdfplumber` (PDF→MD 변환)
- `pandas` (집계)
- `scikit-learn` (TF-IDF 유사도)
- `requests`, `beautifulsoup4` (초록 수집)
- `python-epo-ops-client` (EPO OPS 모드)
- [scripts/requirements.txt](scripts/requirements.txt) 참고
