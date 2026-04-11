---
title: "한국 특허 명세서 오탈자·부호·수식 패턴 DB"
created: 2026-04-11
tags: [patent, typo, korean, reference, patent-draft-review]
---

# 한국 특허 명세서 오탈자·부호·수식 패턴 DB

> [!info] 본 문서의 용도
> `patent-draft-review` 스킬의 `typo_scanner.py`가 사용하는 **패턴 사전**이다.
> 각 패턴은 고유 ID와 severity, 정규식 또는 알고리즘 설명, 수정 제안을 포함한다.
> 발견 사례는 P26057KR1_TB26021K 케이스를 기준으로 축적한다.

## 패턴 분류

| 카테고리 | 접두 | 설명 | 대표 severity |
|----------|------|------|---------------|
| **영문 오탈자** | T-EN- | 한국 명세서에 자주 혼입되는 영어 기술 용어의 오탈자 | critical |
| **띄어쓰기 오류** | T-KO- | 복합명사·기술 용어의 띄어쓰기 일관성 오류 | warning |
| **부호 중복 사용** | R-DUP- | 같은 도면 부호가 다른 구성요소를 지칭 | **critical** |
| **부호 설명 누락** | R-MISS- | 본문에 등장하는 부호가 "부호의 설명" 섹션에 미등재 | critical |
| **수식 깨짐** | F-BRK- | HWPX → MD 변환 중 수식 기호 누락 | warning |
| **용어 혼용** | V-MIX- | 같은 개념을 가리키는 용어 표기가 혼용 | warning |
| **특허문헌 형식** | D-DOC- | 인용 특허 문헌 형식 (호 누락 등) | info |

Severity 정의:
- **critical**: 출원 전 반드시 수정. 무효 사유 또는 심사관 지적 가능성.
- **warning**: 출원 전 수정 권장. 품질·가독성.
- **info**: 개선 권고 수준.

---

## T-EN: 영문 오탈자 패턴

### T-EN-001 `position-dependetn` → `position-dependent`

- **Severity**: critical
- **정규식**: `\bposition-dependetn\b`
- **유래**: P26057KR1 line 114 발견
- **수정**: `position-dependent`
- **메모**: `dependent`의 `t-n` 순서 오류. 영어권 리뷰어에게 반드시 지적됨.

### T-EN-002 `indepdent` → `independent`

- **Severity**: critical
- **정규식**: `\bindepdent(ly)?\b`
- **수정**: `independent(ly)`
- **메모**: `en` 누락.

### T-EN-003 `inherient` → `inherent`

- **Severity**: critical
- **정규식**: `\binherient(ly)?\b`
- **수정**: `inherent(ly)`

### T-EN-004 `refered` → `referred`

- **Severity**: critical
- **정규식**: `\brefered\b`
- **수정**: `referred`

### T-EN-005 `occured` → `occurred`

- **Severity**: critical
- **정규식**: `\boccured\b`
- **수정**: `occurred`

### T-EN-006 `comparision` → `comparison`

- **Severity**: critical
- **정규식**: `\bcomparision\b`
- **수정**: `comparison`

### T-EN-007 `seperat` → `separat`

- **Severity**: critical
- **정규식**: `\bseperat(e|ed|ion|ely)\b`
- **수정**: `separat(e|ed|ion|ely)`

### T-EN-008 `recieve` → `receive`

- **Severity**: critical
- **정규식**: `\brecieve(d|s|r|rs)?\b`
- **수정**: `receive(d|s|r|rs)`

---

## T-KO: 띄어쓰기 오류

### T-KO-001 `두 개골` → `두개골`

- **Severity**: warning
- **정규식**: `두\s+개골`
- **유래**: P26057KR1 line 161 발견
- **수정**: `두개골`
- **메모**: 의료 용어 "두개골(skull)"의 고정 표기.

### T-KO-002 `복원 이미지` 일관성

- **Severity**: info
- **정규식**: N/A (맥락 판단)
- **메모**: `복원 이미지`, `복원이미지`, `복원영상` 중 하나로 통일. 본문 전체 빈도 분석 후 대표 표기 선정.

### T-KO-003 `공액 면` / `공액면` 혼용

- **Severity**: warning
- **정규식**: `공액\s+면` (공백 포함 출현)
- **수정**: `공액면` (고정 표기)

### T-KO-004 `반사 행렬` / `반사행렬` 혼용

- **Severity**: info
- **정규식**: `반사\s+행렬`
- **수정**: `반사행렬`

### T-KO-005 `상기` + 명사 혼용 공백

- **Severity**: info
- **정규식**: N/A (맥락 판단)
- **메모**: `상기반사행렬` vs `상기 반사행렬` — 명세서 관례상 띄어쓰기 권장.

---

## R-DUP: 부호 중복 사용 탐지

### R-DUP-001 같은 부호 → 다른 구성요소

- **Severity**: **critical** (무효 사유 가능)
- **알고리즘**:
  1. 본문에서 `([가-힣\w]+)\((\d+)\)` 패턴으로 (구성요소명, 부호) 쌍 추출
  2. 같은 부호가 2개 이상의 서로 다른 구성요소에 사용되면 플래그
- **유래**: P26057KR1 부호 `121`이 **두개골 표면**과 **공액면** 두 가지를 지칭 (line 124, 126, 127)
- **수정 방향**: 두 구성요소에 서로 다른 부호 부여 (예: 121 → 121', 121a/121b, 또는 신규 부호)
- **예시 출력**:
  ```json
  {
    "pattern_id": "R-DUP-001",
    "severity": "critical",
    "reference_number": "121",
    "assigned_to": ["두개골 표면", "공액면"],
    "locations": [124, 126, 127],
    "suggestion": "두개골 표면과 공액면에 별도 부호 부여"
  }
  ```

---

## R-MISS: 부호 설명 누락

### R-MISS-001 본문 부호가 부호의 설명에 미등재

- **Severity**: critical
- **알고리즘**:
  1. 본문 섹션에서 `(\w+)\((\d+)\)` 패턴으로 모든 (구성요소, 부호) 쌍 수집
  2. 부호의 설명 섹션 파싱 (`\d+ : 구성요소` 형식)
  3. 본문에 있으나 부호의 설명에 없는 부호를 플래그
- **유래**: P26057KR1 부호의 설명에 10개 부호 누락
  - 누락 부호: 100(대상체), 111(두피 표면), 121/122/123(공액면), 200(초음파 프로브), 310(송수신부), 330(기저 변환부), 350(수차 연산부)
- **수정**: 부호의 설명 섹션에 누락 부호를 모두 등재

---

## F-BRK: 수식 깨짐 탐지

### F-BRK-001 연속 공백 + 수식 기호 인근

- **Severity**: warning
- **정규식**: `\s{3,}[가-힣A-Za-z]` 또는 `[=±→⇔]\s{3,}` 등
- **유래**: P26057KR1 line 115~142에서 τ, Δφ, H† 등 수식 기호가 빈 공간으로 남음
- **수정**: 원본 HWPX에서 수식 이미지/기호를 재확인하여 복원
- **메모**: MD 변환 손실 가능성이 높음. `needs_llm_review: true` 플래그.

### F-BRK-002 수식 라벨 고아

- **Severity**: warning
- **정규식**: `식\s*\(\d+\)` 가 본문에 언급되나 인근 3줄에 수식 기호 부재
- **메모**: `식 (1)`, `식 (2)`처럼 수식 번호만 있고 본문에 수식이 없는 경우.

---

## V-MIX: 용어 혼용 탐지

### V-MIX-001 `conjugate surface` / `conjugate plane`

- **Severity**: warning
- **알고리즘**: 같은 MD 파일 내 두 용어의 등장 빈도를 카운트. 둘 다 있으면 플래그.
- **유래**: P26057KR1 `conjugate surface`(line 95)와 `conjugate plane`(line 122, 127) 혼용
- **수정 방향**: 하나로 통일. 곡면 포함 가능성 때문에 **`conjugate surface`** 권장.

### V-MIX-002 `송신기저` / `송신 기저`

- **Severity**: warning
- **정규식**: `송신기저|송신\s기저` (둘 다 카운트)
- **유래**: P26057KR1 청구항(`송신기저` 붙여쓰기) vs 본문(`송신 기저` 띄어쓰기) 불일치
- **수정**: 청구항 표현 기준 통일 (일반적으로 청구항이 정답)

### V-MIX-003 `pulse echo` / `펄스 에코`

- **Severity**: info
- **메모**: 영문·국문 혼용. 최초 등장 시 병기, 이후 국문 유지 권장.

---

## D-DOC: 특허문헌 형식

### D-DOC-001 한국 특허 "호" 누락

- **Severity**: critical
- **정규식**: `대한민국\s*(공개|등록)?\s*특허\s*제\s*10-\d{4}-\d{7}(?!\s*호)`
- **유래**: P26057KR1 line 27 `(특허문헌 1) 대한민국 공개특허 제10-2024-0139512` — "호" 누락
- **수정**: 끝에 `호` 추가

### D-DOC-002 미국 특허 번호 형식

- **Severity**: info
- **정규식**: `미국\s*(공개)?\s*특허\s*제\s*(\d{4}-\d{7})` (하이픈 형식)
- **메모**: 한국 실무상 `US 20YY/NNNNNNN A1` 또는 `제20YY-NNNNNNN호` 형식을 명세서 내에서 일관 사용.

### D-DOC-003 PCT 번호 형식

- **Severity**: info
- **정규식**: `PCT\s*[/-]\s*[A-Z]{2}\d{4}/\d+`
- **수정**: `PCT/KRYYYY/NNNNNN` 표준 형식

---

## 패턴 메타데이터 (scanner 전용)

이 섹션은 `typo_scanner.py`가 프로그래밍 방식으로 파싱한다.

```yaml
patterns:
  - id: T-EN-001
    regex: '\bposition-dependetn\b'
    severity: critical
    category: english_typo
    fix: position-dependent
  - id: T-EN-002
    regex: '\bindepdent(ly)?\b'
    severity: critical
    category: english_typo
    fix: 'independent'
  - id: T-EN-003
    regex: '\binherient(ly)?\b'
    severity: critical
    category: english_typo
    fix: 'inherent'
  - id: T-EN-004
    regex: '\brefered\b'
    severity: critical
    category: english_typo
    fix: referred
  - id: T-EN-005
    regex: '\boccured\b'
    severity: critical
    category: english_typo
    fix: occurred
  - id: T-EN-006
    regex: '\bcomparision\b'
    severity: critical
    category: english_typo
    fix: comparison
  - id: T-EN-007
    regex: '\bseperat(e|ed|ion|ely)\b'
    severity: critical
    category: english_typo
    fix: 'separat\\1'
  - id: T-EN-008
    regex: '\brecieve(d|s|r|rs)?\b'
    severity: critical
    category: english_typo
    fix: 'receive\\1'
  - id: T-KO-001
    regex: '두\s+개골'
    severity: warning
    category: korean_spacing
    fix: 두개골
  - id: T-KO-003
    regex: '공액\s+면'
    severity: warning
    category: korean_spacing
    fix: 공액면
  - id: T-KO-004
    regex: '반사\s+행렬'
    severity: info
    category: korean_spacing
    fix: 반사행렬
  - id: F-BRK-001
    regex: '\s{3,}[가-힣A-Za-z]'
    severity: warning
    category: formula_broken
    needs_llm_review: true
  - id: D-DOC-001
    regex: '대한민국\s*(공개|등록)?\s*특허\s*제\s*10-\d{4}-\d{7}(?!\s*호)'
    severity: critical
    category: patent_doc_format
    fix: '... 호 (append)'
```

알고리즘 기반 패턴 (정규식 없음):

```yaml
algorithmic_patterns:
  - id: R-DUP-001
    algorithm: "same_reference_number_different_components"
    severity: critical
  - id: R-MISS-001
    algorithm: "body_refs_missing_in_reference_signs_section"
    severity: critical
  - id: V-MIX-001
    algorithm: "term_coexistence_count"
    terms: ["conjugate surface", "conjugate plane"]
    severity: warning
  - id: V-MIX-002
    algorithm: "term_coexistence_count"
    terms: ["송신기저", "송신 기저"]
    severity: warning
```

---

## 패턴 DB 업데이트 가이드

본 DB는 `patent-draft-review` 스킬의 Phase 5가 새로운 사례를 발견할 때마다 증분 갱신한다.

**새 패턴 추가 시**:
1. 위 형식(ID + Severity + 정규식/알고리즘 + 유래 + 수정)으로 추가
2. 가능하면 `pattern_id`는 카테고리 접두사와 순번으로 부여
3. **유래** 필드에 발견된 원본 명세서 케이스 명시 (예: "P26057KR1 line 161")
4. `typo_scanner.py` 재실행하여 회귀 케이스가 여전히 탐지되는지 확인

**패턴 제거 시**:
- 오탐(false positive) 비율이 높거나, 특정 분야에만 해당되는 경우 `deprecated` 표시 후 유지 (즉시 삭제 금지)
