---
title: "overseas-trip-plan 플레이스홀더 매핑 문서"
created: 2026-04-11
tags: [skill-docs, placeholder]
---

# Placeholder Map 문서

## 개요

`overseas-trip-plan` v0.1은 **ZIP-level 텍스트 치환** 방식을 사용한다. 원본 HWPX 템플릿에 있는 특정 문자열을 사용자 입력으로 교체한다.

## 매핑 파일 위치

- `assets/placeholder_maps/meeting.json` — Template A (기관방문·회담형)
- `assets/placeholder_maps/conference.json` — Template B (학회·전시회형)

## JSON 구조

```json
{
  "_meta": {
    "template": "template_{type}.hwpx",
    "base_source": "원본 파일명",
    "description": "...",
    "version": "0.1"
  },
  "fields": {
    "<logical_field_name>": {
      "placeholder": "<원본 HWPX 안의 정확한 문자열>",
      "required": true/false,
      "description": "..."
    }
  }
}
```

## v0.1 지원 필드

| 논리 필드 | user_input §1 키 | meeting placeholder | conference placeholder |
|----------|-----------------|--------------------|------------------------|
| `submission_date` | `제출일자` | `2024. 06. 05.` | `2025. 04. 28.` |
| `applicant.department` | `소속` | `원장실` | `나노디스플레이연구실` |
| `applicant.position` | `직급` | `원장` | `책임연구원` |
| `applicant.name` | `성명` | `류 석 현` | `김 재 현` |

## 치환 안전성 주의

ZIP-level 치환은 **동일 문자열을 모두 교체**한다. 따라서:

1. **고유성 높은 문자열만 사용**: "원장", "김재현" 같이 본문 다른 곳에 나올 수 있는 문자열은 오탐 위험.
2. **공백 포함 성명**: "김 재 현"(공백 포함)은 문서 내에서 대부분 유일해서 안전.
3. **연도 포함 날짜**: "2025. 04. 28."처럼 점·공백 포함 형태는 본문에 거의 없어 안전.

## v0.2+ 확장 계획

- [ ] 출장 기간·국가·도시 필드 추가 (template B에서 본문 내 중복 리스크 평가 필요)
- [ ] 주 목적 한 줄 치환
- [ ] 연구과제 계정번호 치환 (예: `MT7120`)
- [ ] 예산 합계액 치환
- [ ] 동행자 표 / 일정 표 / 반출장비 표는 **lxml 기반 `table_utils.py`** 로 행 단위 조작 (별도 스킬 작업)

## 신규 플레이스홀더 추가 절차

1. 원본 HWPX를 `office/unpack.py`로 언팩
2. `Contents/section0.xml`에서 대상 문자열 검색 (고유성 확인)
3. `assets/placeholder_maps/{type}.json` 의 `fields`에 추가
4. `build_trip_plan.py` 의 `APPLICANT_KEY_MAP` 또는 새 매핑 함수 업데이트
5. 테스트: 샘플 user_input → 치환 → 검증
