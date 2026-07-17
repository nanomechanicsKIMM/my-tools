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
- **API 키 위치**: `~/Claude_Work/.env`

> `{SHARED_SKILL_ROOT}` = `~/.claude/skills/patent-incubation-auto`

## 작업

### Step 0: 자기공지·비특허문헌(NPL) 선행조사 + 공지예외 (P0 최우선)

> [!important] 연구기관 최다 무효사유 차단
> KIMM은 연구기관이다. 발명자 본인 또는 KIMM 소속 저자의 논문·학회 발표·보도자료가
> 특허 출원일보다 먼저 공개되면 **자기 공지(self-disclosure)로 신규성이 상실**된다 —
> 연구기관 특허 무효의 최다 원인. KIPRIS(특허문헌) 조사만으로는 이 위험을 잡지 못하므로
> 반드시 이 단계를 선행한다.

1. **발명자 저자검색**: `invention_manifest.json`의 `input.inventor`(발명자명)와
   `source_files`에 포함된 발명자 자신의 논문 저자를 대상으로, CrossRef / OpenAlex
   저자 검색을 수행한다. 검색식은 **발명 주제 키워드 AND 저자명**으로 구성한다.
   - CrossRef: `https://api.crossref.org/works?query.author={저자명}&query.bibliographic={주제키워드}`
   - OpenAlex: `https://api.openalex.org/works?search={주제키워드}` + 저자명 필터
   - Phase 6c의 기존 CrossRef 인프라를 재사용한다(WebFetch 가능).
2. **참조문헌 입력 자동 검사**: `source_files`로 입력된 문헌 중 발명자 자신이 저자인
   논문은 **자동으로 자기공지 후보**로 간주하고 공개일을 확인한다.
3. **공지예외(신규성 의제) 기한 산정**: 자기공지 발견 시 공개일을 기록하고,
   **출원 예정일 기준 공개일로부터 12개월 이내**의 공지예외 주장 기한을 산정한다.
   출원 예정일이 없으면 오늘 날짜 기준 잔여 기한을 계산한다.
4. `prior_art.json`에 `self_disclosure` 배열을 채운다(발견 없으면 빈 배열 `[]`).
   자기공지 발견 시 `grace_period_warning`에 경고 문자열을 채우고, 없으면 `null`.
5. **NPL 일반 조사**: 발명 주제의 핵심 비특허문헌(경쟁 연구그룹 논문)도 함께 조회하여
   진보성 판단 공백을 줄인다.

### Step 0-B: 자기선행 특허 조사 — KIPRIS 국내 중심 (P0 필수, 2026-07-06 신설)

> [!warning] 근거 (실측 사고)
> 발명자 본인·소속기관의 등록/공개 특허는 공개 12개월 경과 시 **제29조 정식 선행기술**이
> 되며, 청구항뿐 아니라 **배경기술·명세서 개시**가 신규 발명의 독립항을 무효화할 수 있다.
> Step 0(자기공지 논문)과 별개로 **특허** 자기선행을 반드시 조사한다.

1. **발명자·출원인 목록 확보**: manifest `input.inventors[]`(공동발명자)·`input.affiliation`
   (소속기관)을 읽는다. 없으면 `inventor`(사용자 1인) 위주로 조사한다.
2. **KIPRIS 국내 검색 (중심)**: 각 발명자명(주발명자 우선)·소속기관명과 핵심 기술 키워드를
   조합해 검색하고, 출원인·발명자가 실제 본인·소속과 일치하는 건만 남긴다(동명이인 배제).
3. **개시 범위 파싱**: 자기선행 후보의 청구범위 **및 배경기술·명세서 개시 요소**를 파싱한다
   (청구항이 타 카테고리여도 배경기술 개시는 신규성 인용 근거).
4. **공지예외 기한 산정**: 공개일 + 12개월(제30조). 경과 건은 "정식 선행기술(회피 필수)".
5. **prior_art.json 기록**: `self_prior_art[]{number, title, relation(본인|공동발명자|소속기관),
   pub_date, grace_deadline, disclosed_elements[], differentiation_requirement}`.
   미발견 시 빈 배열 + §2에 실질 조사 근거(조사일) 기재.
6. **후속 전달**: disclosed_elements는 Phase 6 독립항 설계의 금지 영역 + Gate 5 표시 대상 +
   Phase 6d critic의 신규성 공격 재료.

### Step 1: KIPRIS 검색 키워드 구성

사용자 입력 + 상위 IFR 키워드를 조합하여 KIPRIS 검색식 구성.
- AND: `*`, OR: `+`, NOT: `!`
- 핵심 키워드 3-5개 AND 조합

### Step 2: KIPRIS 검색 실행

```bash
set -a
eval "$(cat "$HOME/Claude_Work/.env" | sed 's/^[[:space:]]*//' | grep -v '^#')"
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

각 특허에 **risk_type**을 추가한다 — 해당 risk_level이 어느 관점의 위험인지 명시:
`"FTO"`(침해 회피) / `"patentability"`(특허성 부정 선행기술) / `"both"`.
FTO와 특허성은 판단 기준이 다르므로 혼재시키지 않는다.

### Step 4b: 구성요소 대비표(claim chart) 산출

위험도 '중간(medium)' 이상 선행특허마다 **엘리먼트 단위 매핑**을 산출한다.
산문 유사/차이 서술은 유지하되(대체 아님), 그 위에 구성요소 단위 표를 **추가**한다.

- 본 발명의 §8 독립항 구성요소를 행으로, 각 선행특허의 개시 여부를 열로 매핑
- 개시 표기: `"○"`(개시) / `"△"`(유사·부분 개시) / `"×"`(미개시)
- 표 마지막에 **결합 신규성**(구성요소 결합이 선행특허에 개시되지 않았는지)을 서술
- `prior_art.json`의 `claim_chart[]` 필드에 기록

### Step 4c: Google Patents 해외 패밀리 조회

위험도 高(high) 국내 특허에 대해 **해외 패밀리**를 확인한다. 국내 등록특허의 해외
패밀리가 더 넓은 청구항을 가질 수 있어 FTO 위험이 국내에 한정되지 않는다.

- Google Patents(`https://patents.google.com/patent/{공개번호}`)를 WebFetch로 조회하여
  동일 패밀리의 해외 공개번호·관할(US/EP/CN/WO 등)을 확인하고 `patents[].jurisdiction`에 기록.
- 임베딩 의미검색·INPADOC API·CPC 확장검색은 도입하지 않는다(스킬 범위 초과).

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
      "jurisdiction": "KR",
      "abstract_summary": "초록 요약",
      "representative_claim": "대표청구항 원문",
      "similarity_score": 0.85,
      "similarity_points": "유사점",
      "difference_points": "차이점",
      "avoidance_feasibility": "상/중/하",
      "risk_level": "high/medium/low",
      "risk_type": "FTO/patentability/both",
      "kipris_link": "URL"
    }
  ],
  "self_disclosure": [
    {
      "source": "CrossRef/OpenAlex/source_files",
      "title": "발명자 논문·발표 제목",
      "pub_date": "2025-11-02",
      "grace_period_deadline": "2026-11-02",
      "risk": "출원 전 자기공개 — 신규성 상실 위험, 공지예외 주장 필요"
    }
  ],
  "grace_period_warning": "자기공지 발견 시 경고 문자열, 없으면 null",
  "claim_chart": [
    {
      "patent_no": "10-2023-0045678",
      "elements": [
        {"element": "본 발명 구성요소 1", "disclosed_in_patent": "○", "note": ""},
        {"element": "본 발명 구성요소 2", "disclosed_in_patent": "△", "note": "소재 상이"},
        {"element": "본 발명 구성요소 3", "disclosed_in_patent": "×", "note": "미개시"}
      ],
      "combination_novelty": "구성요소 1+2+3 결합은 선행특허에 개시되지 않음 = 신규성 핵심"
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
  "rejection_combinations": [
    {
      "target_independent_claim": "독립항 2",
      "main_reference": "10-XXXX-XXXXXXX",
      "secondary_references": ["문헌B", "문헌C"],
      "combination_motivation": "없음|약함|있음",
      "defense": "teaching away / 결합 곤란 / 상승효과 요지",
      "amendment_fallback": "거절 시 끌어올 한정 요소"
    }
  ],
  "analysis_summary": "선행특허 전체 분석 요약"
}
```

> [!important] rejection_combinations 필수 (2026-07 신설)
> 각 독립항마다 최소 1개의 **가상 조합 거절 시나리오**(주인용 + 부인용 1~2건)와 방어
> 논거를 반드시 채운다. 단일 문헌 유사도 점수만으로 "위험 없음" 결론을 내리지 않는다.
> 심사관은 조합으로 진보성을 공격하므로, 조합 거절을 선제적으로 시뮬레이션한다.

`{발명명칭}_선행특허분석.md` 파일도 별도 생성 (Obsidian 호환).

## 주의사항

- KIPRIS 무료 등급 월 1,000건 제한
- 한국어/영문 키워드 병행
- Background Prefetch 결과(kipris_prefetch.json, kipris_refined.json)가 있으면 활용하여 중복 검색 회피

## 국제 선행 검색 (S5) — 필수 (2026-07-06 격상)

**모든 발명에 대해** KIPRIS 국내 검색에 더해 다국가(KR/US/JP/EP/WO) 국제 검색을 수행한다.
종전 "PCT 의도 시"의 조건부에서 필수로 격상 — 실전 비교 테스트(2026-07-06, 구면 근안
디스플레이 건)에서 KIPRIS 단독 조사가 독립항 신규성 앵커를 직접 개시하는 결정적 선행
(JP2015169920A 안구 회전중심 수렴 망막투사, US20220166966A1·US20220311993A1 중산대
Maxwellian)을 전부 놓쳐 신규성 평가가 낙관 편향됨이 확인됨. 국내 한정 조사로 novel 판정
금지.

- **독립항 신규성 앵커 개념의 영문 검색 필수**: 상위 IFR 핵심 개념을 영문 키워드로
  변환하여 Google Patents WebFetch 3~5쿼리 검색. 봇 차단 시 Espacenet 폴백.
- **Google Patents / Espacenet / USPTO**: 주요 경쟁사(삼성·BOE·AUO·Fuzhou 등) 및 핵심 학술 저자의 특허 패밀리 조회.
- **핵심 학술 문헌의 특허 패밀리**: 기능적 최근접 논문의 저자·소속이 출원한 특허(중국/PCT/US)를 반드시 확인 (예: Nature 급 논문은 대응 특허가 있을 가능성 높음).
- **검출 문헌의 방식 규정은 원문 직접 확인**: 타 도구·2차 자료 요약을 신뢰하지 말고 Google Patents 원문(WebFetch)으로 투사형/직시형·자발광/변조 여부를 직접 확인한다(오규정은 차별성 논거를 무너뜨림).
- 국제 검색 결과는 prior_art.json `patents[]`에 `jurisdiction` 필드로 구분 기록하고, 미수행 시 `analysis_summary`에 "국제 검색 미수행 — 국내 한정 결론(신규성 판단 신뢰도 제한)"을 명시하고 ifr_coverage의 novel 판정에 `kr_only_caveat: true`를 부기한다(무언의 전수 검색으로 오인 금지).
