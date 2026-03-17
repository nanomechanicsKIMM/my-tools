---
name: tor
description: "한국기계연구원 과업지시서(TOR, Terms of Reference)를 HWPX 파일로 자동 생성하는 스킬. 사용자가 '과업지시서', 'TOR', '용역 지시서', '과업명/부서명/작성자/과업기간/과업범위/과업내용/검수/책임/자격조건/해제조건'을 언급하면 이 스킬을 사용할 것."
---

# 과업지시서(TOR) HWPX 자동 생성 스킬

한국기계연구원 과업지시서(Terms of Reference)를 자동으로 HWPX 파일로 생성한다.
샘플 파일(`TermsOfReference_sample.hwpx`)의 기관 로고·머리글 레이아웃을 그대로 재사용하고,
본문 10개 섹션만 새로 생성·치환한다.

## 스킬 구조

```
skills/tor/
├── SKILL.md
├── assets/
│   └── TermsOfReference_sample.hwpx   ← 기관 로고·머리글 포함 샘플 양식
└── scripts/
    ├── build_tor.py                   ← 메인 생성 스크립트
    ├── validate.py                    ← HWPX 구조 검증
    ├── requirements.txt               ← lxml
    └── office/
        ├── unpack.py                  ← HWPX → 디렉터리 언팩
        └── pack.py                    ← 디렉터리 → HWPX 재조립
```

> 모든 경로는 스크립트 위치 기준 상대경로로 동작하므로 어느 PC에서도 작동한다.

## 의존성 설치

```bash
# uv 사용 (권장)
uv pip install lxml

# pip 사용
pip install lxml
```

## 실행 방법

```bash
# 작업 디렉토리로 이동 (pyproject.toml 또는 출력 파일 위치)
cd <작업_디렉토리>

# JSON 파일로 실행
PYTHONUTF8=1 uv run python ~/.claude/skills/tor/scripts/build_tor.py \
  --input tor_data.json --output result.hwpx

# CLI 인수로 간단히 실행 (title/dept/author/period만)
PYTHONUTF8=1 uv run python ~/.claude/skills/tor/scripts/build_tor.py \
  --title "과업명" --dept "부서명" --author "홍길동" --period "계약일로부터 50일" \
  --output result.hwpx
```

> **Windows**: `PYTHONUTF8=1` 필수 (한국어 CP949 환경의 stdout 인코딩 문제 방지)

스크립트가 자동으로 validate.py를 실행하여 구조 검증까지 수행한다.

## 입력 JSON 스키마

```json
{
  "title": "과업명",
  "department": "나노디스플레이연구실",
  "author": "홍길동",
  "period": "계약일로부터 50일",
  "purpose": "목적 설명 (1~2문장)",
  "scope_summary": "과업 범위 주요내용 한 줄 (가. 주요내용의 ○ 항목)",
  "scope_items": ["1) 항목1", "2) 항목2"],
  "content_items": ["  가. 세부 설명1", "    ○ 하위 항목"],
  "deliverables": ["가. 검수 방법", "나. 결과물 목록"],
  "responsibilities": ["가. 책임 내용1", "나. 책임 내용2"],
  "qualifications": ["가. 자격 조건1"],
  "termination_conditions": ["가. 조건1", "나. 조건2", "다. 조건3"],
  "misc": "기타 조항 (생략 시 기본 문구 사용)"
}
```

## 10개 섹션 매핑

| 섹션 번호 | 필드명 | 설명 |
|-----------|--------|------|
| 1. 과업명 | `title` | 과업의 공식 명칭 |
| 2. 목적 | `purpose` | 과업 목적 설명 |
| 3. 과업기간 | `period` | 예: "계약일로부터 50일" |
| 4. 과업범위 | `scope_summary` + `scope_items` | 주요내용 + 범위 목록 |
| 5. 과업내용 | `content_items` | 상세 내용 (들여쓰기로 계층 표현) |
| 6. 검수 및 결과물 제출 | `deliverables` | 검수 방법 + 결과물 목록 |
| 7. 책임 및 의무 | `responsibilities` | 갑/을 책임 조항 |
| 8. 자격조건 | `qualifications` | "을"의 자격 요건 |
| 9. 계약해지 및 해제조건 | `termination_conditions` | 해지 조건 목록 |
| 10. 기타 | `misc` | 기타 계약 조항 |

## 사용 워크플로우

1. 사용자가 자연어로 과업지시서 내용을 설명
2. Claude가 JSON 데이터를 작성하여 임시 파일(`tor_data.json`)로 저장
3. `build_tor.py` 실행 → `result.hwpx` 생성
4. validate.py 자동 실행 (구조 검증)
5. 결과 파일 경로를 사용자에게 안내

## 스타일 규칙

- 섹션 제목: `paraPrIDRef="21"` + `charPrIDRef="16"` (13pt Bold)
- 본문 기본: `paraPrIDRef="21"` + `charPrIDRef="17"` (13pt Regular)
- 빈 줄: `paraPrIDRef="34"` + `charPrIDRef="16"`
- 10번 기타: `paraPrIDRef="36"` + `charPrIDRef="16"/"26"` (번호 Bold + 내용 Regular)

### 섹션별 들여쓰기 paraPrIDRef

| 섹션 | 항목 종류 | paraPrIDRef | 텍스트 앞 공백 |
|------|-----------|-------------|---------------|
| 4. 과업범위 | 가. 주요내용 / ○ | `24` | 2칸 / 4칸 |
| 4. 과업범위 | 나. 범위, 1)/2)/3) | `21` | 2칸 / 4칸 |
| 5. 과업내용 | 가./나. 항목 | `21` | 2칸 |
| 5. 과업내용 | ○ 항목 | `39` | 4칸 |
| 6. 검수 | 가. (첫 번째) | `30` | 3칸 |
| 6. 검수 | 나. (두 번째) | `31` | 3칸 |
| 7. 책임 | 가. (첫 번째) | `32` | 3칸 |
| 7. 책임 | 나. (두 번째) | `33` | 3칸 |
| 8. 자격조건 / 9. 해제조건 | 가./나. | `21` | 2칸 |

## 주의사항

- `PYTHONUTF8=1` 필수 (Windows 한국어 환경)
- 작업 디렉토리를 `C:/Users/JHKIM/AI-study/TermsOfReference/`로 설정할 것 (pyproject.toml 위치)
- 기관 로고(`image4.jpg`)는 샘플에서 자동 재사용됨
- PREFIX 내 치환 대상: "나노디스플레이연구실", "김재현", "뇌졸중 환자 재활훈련 프로그램 개발"
