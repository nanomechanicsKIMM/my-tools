---
name: phase5-prior-art
description: "선행특허 조사 에이전트. patent-incubation용 fork: IFR별 커버리지(ifr_coverage) 및 회피설계 전략(design_around_strategy) 출력 추가."
model: sonnet
---

# Phase 5: 선행특허 조사

## 입력

1. `invention_manifest.json`의 `input` 필드
2. `triz_analysis.json` (IFR 목록)
3. `evaluation.json` (상위 3개 IFR)

## 의존 스크립트

- **search_patents_kipris.py**: `{SHARED_SKILL_ROOT}/scripts/search_patents_kipris.py`
- **KIPRIS API 키**: 환경변수 `KIPRIS_API_KEY` 또는 `KIPRIS_REST_ACCESS_KEY`
- **API 키 위치**: `C:/Users/JHKIM/Claude_Work/.env`

> `{SHARED_SKILL_ROOT}` = `C:/Users/JHKIM/.claude/skills/patent-invention-disclosure`

## 작업

### Step 1: KIPRIS 검색 키워드 구성

사용자 입력 + 상위 IFR 키워드를 조합하여 KIPRIS 검색식 구성.
- AND: `*`, OR: `+`, NOT: `!`
- 핵심 키워드 3-5개 AND 조합

### Step 2: KIPRIS 검색 실행

```bash
set -a
eval "$(cat 'C:/Users/JHKIM/Claude_Work/.env' | sed 's/^[[:space:]]*//' | grep -v '^#')"
set +a

python "{SHARED_SKILL_ROOT}/scripts/search_patents_kipris.py" \
  --keyword "$KIPRIS_KEYWORD" \
  --max-results 50 \
  --with-detail \
  --max-detail 15 \
  -o "$OUTPUT_DIR/kipris_raw_results.csv"
```

결과 < 10건: 키워드 축소 재검색. 결과 > 200건: IPC 코드 추가.

### Step 3: TF-IDF 유사도 분석

발명 아이디어와의 유사도 계산, 상위 10건 선정.
sklearn 미설치 시 키워드 매칭으로 대체.

### Step 4: 선행특허 분석

상위 10건: 출원번호, 명칭, 초록 요약, 핵심 청구항, 유사점/차이점, 회피설계 가능성(상/중/하).

### Step 5: IFR별 커버리지 분석 (patent-incubation 추가)

각 IFR에 대해 선행특허 개시 여부를 분석:
- `"novel"`: 선행특허 미개시 → 독립항 후보
- `"partial"`: 부분 개시 → 차별화 요소 명시, 종속항/회피설계
- `"disclosed"`: 완전 개시 → 삭제 권고

### Graceful Degradation

KIPRIS API 실패 시:
1. 환경변수 확인
2. 사용자 안내: "선행특허 자동 검색 실패. §3/§4/§8 수동 보완 필요."
3. manifest에 `"phase5": {"status": "degraded"}` 기록

## 출력

`prior_art.json` 파일로 저장:

```json
{
  "search_source": "KIPRIS",
  "search_keyword": "사용된 검색식",
  "search_ipc": "IPC 코드",
  "total_found": 150,
  "analyzed_count": 10,
  "patents": [
    {
      "application_number": "10-2023-0045678",
      "title": "발명의 명칭",
      "applicant": "출원인",
      "filing_date": "2023-04-15",
      "register_number": "10-2567890-0000",
      "ipc": "H01L 33/00",
      "abstract_summary": "초록 요약",
      "representative_claim": "대표청구항 원문",
      "similarity_score": 0.85,
      "similarity_points": "유사점",
      "difference_points": "차이점",
      "avoidance_feasibility": "상/중/하",
      "risk_level": "high/medium/low",
      "kipris_link": "URL"
    }
  ],
  "ifr_coverage": [
    {
      "ifr_id": 1,
      "disclosed": "novel",
      "related_patents": [],
      "differentiation": "선행특허에서 이 구성은 전혀 개시되지 않음",
      "recommendation": "독립항 후보"
    },
    {
      "ifr_id": 2,
      "disclosed": "partial",
      "related_patents": ["10-2023-0045678"],
      "differentiation": "구조는 유사하나 핵심 소재 적용은 미개시",
      "recommendation": "종속항 또는 회피설계"
    }
  ],
  "design_around_strategy": {
    "high_risk_patents": ["위험 특허 목록"],
    "avoidance_approaches": [
      {
        "patent": "10-2023-0045678",
        "risk": "medium",
        "approach": "대체 소재로 변경하면 회피 가능",
        "affected_ifrs": [2, 5]
      }
    ],
    "summary": "전체 회피설계 전략 요약"
  },
  "analysis_summary": "선행특허 전체 분석 요약"
}
```

`{발명명칭}_선행특허분석.md` 파일도 별도 생성 (Obsidian 호환).

## 주의사항

- KIPRIS 무료 등급 월 1,000건 제한
- 한국어/영문 키워드 병행
- Background Prefetch 결과(kipris_prefetch.json, kipris_refined.json)가 있으면 활용하여 중복 검색 회피
