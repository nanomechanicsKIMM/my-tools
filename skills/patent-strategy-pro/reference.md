# Patent Strategy Pro – Reference

## Google Patents 검색식 문법

- **불린 연산자**: `AND`, `OR`, `NOT` (대문자). 괄호로 그룹: `(A OR B) AND C NOT D`.
- **구문 검색**: 이중 따옴표. `"light emitting"`, `"flexible substrate"`.
- **와일드카드**: 접미사만. `stretch*` → stretchable, stretching, stretched.
- **날짜 필터** (URL 파라미터):
  - `after=priority:YYYYMMDD` – 우선일 이후
  - `before=priority:YYYYMMDD` – 우선일 이전
  - 예: `https://patents.google.com/?q=QUERY&after=priority:20160101&before=priority:20251231`
- **기본 검색 기간**: 10년 (`--years 10`). 사용자 지정 우선.

### Google Patents 구문 규칙 (실증 확인)

- 괄호 그룹은 최대 **2개**까지만 지원 (3개 이상 → syntax error)
- 괄호와 괄호 사이에 반드시 **AND** 또는 **OR** 연결 필요 (암묵적 AND 미지원)
- 제외 키워드는 `-` 대신 **AND NOT** 사용 (예: `-OLED` → `AND NOT OLED`)
- 따옴표 내 하이픈(`-`) 사용 금지 (예: `"roll-to-roll"` → syntax error → `"roll to roll"`)

### 검색식 구성 전략

- **구조**: `(핵심 용어 동의어 OR 그룹) AND (기술 키워드 OR 그룹) AND NOT 제외1 AND NOT 제외2`
  - 괄호 2개 제한이므로 핵심 용어 1그룹 + 키워드 1그룹 + AND NOT (괄호 없이)
- **MAIN 검색식**: ~5,000건 목표. 핵심 용어 동의어 5~7개 + 넓은 키워드 10~13개
- **SUB 검색식**: ~1,000건 목표. 동일 핵심 용어 동의어 + 세부 기술 고유 키워드 8~12개
- **키워드 넓이 조절**: 단일어(`"sensor"`)는 매우 넓고, 2어구(`"strain sensor"`)는 좁음. 건수에 따라 조절

### Playwright 기반 자동 건수 조정 (Google Patents 모드)

검색식 생성 후 Playwright MCP로 Google Patents에 접속하여 결과 건수를 자동 확인하고,
목표 범위(MAIN ~5,000 / SUB ~1,000)에 맞을 때까지 반복 조정한다.

**건수 추출 방법**:
```javascript
// navigate 후 5초 대기, 그 후 evaluate로 결과 건수 파싱
() => {
  const all = document.body.innerText;
  const match = all.match(/([\d,]+)\s+results/i);
  return match ? match[1] : 'NOT FOUND';
}
```

**조정 전략**:

| 상황 | 조치 |
|------|------|
| 건수 >> 목표 (2배 이상) | 핵심 용어 동의어 제거, 단일어 키워드를 2어구로 구체화 |
| 건수 > 목표 (1.2~2배) | 가장 넓은 키워드 1~2개 제거 또는 구체화 |
| 건수 < 목표 (0.5~0.8배) | 관련 동의어/키워드 1~2개 추가 |
| 건수 << 목표 (0.5배 미만) | 2 AND 그룹 → 1 통합 OR 그룹, 핵심 용어 동의어 추가, 키워드 단일어화 |

**반복 제한**: 최대 5회. 5회 후에도 범위 밖이면 현재 결과로 확정하고 사용자에게 보고.

### EPO OPS 자동 건수 조정 (EPO 모드)

EPO OPS는 `search_patents()` 함수가 total count를 즉시 반환하므로 Playwright 없이 API 응답으로 건수를 확인한다.

**건수 확인 방법**:
```python
# search_patents_epo.py의 search_patents() 함수가 출력:
#   → {total} total results (fetching up to {effective_total})
# 또는 직접 EPO OPS API 호출로 total count만 확인:
python search_patents_epo.py --cql '{cql_query}' --count-only
```

에이전트가 직접 `search_patents_epo.py`를 `--count-only` 모드로 호출하여 건수를 확인하고,
목표 범위에 맞을 때까지 CQL 쿼리의 키워드를 조정한 후 실제 다운로드를 실행한다.

**EPO CQL 조정 전략**:

| 상황 | 조치 |
|------|------|
| 건수 >> 목표 | AND 그룹 추가, 키워드를 ti= (제목 한정)으로 축소 |
| 건수 > 목표 (1.2~2배) | OR 그룹에서 가장 넓은 키워드 1~2개 제거 |
| 건수 < 목표 (0.5~0.8배) | OR 그룹에 동의어 추가, ta= (제목+초록)으로 확장 |
| 건수 << 목표 (0.5배 미만) | AND 그룹 제거, ta= 검색으로 전환, 키워드 단일어화 |
| EPO 413 에러 | OR 그룹 분할, 개별 키워드 검색 후 합산 (search_sub_techs 방식) |

**EPO 특수 제약**:
- 최대 2,000건/쿼리 (초과 시 `--split-by-year` 자동 적용)
- MAIN 목표: ~2,000건 (EPO 한도), SUB: ~500건
- 413 에러 시 OR 그룹 크기 축소 또는 개별 키워드 검색으로 전환

**반복 제한**: Google Patents 모드와 동일하게 최대 5회.

---

## 세부 기술 도출 방법론

### 1. RFP 분석 대상 섹션

`extract_sub_technologies.py`가 다음 섹션에서 세부 기술을 추출한다:

| 섹션 | 파싱 대상 | 우선순위 |
|------|-----------|----------|
| 과제목표 / 연구목표 | 목표 문장, 기술 동사+명사 패턴 | 최고 |
| 연구개발내용 / 개발내용 | 하위 항목, 번호 목록 | 높음 |
| 성과지표 / 핵심성과지표 | 정량 목표와 연결된 기술명 | 높음 |
| 기술분류 / 키워드 | 영문 키워드 | 중간 |
| 추진배경 / 기술동향 | 배경 기술명 | 낮음 |

### 2. 세부 기술 JSON 구조

```json
{
  "rfp_title": "RFP 사업명",
  "sub_technologies": [
    {
      "id": "sub1",
      "name_ko": "세부 기술 한글명",
      "name_en": "Sub-technology English name",
      "description": "세부 기술 설명 2~3문장",
      "key_terms": ["term1", "term2", "term3"],
      "exclude_terms": ["excluded1", "excluded2"],
      "rfp_objectives": ["RFP 목표 1", "RFP 목표 2"]
    }
  ]
}
```

### 3. 세부 기술 도출 원칙

- **3~5개 유지**: 너무 세분화하면 검색 건수 부족, 너무 광범위하면 노이즈 증가
- **상호 배타성**: 각 세부 기술은 서로 구분되는 핵심 기술어를 가져야 함
- **RFP 추적성**: 각 세부 기술이 RFP의 어느 목표/내용과 대응되는지 명시
- **사용자 확인**: 도출 후 Claude가 사용자에게 제시하고 수정 허용

---

## 연관성 점수 알고리즘

### 제목 연관성 점수 (score_title_relevance.py)

```
score = TF-IDF_cosine(title, RFP)
      + Σ(include_weight for each include_term found in title)
      - Σ(exclude_weight for each exclude_term found in title)
```

- `include_weight` 기본값: 0.2 (포함 단어 1개당 +0.2)
- `exclude_weight` 기본값: 0.5 (제외 단어 1개당 -0.5)
- 세부 기술 검색에서는 `key_terms`를 `--include-terms`로 사용

### 초록+대표청구항 연관성 점수 (score_abstract_relevance.py)

```
base = 0.5 * TF-IDF_cosine(abstract, RFP) + 0.5 * TF-IDF_cosine(claim1, RFP)
score = base + Σ(include_weight) - Σ(exclude_weight)
```

- 청구항(claim)이 없으면 초록만으로 계산 (abstract weight = 1.0)
- `abstract_weight : claim_weight = 5 : 5` (기본)

---

## 공백 기술 분석 (Gap Analysis) 방법론

### 분석 프레임워크

```
공백 = RFP 요구사항 ∩ 기존 특허 미커버 영역
```

### 공백 분석 절차

1. **RFP 요구사항 목록화**: RFP 목표/성과지표에서 기술 요구사항 추출
2. **특허 커버리지 평가**: 핵심 특허 분석으로 각 요구사항 충족 여부 판단
   - ◎ 완전 커버: 복수의 핵심 특허가 직접 청구
   - ○ 부분 커버: 관련 특허 존재하나 완전하지 않음
   - △ 간접 커버: 관련 기술이지만 직접 적용 어려움
   - × 공백: 특허 미발견 또는 극소수
3. **공백 기술 정의**: × 및 △ 항목에서 특허화 기회 도출
4. **선행기술 회피 분석**: ◎/○ 항목에서 설계 변경 포인트 도출

### 공백 분석 보고서 표 형식

| 기술 요구사항 | RFP 항목 | 특허 커버리지 | 주요 선행 특허 | 공백 내용 | 특허화 제안 |
|-------------|---------|------------|------------|---------|----------|
| 요구사항 1 | §목표2 | ○ 부분 커버 | US1234567 등 | 특정 조건 미커버 | 청구 방향 제안 |
| 요구사항 2 | §성과지표3 | × 공백 | - | 전무 | 독립항 기회 |

---

## Objective-Solution Matrix (OS Matrix) 방법론

### 매트릭스 구조

- **행(Row)**: RFP 목표/기술 요구사항 (5~10개)
- **열(Column)**: 핵심 특허별 솔루션 접근법 또는 기술 카테고리
- **셀**: ◎(강한 대응) / ○(대응) / △(약한 대응) / ×(미대응)

### OS Matrix 작성 방법

1. RFP에서 기술 목표 추출 (행): 과제목표·성과지표에서 5~10개
2. 핵심 특허를 솔루션 접근법으로 분류 (열): 재료/구조/공정/알고리즘 등
3. 각 셀에 대응 관계 기입
4. **공백 행** 식별 → 특허화 기회
5. **공백 열** 식별 → 기술 조합 기회

### OS Matrix 보고서 형식

```markdown
| RFP 목표 | 접근법A | 접근법B | 접근법C | 공백 여부 |
|---------|--------|--------|--------|---------|
| 목표1   |   ◎    |   ○    |   ×    | 접근C 공백 |
| 목표2   |   ×    |   ×    |   ○    | 접근A,B 공백 |
| 목표3   |   ×    |   ×    |   ×    | **전체 공백** |
```

---

## IP 창출 전략 방법론

### 전략 프레임워크 (세부 기술별)

각 세부 기술에 대해 다음 4가지 전략을 도출한다:

#### 1. 핵심 독립항 전략

- **대상**: 공백 기술 × 항목, 신규 조합 가능 기술
- **방향**: 청구범위 최대화 (상위 개념으로 청구)
- **예시 형식**: "A 방법/장치/시스템으로서, [핵심 구성요소]를 포함하는 것을 특징으로 하는..."

#### 2. 선점 전략 (Fast-follow)

- **대상**: △ 항목 (간접 커버 영역)
- **방향**: 기존 특허보다 개선된 구성으로 청구
- **회피 설계**: 기존 독립항의 필수 구성요소 제거 또는 대체

#### 3. 포위 전략 (Surrounding)

- **대상**: 경쟁사 핵심 특허 주변
- **방향**: 응용, 파생 기술, 제조 방법, 시스템 구성으로 청구
- **목적**: 라이선스 협상력 확보

#### 4. 방어 전략 (Defensive)

- **대상**: 자사 핵심 기술 보호
- **방향**: 청구항 계층화 (독립항 + 다수 종속항)
- **공개 타이밍**: 특허 출원 vs 영업비밀 선택 기준

### IP 전략 표 형식

| 세부 기술 | 전략 유형 | 청구 방향 | 우선순위 | 담당 기술 범위 | 주의할 선행 특허 |
|---------|---------|---------|---------|------------|------------|
| 세부기술1 | 핵심 독립항 | [청구 방향] | 최우선 | [범위] | [특허번호] |

---

## 외부 도메인 사전 (Domain Dictionary)

### 용도

내장 `_KO_EXPAND` 사전(14개 분야, 190+개 매핑)이 커버하지 못하는 특수 분야의 RFP에 대해, 사용자가 추가 한→영 매핑을 JSON 파일로 제공할 수 있다.

### JSON 형식

```json
{
  "한글키워드1": ["english_term1", "english_term2", "english_term3"],
  "한글키워드2": ["english_term1", "english_term2"]
}
```

### 사용법

```bash
python extract_sub_technologies.py rfp.md -o sub_techs.json --domain-dict my_domain.json
```

외부 사전의 키가 내장 사전과 동일하면 외부 사전이 우선한다 (override).

### 내장 사전 커버 분야

| 분야 | 예시 키워드 |
|------|-----------|
| 디스플레이/TFT | 백플레인, OLED, 화소 |
| 센싱/변형 | 센서, 변형, 감지 |
| 배터리/에너지 | 배터리, 전지, 전해질 |
| 반도체/공정 | 반도체, 식각, 증착 |
| AI/ML | 딥러닝, 신경망, 추론 |
| 통신/네트워크 | 5G, 안테나, 변조 |
| 바이오/의료 | 진단, 바이오, 생체신호 |
| 자동차/EV | 전기차, BMS, 자율주행 |
| 광학/포토닉스 | 레이저, 광통신, 렌즈 |
| 전력전자 | 컨버터, 인버터, 전력 |
| 소재/제조 | 복합재, 코팅, 3D프린팅 |
| 로봇/자동화 | 로봇, 액추에이터, 제어 |
| 환경/에너지변환 | 태양전지, 풍력, 정화 |
| UI/UX | 인터페이스, 상호작용, UX |

---

## 세부 기술 품질 기준

### key_terms 차별화 검증

스크립트가 자동 수행하며, Claude 보정 시에도 준수해야 하는 기준:

| 기준 | 임계값 | 의미 |
|------|--------|------|
| Jaccard 유사도 | ≤ 50% | 임의의 두 세부 기술 key_terms 간 Jaccard > 50% 이면 경고 |
| 최소 key_terms | ≥ 3개 | 3개 미만이면 검색 결과 과다 (노이즈) |
| 상위 2개 동일 | 금지 | 모든 세부 기술이 같은 상위 2개 terms 공유 시 검색 결과 중복 |

### Claude 보정 체크리스트

Step 2-B에서 Claude가 반드시 확인해야 할 항목:

- [ ] 세부 기술이 RFP 연구개발내용의 서로 다른 항목에 대응하는가?
- [ ] 중복된 세부 기술이 합쳐졌는가? (자동 추출 시 제목/내용이 다르지만 실질 동일한 기술 존재)
- [ ] 각 세부 기술의 key_terms가 해당 기술에만 고유한 단어를 포함하는가?
- [ ] exclude_terms가 key_terms와 충돌하지 않는가?
- [ ] RFP의 핵심 성과지표에 대응하는 세부 기술이 빠지지 않았는가?

---

## 출원인 통일 (Assignee Normalization)

### Compact 표시 규칙

보고서·표·ASCII 차트에서 출원인명 compact 처리:

- 삭제 대상 접미사: `LLC`, `Inc.`, `Ltd.`, `Co., Ltd.`, `GmbH`, `Corporation`, `Corp.`, `S.A.`, `B.V.`, `AG`, `K.K.`
- 예: `Apple Inc. → Apple`, `Google LLC → Google`, `Samsung Electronics Co., Ltd. → Samsung Electronics`
- `Semiconductor Energy Laboratory Co., Ltd. → Semiconductor Energy Laboratory`

### 영어 통일명 (주요 회사)

| 원문 변형 | 영어 통일명 |
|---------|----------|
| 삼성전자, Samsung Electronics Co., Ltd., 三星电子 | Samsung Electronics |
| 삼성디스플레이, Samsung Display Co., Ltd. | Samsung Display |
| LG디스플레이, LG Display Co., Ltd. | LG Display |
| 엘지전자, LG Electronics Co., Ltd. | LG Electronics |
| BOE Technology Group Co., Ltd., 京东方 | BOE Technology |
| Semiconductor Energy Laboratory Co., Ltd., SEL | Semiconductor Energy Laboratory |
| Apple Inc., 苹果公司 | Apple |
| Google LLC, Google Inc., Alphabet | Google |
| Microsoft Corporation, Microsoft Technology Licensing | Microsoft |
| 华为技术有限公司, Huawei Technologies | Huawei |

---

## 국가별 집계 (보고서용)

- **유럽 통합**: EP, ES, DE, GB, FR, NL, DK, BE → "유럽"
- **한글 명칭**: 미국(US), 중국(CN), 일본(JP), 한국(KR), 유럽(EP 통합), PCT(WO), 대만(TW), 호주(AU)
- 표·차트는 한글만 표기

---

## 보고서 파일명 규칙

- 패턴: `{YYYYMMDD}_{topic}_특허전략보고서.md`
- 예: `20260315_센서융합디스플레이_특허전략보고서.md`

---

## CSV 컬럼 (Google Patents 일반 내보내기)

| 컬럼명 | 용도 |
|-------|------|
| title | 특허 제목 (제목 연관성 점수에 사용) |
| publication number | 특허 번호 |
| priority date | 우선일 (연도별 통계) |
| publication date | 공개일 |
| assignee | 출원인 |
| result link | 특허 상세 페이지 URL (초록 수집에 사용) |
| abstract | 초록 (fetch_abstracts.py로 추가) |
| representative_claim | 대표청구항 (fetch_abstracts.py로 추가) |

---

## 기술 단계 해석

- **도입기**: 출원이 서서히 증가하거나 일정 수준 유지. 최근 감소 → 공개 지연(18개월) 가능성 먼저 고려
- **성장기**: 연도별 건수 뚜렷한 증가세
- **성숙기**: 피크 이후 감소 + 기술 대체 근거 있을 때만
- **주의**: 우선일 기준 최근 2~3년 감소만으로 "성숙기" 단정 금지

---

## CSV 다운로드 (Google Patents 모드)

### Playwright 자동 탭 오픈

검색식 건수 조정 완료 후, Playwright로 MAIN + SUB1~N 전체 URL을 브라우저 탭으로 동시에 열어
사용자가 각 탭에서 바로 CSV를 다운로드할 수 있도록 한다.

```javascript
// 5개 URL을 한 번에 탭으로 오픈하는 Playwright 코드
async (page) => {
  const urls = [
    { name: 'MAIN', url: '<main_url>' },
    { name: 'SUB1', url: '<sub1_url>' },
    // ...
  ];
  await page.goto(urls[0].url);
  const context = page.context();
  for (let i = 1; i < urls.length; i++) {
    const newPage = await context.newPage();
    await newPage.goto(urls[i].url);
  }
  return `Opened ${urls.length} tabs`;
}
```

### 수동 다운로드 절차

각 탭에서:
1. 검색 결과 상단 **Download** 아이콘 클릭
2. **"Download (CSV)"** 선택
3. 파일명 규칙: `gp-search-{date}_{id}.csv` (예: `gp-search-20260320_main.csv`)
4. 저장 경로: `{output_dir}/`

- Google Patents CSV 다운로드는 Playwright 자동화 불가 (사용자 수동 필요)
- Google Patents 정책상 최대 1,000건 (반복 검색식 조정으로 분할 수집 가능)
