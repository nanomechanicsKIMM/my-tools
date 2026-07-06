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
   - OpenAlex: `https://api.openalex.org/works?search={주제키워드}&filter=author.id:...` 또는 저자명 필터
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
> 실측: 구면 근안 디스플레이 건에서 발명자 자신의 KR 10-2906241 배경기술(수직 발광·구면
> 결상·micro-LED 개시)을 사전에 파싱하지 않으면 독립항이 자기선행 개시 범위에 근접하는
> 신규성 결함이 발생함. Step 0(자기공지 논문)과 별개로 **특허** 자기선행을 반드시 조사한다.

1. **발명자·출원인 목록 확보**: `invention_manifest.json`의 `input.inventors[]`(공동발명자
   포함)와 `input.affiliation`(소속기관)을 읽는다. `inventors[]`가 없으면
   `inventor`(사용자 1인) 위주로, `affiliation`이 없으면 발명자명만으로 조사한다.
   (KIMM 발명이면 affiliation 기본값 "한국기계연구원"을 사용자에게 확인 후 적용 가능.)
2. **KIPRIS 국내 검색 (중심)**: 각 발명자명(우선순위: 주발명자 → 공동발명자)과 핵심
   기술 키워드를 조합해 검색한다:
   ```bash
   python "{SKILL_ROOT}/scripts/search_patents_kipris.py" --keyword "<주발명자명>*<핵심기술어>" --max-results 30 --with-detail --max-detail 10
   python "{SKILL_ROOT}/scripts/search_patents_kipris.py" --keyword "<소속기관명>*<핵심기술어>" --max-results 30   # affiliation 있을 때
   ```
   결과에서 출원인·발명자가 실제 본인·소속과 일치하는 건만 남긴다(동명이인 배제 —
   기술분야 불일치 건 제거).
3. **개시 범위 파싱 (청구항만 보지 말 것)**: 자기선행 후보 각각의 청구범위 **및
   배경기술·명세서 본문의 개시 요소**를 파싱한다. 청구항이 다른 카테고리(예: 제조방법)
   여도 배경기술 개시(구조·동작·용도)는 신규성 인용 근거가 된다. 필요 시
   download_patent_pdf.py로 공보 전문을 확보해 확인한다.
4. **공지예외 기한 산정**: 각 건의 공개일 기준 12개월(제30조) 기한을 산정 — 경과 건은
   "정식 선행기술(회피 필수)", 기한 내 건은 "공지예외 주장 가능(기한 명시)"로 분류.
5. **prior_art.json 기록**:
   ```json
   "self_prior_art": [
     {"number": "KR 10-XXXXXXX", "title": "...", "relation": "발명자 본인|공동발명자|소속기관",
      "pub_date": "YYYY-MM-DD", "grace_deadline": "YYYY-MM-DD 또는 '경과 — 제29조 정식 선행기술'",
      "disclosed_elements": ["배경기술·명세서 개시 요소"],
      "differentiation_requirement": "독립항이 이 개시를 넘기 위한 필요 한정"}
   ]
   ```
   미발견 시 `"self_prior_art": []` + §2에 "발명자·소속 KIPRIS 조사 결과 자기선행
   미발견(조사일)"로 실질 조사 근거를 남긴다.
6. **후속 전달**: `disclosed_elements`는 Phase 6 §8 독립항 설계의 **금지 영역**(그 요소들만으로
   구성된 독립항 금지)으로, Step 6d critic의 신규성 공격 재료로 전달된다.

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

# 키워드 검색 (초록 + 대표청구항 포함, 상위 15건 상세 조회)
python "{SKILL_ROOT}/scripts/search_patents_kipris.py" \
  --keyword "$KIPRIS_KEYWORD" \
  --max-results 50 \
  --with-detail \
  --max-detail 15 \
  -o "$OUTPUT_DIR/kipris_raw_results.csv"
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
- **risk_type**: 해당 위험도(risk_level)가 어느 관점의 위험인지 명시한다 —
  `"FTO"`(침해 회피: 이 특허가 살아있으면 실시 시 침해 가능) 또는
  `"patentability"`(특허성: 이 특허가 본 발명의 신규성·진보성을 부정하는 선행기술)
  또는 `"both"`. FTO와 특허성은 판단 기준이 다르므로 혼재시키지 않는다.
- KIPRIS 상세 페이지 링크

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
  동일 패밀리의 해외 공개번호·관할(US/EP/CN/WO 등)을 확인한다.
- 확인된 패밀리는 `patents[].jurisdiction` 필드에 기록한다.
- 임베딩 의미검색·INPADOC API·CPC 확장검색은 도입하지 않는다(스킬 범위 초과).

### Step 5: IFR별 커버리지 분석

각 IFR에 대해 선행특허 개시 여부를 분석하여 `ifr_coverage[]`에 기록한다:
- `"novel"`: 선행특허 미개시 → 독립항 후보
- `"partial"`: 부분 개시 → 차별화 요소 명시, 종속항/회피설계
- `"disclosed"`: 완전 개시 → 삭제 권고

각 IFR에 `related_patents`, `differentiation`, `recommendation`을 함께 채운다.

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
      "jurisdiction": "KR",
      "abstract_summary": "초록 요약 2-3문장",
      "representative_claim": "대표청구항 (청구항 1) 원문",
      "key_claims": "핵심 청구항 요약",
      "similarity_score": 0.85,
      "similarity_points": "유사점 설명",
      "difference_points": "차이점 설명",
      "avoidance_feasibility": "상/중/하",
      "risk_level": "high/medium/low",
      "risk_type": "FTO/patentability/both",
      "kipris_link": "http://kpat.kipris.or.kr/kpat/biblioa.do?method=biblioFrame&applno=1020230045678"
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

> [!important] rejection_combinations 필수
> 각 독립항마다 최소 1개의 **가상 조합 거절 시나리오**(주인용 + 부인용 1~2건)와 방어
> 논거(teaching away / 결합 곤란 / 상승효과) 및 amendment_fallback을 반드시 채운다.
> 단일 문헌 유사도 점수만으로 "위험 없음" 결론을 내리지 않는다 — 심사관은 조합으로
> 진보성을 공격하므로 조합 거절을 선제 시뮬레이션한다.

`{발명명칭}_선행특허분석.md` 파일도 별도 생성 (Obsidian 호환).

## 국제 선행 검색 (S5) — 필수 (2026-07-06 격상)

**모든 발명에 대해 KIPRIS 국내 검색에 더해 다국가(KR/US/JP/EP/WO) 국제 검색을 필수로
수행한다.** 종전에는 "PCT 의도 또는 high 국내 특허 존재 시"에만 조건부였으나, 실전 비교
테스트(2026-07-06, 구면 근안 디스플레이 건)에서 KIPRIS 단독 조사가 결정적 근접 선행을
전부 놓쳤음이 확인되어 필수로 격상한다:

> [!warning] 격상 근거 (실측 사고 사례)
> KIPRIS 단독 조사는 JP2015169920A(Yamamoto Kogaku/오사카 — **수렴점을 안구 회전중심에
> 배치**해 안구 회전을 허용하는 망막투사, 독립항 신규성 앵커 개념을 직접 개시),
> US20220166966A1·US20220311993A1(중산대 — VAC-free Maxwellian 화소블록-조리개)을 모두
> 놓쳐 IFR 신규성 평가가 낙관 편향됨. EPO 다국가 검색을 쓴 경쟁 파이프라인(patent-pack)은
> 이들을 검출함. 국내 한정 조사는 신규성 결론의 근거가 될 수 없다.

수행 규칙:

1. **독립항 신규성 앵커 개념의 영문 검색 필수**: 상위 IFR(독립항 후보)의 핵심 개념을
   영문 키워드로 변환(예: "eye rotation center convergence near-eye display",
   "Maxwellian view retinal projection", "directional emission curved display")하여
   **Google Patents를 WebFetch로 3~5개 쿼리** 검색한다. 봇 차단 시 Espacenet 폴백.
2. **주요 관할 커버**: KR/US/JP/EP/WO 최소 5개 관할의 공개문헌을 커버한다. 검색 결과는
   `patents[]`에 `jurisdiction` 필드로 구분 기록한다.
3. **핵심 학술 문헌의 특허 패밀리**: 기능적 최근접 논문의 저자·소속이 출원한 특허
   (중국/PCT/US)를 확인한다.
4. **검출 문헌의 원문 성격 규정은 직접 확인**: 타 도구·2차 자료의 요약을 신뢰하지 말고
   Google Patents 원문(WebFetch)으로 방식(투사형/직시형, 자발광/변조 등)을 직접 확인한다.
   (실측: patent-pack이 JP2015169920A를 '스캐너 투사형'으로 오규정 — 실제는 자발광
   디스플레이+HOE. 성격 오규정은 차별성 논거를 무너뜨린다.)
5. **degraded 처리**: 국제 검색이 불가능한 환경(네트워크 차단 등)이면 `analysis_summary`에
   **"국제 검색 미수행 — 국내 한정 결론(신규성 판단 신뢰도 제한)"**을 반드시 명시한다
   (무언의 전수 검색으로 오인 금지). 이 경우 ifr_coverage의 novel 판정에
   `"kr_only_caveat": true`를 부기한다.

## 주의사항

- KIPRIS 검색식의 AND/OR/NOT 연산자: `*`, `+`, `!` (EPO CQL과 다름)
- 한국어 키워드 기반 검색이므로 영문 키워드도 함께 시도할 것
- 상세 API (초록 조회)는 건당 1회 호출이므로 max-detail을 적절히 설정
- KIPRIS 무료 등급은 월 1,000건 제한 — 불필요한 반복 호출 자제
