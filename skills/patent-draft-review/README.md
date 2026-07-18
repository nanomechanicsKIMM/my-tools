---
title: "patent-draft-review"
created: 2026-04-11
tags: [skill, patent, TRIZ, korean-patent, claude-code]
---

# patent-draft-review

출원 전 특허 명세서 초안을 **TRIZ 진단 + 청구항 구조 + 선행특허 대응(옵션) + 오탈자·부호·용어 + 요약서·도면**을 통합 점검하여 Obsidian 호환 개선방안 MD로 자동 생성하는 Claude Code 스킬. 한국 특허 실무에 특화.

## 스킬 개요

| 항목 | 내용 |
|------|------|
| **트리거** | "명세서 검토", "특허 초안 검토", "출원 전 진단", "patent draft review", "진보성 향상 방안" |
| **입력** | HWPX / MD / PDF 명세서 초안 (+ 선택: 선행특허 분석 MD) |
| **출력** | `{invention_id}_개선방안.md` (Obsidian 호환, 11 섹션 + 부록 3개) |
| **모델** | opus (Phase 2, 4, 7, 9) + sonnet (Phase 1, 3, 5, 6, 8) |

## 차별점

| 기존 스킬 | 시점 | 대상 | 산출물 |
|-----------|------|------|--------|
| `patent-incubation-auto` | 발명 단계 | 아이디어 → 신규 | 발명내용설명서 HWPX/MD |
| **`patent-draft-review`** (본 스킬) | **출원 전** | **기존 명세서 초안** | **개선방안 MD** |
| `patent-defence` | 거절 후 | 거절 이유 통지 | 당소의견안 |
| `patent-strategy-pro` | 포트폴리오 | RFP/기술 분야 | 전략 보고서 |

## 아키텍처 (9 Phase Orchestration)

```
Phase 0: 입력 수집 + manifest (SKILL.md 내장)
Phase 1: 명세서 파싱 (sonnet, hwpx_to_md.py → sections.json)
Phase 2: TRIZ 진단 (opus, 모순·IFR 도출)
Phase 3: 청구항 구조 진단 (sonnet, 매몰 차별 요소 탐지)
Phase 4: 선행특허 대비 (opus, 옵션)
Phase 5: 오탈자·부호·용어 (sonnet, typo_scanner.py)
Phase 6: 요약서·도면 점검 (sonnet)
Phase 7: 리포트 작성 (opus, render_report.py)
Phase 8: 참고문헌 자동 생성 (sonnet)
Phase 9: v1 → v2 병합 (opus, 재호출 시)
```

**MVP 구현 상태**: Phase 0/1/2/3/5/7 완료. Phase 4/6/8/9 는 확장 단계.

## 파일 구조

```
patent-draft-review/
├── SKILL.md                              # 스킬 진입점 (오케스트레이션 로직 내장)
├── agents/                               # 5 Phase 에이전트 (Phase 0 제외)
│   ├── phase1-spec-parser.md
│   ├── phase2-triz-diagnose.md
│   ├── phase3-claim-structure.md
│   ├── phase5-proofreader.md
│   └── phase7-report-writer.md
├── scripts/                              # 4 Python 스크립트 (stdlib only)
│   ├── hwpx_to_md.py                    # hwpx-xml/text_extract.py 래퍼
│   ├── typo_scanner.py                  # 오탈자·부호·수식 스캐너
│   ├── claim_parser.py                  # 청구항 종속 관계 파서
│   └── render_report.py                 # Handlebars-lite 템플릿 엔진
├── reference/                            # 6 DB
│   ├── SOURCE.md                        # 재사용 자산 hash 기록
│   ├── korean-patent-typo-patterns.md   # 23개 오탈자·부호·수식 패턴
│   ├── korean-claim-form-rules.md       # 청구항 형식 규칙 + 매몰 판정
│   ├── triz-40-principles.md            # (patent-incubation-auto 복사)
│   ├── triz-contradiction-matrix.json   # (복사)
│   └── triz-separation-principles.md    # (복사)
└── templates/                            # 6 Handlebars-lite 템플릿
    ├── improvement-plan-v1.md           # 11 섹션 + 부록 A/B/C 메인 템플릿
    ├── improvement-plan-v2-delta.md     # v1 → v2 업데이트 델타
    ├── references-section.md            # 참고문헌 A/B/C/D/E 5분류
    ├── claim-amendment-table.md         # 청구항 보정안 A/B/C/D 비교
    ├── mechanism-diff-table.md          # 5필드 메커니즘 차이 논증표
    └── priority-checklist.md            # 4단계 우선순위 체크리스트
```

## 의존성

### 필수

- **Python 3.9+** (권장: 3.14 — native generic 타입 힌트 사용)
- Python 표준 라이브러리만 사용 (PyYAML 미의존)

### 재사용 자산 (설치 필요)

- **`hwpx-xml` 스킬**: `scripts/text_extract.py` (HWPX → MD 파싱)
  - 경로: `~/.claude/skills/hwpx-xml/scripts/text_extract.py`
  - `python-hwpx` 패키지 의존
- **`patent-incubation-auto` 스킬**: TRIZ 레퍼런스 3종
  - 본 스킬의 `reference/triz-*` 는 해당 스킬에서 복사한 사본
  - SHA-256 hash 는 `reference/SOURCE.md` 에 기록됨 (drift 감지용)

## 회귀 검증 결과 (P26057KR1 베이스라인)

| 지표 | 목표 | 실측 | 결과 |
|------|------|------|------|
| **오탈자 탐지 재현율** (QC-02) | ≥ 85% | **6/6 = 100%** | ✅ |
| 부호 설명 누락 탐지 | — | **9/9 = 100%** | ✅ |
| 청구항 파싱 정확도 | — | **17/17 (독립 2 + 종속 15)** | ✅ |
| E2E 렌더링 구조 일치 | ≥ 90% | **415/448 = 92.6%** | ✅ |
| E2E 체크리스트 | 10/10 | **10/10** | ✅ |

**탐지된 P26057 치명 오류 6건**:
- E-01: `position-dependetn` (T-EN-001)
- E-02: 부호 300 혼용 (R-DUP-001)
- E-03: 부호 121 중복 (R-DUP-001)
- E-04: `두 개골` 띄어쓰기 (T-KO-001)
- E-05: 특허문헌 "호" 누락 (D-DOC-001)
- E-06: 수식 기호 깨짐 (F-BRK-001)

## 사용 예시

```
사용자: "C:/path/to/draft.hwpx 를 검토해 줘"

Claude 자동 트리거:
  Skill("patent-draft-review", args="C:/path/to/draft.hwpx")
  → Phase 0~7 파이프라인 실행
  → 산출물: C:/path/to/draft_개선방안.md
```

선행특허 분석 결과를 함께 제공할 때:

```
사용자: "draft.hwpx 를 진보성향상방안.md 와 함께 검토"

Skill("patent-draft-review",
      args="draft.hwpx --prior-art 진보성향상방안.md")
→ Phase 4 선행특허 대비 활성화 (확장 단계)
```

## 보안 규칙 (R-13)

> [!danger] 미공개 출원 내용 보호
> 본 스킬은 출원 전 특허 명세서를 다루므로 **WebFetch/WebSearch 전면 금지**.
> 참고문헌 링크는 오프라인 정규식 기반 URL 조립만 수행.
> 에이전트 로그에 청구항 전문 출력 금지.

## 개발 이력

본 스킬은 `.omc/plans/patent-draft-review-skill-plan.md` (v1.4) 설계 문서에 기반하여 Ralph 자동화 워크플로우로 4 iteration 에 걸쳐 개발되었다:

| Iteration | Milestone | 산출물 | 검증 |
|-----------|-----------|--------|------|
| Ralph #1 | M1 Foundation | SKILL.md + 6 templates | Architect APPROVED |
| Ralph #2 | M2 Phase 1/5 | 파싱 + 오탈자 | QC-02 6/6 = 100% |
| Ralph #3 | M3 Phase 2/3 | TRIZ + 청구항 | 17 청구항 파싱 100% |
| Ralph #4 | M5-lite Phase 7 | 리포트 작성 | E2E 10/10, 구조 92.6% |

**MVP 총 규모**: ~4,400 lines, 22 파일

## 확장 로드맵 (MVP 이후)

| Phase | 설명 | 우선순위 |
|-------|------|----------|
| M4: Phase 4 | 선행특허 대비 (opus) — SP1/SP2/KR-SP1 메커니즘 차이 자동 생성 | 🟡 |
| M6: Phase 6 | 요약서/도면 점검 (sonnet) | 🟢 |
| M8: Phase 8 | 참고문헌 자동 생성 (DOI/Google Patents) | 🟢 |
| M9: Phase 9 | v1→v2 병합 (opus) — 선행특허 재통합 | 🟡 |

## 라이선스

설계 플랜 원본은 본 레포지토리의 역사 기록용 문서이며, 스킬 자체는 Claude Code 스킬 표준을 따른다.

## 참고

- **patent-incubation-auto**: 신규 발명내용설명서 작성 (본 스킬의 역방향)
- **patent-defence**: 거절 이유 통지 후 대응
- **patent-strategy-pro**: 포트폴리오 전략
- **hwpx-xml**: HWPX XML 편집 (본 스킬의 text_extract.py 제공)
