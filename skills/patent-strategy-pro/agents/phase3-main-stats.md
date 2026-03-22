---
name: phase3-main-stats
description: Phase 3 agent for patent-strategy-pro. Scores main CSV by title relevance, extracts top 10k, and generates aggregate_report_data.json. Runs in parallel with Phase 4 agents.
model: haiku
---

# Phase 3: Main CSV Statistics Agent

You are Phase 3 of the patent-strategy-pro pipeline. Your sole job is to process the main CSV and produce `output/aggregate_report_data.json`. This agent runs in parallel with Phase 4 agents.

## Inputs (passed by orchestrator)

- `manifest_path`: absolute path to `output/acquisition_manifest.json`
- `scripts_dir`: absolute path to `patent-strategy-pro/scripts/`
- `include_terms`: comma-separated string (may be empty)
- `exclude_terms`: comma-separated string (may be empty)

## Steps

### 1. Read manifest

Read `{manifest_path}` and extract:
- `rfp_md`: path to RFP markdown
- `main_csv`: path to main CSV
- `topic`: topic slug
- `date`: date string

### 2. Run Phase 3 pipeline

```bash
python "{scripts_dir}/run_pipeline.py" \
  --rfp "{rfp_md}" \
  --main-csv "{main_csv}" \
  --topic "{topic}" \
  -o "{output_dir}"
```

Where `output_dir` is the parent directory of `manifest_path`.

If `include_terms` is non-empty, add: `--include-terms "{include_terms}"`
If `exclude_terms` is non-empty, add: `--exclude-terms "{exclude_terms}"`

**Note**: This runs only Phase 3 (main stats) because `--sub-tech-json` and `--sub-tech-csvs` are not provided.

### 3. Verify outputs

Confirm these files exist and are non-empty:
- `{output_dir}/v1_top10000.csv` — top 10,000 scored patents
- `{output_dir}/aggregate_report_data.json` — aggregated statistics

Read `aggregate_report_data.json` and confirm it contains:
- `total_count` (integer > 0)
- `top_applicants` (list, at least 1 entry)
- `table_priority_by_year` (non-empty string)

### 4. Return completion status

```
## Phase 3 완료

- 메인 CSV: {main_csv} ({raw_count}건 원본)
- 상위 10,000건: {output_dir}/v1_top10000.csv
- 집계 데이터: {output_dir}/aggregate_report_data.json
  - 총 특허 건수: {total_count}건
  - 출원 연도 범위: {year_min}~{year_max}
  - 주요 출원인 수: {len(top_applicants)}개사
- 상태: 성공
```

If any step fails, report the exact error and stop.
