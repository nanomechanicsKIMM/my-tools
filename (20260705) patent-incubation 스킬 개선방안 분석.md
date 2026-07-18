---
title: patent-incubation-auto / -interactive 스킬 개선방안 분석
created: 2026-07-05
tags:
  - patent
  - TRIZ
  - SMART지수
  - skill-review
  - patent-incubation
---

# patent-incubation 스킬 개선방안 분석

> [!info] 분석 범위
> `patent-incubation-auto` / `patent-incubation-interactive` 두 스킬(레포 최신본 기준)을 4개 축 — ① 특허성 우수 기술 창출, ② SMART 지수 향상, ③ 도면·그림 생성, ④ TRIZ 모순 발견·해결 — 으로 병렬 심층 분석(에이전트 4기, Opus)하고 개선사항을 우선순위(H/M/L)로 도출함.

## 0. 총평

두 스킬은 "TRIZ 분석 → 모순/IFR → 정량평가 → KIPRIS 선행조사 → 발명내용설명서 → 도면 → 인용검증 → HWPX"라는 완결된 파이프라인을 갖췄고, 특히 **모순-IFR 커버리지 매핑, TRIZ 용어 격리 규칙, 클린 리스트 원칙(2026-07), Phase 6.5 청구항 하드닝(interactive)** 은 실무적으로 우수함. 그러나 4개 축 공통으로 다음 구조적 결함이 확인됨:

1. **특허성 점수의 순환 논리**: 선행조사(Phase 5) *이전*인 Phase 4에서 "선행기술 대비 차별화" 점수를 부여 → 증거 없는 추측 점수로 주발명(§6)이 결정됨.
2. **auto ↔ interactive 격차**: 무인 실행이라 방어 로직이 더 필요한 auto에 오히려 청구항 하드닝·예상 거절 조합·IFR 커버리지·도면 규칙 A/B/C가 전부 없음.
3. **검증의 육안 의존**: 도면 품질(텍스트 겹침·부호 일관성), 청구항 뒷받침 등이 기계적 게이트 없이 "Read 육안검증"에 의존.
4. **운영 환경 불일치**: 설치본(`~/.claude/skills`)이 레포보다 구버전(2026-07 개정 미반영), `C:/Users/JHKIM/...` Windows 경로 하드코딩으로 macOS에서 KIPRIS .env·폰트·Zettelkasten 참조가 전부 깨짐.

---

## 1. 운영·인프라 이슈 (분석 중 직접 확인)

| # | 문제 | 상세 | 우선순위 |
|---|------|------|:---:|
| 1-1 | **설치본-레포 불일치** | `~/.claude/skills/patent-incubation-interactive`에 `scripts/`(verify_citations.py, svg2png.py 등)·`reference/` 디렉터리 자체가 없음. auto 설치본에도 SVG 스크립트 3종·svg-figure-creation.md 누락. **현 상태로 실행하면 클린 리스트 원칙·강제 게이트·규칙 C가 전혀 작동하지 않음** | **H** |
| 1-2 | **Windows 경로 하드코딩** | 두 SKILL.md의 Skill Constants가 `C:/Users/JHKIM/...`, KIPRIS .env·miniconda python·`D:/Zettelkasten/References/`·`C:/Windows/Fonts/malgun.ttf`(변환 스크립트 3종) 모두 macOS에서 실패 | **H** |
| 1-3 | 동기화 절차 부재 | 레포→설치본 sync 스크립트(또는 심링크) 없음. `setup.sh` 계열에 스킬 동기화 단계 추가 필요 | M |

> [!warning] 1-1은 즉시 조치 권장
> 레포가 source of truth라면 `~/.claude/skills/patent-incubation-{auto,interactive}` 를 레포 디렉터리로 **심링크**하는 것이 가장 단순한 해결책. 경로 상수는 `SKILL_ROOT`를 OS 무관 상대 기준으로 재정의.

---

## 2. TRIZ 관점: 모순의 발견 및 해결 전략

### 강점
- 39 파라미터 강제 선택으로 모순 매트릭스 무결성 보장, 기술적/물리적 모순 분리 처리.
- **모순-IFR 커버리지 매핑 + uncovered_contradictions 강제 게이트**(auto phase2)는 방법론적으로 우수.
- TRIZ 용어 3단 격리(§1~§9 금지 / 부록 A 허용 / HWPX 금지)는 심사관 노출 차단 + 내부 추적성의 실무 최적해.

### 약점/공백
- **기능분석(Function Analysis)·근본원인체인(CECA)·Su-Field 분석 부재** — 개선/악화 파라미터 선정이 LLM 직관에 의존, 숨은 모순(2차 유해기능·과잉기능) 구조적 누락 위험. user-philosophy의 "근본에서 해결" 철학이 에이전트 절차로 미구현.
- **IFR 개념 혼동**: 현재 IFR = "해결책 아이디어". 고전 IFR("자원만으로·유해작용 없이 스스로 달성") 기준·이상성비(Σ유용/Σ비용+유해) 부재 → "최소 10개" 강제는 수량 게이트일 뿐, near-duplicate 양산 유인.
- **현대 TRIZ 도구 공백**: 76 표준해(불충분/유해 기능의 고유 해법), 기술진화법칙 TESE(→ 종속항/장래 실시예 직결), 자원분석 MATChEM, Trimming(→ 독립항 최소구성), ARIZ(강한 모순 폴백).
- **TRIZ→청구항 경로 부재**: 어느 IFR이 독립항 광역 구성이고 어느 것이 종속항 fallback인지 매핑 없이 Phase 6가 매번 즉흥 번역.
- **Phase 2 출력 스키마 불일치**: auto는 물리적 모순 구조화(`requirement_a/b`)+커버리지 강제검증, interactive는 단일 문자열+검증 없음 → 동일 입력에 다른 품질.

### 개선안
| 우선순위 | 개선안 | 대상 |
|:---:|------|------|
| H | Phase 1에 기능분석 서브스텝 + `function_interactions` 필드 추가, 파라미터를 기능모델에서 유도 | `phase1-triz-system.md` |
| H | IFR에 `ideality_statement`·`resources_used`·`harm_removed` 필드 추가, "10개"를 "5축(구조/공정/재료/제어/장) 각 1개+ 총 10개"로 교체 | `phase2-contradiction-ifr.md` |
| H | 신규 reference: `triz-function-cause-analysis.md`, `triz-sufield-76-standards.md`, `triz-resource-analysis.md`, `triz-to-claim-mapping.md`, `triz-analysis-schema.json`(공유 정본 스키마) | `reference/` |
| H | interactive phase2에 auto의 uncovered 강제검증·물리모순 구조화 이식 | `interactive/agents/phase2` |
| M | IFR에 `claim_role`(independent-core/dependent-fallback/alternative-embodiment) 필드 → Phase 6 전달 | phase2 스키마 |
| M | `triz-evolution-trends.md`(TESE 8법칙) + Trimming 가이드 | `reference/` |
| L | `triz-ariz-lite.md` 폴백 경로 | `reference/` |

**권장 순서**: 경량(이상성 정의+스키마 통일) → 기능분석/CECA·76표준해 → TESE·Trimming → ARIZ.

---

## 3. 특허성 우수 기술 창출 전략

### 강점
- KIPRIS 상세조회로 초록·대표청구항 실체 비교. interactive는 국제검색(Google Patents/Espacenet/USPTO)+예상 거절 조합(주인용+부인용)+회피설계 전략까지 커버.
- Phase 6.5 하드닝(112b·트리 정합·권리범위 계층·수치한정 이동)은 정확한 실무 반영.

### 약점/공백
- **[최대 구조 결함] Phase 4→5 순서 역전**: "선행기술 대비 차별화" 점수를 선행기술 없이 부여하는 순환 논리. 재산정은 서술 지시뿐, 정량 재계산·순위 재정렬 절차 없음.
- **auto에 방어 3종 통째 누락**: Phase 6.5 하드닝, rejection_combinations, ifr_coverage/국제검색/회피설계.
- 유사도 판정이 TF-IDF/키워드 겹침 의존 → **어휘는 다르나 기능이 동일한 가장 위험한 선행문헌을 놓침**.
- 진보성 논거가 "구성의 곤란성 + 효과의 현저성" 2요건으로 구조화 안 됨. 거절 조합의 방어논거(teaching away 등)가 §4/§7 본문으로 환류되지 않아 사장됨.
- 균등론/금반언 대비, 방어적 상위개념화(우리 청구항이 회피당하지 않게), claim ladder, 112(f) 점검 부재.

### 개선안
| 우선순위 | 개선안 | 대상 |
|:---:|------|------|
| H | **auto에 방어 3종 이식**(하드닝은 Gate 대신 "issue 시 §8 자동 1회 재작성+manifest 기록") | `auto/SKILL.md`, `auto/agents/phase5` |
| H | **특허성 재산정 2패스**: Phase 4 → `P_prior`, Phase 5 후 ifr_coverage(novel/partial/disclosed) 기반 `P_final` 재계산·순위 재정렬 → `evaluation_final.json` → §6 주발명 재선정 | 양 스킬 워크플로우 |
| H | §7에 진보성 3요건 블록 필수화(① 구성 곤란성 ② 효과 현저성(정량) ③ 상승효과(창발)) + 거절 조합 방어논거의 §4/§7 환류 지시 | `phase6-disclosure-writer.md` |
| H | 하드닝에 6번(균등론/금반언)·7번(방어적 상위개념화) 추가 | `interactive/SKILL.md` Phase 6.5 |
| H | 유사도 판정을 "TF-IDF 후보선별 → 구성요소 대응표(claim charting) 재판정" 2단계로 | `phase5-prior-art.md` |
| M | 검색 재현율 절차화(동의어·영문 병기+IPC broad+인용 1-hop 확장), NPL 검색 훅(CrossRef/OpenAlex 재사용) | phase5 |
| M | P 척도를 ifr_coverage에 앵커링(Phase 4 상한 7점 캡, 9-10은 novel 확정 시에만) | `phase4-evaluator.md` |
| L | 112(f) means-plus-function 경고 1줄 | Phase 6.5 |

---

## 4. SMART 지수 향상 전략

### SMART 평가 체계 (KIPA SMART3/SMART5)
- **권리성 35 / 기술성 35 / 활용성 30**, AAA~C 9등급. 세부 가중치·산식은 KIPA 비공개.
- 핵심 통찰: 지표의 절반(피인용·패밀리·심사이력)은 **출원 후에만 생기는 사후지표** → 발명내용설명서 단계에서는 "출원 시점에 결정되는 선행지표"(청구항 구조·명세서 충실도·IPC/패밀리 출원전략 권고)에 집중해야 함.
- 출처: [SMART5](https://smart.kipa.org/) · [평가요소](https://smart.kipa.org/intro/valelement.do) · KIPA 브로슈어. 정량 목표치는 공개 방향성 기반 실무 권장치이며 KIPA 산식과 1:1 검증된 값은 아님.

### 현재 커버리지 진단
| SMART 부문 | 현재 상태 |
|-----------|----------|
| 권리성 | Phase 6.5가 부분 커버. 단 §8 지침이 **"독립항 1개+종속항 2~4개, 3~5개 항"으로 SMART 역방향**(독립항 1개는 하한) |
| 기술성 | 사실상 미겨냥 — IPC/CPC 전략, 기술수명주기 위치, 실시가능성 정량 게이트 부재 |
| 활용성 | 가장 약함 — 시장규모·대체기술·사업화 경로·패밀리(PCT) 전략 서술 요구 없음 |

Phase 4의 F/C/E/P/V 5기준은 IFR 선별용 내부 지표로 SMART 3부문과 미정렬 → 발명자가 예상 등급 경보를 받지 못함.

### 개선안
| 우선순위 | 개선안 | 대상 |
|:---:|------|------|
| H | §8 정량 목표 상향: **"카테고리별 독립항 2~3개(장치·방법·소자), 독립항당 종속항 3개+, 총 12~20항"** (비용 부담은 핵심세트/확장세트 분리 권고로 상쇄) | `phase6-disclosure-writer.md` §8, `disclosure-report.md` |
| H | 신규 `reference/smart-index-checklist.md`: 3부문 × 제어 가능 선행지표만 체크리스트화, 사후지표는 '출원전략 권고'로 분리 표기 | `reference/` |
| H | Phase 6.5에 6번째 점검 "SMART 권리성 정량 점검"(독립항 카테고리≥2, 총 청구항≥12, 전 구성요소 §6 뒷받침) | `interactive/SKILL.md` |
| M | `evaluation.json`에 `smart_projection`(권/기/활 상·중·하 정성 3단계 — 부문 편중 경보 용도) | `phase4-evaluator.md` |
| M | §3에 기술수명주기 위치, §7에 시장규모·대체기술 우위·사업화 경로 필수 서브지침 | phase6 writer |
| L | Phase 5 선행특허 빈출 IPC/CPC 집계 → 대표 분류 3개 부록 B 자동 기재 | phase5 |

---

## 5. 도면 및 그림 생성 전략

### 강점
- 벡터 우선 아키텍처(손코딩 SVG→PNG→HWPX BinData)와 SVG/EMF/outlined-PPT 3종 변환은 실전 검증됨.
- 규칙 A(원본 재활용)·B(텍스트 비겹침)·C(도면-설명 동기화, 2026-07)는 방향이 옳음.

### 약점/공백 (5대 공백, 모두 H)
1. **기계적 품질검증 전무**: 규칙 B가 "Read 육안검증"에만 의존 — 검증 불가능한 규칙. `outline_svg_text.py`의 폰트 폭 계산 로직을 재활용해 bbox 충돌 검사기 `svg_lint.py` 신설 가능.
2. **PNG 정렬 버그**: `convert_hwpx.py:645`의 `sorted(glob.glob("*.png"))` 순수 알파벳 정렬 → 도면 10개 이상이면 fig10이 fig2보다 앞에 삽입. 자연 정렬(natural sort)로 1줄 수정.
3. **도면부호↔§6 본문↔§8 청구항 구성요소 명칭 일관성 메커니즘 전무** — 명세서 정합성의 핵심인데 부재. `check_refnum_consistency.py` 신설 권고.
4. **규칙 A/B/C가 interactive SKILL.md에만 존재** — 두 스킬의 phase6b 에이전트는 바이트 단위 동일한데 auto에는 규칙이 전혀 없음. 에이전트 본문 편입+공유 reference화 필요.
5. **정책 모순**: 색상(phase6b "흑백 기본" vs svg-figure-creation.md 컬러 팔레트), DPI(auto 150/200 vs interactive 규칙 C 600 vs 출원용 300+), 해칭 primitive 부재.

추가: 변환 스크립트 3종의 `C:/Windows/Fonts/malgun.ttf` 하드코딩 → macOS에서 전량 실패(§1-2와 동일 뿌리).

### 개선안
| 우선순위 | 개선안 | 대상 |
|:---:|------|------|
| H | `convert_hwpx.py:645` 자연 정렬 수정 (1줄) | `scripts/convert_hwpx.py` |
| H | `svg_lint.py` 신설(텍스트 bbox 충돌·라벨 누락 기계 검사) — 규칙 B를 검증 가능한 게이트로 | `scripts/` |
| H | `check_refnum_consistency.py` 신설(도면부호-§6-§8 대조) | `scripts/` |
| H | 규칙 A/B/C를 phase6b 에이전트 본문에 편입(양 스킬 공유) | `agents/phase6b` |
| H | 색상/해칭/DPI 정책 단일화(발명신고서용 vs 출원 도면용 2모드 명시) | `svg-figure-creation.md` |
| M | 폰트 경로 platform 분기(macOS: AppleGothic/NanumGothic 폴백) | svg2png/svg2emf/outline_svg_text |
| M | visual-verdict 스킬 연계한 스크린샷 QA 옵션 | phase6b |

---

## 6. 통합 우선순위 로드맵

> [!tip] 실행 순서 제안 (효과/노력 비율 순)

**1주차 — 즉효·저노력 (버그/인프라)**
- [ ] 설치본↔레포 심링크 또는 sync 스크립트 (§1-1)
- [ ] 경로 상수 OS 무관화 + 폰트 platform 분기 (§1-2)
- [ ] convert_hwpx.py 자연 정렬 1줄 수정 (§5-2)

**2주차 — 구조 결함 해소 (파일 병합 중심)**
- [ ] auto에 방어 3종 이식(하드닝+거절조합+커버리지/국제검색) (§3)
- [ ] 규칙 A/B/C를 phase6b 에이전트에 편입 (§5-4)
- [ ] Phase 2 출력 스키마 통일(`triz-analysis-schema.json`) (§2)

**3~4주차 — 품질 게이트 신설**
- [ ] 특허성 재산정 2패스(`P_prior`→`P_final`→재정렬) (§3)
- [ ] §8 청구항 정량 목표 상향 + SMART 권리성 점검(Phase 6.5 6번) (§4)
- [ ] 진보성 3요건 §7 필수화 + 방어논거 §4/§7 환류 (§3)
- [ ] `svg_lint.py`·`check_refnum_consistency.py` 신설 (§5)

**5주차 이후 — 방법론 심화**
- [ ] 기능분석/CECA·76 표준해·자원분석 reference 신설 (§2)
- [ ] `triz-to-claim-mapping.md` + IFR `claim_role` 필드 (§2)
- [ ] `smart-index-checklist.md` + `smart_projection` (§4)
- [ ] claim charting 2단계 유사도 판정 (§3)

### 신규 파일 제안 총괄

| 파일 | 유형 | 축 | 우선순위 |
|------|------|-----|:---:|
| `reference/triz-analysis-schema.json` | 스키마 | TRIZ | H |
| `reference/triz-function-cause-analysis.md` | reference | TRIZ | H |
| `reference/triz-sufield-76-standards.md` | reference | TRIZ | H |
| `reference/triz-resource-analysis.md` | reference | TRIZ | H |
| `reference/triz-to-claim-mapping.md` | reference | TRIZ→청구항 | H |
| `reference/smart-index-checklist.md` | reference | SMART | H |
| `scripts/svg_lint.py` | 스크립트 | 도면 | H |
| `scripts/check_refnum_consistency.py` | 스크립트 | 도면·명세서 | H |
| `reference/triz-evolution-trends.md` | reference | TRIZ | M |
| `reference/triz-ariz-lite.md` | reference | TRIZ | L |

---

## 7. Root Cause 정리

세 갈래의 근본 원인으로 수렴함:

1. **파이프라인이 "아이디어 창출 최적화" 순서로 설계**되어 특허성·SMART 검증이 사후적으로 얹힘 → 증거(선행조사) 이전에 점수가 매겨지고, 방어 논거가 본문으로 환류되지 않음. 해결: "선행조사 증거 → 특허성 재산정 → 진보성 논거 → 청구항 하드닝"을 하나의 강제 데이터 흐름으로 통합.
2. **interactive에 축적된 개선(2026-07 개정 포함)이 auto로 역이식되지 않음** → 무인 실행일수록 강해야 할 방어가 오히려 약함. 해결: 공유 reference/스키마로 단일 소스화.
3. **품질 규칙이 선언은 됐으나 기계적 게이트가 없음**(도면 비겹침, 부호 일관성, 청구항 뒷받침) → verify_citations.py처럼 exit-code 게이트로 승격.

## 관련 문서
- [[patent-incubation-auto SKILL]] · [[patent-incubation-interactive SKILL]]
- 분석 근거 파일 위치: `my-tools/skills/patent-incubation-{auto,interactive}/`
