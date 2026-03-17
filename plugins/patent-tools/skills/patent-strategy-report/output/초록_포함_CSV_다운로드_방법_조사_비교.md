---
title: "특허 검색 결과 CSV에 초록 포함하여 다운로드하는 방법 조사·비교"
created: 2026-03-07
tags: [특허, Google-Patents, CSV, 초록, abstract, 다운로드]
---

# 특허 검색 시 초록까지 포함한 CSV 다운로드 방법 조사·비교

특허 검색 결과를 **초록(abstract)까지 포함한 CSV**로 받는 방법을 조사하고 비교한다.

---

## 1. Google Patents 공식 "Download (CSV)"

### 방식

- 검색 결과 페이지 상단 **"Download (CSV)"** 버튼 클릭.
- 공식 도움말: 최대 **상위 1,000건** 다운로드 가능, 생성에 수 초 소요.

### 포함 컬럼 (실제 내보내기 기준)

- **id**, **title**, **assignee**, **inventor/author**, **priority date**, **filing/creation date**, **publication date**, **grant date**, **result link**, **representative figure link**
- **초록(abstract) 컬럼 없음** — 공식 CSV에는 포함되지 않는다.

### 장단점

| 장점 | 단점 |
|------|------|
| 무료, 별도 가입·API 불필요 | **초록 미포함** |
| 즉시 다운로드 | 최대 1,000건 제한 |
| RFP와 동일 검색식·필터 사용 가능 | |

**결론**: 초록이 필요하면 아래 보조 방법 중 하나를 써야 한다.

---

## 2. 현재 스킬: CSV 다운로드 후 초록 크롤링 (fetch_abstracts.py)

### 방식

1. Google Patents에서 **Download (CSV)** 로 v1 CSV 저장 (초록 없음).
2. 스킬의 **`fetch_abstracts.py`** 실행: CSV의 **result link** 컬럼 URL을 하나씩 GET 요청해 HTML에서 초록 추출 후 **abstract** 컬럼 추가.

### 사용 예

```bash
python fetch_abstracts.py <v1.csv> -o <output_with_abstracts.csv> [--delay 1.5] [--resume abstracts.json] [--limit N]
```

- `--delay`: 요청 간격(초), 기본 1.5 — 서버 부하·차단 방지.
- `--resume`: 중단 시 이어받기용 JSON.
- `--limit`: 처리할 행 수 제한(테스트용).

### 장단점

| 장점 | 단점 |
|------|------|
| **무료**, Google Patents와 동일 검색 결과 사용 | 건당 요청이라 **시간 소요**(1,000건 × 1.5초 ≈ 25분) |
| 초록 포함 CSV를 로컬에서 완전히 보유 | HTML 구조 변경 시 파서 수정 필요 |
| `--resume`로 중단 후 재개 가능 | 과도한 요청 시 차단 가능성 |

**결론**: 공식 CSV만 쓸 때 **초록을 붙이는 실무적 방법**이다. 1,000건 이하·비정기 조사에 적합.

---

## 3. SerpApi Google Patents API (유료)

### 방식

- **SerpApi**의 Google Patents API로 검색·상세 정보 요청.
- 응답 JSON에 title, **abstract**, inventor, dates, legal status 등 포함 → CSV로 변환 가능.

### 특징

- **초록 포함** 구조화 데이터 제공.
- 무료 크레딧 제한 있음(월 100 검색 등); 이후 유료.
- Google Patents와 동일한 데이터 소스이지만 SerpApi를 경유.

### 장단점

| 장점 | 단점 |
|------|------|
| 초록 등 **상세 필드 포함**, JSON/CSV 변환 용이 | **유료**(대량 사용 시) |
| 크롤링 없이 API 호출만으로 처리 | Google Patents 검색 UI와 동일한 쿼리/필터를 API로 재현해야 함 |

**참고**: [SerpApi Google Patents](https://serpapi.com/google-patents-api), [Export to CSV with Python](https://serpapi.com/blog/export-patent-details-from-google-patents-to-csv-using-python/)

---

## 4. USPTO 공식 데이터 (미국 특허 중심)

### 방식

- **USPTO Open Data / Bulk Search**: [developer.uspto.gov/data/bulk-search](https://developer.uspto.gov/data/bulk-search)
- 출원·공개 특허 검색 후 **초록 포함** 데이터 다운로드.
- 미국(US) 출원/공개 중심; PCT·다국가 가족은 별도 처리.

### 장단점

| 장점 | 단점 |
|------|------|
| **공식 데이터**, **초록 포함** | **미국 특허 중심** — 한국·중국·유럽 등 비중 높은 검색에는 부적합 |
| 무료, 대량 다운로드 가능 | Google Patents와 검색식·결과 집합이 다름 |

**결론**: US 위주 조사일 때 초록 포함 CSV를 공식적으로 받는 데 적합.

---

## 5. Google Patents Public Datasets (BigQuery)

### 방식

- **Google Cloud BigQuery**의 `patents-public-data` 데이터셋.
- SQL로 특허 검색·초록 등 필드 선택 후 내보내기(CSV 등).

### 장단점

| 장점 | 단점 |
|------|------|
| **초록 포함** 대규모 데이터, SQL로 유연한 집계·필터 | BigQuery 사용 비용·가입 필요 |
| Google Patents와 동일/유사 데이터 소스 | 검색식 → SQL 변환 및 인프라 설계 필요 |

**결론**: 대규모·반복 분석에 적합; 소규모 1회성 CSV 수집에는 과할 수 있음.

---

## 6. 방법 비교 요약

| 방법 | 초록 포함 | 비용 | 건수 제한 | 검색 = Google Patents | 난이도 |
|------|-----------|------|-----------|------------------------|--------|
| **Google Patents Download (CSV)** | ❌ | 무료 | 최대 1,000건 | ✅ 동일 | 쉬움 |
| **fetch_abstracts.py (스킬)** | ✅ | 무료 | CSV 행 수만큼 | ✅ 동일 | 쉬움 (시간 소요) |
| **SerpApi Google Patents API** | ✅ | 유료(한도 후) | API 한도 | ✅ 유사 | 중간 |
| **USPTO Bulk / Open Data** | ✅ | 무료 | 넉넉함 | ❌ US 중심 | 중간 |
| **BigQuery patents-public-data** | ✅ | 사용량 과금 | 대규모 | ✅ 유사 | 높음 |

---

## 7. 권장 시나리오

- **Google Patents 검색 결과를 그대로 쓰고, 초록만 추가하고 싶을 때**  
  → **공식 Download (CSV)** + **`fetch_abstracts.py`** (현재 스킬) 사용을 권장한다.  
  - 1,000건 이하, 비정기 조사에 적합하고, 추가 비용·가입 없이 초록 포함 CSV를 만들 수 있다.

- **미국 특허만 집중 조사할 때**  
  → USPTO Bulk Search로 초록 포함 CSV를 받는 방법을 검토한다.

- **대량·반복 분석·예산이 있을 때**  
  → SerpApi(초록 포함 자동화) 또는 BigQuery(대규모 초록 포함 분석)를 고려한다.

---

## 8. 현재 스킬 내 관련 파일

- **scripts/fetch_abstracts.py**: result link 크롤링으로 `abstract` 컬럼 추가.
- **scripts/run_v1_to_v2_pipeline.py**: v1 CSV → 제목 상위 N건 → (선택) fetch_abstracts → 초록 상위 M건 → v2 CSV.
- **reference.md**: "노이즈·NOT 개선 워크플로우 (초록 기반)" — 초록 추가 후 노이즈 분류·NOT 추출 절차.
