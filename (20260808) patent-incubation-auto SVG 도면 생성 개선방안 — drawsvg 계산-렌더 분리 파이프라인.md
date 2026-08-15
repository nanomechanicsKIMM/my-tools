---
date: 2026-08-08
description: "다운로드 폴더의 GitHub SVG 레포 분석(2026-08-06)을 검토하고, patent-incubation-auto 스킬의 도면 생성(현행 손코딩 SVG)을 drawsvg 기반 계산-렌더 분리 파이프라인으로 업그레이드하는 방안. 실측 실패 모드 근거, P0~P2 단계, 사용자 취사선택 슬롯"
tags:
  - LLM_work
  - my_patent
  - patent-drawing
---

# (20260808) patent-incubation-auto SVG 도면 생성 개선방안 — drawsvg 계산-렌더 분리 파이프라인

> 입력: `docs/github_svg_patent_diagram_repo_analysis_2026-08-06.md`(다운로드 폴더 원본의 사본, 레포 10종 평가).
> 대상: `skills/patent-incubation-auto`(공유)와 `patent-incubation-interactive`(참조)의 Phase 6b 도면 생성.
> 채택 여부는 사용자 취사선택(§6) 후 구현한다.

## §1 현행과 제안의 정면 충돌 (평균 내지 않고 판정)

- **현행** (`reference/svg-figure-creation.md` §1): LLM이 SVG XML을 손코딩. 외부 라이브러리(svgwrite, drawSvg)는 "추가 의존성"으로 명시 기각. 근거는 의존성 0, 완전 제어, git diff, 재현 가능.
- **레포 분석 권고**: drawsvg를 렌더 엔진으로, 물리식 계산은 Python 계층으로 분리, svgpathtools로 QA, FigureSpec으로 재현성 확보.

**판정: 레포 분석 권고 채택(손코딩은 fallback으로 강등).** 현행 기각 논거가 실측으로 반박되었기 때문이다.

| 손코딩의 주장 | 실측 반례 (구면 NED 세션, 2026-07~08) |
|--------------|--------------------------------------|
| "재현 가능" | 곡률 반경 30 → 43 mm 변경 시 도면 전면 재작도 필요(파라미터화 부재). 실제로는 vault 쪽에서 matplotlib 스크립트(gen_diagrams_v14.py)로 이탈하여 **파이프라인이 둘로 갈라짐** |
| "완전 제어" | 좌표를 LLM이 암산 — v14 광학 전문가 비평에서 issue 9건(안구 단면 전후 반전, 굴절 광선 망막 관통, 라벨 중첩, tofu). 제어가 아니라 검산 없는 배치였음 |
| "의존성 0" | 이미 svglib, reportlab, Inkscape, pycairo 의존(변환 계층). drawsvg와 svgpathtools는 순수 파이썬 경량 MIT 2종 추가일 뿐 |
| git diff 가능 | 손코딩 SVG의 diff는 좌표 잡음. FigureSpec(JSON) + 생성 코드의 diff가 의미 단위로 우월 |

한편 레포 분석의 결론 자체는 본 세션의 경험과 정확히 합치한다: "물리 법칙은 그림 엔진에 내장시키지 말고 Python 계산 계층에서 좌표로 변환하고, SVG 엔진은 정확하게 그리는 책임만" — 이는 파동광학 검증(계산)과 도면(렌더)을 분리해 온 실제 작업 방식의 일반화다.

## §2 채택 대상 (레포 분석 §7 대비 취사)

| 레포 | 역할 | 채택 |
|------|------|------|
| cduck/drawsvg (MIT) | 최종 SVG 렌더 엔진 | **P0 채택** |
| mathandy/svgpathtools (MIT) | path 검증, bbox, 교차 QA | **P0 채택** |
| cdelker/schemdraw (MIT) | 구동 회로, 신호 블록 도면 | P1 채택(회로 도면 발생 시) |
| matplotlib | 정량 차트 전용으로 존치 | 역할 재정의(P0) |
| build123d / CadQuery | 기계 부품 단면, hidden line | P2 선택(기계 발명 건 발생 시, 무거운 의존성) |
| Kroki / PlantUML | 흐름도 | 미채택 — 기존 mermaid 규칙과 중복, 물리 제어 불가 |
| Manim / manim-physics | 애니메이션 | 미채택 — 정적 특허 도면 범위 밖 |

## §3 P0 — patent_svg 래퍼 패키지 (스킬 scripts/에 신설)

레포 분석 §6의 구조를 KIMM 실무에 맞춰 조정:

```text
scripts/patent_svg/
  geometry.py     # 좌표계·단위·물리식 계산 (안구 단면, 광선 굴절, 적층 두께 등 도메인 함수 포함)
  primitives.py   # 특허 primitive: 기판/적층 레이어/전극/렌즈/광선 다발/화살표/단면 해칭
  annotations.py  # 참조부호·라벨·leader line (충돌 회피 배치)
  styles.py       # patent_bw(출원용 흑백) + kimm_semantic(현행 §2.1 색상 팔레트 유지 — 내부 검토용)
  validators.py   # svgpathtools 기반 QA 게이트
  exporters.py    # 기존 svg2png/svg2emf/outline_svg_text 파이프라인 연결 + matplotlib SVG use-평탄화 통합
```

핵심 규칙 3건:

1. **FigureSpec 필수**: 모든 도면은 파라미터 JSON(FigureSpec)에서 생성하고, spec과 SVG를 함께 저장한다(재현성 — 파라미터 변경 시 재실행으로 전 도면 갱신. 물리 근거 벡터·경로는 수식과 파라미터를 metadata에 기록 — 모순 심화 프로토콜 P6의 근사 계층 표기와 정합).
2. **validators 게이트**: 도면 완료 보고 전에 (a) 라벨·참조부호 bbox 상호 충돌 0건 (b) leader line과 도형의 의도치 않은 교차 0건 (c) viewBox 자동 fit (d) 텍스트 글리프 커버리지(NFC 정규화, 누락 글리프 검출) 통과를 요구한다. **v14 비평 패스에서 사람이 잡던 결함(라벨 중첩, tofu)의 자동화**이며, 기하 정합(광선이 망막을 관통하는 류)은 geometry.py의 도메인 함수가 원천 차단한다.
3. **텍스트는 순수 `<text>`로 생성**: drawsvg는 glyph `<use>` 참조를 만들지 않으므로 matplotlib SVG의 PowerPoint 도형 변환 텍스트 소실 문제(Gotcha 2026-07-31, use 6,691건 평탄화 사태)가 개념도 경로에서 원천 소멸한다. PowerPoint Convert-to-Shape가 필요하면 기존 outline_svg_text.py를 최종 단계에 그대로 연결한다.

Phase 6b 에이전트(`agents/phase6b-diagram-generator.md`)와 `reference/svg-figure-creation.md` §8 워크플로우 개정:

```text
[§9 도면 목록] → [FigureSpec 작성(도면별 JSON)] → [patent_svg 생성 스크립트]
  → [validators 게이트: 0건 통과 전 완료 보고 금지]
  → [용도별 변환: PNG(HWPX) / EMF / outlined SVG(PPTX)]
손코딩 SVG는 단순 1회성 도면(구성 요소 5개 이하)의 fallback으로만 허용.
matplotlib은 정량 차트(데이터 곡선, 파라미터 스윕) 전용 — SVG 산출 시 use-평탄화를 exporters가 자동 수행.
```

## §4 P1 — 도메인 확장 (다음 실사용 건에서)

1. **광학 도메인 함수 확충**: 축소 모형안 단면, 굴절 광선 추적(파동광학 검증 스크립트의 기하 상수 재사용), 빔 다발과 초점면 — 구면 NED v17 이월 도면 3매가 첫 수요.
2. **schemdraw 통합**: 시스템 계열 청구항(아이트래커, 제어부, 구동부) 블록도와 구동 회로 — 회로 심볼을 LLM이 직접 그리지 않게 한다.
3. **interactive 스킬 동기화**: interactive의 로컬 scripts(svg2png 등)는 유지하되 patent_svg는 공유 루트(auto) 참조로 통일.

## §5 검증 계획 (사전 등록 원칙 P7 준수)

파일럿 = 구면 NED v17 이월 도면 3매(IFR-38 구성도 신설 + 파동 법칙 차트 재작성 + 이중 모드 구성도 재작도)를 patent_svg로 제작.

- 게이트 1: validators 4종 0건 통과.
- 게이트 2: 광학 전문가 비평 패스 issue 수가 v14 실적(9건) 대비 절반 이하.
- 게이트 3: HWPX 임베드와 PowerPoint 도형 변환 왕복에서 텍스트·형상 무손실.
- 게이트 4: 파라미터 1개 변경(예: 결합 규모 5x5 → 7x7) 후 재실행으로 관련 도면 전량 자동 갱신.
- 실패 시: 해당 도면 유형은 손코딩 fallback으로 남기고 실패 원인을 가이드에 기록(부정 결과 자산화 P10).

## §6 사용자 취사선택 슬롯

| # | 항목 | 비용 | 채택 여부 |
|---|------|------|----------|
| V1 | P0 — patent_svg 래퍼 신설 + Phase 6b·svg-figure-creation.md 개정 + pip 의존성 2종(drawsvg, svgpathtools) | 중(1세션) | **채택·구현 완료 (2026-08-08)** |
| V2 | 파일럿 — v17 이월 도면 3매를 신 파이프라인으로 제작(§5 게이트) | 중 | **채택·완료 (2026-08-08): 개념도 3매(기본/이중모드/7x7 변형), 게이트 1·2·4 통과, 게이트 3은 use 0건 확인·실기기 왕복은 사용자 확인 대기** |
| V3 | P1 — schemdraw 통합과 광학 도메인 확충 | 소(수요 발생 시) | (대기) |
| V4 | P2 — build123d(기계 발명용, 무거운 의존성) | 보류 권고 | (대기) |
| V5 | 미채택 확정 — Kroki/PlantUML/Manim (근거 §2) | 없음 | (대기) |

V1+V2를 함께 채택하면 v17 도면 작업(이월분)이 곧 파일럿이 되어 검증 비용이 상쇄된다. 채택분은 스킬(심링크 = my-tools 직접 반영) 수정 후 파일럿 실행으로 이어간다.

## 참고

- 입력 분석: `docs/github_svg_patent_diagram_repo_analysis_2026-08-06.md`
- 현행 가이드: `skills/patent-incubation-auto/reference/svg-figure-creation.md`
- 실측 근거: LLM_wiki `to-do/patent_spherical_NED/figures/(20260731) v14 도면 광학 전문가 검토 기록.md`(issue 9건), Gotchas "PowerPoint SVG 도형 변환 use 미지원"(2026-07-31)
