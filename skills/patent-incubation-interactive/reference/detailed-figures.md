# 상세·실척 기술 도면 작성 지침 (matplotlib 계산 기반)

2026-07-16 신설 — 구면 Maxwellian NED v12 실전(도면 15종 전면 재생성)에서 도출.
공동 발명자 회람에서 "상세한 디테일이 생략되어 이해가 어렵다"는 지적을 받은 개념도(박스+화살표 수준)를
**실척(real-scale)·물리 계산 기반 도면**으로 끌어올리는 방법. `patent-incubation-auto`와
`patent-incubation-interactive`가 공유한다.

## 1. 언제 이 모드를 쓰나 (Step 3 손코딩 SVG와의 분업)

- 발명이 **기하·광학·역학·열 등 물리 배치**로 정의될 때 — 실척 단면이 곧 발명의 설명임
  (예: 구면 패널-안구 기하, 광선 수렴, 소자 적층)
- **정량 주장(모순·한계·동작점)이 명세서 논거의 중심**일 때 — 수치 차트가 필수
- 사용자가 "상세하게/현실적으로"를 요구하거나, 회람 의견으로 디테일 부족이 지적되었을 때
- 반대로 절차 흐름·시스템 블록·간단 비교는 기존 Mermaid / 손코딩 SVG(Step 3)로 충분 —
  이 모드는 대체가 아니라 **물리계 발명용 1차 경로 승격**이다.

## 2. 핵심 원칙 5

1. **실척 좌표계**: 축 단위를 실제 물리 단위(mm 등)로 잡고, 구성요소 치수는 문헌·명세서 값을 그대로 쓴다.
   예(안구 단면): 각막 곡률 7.8 mm, 각막-회전중심 13 mm, 안구 반경 12 mm, 동공면 = 각막 후방 3 mm,
   수정체·망막·중심와를 모두 그린다. 실척이면 "그림이 맞는지"를 치수로 검증할 수 있다.
2. **광선·궤적은 손으로 긋지 않고 계산으로**: 원뿔 반각, paraxial 굴절(축소 눈 60 D:
   `slope' = slope − h·P`, P=0.06/mm) 같은 간단한 물리 모델을 코드에 넣어 광선이 스스로 맞게
   그려지게 한다. 도면 작성이 곧 수치 검산(sanity check)이 된다.
3. **소자 단면은 전 기능층 적층 + 재료 표기**: 기판/방열층/하부 DBR(재료쌍·층수)/발광층/상부 DBR/
   전극/봉지/격벽처럼 §6 소재 문단과 1:1 대응하도록 그린다. 층 무늬(줄), 두께 비례, 재료명 라벨.
4. **정량 주장은 차트로**: 상충·한계는 로그축 곡선 + 요구 수준선(점선) + 동작점 마커로 시각화한다.
   차트의 계산식과 본문 §6/§9 수치가 일치해야 한다(내부 정합 — critic 공격 방어).
5. **도메인 프리미티브 헬퍼 모듈**: `fig_common.py` 패턴 — 팔레트 상수(종래=적색계, 본 발명=청색계),
   반복 도메인 요소(draw_eye, draw_panel, cone, arrow, box, 굴절 함수)를 공통 모듈로 두고,
   도면 스크립트는 5매 단위 배치 파일로 분할한다(실패 반경 축소, 부분 재실행 용이).

## 3. 규격·스타일

- matplotlib `Agg`, 흰색 배경, `plt.rcParams["font.family"] = "Malgun Gothic"`,
  `axes.unicode_minus = False`
- 크기: **figsize (11~14, 5~8) in × dpi 300 → 폭 약 3300 px**. 소형 figsize×600 dpi와 픽셀 수는
  같지만 300 dpi 대형 figsize 쪽이 폰트 크기(pt) 제어가 쉽다. HWPX 삽입 화질 동등.
- 폰트 크기: 본문 라벨 10~11.5, 패널 제목 11~12, suptitle 13~15 — 인쇄 축소를 견디는 크기.
- 다중 패널: `subplots`/`gridspec`으로 (a)(b)(c) 병렬 + suptitle. 보조 정량 곡선은 `inset_axes`.
- 라벨은 **부품 이름 텍스트만** — 참조 부호(10, 100 등)·"[도 N]" 금지(도면 번호·부호 미사용 정책).

## 4. 함정 (v12 실전 시행착오)

- **Malgun Gothic 글리프 누락**: `≈`(U+2248)·`−`(U+2212)·`·` 등 특수문자는 두부 문자로 렌더됨.
  "약", "x", ASCII 하이픈으로 대체. 실행 로그의 "Glyph missing" 경고는 반드시 해결.
- **로그축 tick의 mathtext 마이너스**: 로그축이 10^-1 형태(U+2212 포함)로 tick을 렌더할 수 있음 →
  `FixedLocator([0.1, 0.3, 1, 3]) + FuncFormatter(lambda v, p: f"{v:g}") + NullFormatter(minor)`로
  plain 숫자를 강제.
- **annotate와 제목·범례 겹침**: `set_ylim`으로 상단 headroom을 확보한 뒤 빈 영역에 텍스트를 두고
  화살표로 대상을 가리킨다. 데이터 좌표(textcoords="data")가 offset points보다 예측 가능.
- **광선 과다·무한 연장 금지**: 광선은 5~9개로 제한하고 물리 경계(망막 등)에서 클리핑한다.
  전부 그리면 도면이 실타래가 된다.

## 5. 육안 검증 루프 (필수)

렌더 → **Read 도구로 PNG를 직접 열어** 겹침·잘림·글리프 깨짐·방향 오류를 확인 → 수정 → 재렌더.
최소한 핵심 도면(시스템 기하, 정량 차트, 신규 개념도)은 반드시 육안 확인한다.
v12 실전에서 15종 중 3건(광선 과다 1, 주석-제목 충돌 2)이 이 루프에서 발견·수정되었다.

## 6. 산출·파이프라인 통합 (기존 규칙과의 접속)

- `save()`에서 **PNG(diagrams/, dpi 300)와 SVG(figures/)를 동시 저장**한다.
  `plt.rcParams["svg.fonttype"] = "path"` — 텍스트가 이미 path로 아웃라인되므로
  `outline_svg_text.py` 단계가 불필요하고 PowerPoint 한글 SVG 버그도 회피된다.
- **덱 조립**: PowerPoint COM `Shapes.AddPicture(SVG)`로 figures_deck.pptx 조립
  (편집 가능 — PNG 래스터 삽입 금지 규칙 충족). 슬라이드 N = 도면 N 1:1, 표지 없음,
  캡션은 내용 제목만. 조립 후 zip으로 `ppt/slides/slide*.xml` 수와 `ppt/media/*.svg` 파트 수를 검증.
- **HWPX 삽입**: `diagrams/*.png` + `captions.json`(파일명 → 내용 기반 제목) →
  `convert_hwpx.py --diagrams`. 파일명은 `fig01_`, `fig02_`처럼 **zero-pad**하여 정렬 순서를 보장.

## 7. 최소 골격 (fig_common.py 패턴)

```python
# -*- coding: utf-8 -*-
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "path"      # 덱용 SVG 텍스트 아웃라인

BLUE, RED = "#1A5FB4", "#C0392B"           # 본 발명 / 종래 팔레트
OUT_PNG, OUT_SVG = "diagrams", "figures"

def save(fig, name, dpi=300):
    fig.savefig(os.path.join(OUT_PNG, name), dpi=dpi, facecolor="white", bbox_inches="tight")
    fig.savefig(os.path.join(OUT_SVG, name.replace(".png", ".svg")),
                facecolor="white", bbox_inches="tight")
    plt.close(fig)

# 도메인 프리미티브 예: 실척 안구 단면 (mm, 회전중심 = 원점)
def draw_eye(ax, gaze_deg=0.0):
    """공막 원(r=12) + 각막 원호(곡률 7.8, 정점 x=-13) + 동공면(x=-10) + 수정체 + 망막 + 중심와 + 회전중심."""
    ...

# 물리 계산 예: 축소 눈 paraxial 굴절 (60 D)
def refract_at_cornea(pixel, target=(0, 0), P=0.06, cornea_x=-13.0):
    x0, y0 = pixel; m0 = (target[1]-y0)/(target[0]-x0)
    h = y0 + m0*(cornea_x - x0)
    return h, m0, m0 - h*P
```
