---
title: "overseas-trip-plan 예시 모음"
created: 2026-04-11
tags: [skill-docs, examples]
---

# 예시 모음

## 빠른 시작

### 1. 작업 디렉터리에 양식 복사

```bash
cd /path/to/my-trip-project
cp ~/.claude/skills/overseas-trip-plan/assets/user_input_template.md ./user_input.md
```

### 2. conference 모드 — 학회 출장

`user_input.md` frontmatter 예시:

```yaml
---
trip_type: conference
conference_url: "https://www.displayweek.org/"
program_urls:
  - "https://www.displayweek.org/symposium/"
  - "https://www.displayweek.org/expo/"
output_filename: "국외출장계획서_DisplayWeek2026.hwpx"
---
```

§1 신청자 정보:
```markdown
## 1. 신청자 정보 ⭐

| 항목 | 값 |
|------|----|
| 제출일자 | 2026. 04. 15. |
| 소속 | 나노디스플레이연구실 |
| 직급 | 책임연구원 |
| 성명 | 김재현 |
```

### 3. Advance Program PDF 다운로드 (선택)

```bash
PYTHONUTF8=1 uv run python ~/.claude/skills/overseas-trip-plan/scripts/fetch_reference_pdf.py \
    --url "https://www.displayweek.org/files/DisplayWeek2026_AP.pdf" \
    --output-dir references/ \
    --filename DisplayWeek2026_AP.pdf
```

저장 결과:
```
./references/
├── manifest.json                  # 다운로드 이력·체크섬
└── DisplayWeek2026_AP.pdf
```

### 4. HWPX 생성

```bash
PYTHONUTF8=1 uv run python ~/.claude/skills/overseas-trip-plan/scripts/build_trip_plan.py \
    --input user_input.md \
    --output 국외출장계획서.hwpx \
    --pdf-ref references/DisplayWeek2026_AP.pdf
```

## meeting 모드 — 기관 방문 출장

```yaml
---
trip_type: meeting
conference_url: ""
output_filename: "국외출장계획서_MIT방문.hwpx"
---
```

§1 신청자 정보:
```markdown
## 1. 신청자 정보 ⭐

| 항목 | 값 |
|------|----|
| 제출일자 | 2026. 04. 20. |
| 소속 | 원장실 |
| 직급 | 원장 |
| 성명 | 홍길동 |
```

생성:
```bash
PYTHONUTF8=1 uv run python ~/.claude/skills/overseas-trip-plan/scripts/build_trip_plan.py \
    --input user_input.md \
    --output 국외출장계획서_MIT.hwpx
```

## WebFetch 자동 수집 (Claude 주도)

Claude 세션에서 자연어로 요청:

> "이 user_input.md로 국외출장계획서 만들어줘"

Claude 내부 동작:
1. `user_input.md` 읽고 frontmatter 확인
2. `trip_type=conference` + `conference_url` 있으면 **WebFetch** 호출
3. 행사명·일정·장소·개요 자동 수집 → 빈 필드 보완
4. (Advance Program PDF URL 있으면) `fetch_reference_pdf.py` 실행 → PDF 저장
5. (PDF 있으면) `pdf-to-md` 스킬로 텍스트 추출 → 세션 리스트 보완
6. `build_trip_plan.py` 실행 → HWPX 생성
7. 생성 결과 + 미입력 필드 리포트

## 과거 실사용 예시

`~/Claude_Work/business_trip_plan/user_input_SID2026.md` 참고.
이 파일은 Display Week 2026을 대상으로 작성된 실제 `conference` 모드 입력 예시이다.

## 주의사항

- v0.1은 **신청자 헤더·제출일자까지만** 자동 치환. 본문 상세(일정·기관 방문 블록 등)는 생성된 hwpx를 한글에서 수동 편집 권장.
- 표 구조(동행자·일정·예산) 자동 생성은 v0.2+ 지원 예정.
