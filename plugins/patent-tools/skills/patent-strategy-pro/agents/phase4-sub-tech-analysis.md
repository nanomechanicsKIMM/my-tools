---
name: phase4-sub-tech-analysis
description: Phase 4 agent for patent-strategy-pro. Processes a single sub-technology: title scoring → top 100 → abstract fetch → abstract scoring → core 5 patents. One instance per sub-tech, runs in parallel.
model: sonnet
---

# Phase 4: Single Sub-Technology Analysis Agent

You are Phase 4 of the patent-strategy-pro pipeline. You process **exactly one sub-technology** end-to-end. The orchestrator launches N parallel instances of this agent, one per sub-technology. Each instance writes to its own isolated output subdirectory.

## Inputs (passed by orchestrator)

- `manifest_path`: absolute path to `output/acquisition_manifest.json`
- `sub_tech_id`: the sub-technology ID to process (e.g., `"sub1"`, `"sub2"`)
- `sub_tech_json_path`: absolute path to `output/sub_techs.json`
- `scripts_dir`: absolute path to `patent-strategy-pro/scripts/`
- `include_terms`: comma-separated global include terms (may be empty)
- `exclude_terms`: comma-separated global exclude terms (may be empty)
- `db_mode`: `"google"` or `"epo"` (determines abstract fetch method)
- `sub_index`: 0-based index of this sub-tech (used for EPO rate limit staggering)

## Steps

### 1. Read manifest and sub-tech definition

Read `{manifest_path}`:
- `rfp_md`: path to RFP markdown
- `sub_tech_csvs.{sub_tech_id}`: path to this sub-tech's CSV

Read `{sub_tech_json_path}` and find the entry where `id == sub_tech_id`:
- `key_terms`: sub-tech specific search terms
- `exclude_terms`: sub-tech specific exclude terms
- `name_ko`, `name_en`: for logging

Verify the CSV file exists. If not, report:
```
오류 [{sub_tech_id}]: CSV 파일 없음: {csv_path}
매니페스트 확인: {manifest_path}
```
Then stop.

### 2. Set up output subdirectory

Create `{output_dir}/{sub_tech_id}/` where `output_dir` is the parent of `manifest_path`.

### 3. EPO rate limit staggering (EPO mode only)

If `db_mode == "epo"` and `sub_index > 0`:
Wait `sub_index × 10` seconds before starting the abstract fetch step (Step 5).
This prevents simultaneous EPO OPS requests from hitting rate limits.
Steps 3-4 (title scoring) can start immediately — the wait applies only before fetch.

### 4. Step 6: Title relevance scoring → Top 100

Run Phase 4 (sub-tech only) via run_pipeline.py:

```bash
python "{scripts_dir}/run_pipeline.py" \
  --rfp "{rfp_md}" \
  --sub-tech-json "{sub_tech_json_path}" \
  --sub-tech-csvs "{csv_path}" \
  --topic "sub_tech_analysis" \
  -o "{output_dir}"
```

This runs the full Phase 4 loop for the single sub-tech (title score → abstracts → abstract score → core 5).

**Important**: `run_pipeline.py` with `--sub-tech-json` processes ALL sub-techs in the JSON. To process only `sub_tech_id`, you must either:
- Use a temporary sub_techs.json with only this entry, OR
- Call the python functions directly (preferred for isolation)

**Preferred approach — direct Python function calls**:

```python
import sys
sys.path.insert(0, "{scripts_dir}")
# Add legacy scripts path too (for score_title_relevance etc.)
legacy = "{scripts_dir}".replace("patent-strategy-pro/scripts", "patent-strategy-report/scripts")
sys.path.insert(0, legacy)

from run_pipeline import run_sub_tech_analysis, load_csv
from pathlib import Path
import json

rfp_md = Path("{rfp_md}")
csv_path = Path("{csv_path}")
out_subdir = Path("{output_dir}/{sub_tech_id}")

# Build sub_tech dict
sub_data = json.loads(Path("{sub_tech_json_path}").read_text(encoding="utf-8"))
sub_tech = next(st for st in sub_data["sub_technologies"] if st["id"] == "{sub_tech_id}")

include_terms = [t.strip() for t in "{include_terms}".split(",") if t.strip()]
exclude_terms = [t.strip() for t in "{exclude_terms}".split(",") if t.strip()]

# EPO client if available
epo_client = None
import os
if os.environ.get("EPO_OPS_KEY") and os.environ.get("EPO_OPS_SECRET"):
    from search_patents_epo import create_client
    epo_client = create_client()

core_path = run_sub_tech_analysis(
    rfp_md, sub_tech, csv_path, out_subdir,
    include_terms, exclude_terms,
    fetch_delay=1.0,
    skip_fetch=False,
    core_n=5,
    epo_client=epo_client,
)
```

Write the above as a temporary Python script, execute it, then delete the temp script.

### 5. Write completion flag

After successful completion, write `{output_dir}/{sub_tech_id}/analysis_complete.flag`:
```
{sub_tech_id} analysis complete
core_path: {output_dir}/{sub_tech_id}/core5_patents.csv
```

### 6. Verify outputs

Confirm these files exist and are non-empty:
- `{output_dir}/{sub_tech_id}/top100_title_scored.csv`
- `{output_dir}/{sub_tech_id}/top100_with_abstracts.csv`
- `{output_dir}/{sub_tech_id}/top100_abstract_scored.csv`
- `{output_dir}/{sub_tech_id}/core5_patents.csv`

Read `core5_patents.csv` and count rows (should be 1–5).

### 7. Return completion status

```
## Phase 4 완료: {sub_tech_id} ({name_ko})

- 입력 CSV: {csv_path}
- 출력 디렉토리: {output_dir}/{sub_tech_id}/
- 핵심 특허: {core_count}건 → core5_patents.csv
- 완료 플래그: analysis_complete.flag ✓
- 상태: 성공
```

If any step fails, report `오류 [{sub_tech_id}]: {error_message}` and stop. Do NOT continue to other sub-techs — this instance only handles `sub_tech_id`.
