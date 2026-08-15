---
title: 물리 법칙 기반 특허·공학 설계 SVG 개념도 생성용 GitHub 레포 분석
created: 2026-08-06
tags:
  - github
  - svg
  - patent-drawing
  - engineering-design
  - physics-based-diagram
---

# 물리 법칙 기반 SVG 개념도 생성 레포 분석

## 1. 목적과 평가 기준

목표는 특허 명세서·공학 설계 문서에 삽입할 수 있는 **개념도 SVG**를 자동 생성하는 데 적합한 오픈소스 GitHub 레포를 찾는 것이다. 여기서 "물리 법칙 기반"은 단순 이미지 생성이 아니라 다음 입력을 코드로 받아 도면 위치·형상·화살표·궤적을 결정할 수 있음을 뜻한다.

- 좌표, 치수, 각도, 반경, 간격, 곡률
- 힘, 변위, 속도, 전류, 전압, 유량, 열 흐름 등 벡터/스칼라 물리량
- 광선, 전기장/자기장, 유선, 파동, 기구 운동 경로
- 부품 간 조립 관계, 단면, 투영, hidden/visible edge
- 특허 도면에 필요한 흑백 선도, 참조부호, 간결한 라벨, 구성요소 계층

평가 기준:

| 기준 | 의미 |
|---|---|
| SVG 직접성 | SVG를 직접 쓰거나 안정적으로 SVG 출력이 가능한가 |
| 물리·기하 제어성 | 수식/파라미터/좌표 기반으로 도면을 재현할 수 있는가 |
| 특허 도면 적합성 | 흑백 선, 화살표, 라벨, 참조부호, 단순화된 형상 제어가 쉬운가 |
| 공학 설계 적합성 | 기계/CAD/회로/시스템/수치 결과를 다룰 수 있는가 |
| 유지보수성 | 최근 push/release, 테스트/문서/사용자 규모가 충분한가 |
| 라이선스 리스크 | 기관 내부 활용·배포 시 부담이 낮은가 |

## 2. 최종 추천

### 추천 1: `drawsvg` 중심 파이프라인

**가장 적합한 기본 엔진은 [cduck/drawsvg](https://github.com/cduck/drawsvg)이다.** Python에서 SVG primitive를 직접 생성하고 `save_svg()`로 저장할 수 있다. README와 코드에서 `Drawing`, `Path`, `Line`, `Arc`, `Text`, marker 기반 화살표, Jupyter 표시, SVG/PNG 저장 기능을 확인했다.

권장 구조:

```text
설계 파라미터/물리식 계산
-> 좌표·곡선·벡터·부품 배치 데이터 생성
-> drawsvg로 흑백 SVG 구성
-> svgpathtools로 path 검증/후처리
-> 필요 시 HWPX/PPTX/PNG 변환
```

왜 적합한가:

- 특허 도면은 사실상 "정확한 벡터 선도 + 라벨 + 화살표 + 단순화된 부품 형상"이다.
- `drawsvg`는 SVG를 최종 산출물로 직접 다루므로 불필요한 rasterization이 없다.
- 물리 엔진은 없지만, 물리식 계산 결과를 좌표로 변환하는 것은 Python/Numpy로 분리하는 편이 더 견고하다.
- 특허 도면의 표준화, 예를 들어 stroke width, black-only style, font size, marker, viewBox를 코드 규칙으로 고정하기 쉽다.

주의할 점:

- CAD kernel이나 FEM/rigid-body solver가 아니다.
- 복잡한 3D 부품 단면은 `build123d` 또는 `CadQuery`에서 만든 뒤 SVG 선도화하는 편이 낫다.
- 텍스트 배치 충돌, 참조부호 자동 회피, leader line 정렬 같은 특허 도면 특화 기능은 별도 wrapper를 만들어야 한다.

### 추천 2: `drawsvg + svgpathtools`

[mathandy/svgpathtools](https://github.com/mathandy/svgpathtools)는 SVG path와 Bezier curve의 읽기, 쓰기, 분석, 교차, curvature, bounding box, arc length 등을 제공한다. 자체가 도면 생성 프레임워크라기보다는 **검증·후처리 엔진**이다.

특허 도면에서 유용한 지점:

- 화살표 leader line이 구성요소와 교차하는지 검사
- 곡선 경로의 bounding box를 계산해 viewBox 자동 조정
- 유선/광선/전기장 선의 path 길이와 방향을 검증
- imported SVG path를 정리하고 단순화하기 위한 중간 처리

권장 사용 위치:

```text
drawsvg 생성 SVG
-> svgpathtools로 path intersection, bbox, curvature check
-> 라벨/화살표 충돌 보정
-> final SVG 저장
```

### 추천 3: 기계·부품·단면은 `build123d` 또는 `CadQuery`

[gumyr/build123d](https://github.com/gumyr/build123d)는 Open Cascade 기반의 Pythonic CAD-as-code 도구다. README와 예제에서 1D/2D/3D shape, BREP, sketch, extrusion, projection, `ExportSVG` 사용 예제를 확인했다. Apache-2.0 라이선스라 기관 내부 활용에도 부담이 낮다.

[CadQuery/cadquery](https://github.com/CadQuery/cadquery)는 더 성숙한 Python parametric CAD framework이다. 코드에서 `cadquery/occ_impl/exporters/svg.py`의 `getSVG()`와 visible/hidden edge projection 처리를 확인했다. STEP/DXF/STL 등 CAD 포맷 출력이 강하다.

선택 기준:

- 새 프로젝트에서 Pythonic하고 readable한 CAD-as-code를 원하면 `build123d`
- 기존 CadQuery 생태계, CQ-editor, STEP/DXF 워크플로우가 필요하면 `CadQuery`
- 최종 특허 도면의 라벨·화살표·참조부호는 CAD 출력 후 `drawsvg`로 얹는 방식 추천

## 3. 10개 레포 상세 분석

### 1. cduck/drawsvg

- URL: <https://github.com/cduck/drawsvg>
- 언어: Python
- 라이선스: MIT
- 별: 693
- 최근 push: 2026-07-29
- 확인 내용: README, `drawsvg/drawing.py`, examples/docs 디렉터리

핵심 기능:

- Python 코드로 SVG vector image와 animation 생성
- `Drawing`, `Path`, `Line`, `Circle`, `Arc`, `Text`, marker 등 SVG primitive 사용
- `as_svg()`, `save_svg()`, `save_png()` 등 출력 함수 존재
- Jupyter inline 표시 지원

장점:

- SVG 직접 생성성이 가장 높다.
- 특허 도면의 흑백 선, 화살표, 라벨, 간단한 단면도 구현에 적합하다.
- 물리식 계산 결과를 좌표로 넘기면 도면이 완전히 재현 가능하다.
- 의존성이 상대적으로 가볍고 MIT 라이선스다.

단점:

- 물리 엔진, CAD kernel, 자동 레이아웃 엔진은 아니다.
- 라벨 충돌 회피, 참조부호 규칙, 도면 번호 규칙은 직접 구현해야 한다.
- 복잡한 3D 투영이나 hidden line 처리는 부적합하다.

특허 SVG 적합도: **A**

추천 역할: **최종 SVG 렌더링 엔진**

### 2. mathandy/svgpathtools

- URL: <https://github.com/mathandy/svgpathtools>
- 언어: Python
- 라이선스: MIT
- 별: 636
- 최근 push: 2025-11-30
- 확인 내용: README, examples/test 디렉터리, `svgpathtools/paths2svg.py`

핵심 기능:

- SVG Path와 Bezier curve 읽기/쓰기/분석
- tangent, normal, curvature, intersection, bounding box, arc length 계산
- `wsvg()`, `disvg()`, `paths2Drawing()` 계열 함수 확인

장점:

- 도면의 geometry QA에 좋다.
- 물리 기반 경로, 예를 들어 광선, 유선, 전하 이동 경로를 곡선 path로 표현할 때 검증이 가능하다.
- 기존 SVG를 읽고 path 단위로 분석할 수 있다.

단점:

- 처음부터 예쁜 특허 도면을 만드는 상위 API는 아니다.
- shape primitive나 라벨 시스템은 `drawsvg`보다 약하다.
- 내부적으로 `svgwrite` 의존이 있어 장기적으로 wrapper 레벨에서 의존성 관리를 해야 한다.

특허 SVG 적합도: **A-**

추천 역할: **SVG path 검증·후처리**

### 3. gumyr/build123d

- URL: <https://github.com/gumyr/build123d>
- 언어: Python
- 라이선스: Apache-2.0
- 별: 2,796
- 최신 release: v0.11.1, 2026-07-02
- 최근 push: 2026-08-05
- 확인 내용: README, docs/examples/src/tests 구조, `examples/packed_boxes.py`

핵심 기능:

- Open Cascade 기반 BREP CAD-as-code
- 1D edge/wire, 2D face/sketch, 3D solid/part 모델링
- example에서 `project_to_viewport()`와 `ExportSVG` 기반 SVG projection 사용 확인

장점:

- 치수·형상·단면·조립 관계가 중요한 기계 특허에 매우 적합하다.
- Python 코드로 부품 파라미터를 바꾸면 도면도 재생성할 수 있다.
- Apache-2.0이라 라이선스 리스크가 낮다.
- 최근 유지보수와 릴리즈가 활발하다.

단점:

- 특허 명세서용 라벨, 참조부호, leader line은 별도 레이어로 얹어야 한다.
- CAD 설치 의존성이 `drawsvg`보다 크다.
- 개념도보다는 실제 형상 모델링에 강하다.

특허 SVG 적합도: **A-**

추천 역할: **기계/부품/단면 형상 생성 후 SVG 투영**

### 4. CadQuery/cadquery

- URL: <https://github.com/CadQuery/cadquery>
- 언어: Python
- 라이선스: Apache-2.0 계열로 확인
- 별: 5,561
- 최신 release: v2.8.0, 2026-06-20
- 최근 push: 2026-07-31
- 확인 내용: README, examples/doc/tests 구조, `cadquery/occ_impl/exporters/svg.py`

핵심 기능:

- OCCT 기반 parametric 3D CAD scripting
- STEP, DXF, STL 등 CAD 출력
- `getSVG()` 코드에서 visible/hidden edge 분리, projection direction, stroke width, hidden line style 등의 SVG exporter 옵션 확인

장점:

- 성숙도와 사용자 기반이 크다.
- 3D 부품을 실제 CAD 모델로 만든 뒤 특허용 투영선을 뽑기 좋다.
- hidden line, projection, bounding box 등 도면화에 필요한 기반이 있다.

단점:

- 설치와 실행 환경이 상대적으로 무겁다.
- 개념도 라벨링과 스타일링은 CAD exporter만으로 충분하지 않다.
- 순수 SVG 개념도 생성에는 `drawsvg`보다 생산성이 낮다.

특허 SVG 적합도: **B+**

추천 역할: **정밀 3D CAD 원천 모델과 hidden/visible line projection**

### 5. cdelker/schemdraw

- URL: <https://github.com/cdelker/schemdraw>
- 언어: Python/Jupyter Notebook 중심
- 라이선스: MIT
- 별: 256
- 최근 push: 2026-07-18
- 확인 내용: README, docs/test/schemdraw 구조

핵심 기능:

- 전기 회로 schematic 생성
- 저항, capacitor, diode, transistor, opamp, signal processing element 지원
- README 예제에서 `schemdraw.Drawing(file='schematic.svg')`로 SVG 저장 확인
- timing diagram, state machine, flowchart도 지원

장점:

- 전자회로, 센서, 구동회로, 신호처리 블록 특허 도면에 바로 쓸 수 있다.
- 회로 심볼과 연결 규칙이 이미 있어 LLM이 직접 그리는 것보다 오류가 적다.
- MIT 라이선스이며 Python 기반이다.

단점:

- 기계/광학/유체/열 설계 개념도에는 범위가 좁다.
- 특허용 참조부호 스타일은 별도 조정이 필요하다.
- primary language가 Jupyter Notebook으로 표시되어 패키지 메타데이터만 보면 작게 보일 수 있다.

특허 SVG 적합도: **B+**

추천 역할: **회로·신호·제어 블록 특허 도면**

### 6. matplotlib/matplotlib

- URL: <https://github.com/matplotlib/matplotlib>
- 언어: Python
- 라이선스: Matplotlib License
- 별: 23,063
- 최신 release: v3.11.1, 2026-07-18
- 최근 push: 2026-08-05
- 확인 내용: README, gallery/doc/lib 구조, SVG 관련 examples 검색

핵심 기능:

- Python 정적/동적/인터랙티브 visualization
- publication-quality figure 출력
- SVG backend와 `savefig(...svg)` 워크플로우

장점:

- 수치 계산 결과를 도면화하는 데 가장 안정적이다.
- 벡터장, 등고선, 궤적, 파라미터 sweep, 실험 데이터 기반 설계 그림에 강하다.
- 문서, 예제, 유지보수성이 매우 좋다.

단점:

- 기본 output은 논문 그래프 스타일이지 특허 개념도 스타일은 아니다.
- 라벨과 화살표가 많아지면 수동 layout 조정이 필요하다.
- SVG DOM 구조가 사람이 편집하기에는 복잡할 수 있다.

특허 SVG 적합도: **B**

추천 역할: **물리 계산 결과, vector field, trajectory, contour 기반 보조 도면**

### 7. ManimCommunity/manim

- URL: <https://github.com/ManimCommunity/manim>
- 언어: Python
- 라이선스: MIT
- 별: 39,895
- 최신 release: v0.20.1, 2026-02-27
- 최근 push: 2026-08-05
- 확인 내용: README, docs/example_scenes/tests 구조

핵심 기능:

- 수학 설명 애니메이션 엔진
- 좌표계, 도형, transform, animation primitive
- explanatory physics/math video에 강함

장점:

- 물리 원리 설명용 장면 설계에 강하다.
- LLM이 "현상 설명 그림"을 생성할 때 구조화된 scene abstraction을 제공한다.
- 복잡한 작동 원리를 순차적으로 이해시키는 보조 애니메이션에는 좋다.

단점:

- 특허 명세서용 정적 SVG 최종본 생성에는 과하다.
- 영상/장면 중심이라 흑백 선도, 참조부호, 도면 스타일을 맞추려면 별도 제약이 필요하다.
- CAD 치수 정확도나 hidden line 도면화 도구는 아니다.

특허 SVG 적합도: **B-**

추천 역할: **발명 원리 설명 애니메이션 또는 내부 검토용 시각화**

### 8. Matheart/manim-physics

- URL: <https://github.com/Matheart/manim-physics>
- 언어: Python
- 라이선스: GitHub metadata상 미표시
- 별: 402
- 최근 push: 2024-08-01
- 확인 내용: README, docs/tests/manim_physics 구조

핵심 기능:

- Manim 기반 2D physics simulation plugin
- rigid mechanics, electromagnetism, wave 등 물리 장면 생성

장점:

- 물리 현상 시각화에는 주제 적합성이 높다.
- Manim과 결합하면 장면 설명력이 좋다.

단점:

- README에서 유지보수 여력 부족을 직접 언급한다.
- 라이선스가 GitHub metadata상 확인되지 않아 기관 재사용 전 확인 필요하다.
- 최종 특허 SVG 도면용보다 교육/애니메이션용에 가깝다.

특허 SVG 적합도: **C+**

추천 역할: **초기 물리 현상 시각화 참고. 최종 도면 엔진으로는 비추천**

### 9. yuzutech/kroki

- URL: <https://github.com/yuzutech/kroki>
- 언어: JavaScript 중심
- 라이선스: MIT
- 별: 4,271
- 최신 release: v0.32.0, 2026-08-03
- 최근 push: 2026-08-05
- 확인 내용: README.adoc, server/modules/docs 구조

핵심 기능:

- 여러 diagram-as-code 도구를 통합 API로 SVG 등으로 출력
- PlantUML, Graphviz, Mermaid, WaveDrom, WireViz, Bytefield, D2 등 지원

장점:

- 시스템 구성도, 신호 흐름, sequence, timing, protocol, block diagram을 빠르게 SVG로 만들 수 있다.
- 여러 문법을 한 API에서 다룰 수 있어 자동화 파이프라인이 깔끔하다.
- 최근 릴리즈와 유지보수가 활발하다.

단점:

- 물리식 기반 좌표/기하 제어에는 부적합하다.
- 특허 도면에서 요구하는 개별 선/라벨 위치 제어는 제한적이다.
- 외부 서버/API 방식으로 쓰면 보안·재현성 이슈가 있어 self-host가 낫다.

특허 SVG 적합도: **C+**

추천 역할: **시스템 블록도, 공정 흐름도, timing diagram 보조 생성**

### 10. plantuml/plantuml

- URL: <https://github.com/plantuml/plantuml>
- 언어: Java
- 라이선스: LGPL-3.0
- 별: 13,226
- 최신 release: v1.2026.6, 2026-06-08
- 최근 push: 2026-08-05
- 확인 내용: README, docs/site/src 구조

핵심 기능:

- 텍스트 설명에서 UML 및 비UML 다이어그램 생성
- sequence, class, activity, state, timing, network, WBS, mindmap 등 지원

장점:

- 공정 순서, 제어 플로우, 시스템 구성, 상태 전이 특허 도면에 빠르다.
- 문법이 널리 알려져 있고 자동 생성이 쉽다.
- SVG 출력 생태계가 충분하다.

단점:

- 물리적 형상, 기하, 힘/광선/유동 경로를 정확히 배치하는 데는 약하다.
- 자동 layout 결과가 특허 도면용으로 항상 깔끔하지 않다.
- LGPL 조건을 내부 배포/제품화 관점에서 확인해야 한다.

특허 SVG 적합도: **C**

추천 역할: **방법 흐름도, 제어 상태도, 시스템 개념도**

## 4. 제외 또는 보조 후보

### mozman/svgwrite

- URL: <https://github.com/mozman/svgwrite>
- README와 repo description에서 inactive/unmaintained 성격을 확인했다.
- SVG 생성 자체는 단순하고 의존성이 적지만, 신규 특허 도면 자동화 엔진으로는 `drawsvg`가 더 적합하다.
- `svgpathtools` 내부 의존으로 간접 사용될 수는 있다.

### pyx-project/pyx

- URL: <https://github.com/pyx-project/pyx>
- PostScript/PDF/SVG와 TeX/LaTeX 연계가 강한 과학 도식 도구다.
- GPL-2.0 라이선스와 상대적으로 좁은 생태계 때문에 기관 내부의 범용 특허 도면 자동화 기본 엔진으로는 우선순위가 낮다.

## 5. 적용 시나리오별 추천

| 시나리오 | 추천 조합 | 이유 |
|---|---|---|
| 일반 특허 개념도: 부품, 화살표, 라벨, 효과 흐름 | `drawsvg` | SVG primitive 직접 제어가 가장 중요 |
| 광선/유선/전기장/파동 경로 | `drawsvg + svgpathtools + numpy/scipy` | path 생성과 path 검증을 분리 |
| 기계 부품 단면, 조립 구조, hidden edge | `build123d -> SVG projection -> drawsvg annotation` | CAD 형상과 특허 라벨을 분리 |
| 기존 CAD/STEP/DXF 연동 | `CadQuery -> SVG/DXF -> drawsvg cleanup` | 성숙한 CAD 생태계 활용 |
| 회로·센서·전극 구동도 | `schemdraw + drawsvg` | 회로 심볼은 전용 도구가 안전 |
| 수치 결과 기반 설계 원리 | `matplotlib -> SVG -> drawsvg cleanup` | 계산 결과 시각화 안정성 |
| 공정 흐름·제어 상태·시스템 블록도 | `Kroki` 또는 `PlantUML` | diagram-as-code 자동 layout |
| 물리 현상 애니메이션 | `Manim`, 필요 시 `manim-physics` | 정적 특허 도면보다는 설명 영상용 |

## 6. 특허용 SVG 생성기 설계 제안

추천 구현은 `drawsvg`를 중심으로 한 얇은 도메인 wrapper이다.

```text
patent_svg/
  geometry.py       # 물리식, 좌표계, 변환, 단위
  primitives.py     # plate, layer, beam, lens, electrode, channel 등 특허 primitive
  annotations.py    # 참조부호, leader line, arrow, label collision
  styles.py         # black-only, stroke width, font, marker 규칙
  validators.py     # svgpathtools 기반 bbox/intersection/readability QA
  exporters.py      # svg, png, pptx/hwpx 변환용 후처리
```

핵심 규칙:

- 모든 도면은 `FigureSpec` JSON/YAML에서 생성한다.
- 입력 파라미터와 출력 SVG를 같이 저장해 재현성을 확보한다.
- 특허 제출용 기본 style은 흑백, fill 없음 또는 hatch, 일정 stroke width로 제한한다.
- 참조부호는 사람이 읽는 라벨과 분리하고, leader line의 교차를 QA한다.
- 물리 근거가 있는 벡터/경로는 식과 파라미터를 metadata에 남긴다.

예시 `FigureSpec`:

```yaml
figure_id: fig_1
title: stacked electrode force focusing structure
canvas:
  width: 1200
  height: 800
style: patent_bw
parameters:
  electrode_gap_um: 20
  field_angle_deg: 35
objects:
  - type: substrate
    ref: 110
  - type: patterned_electrode
    ref: 120
  - type: force_vector_field
    equation: E = -grad(V)
annotations:
  - ref: 120
    label: electrode pattern
```

## 7. 최종 판단

최종 추천은 다음과 같다.

1. **기본 엔진: `cduck/drawsvg`**
2. **검증·후처리: `mathandy/svgpathtools`**
3. **기계/CAD 보조: `gumyr/build123d` 우선, 기존 CadQuery 자산이 있으면 `CadQuery/cadquery`**
4. **회로 도면 보조: `cdelker/schemdraw`**
5. **수치·물리 결과 보조: `matplotlib/matplotlib`**
6. **흐름도/시스템도 보조: `yuzutech/kroki` 또는 `plantuml/plantuml`**

특허용 개념도 SVG 파일을 안정적으로 도출하려면, Manim류처럼 장면을 렌더링하는 도구보다 `drawsvg`처럼 SVG DOM을 직접 제어하는 도구가 더 적합하다. 물리 법칙은 그림 엔진에 내장시키기보다 Python 계산 계층에서 좌표·path·벡터로 변환하고, SVG 엔진은 이를 정확하게 그리는 책임만 갖게 하는 구조가 가장 유지보수성이 높다.

## 8. 확인한 주요 소스

- cduck/drawsvg: <https://github.com/cduck/drawsvg>
- drawsvg drawing API: <https://github.com/cduck/drawsvg/blob/master/drawsvg/drawing.py>
- mathandy/svgpathtools: <https://github.com/mathandy/svgpathtools>
- svgpathtools SVG writer: <https://github.com/mathandy/svgpathtools/blob/master/svgpathtools/paths2svg.py>
- gumyr/build123d: <https://github.com/gumyr/build123d>
- build123d SVG example: <https://github.com/gumyr/build123d/blob/dev/examples/packed_boxes.py>
- CadQuery/cadquery: <https://github.com/CadQuery/cadquery>
- CadQuery SVG exporter: <https://github.com/CadQuery/cadquery/blob/master/cadquery/occ_impl/exporters/svg.py>
- cdelker/schemdraw: <https://github.com/cdelker/schemdraw>
- matplotlib/matplotlib: <https://github.com/matplotlib/matplotlib>
- ManimCommunity/manim: <https://github.com/ManimCommunity/manim>
- Matheart/manim-physics: <https://github.com/Matheart/manim-physics>
- yuzutech/kroki: <https://github.com/yuzutech/kroki>
- plantuml/plantuml: <https://github.com/plantuml/plantuml>
- mozman/svgwrite: <https://github.com/mozman/svgwrite>
- pyx-project/pyx: <https://github.com/pyx-project/pyx>
