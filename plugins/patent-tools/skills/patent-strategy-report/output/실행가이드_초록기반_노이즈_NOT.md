# 초록 기반 노이즈·NOT 파이프라인 실행 가이드

**목적**: CSV에 초록이 없을 때, 특허 페이지를 크롤링해 초록을 추가하고, RFP와의 상관성으로 노이즈를 분류한 뒤, **노이즈 특허만 분석해 NOT 키워드를 추출**한다.

---

## 1. 의존성 설치

```bash
cd .codex\skills\patent-strategy-report\scripts
uv pip install -r requirements.txt
```

- `requests`, `beautifulsoup4`, `scikit-learn` 이 추가되어 있음.

---

## 2. 한 번에 실행 (권장)

```bash
uv run python run_noise_pipeline_with_abstracts.py "<CSV경로>" "<RFP경로>" --current-query "(Display OR ...)" --search-url "https://patents.google.com/?q=..."
```

- **처음 실행**: 전체 크롤링이므로 시간이 오래 걸릴 수 있음. 테스트 시 `--fetch-limit 50` 으로 50건만 초록 수집.
- **이미 초록이 있는 CSV**가 있으면 `--skip-fetch` 로 1단계 생략.

**출력 파일** (기본 `output/`):

| 파일 | 설명 |
|------|------|
| `csv_with_abstract.csv` | 초록 컬럼이 추가된 CSV (skip-fetch 시 미생성) |
| `scored_relevance.csv` | `relevance_score`, `is_noise` 컬럼 추가 |
| `not_from_noise_result.txt` | SUGGESTED_NOT_TERMS, IMPROVED_QUERY_SUGGESTION, IMPROVED_SEARCH_URL |

---

## 3. 단계별 실행

### 3.1 초록 크롤링

```bash
uv run python fetch_abstracts.py "<입력CSV>" -o output/csv_with_abstract.csv --delay 1.5 [--limit 100] [--resume output/abstracts.json]
```

- `--resume`: 중단 후 재실행 시 이미 수집한 id→abstract를 불러와 이어서 수집.

### 3.2 초록–RFP 상관성 점수 및 노이즈 분류

```bash
uv run python score_relevance.py output/csv_with_abstract.csv "<RFP경로>" -o output/scored_relevance.csv --threshold 0.12 --no-abstract-use-title
```

- 점수 < 0.12 인 행을 노이즈(`is_noise=true`)로 분류. 필요 시 `--threshold` 조정.

### 3.3 노이즈에서 NOT 키워드 추출

```bash
uv run python extract_not_from_noise.py output/scored_relevance.csv "<RFP경로>" --current-query "..." --search-url "..." -o output/not_from_noise_result.txt --top-n 8
```

---

## 4. 다음 단계

- `not_from_noise_result.txt` 의 **IMPROVED_SEARCH_URL** 로 Google Patents 검색 후 새 CSV 다운로드.
- 새 CSV로 기존 파이프라인(`run_full_pipeline.py` 또는 이 파이프라인)을 다시 실행하여 REMOVAL_RATIO ≤ 10% 가 될 때까지 반복.
