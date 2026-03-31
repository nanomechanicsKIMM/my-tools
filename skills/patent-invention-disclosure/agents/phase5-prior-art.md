---
name: phase5-prior-art
description: "선행특허 조사 에이전트. KIPRIS Plus REST API를 통해 한국 특허 키워드 검색을 수행하고 TF-IDF 유사도로 상위 10건을 선정한다."
model: sonnet
---

# Phase 5: 선행특허 조사

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_analysis.json` (IFR 목록)
3. `evaluation.json` (상위 3개 IFR)

## 의존 스크립트

- **search_patents_kipris.py**: `{SKILL_ROOT}/scripts/search_patents_kipris.py`
- **KIPRIS API 키**: 환경변수 `KIPRIS_API_KEY` 또는 `KIPRIS_REST_ACCESS_KEY`
- **API 키 위치**: `C:/Users/JHKIM/Claude_Work/.env`

## 작업

### Step 1: KIPRIS 검색 키워드 구성

사용자 입력(기술분야, 과제, 아이디어)과 상위 IFR 키워드를 조합하여 KIPRIS 검색식을 구성한다.

```
KIPRIS 검색식 규칙:
- AND 연산자: * (예: "마이크로LED*전사")
- OR 연산자: + (예: "레이저+광원")
- NOT 연산자: ! (예: "디스플레이!LCD")
- 핵심 키워드 3-5개를 AND 조합
- IPC 분류 코드는 --ipc 옵션으로 별도 지정
```

예시:
```
마이크로LED*전사*가변피치
```

### Step 2: KIPRIS 검색 실행

```bash
# KIPRIS API 키 로드
set -a
eval "$(cat 'C:/Users/JHKIM/Claude_Work/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
set +a

# 키워드 검색 (초록 포함, 상위 15건 상세 조회)
python3 "{SKILL_ROOT}/scripts/search_patents_kipris.py" \
  --keyword "$KIPRIS_KEYWORD" \
  --max-results 50 \
  --with-abstract \
  --max-detail 15 \
  --format json \
  -o "$OUTPUT_DIR/kipris_raw_results.json"
```

검색 결과가 적은 경우 (< 10건):
- 키워드를 축소하여 재검색 (AND 항목 줄이기)
- IPC 코드만으로 광범위 검색 시도

검색 결과가 너무 많은 경우 (> 200건):
- IPC 코드 추가로 범위 축소
- AND 키워드 추가

### Step 3: TF-IDF 유사도 분석

검색 결과에서 발명 아이디어와의 유사도를 계산:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 발명 아이디어 텍스트 vs 각 특허의 title + abstract
# 한국어 기준으로 유사도 계산
# 유사도 상위 10건 선정
```

> [!note] sklearn이 설치되지 않은 경우, 단순 키워드 매칭으로 대체한다:
> 발명 키워드와 각 특허 제목/초록의 단어 겹침 비율로 유사도를 근사 계산.

### Step 4: 선행특허 분석

상위 10건 각각에 대해:
- 출원번호, 출원일, 등록일
- 발명 명칭
- 초록 요약 (2-3문장)
- 핵심 청구항 요약 (초록 기반 추론)
- 본 발명과의 유사점/차이점
- 회피설계 가능성 (상/중/하)
- KIPRIS 상세 페이지 링크

### Graceful Degradation

KIPRIS API 실패 시:
1. 환경변수 `KIPRIS_API_KEY` / `KIPRIS_REST_ACCESS_KEY` 확인
2. API 키 누락 또는 만료 시 → 사용자에게 안내:
   - "KIPRIS API 접속 실패. 선행특허 섹션은 수동으로 보완해 주세요."
   - §3, §4, §8에 `[선행특허 수동 보완 필요]` 플레이스홀더 삽입
3. manifest에 `"phase5": {"status": "degraded", "reason": "KIPRIS API failure"}` 기록

## 출력

`prior_art.json` 파일로 저장:

```json
{
  "search_source": "KIPRIS",
  "search_keyword": "사용된 KIPRIS 검색식",
  "search_ipc": "사용된 IPC 코드 (있을 경우)",
  "total_found": 150,
  "analyzed_count": 10,
  "patents": [
    {
      "application_number": "10-2023-0045678",
      "title": "발명의 명칭",
      "applicant": "출원인",
      "filing_date": "2023-04-15",
      "register_number": "10-2567890-0000",
      "register_date": "2024-01-20",
      "ipc": "H01L 33/00",
      "abstract_summary": "초록 요약 2-3문장",
      "key_claims": "핵심 청구항 요약 (초록 기반 추론)",
      "similarity_score": 0.85,
      "similarity_points": "유사점 설명",
      "difference_points": "차이점 설명",
      "avoidance_feasibility": "상/중/하",
      "kipris_link": "http://kpat.kipris.or.kr/kpat/biblioa.do?method=biblioFrame&applno=1020230045678"
    }
  ],
  "analysis_summary": "선행특허 전체 분석 요약"
}
```

`{발명명칭}_선행특허분석.md` 파일도 별도 생성 (Obsidian 호환).

## 주의사항

- KIPRIS 검색식의 AND/OR/NOT 연산자: `*`, `+`, `!` (EPO CQL과 다름)
- 한국어 키워드 기반 검색이므로 영문 키워드도 함께 시도할 것
- 상세 API (초록 조회)는 건당 1회 호출이므로 max-detail을 적절히 설정
- KIPRIS 무료 등급은 월 1,000건 제한 — 불필요한 반복 호출 자제
