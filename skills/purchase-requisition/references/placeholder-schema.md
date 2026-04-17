# payload.json 스키마

`scripts/build_forms.py` 가 받는 단일 JSON 페이로드. `spec` 또는 `purpose` 키 중 하나만 있어도 동작한다.

```jsonc
{
  // 출력 파일 베이스명. 스크립트가 ` 규격서.hwpx` / ` 용도설명서.hwpx` 접미사를 붙인다.
  // CLAUDE.md 의 LLM_work/active/ 규칙(`(YYYYMMDD LLM) <제목>`)을 따르길 권장.
  "output_basename": "(20260417 LLM) <품명 약식>",

  "spec": {
    "품명": "string",            // 표 헤더 셀 #1: 품명 (Description)
    "규격": "string",            // 표 헤더 셀 #2: 규격 (Specification)
    "단위": "EA | 식 | 유저 | ...",
    "수량": "1",                 // 문자열로 입력
    "sections": [
      {
        "title": "1. 제품 개요 및 사용 목적",
        // body 는 string 또는 string[] — string 일 때 \n 으로 paragraph 분리
        "body": [" 본 장비는 ...", " 두 번째 문단."]
      },
      { "title": "2. 주요 사양", "body": [" - CPU : ...", " - RAM : ..."] }
      // 섹션 수 제한 없음. 일반적으로 2~4개.
    ]
  },

  "purpose": {
    "품명": "string",
    "수량단위": "1 EA",
    "금액": "9,900,000원 (부가세 포함)",
    "모델명": "string or '-'",
    "HSK": "8471.30-0000 or '-'",

    "연구명": "string",
    "연구기간": "YYYY.MM.DD.-YYYY.MM.DD",
    "연구책임자": "string",      // 표 row 의 PI
    "자금명": "연구비(NK***)",

    // 4~5문장, 개조식, 상세 표현. \n 으로 paragraph 분리.
    "용도개요": " 본 과제 ...\n - 첫째 ...\n - 둘째 ...\n - 셋째 ...\n - 본 장비 도입 효과 ...",

    "활용빈도": "1500시간/년",
    "기보유량": "확인 불가능",
    "기보유량_2": "확인 불가능",   // 샘플 형식상 같은 값 두 번
    "공동활용": "없음",
    "공동활용_2": "없음",
    "장비구분": "컴퓨터/노트북",
    "설치장소": "연구○동 ○호",
    "특기사항": "",

    "부서명": "string",          // footer 의 구매요구부서명
    "연구책임자_서명": "string"  // footer 의 연구책임자 (보통 위와 동일)
  }
}
```

## 셀 위치 매핑 (참조용)

### 규격서 (4행 × 5열)

| (row, col) | 내용 | payload 키 |
|---|---|---|
| (0, 0) | 제목 "규 격 서" (5열 병합) | (고정) |
| (1, 0..4) | 헤더: No. / 품명 / 규격 / 단위 / 수량 | (고정) |
| (2, 0) | "1" | (고정) |
| (2, 1) | 품명 | `spec.품명` |
| (2, 2) | 규격 | `spec.규격` |
| (2, 3) | 단위 | `spec.단위` |
| (2, 4) | 수량 | `spec.수량` |
| (3, 0) | 본문 (5열 병합, 다중 paragraph) | `spec.sections[]` |

### 용도설명서 (12행 × 7열)

| 라벨 셀 텍스트 | 값 셀(들) | payload 키 |
|---|---|---|
| 품 명 | merged 6-col | `purpose.품명` |
| 수 량 / 단위 | col1: 수량단위, col3: 금액 | `purpose.수량단위`, `purpose.금액` |
| 모 델 명 | col1: 모델명, col3: HSK | `purpose.모델명`, `purpose.HSK` |
| 연 구 명 | col1: 연구명, col3: 연구기간 | `purpose.연구명`, `purpose.연구기간` |
| 연 구 책 임 자 | col1: PI, col3: 자금명 | `purpose.연구책임자`, `purpose.자금명` |
| 용 도 개 요 (사용목적) | merged 6-col multi-line | `purpose.용도개요` |
| 활용예상빈도 | merged 6-col | `purpose.활용빈도` |
| 기 보 유 량 (D/B검토) | col1, col2 | `purpose.기보유량`, `purpose.기보유량_2` |
| 공동활용가능성 (취득전) | col1, col2 | `purpose.공동활용`, `purpose.공동활용_2` |
| 장 비 구 분 | merged 6-col | `purpose.장비구분` |
| 설치 사용 장소 | merged 6-col | `purpose.설치장소` |
| 기타 특기 사항 | merged 6-col | `purpose.특기사항` |
| (footer) 구매요구부서명 : ... | tab.tail in `<hp:t>` | `purpose.부서명` |
| (footer) 연구책임자 : ... | `<hp:t>.text` | `purpose.연구책임자_서명` |

## 줄바꿈 처리

- 셀 단일값 (예: `purpose.연구명`) → 한 줄 문자열
- 셀 다중행 (예: `purpose.용도개요`) → `\n` 으로 paragraph 분리. 빈 줄도 paragraph 1개로 카운트
- 규격서 본문 `sections[].body` → string 일 때 `\n` 분리, string[] 일 때 그대로 paragraph 별 줄

## 안전 규칙

- 모든 값은 **plain text**. XML 특수문자(`<`, `>`, `&`)는 자동 escape 안 됨 — 입력 단계에서 피할 것.
- HWPX 파일 자체 양식(셀 추가/삭제, 행 추가)은 수정하지 않음. 셀 추가가 필요하면 템플릿 hwpx 를 한컴오피스로 직접 편집한 뒤 `assets/templates/` 에 덮어쓸 것.
