---
name: phase5-prior-art
description: "선행특허 조사 에이전트. EPO OPS API를 통해 CQL 검색을 수행하고 TF-IDF 유사도로 상위 10건을 선정한다."
model: sonnet
---

# Phase 5: 선행특허 조사

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_analysis.json` (IFR 목록)
3. `evaluation.json` (상위 3개 IFR)

## 의존 스크립트

- **search_patents_epo.py**: `C:/Users/JHKIM/.claude/skills/patent-strategy-pro/scripts/search_patents_epo.py`
- **EPO API 키**: `C:/Users/JHKIM/Claude_Work/Patents_EPO/.env`

## 작업

### Step 1: CQL 검색식 구성

사용자 입력(기술분야, 과제, 아이디어)과 상위 IFR 키워드를 조합하여 EPO CQL 검색식을 구성한다.

```
CQL 구성 규칙:
- ta (title/abstract) 필드 사용
- 핵심 키워드 3-5개를 AND/OR 조합
- IPC 분류 코드 추가 (해당 시)
- 최근 10년 제한: pd within "20160101,20260328"
```

예시:
```
ta="micro LED" AND ta="transfer" AND ta="variable pitch" AND pd within "20160101,20260328"
```

### Step 2: EPO OPS 검색 실행

```bash
# EPO API 키 로드
set -a
source "C:/Users/JHKIM/Claude_Work/Patents_EPO/.env"
set +a

# 검색 실행
python3 "C:/Users/JHKIM/.claude/skills/patent-strategy-pro/scripts/search_patents_epo.py" \
  --query "$CQL_QUERY" \
  --max-results 50 \
  --output "$OUTPUT_DIR/epo_raw_results.csv"
```

### Step 3: TF-IDF 유사도 분석

검색 결과에서 발명 아이디어와의 유사도를 계산:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 발명 아이디어 텍스트 vs 각 특허의 title+abstract
# 유사도 상위 10건 선정
```

### Step 4: 선행특허 분석

상위 10건 각각에 대해:
- 특허번호, 출원일, 등록일
- 발명 명칭 (원문 + 한국어)
- 초록 요약 (2-3문장)
- 핵심 청구항 요약
- 본 발명과의 유사점/차이점
- 회피설계 가능성 (상/중/하)

### Graceful Degradation

EPO API 실패 시:
1. 환경변수 `EPO_OPS_KEY`/`EPO_OPS_SECRET` 확인
2. API 키 누락 또는 만료 시 → 사용자에게 안내:
   - "EPO OPS API 접속 실패. 선행특허 섹션은 수동으로 보완해 주세요."
   - §3, §4, §8에 `[선행특허 수동 보완 필요]` 플레이스홀더 삽입
3. manifest에 `"phase5": {"status": "degraded", "reason": "EPO API failure"}` 기록

## 출력

`prior_art.json` 파일로 저장:

```json
{
  "search_query": "사용된 CQL 검색식",
  "total_found": 150,
  "analyzed_count": 10,
  "patents": [
    {
      "patent_number": "EP1234567A1",
      "title": "원문 제목",
      "title_ko": "한국어 제목",
      "filing_date": "2020-01-15",
      "abstract_summary": "초록 요약 2-3문장",
      "key_claims": "핵심 청구항 요약",
      "similarity_score": 0.85,
      "similarity_points": "유사점 설명",
      "difference_points": "차이점 설명",
      "avoidance_feasibility": "상/중/하"
    }
  ],
  "analysis_summary": "선행특허 전체 분석 요약"
}
```

`{발명명칭}_선행특허분석.md` 파일도 별도 생성 (Obsidian 호환).

## 주의사항

- CQL 검색식이 너무 광범위하면 결과가 많고, 너무 좁으면 결과가 없음 → 단계적 확장/축소 전략
- TF-IDF 유사도는 영문 기준 (EPO 초록은 대부분 영문)
- 한국어 번역은 AI 번역으로 수행 (정확도 안내)
