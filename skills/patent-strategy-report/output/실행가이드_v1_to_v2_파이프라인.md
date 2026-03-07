---
title: "v1 → v2 노이즈 필터 파이프라인 실행 가이드"
created: 2026-03-07
tags: [특허, 노이즈필터, v1, v2, RFP, TF-IDF]
---

# v1 → v2 노이즈 필터 파이프라인

검색식으로 다운로드한 v1 CSV에서 **제목–RFP 연관성**으로 상위 5000건을 남긴 뒤, **초록 추가** 후 **초록–RFP 연관성**으로 상위 2500건을 점수순 정렬해 v2로 저장하는 3단계 파이프라인입니다.

## 단계 요약

| 단계 | 설명 | 스크립트 | 입·출력 |
|------|------|----------|---------|
| **1** | v1에서 **title**과 RFP의 연관성(TF-IDF 코사인)으로 점수화 → **상위 5000건** CSV 저장 | `filter_title_top_n.py` | v1.csv → v1_top5000.csv |
| **2** | 위 5000건 CSV에 **특허 초록** 컬럼 추가 (크롤링) | `fetch_abstracts.py` | v1_top5000.csv → v1_top5000_with_abstracts.csv |
| **3** | **abstract**과 RFP의 연관성으로 점수화 → **상위 2500건**을 점수순 정렬해 **v2.csv** 저장 | `filter_abstract_top_n.py` | *_with_abstracts.csv → v2.csv |

## 한 번에 실행 (파이프라인)

```bash
cd <Patent_Analysis 또는 스크립트 상위 경로>
python .codex/skills/patent-strategy-report/scripts/run_v1_to_v2_pipeline.py <v1_csv 경로> <RFP.md 경로> --output-dir output
```

- 기본: `--top1 5000`, `--top2 2500`, 출력 디렉터리 `output/`
- **Step 2(초록 크롤링)**는 시간이 오래 걸리므로, 중단 후 재개하려면 `--resume output/abstracts_resume_top5000.json` 사용

### 초록 단계 건너뛰기

이미 5000건 CSV에 초록을 넣었거나, 초록이 있는 다른 CSV를 쓰는 경우:

```bash
python .../run_v1_to_v2_pipeline.py dummy <RFP.md> --from-abstracts <초록포함_CSV 경로> -o output
```

(첫 번째 인자 `v1_csv`는 `--from-abstracts` 사용 시 무시되므로 아무 값이나 넣어도 됨)

## 단계별 실행

### Step 1: 제목 기준 상위 5000건

```bash
python .codex/skills/patent-strategy-report/scripts/filter_title_top_n.py <v1.csv> <RFP.md> -o output/v1_top5000.csv --top 5000
```

- 출력 CSV에 `relevance_score` 컬럼이 추가됩니다.
- **제외 키워드**(RFP 범위에서 제외할 단어, 예: OLED·LCD): `--exclude-terms "OLED,LCD"` 를 붙이면, **제목**에 해당 단어가 포함된 행은 점수 계산 전에 제거된 뒤 상위 N건이 출력됩니다. 검색식에서 NOT을 썼더라도 수집 CSV에 섞여 들어온 경우를 보정할 수 있습니다.

### Step 2: 5000건 CSV에 초록 추가

```bash
python .codex/skills/patent-strategy-report/scripts/fetch_abstracts.py output/v1_top5000.csv -o output/v1_top5000_with_abstracts.csv --delay 1.5 --resume output/abstracts_resume_top5000.json
```

- `--resume`: 중단 후 같은 파일로 다시 실행하면 이미 받은 초록은 건너뜁니다.
- `--limit N`: 테스트 시 N건만 처리할 때 사용.

### Step 3: 초록 기준 상위 2500건 → v2 (점수순 정렬)

```bash
python .codex/skills/patent-strategy-report/scripts/filter_abstract_top_n.py output/v1_top5000_with_abstracts.csv <RFP.md> -o output/v2.csv --top 2500
```

- v2.csv는 **abstract–RFP 연관성 점수** 기준 **내림차순** 정렬된 상위 2500건입니다.
- **핵심 특허**(예: 상위 10건)를 뽑을 때: 동일 CSV에서 **제목 또는 초록**에 RFP 제외 키워드(예: OLED, LCD)가 포함된 행을 제거한 뒤, 점수순 상위 N건을 저장하도록 파이프라인을 구성할 수 있습니다. (일반화된 10k→500→core 10 파이프라인 예: `run_10k_500_core_pipeline.py` 참고.)

## 의존성

- **scikit-learn** (TF-IDF, cosine_similarity)
- **requests**, **beautifulsoup4** (fetch_abstracts.py)

`requirements.txt`에 없으면 추가 후:

```bash
pip install scikit-learn requests beautifulsoup4
```

## 출력 파일

- `output/v1_top5000.csv` — 제목–RFP 상위 5000건 + relevance_score
- `output/v1_top5000_with_abstracts.csv` — 위 파일 + abstract 컬럼
- `output/v2.csv` — 초록–RFP 상위 2500건, 점수순 정렬 (최종 결과)
- `output/abstracts_resume_top5000.json` — 초록 크롤링 재개용 (선택)
