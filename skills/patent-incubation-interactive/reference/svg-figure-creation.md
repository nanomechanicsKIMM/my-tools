# SVG 발명내용설명서 도면 생성·변환 가이드

> 발명내용설명서(§9 도면 목록)와 KIMM 양식 HWPX에 임베드하기 위한 기술 도면을
> **손코딩 SVG**로 작성하고 PNG·EMF·outlined SVG 3종으로 변환하는 표준 파이프라인.
> 2026-05 micro-LED EL 검사 발명 (6개 도면, 4,095 글리프) 검증 완료.

---

## 1. 왜 손코딩 SVG인가

| 대안 | 한계 |
|------|------|
| matplotlib | 데이터 플롯 중심, 자유 레이아웃 어려움. Korean superscript U+2075 등 누락 |
| Graphviz | 그래프/네트워크 한정, freeform 도면 불가 |
| Mermaid | flowchart·sequence 한정, 기술 단면도 부적합 |
| Inkscape (GUI) | 재현 불가능, git diff 불가 |
| 외부 라이브러리 (svgwrite·drawSvg) | 추가 의존성 |
| **손코딩 SVG (Write tool)** | **의존성 0, 완전 제어, git diff 가능, 재현 가능, 무한 확대** |

LLM이 SVG XML을 직접 작성하는 것이 특허 도면 작성에 가장 효과적이다.

---

## 2. 디자인 컨벤션 (KIMM 발명 도면 표준)

### 2.1 색상 의미 팔레트 (semantic palette)

| 색 | HEX | 의미 |
|----|-----|------|
| 빨강 | `#c83232` | p 측 (positive electrode), 적색 ridge marker |
| 파랑 | `#1f6dd1` | n 측 (negative electrode), blue dashed |
| 금색 | `#d4a017` | p-pad |
| 회색 | `#aaa` | n-pad |
| 짙은 청회색 | `#2a3850` | 칩(chip) top, 어두운 본체 |
| 옅은 청색 | `#cfe0f7` ~ `#e8f0fa` | PDMS body fill |
| 진청색 | `#1f4068` | PDMS 외곽선, 굵은 윤곽 |
| 노란색 | `#ffcb47` | 활성/점등 상태 강조 |
| 주황 화살표 | `#ffaa00` | EL 광 방향, 광 신호 |
| 회색 배경 | `#ccc`, `#f0f0f0`, `#fafafa` | 기판, wafer 배경 |

### 2.2 viewBox / 크기

- viewBox: 일반 `800-980` × `480-640` (대부분 `900 × 560`)
- 상단 25–45 라인은 제목·부제 전용
- 하단 ~80 라인은 핵심 노트·범례

### 2.3 텍스트 컨벤션

- **제목**: `font-size="16" font-weight="bold" text-anchor="middle"` y=25
- **부제**: `font-size="12" fill="#555"` y=45
- **라벨**: `font-size="11-13"` (본문)
- **수식**: `font-size="11-12"` 별도 박스 (`<rect fill="#f6f6f0" stroke="#888"/>`)
- **하단 노트**: `font-size="11" fill="#000"` 또는 `#444`
- **각 `<text>` 에 font-family 명시 권장** (PowerPoint·svglib 호환성)

### 2.4 정형 패턴

| 요소 | 표준 패턴 |
|------|----------|
| 칩 그리드 | `<rect>` 3단 중첩 (chip body + p-pad + n-pad) |
| PDMS body | `<rect rx=20 fill=#cfe0f7 stroke=#1f4068>` |
| 도전 wire 단면 | `<circle r=6 fill=#c83232 (p) or #1f6dd1 (n)>` |
| 화살표 머리 | `<defs><marker>` + `marker-end="url(#arr)"` |
| 점선 | `stroke-dasharray="3 2"` 또는 `"4 2"` 또는 `"6 4"` |
| 치수선 | `<line>` 3개 (양 끝 캡 + 중간 길이) |
| 회전/Rolling 방향 | `<line>` + `<polygon>` 화살촉 |

---

## 3. SVG 기본 primitives 치트시트

```xml
<!-- viewBox로 무한 확대 보장 -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 560"
     font-family="Malgun Gothic" font-size="13">

  <!-- 화살표 marker (defs는 맨 위에) -->
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <polygon points="0,0 8,3 0,6" fill="#000"/>
    </marker>
  </defs>

  <!-- 사각형 (rounded corners 가능) -->
  <rect x="60" y="70" width="780" height="380"
        fill="#fafafa" stroke="#888" rx="0"/>

  <!-- 원 / 타원 -->
  <circle cx="450" cy="280" r="135" fill="#cfe0f7" stroke="#1f4068"/>
  <ellipse cx="200" cy="280" rx="30" ry="100" fill="#e8f0fa"/>

  <!-- 선 / 화살표 -->
  <line x1="100" y1="200" x2="500" y2="200" stroke="#c83232" stroke-width="3"
        marker-end="url(#arr)"/>

  <!-- 점선 -->
  <line x1="0" y1="0" x2="100" y2="100" stroke="#444" stroke-dasharray="4 2"/>

  <!-- 자유 형상 path -->
  <path d="M 0 0 L 100 0 L 100 30 L 80 30 L 80 60 L 50 60 L 50 30 L 0 30 Z"
        fill="#cfe0f7" stroke="#1f4068"/>

  <!-- 그룹 + transform (sub-figure 단위 이동·회전) -->
  <g transform="translate(100, 50)">
    <rect width="50" height="30" fill="#2a3850"/>
    <text x="25" y="20" font-size="11" text-anchor="middle" fill="white">chip</text>
  </g>

  <!-- 텍스트 -->
  <text x="450" y="25" text-anchor="middle" font-size="16" font-weight="bold">
    Fig. 1 — 제목
  </text>

  <!-- 회전 텍스트 (라벨) -->
  <text x="40" y="285" font-size="12" transform="rotate(-90 40 285)" text-anchor="middle">
    D_roll (예: 50 mm)
  </text>

</svg>
```

---

## 4. 작성 워크플로우 (LLM이 수행하는 순서)

```
1. 사용자 요구사항 분석 (어떤 구성요소·관계를 시각화할지)
       ↓
2. 멘탈 레이아웃 설계 (viewBox 크기, sub-figure 배치, 색상 의미)
       ↓
3. 좌표 계산 (모든 (x, y), 크기 직접 산출)
       ↓
4. XML composition (Write tool로 .svg 파일 생성)
   ├─ 4-1) Title text (y=25, font-size=16, bold, anchor=middle)
   ├─ 4-2) Subtitle text (y=45, font-size=12, fill=#555)
   ├─ 4-3) <defs> (markers, gradients) — 맨 위
   ├─ 4-4) 배경·기판 (큰 도형 먼저)
   ├─ 4-5) 중간 도형 (chips, wires, body)
   ├─ 4-6) 작은 도형 (pads, dots)
   ├─ 4-7) 연결선·화살표
   ├─ 4-8) 라벨·치수선·범례 (z-order 최상위)
   └─ 4-9) Bottom notes
       ↓
5. 시각 검증 (필요시 PNG 변환 후 사용자에게 보여줌)
       ↓
6. (선택) Korean PNG·EMF·outlined SVG 변환 (다음 §5 참조)
```

---

## 5. 3가지 변환 파이프라인

생성된 SVG는 용도에 따라 3가지 형식으로 변환된다.

### 5.1 SVG → PNG (HWPX 임베드용)

**스크립트**: `scripts/svg2png.py`

**핵심 메커니즘 (4중 방어)**:
```python
# 1. cairocffi 차단 → rlPyCairo가 pycairo(작동)로 fallback
sys.modules['cairocffi'] = None

# 2. Malgun Gothic + Arial Unicode MS 등록
pdfmetrics.registerFont(TTFont('MalgunGothic', 'C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('ArialUnicode', 'C:/Windows/Fonts/ARIALUNI.TTF'))

# 3. SVG 사전 치환 — 화살표·minus는 시각적 동등 문자로
GLYPH_REPLACE = {'↳': '→', '−': '-'}

# 4. svg2rlg() 결과 트리 walk → String 단위로 cmap 검사 + fallback 폰트 선택
def force_font(node):
    if isinstance(node, String):
        if all(ord(c) in CMAPS['MalgunGothic'] for c in node.text if c.strip()):
            node.fontName = 'MalgunGothic'
        elif all(ord(c) in CMAPS['ArialUnicode'] for c in node.text if c.strip()):
            node.fontName = 'ArialUnicode'
```

**용도**: HWPX 양식 §9 셀에 임베드 (KIMM 발명내용설명서 자동 변환 파이프라인). `convert_hwpx.py`가 이 PNG를 읽어 OOXML에 삽입.

**의존성**: `svglib`, `reportlab`, `pycairo`, `rlPyCairo`, `fonttools`

### 5.2 SVG → EMF (PowerPoint 메타파일 임포트용)

**스크립트**: `scripts/svg2emf.py`

**핵심**:
```python
# Inkscape 1.x CLI 호출
subprocess.run([
    "C:/Program Files/Inkscape/bin/inkscape.exe",
    src_svg,
    "--export-type=emf",
    f"--export-filename={dst_emf}",
])
```

**용도**: PowerPoint > 삽입 > 그림 > .emf 선택 → 그룹 해제 → 개별 shape 편집

**중요 한계**: Inkscape EMF 백엔드는 한글 텍스트를 **항상 Bezier path로 변환**한다 (CJK 글리프 호환성 보장 목적). 텍스트는 시각 보존되나 PowerPoint에서 텍스트로 편집 불가.

**의존성**: Inkscape 1.x (`winget install --id Inkscape.Inkscape`)

### 5.3 SVG → Outlined SVG (PowerPoint Convert-to-Shape용)

**스크립트**: `scripts/outline_svg_text.py`

**핵심 메커니즘**:
```python
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

font = TTFont('C:/Windows/Fonts/malgun.ttf')
cmap = font.getBestCmap()
glyph_set = font.getGlyphSet()
upem = font['head'].unitsPerEm
hmtx = font['hmtx'].metrics

# 각 문자에 대해:
for ch in text:
    gname = cmap.get(ord(ch))
    glyph = glyph_set[gname]
    pen = SVGPathPen(glyph_set)
    glyph.draw(pen)
    d = pen.getCommands()              # SVG path "d" 문자열
    adv = hmtx[gname][0]               # 자간 (font units)
    # SVG y는 top-down, glyph 좌표는 bottom-up → scale(s, -s)로 Y 반전
    transform = f"translate({x},{y}) scale({scale},{-scale})"
```

**용도**: PowerPoint > 삽입 > 그림 > .svg → 우클릭 > 그래픽 도형으로 변환 시 텍스트가 path로 보존되어 **100% 시각 보존** 보장.

**왜 이 방식이 필요한가**:
PowerPoint의 SVG-to-Shape 변환기는 Korean 텍스트를 변환 단계에서 강제로 누락시키는 알려진 버그가 있다. 다음을 시도해도 실패:
- `font-family="sans-serif"` (generic family 미지원)
- `font-family="Malgun Gothic"` 명시 (PowerPoint converter 한계)
- `@font-face` 선언 + `style=` 다중 redundancy (PowerPoint converter 한계)

유일한 100% 작동 방식 = **텍스트를 SVG `<path>` 로 미리 변환** → PowerPoint는 변환할 텍스트가 없으므로 누락 불가.

**의존성**: `fonttools` (이미 reportlab/svglib와 함께 설치됨)

**3단 폰트 fallback**:
- 1차: Malgun Gothic (Korean + 99% BMP)
- 2차: Malgun Gothic Bold (font-weight=bold 시)
- 3차: Arial Unicode MS (100% BMP coverage — 3개 누락 글리프 `↳ − ≈` 대응)

---

## 6. 기술적 함정·주의사항

| 항목 | 함정 | 해결 |
|------|------|------|
| **cairocffi DLL 부재 (Windows)** | rlPyCairo가 cairocffi 우선 import → libcairo-2.dll 미발견 → renderPM 깨짐 | `sys.modules['cairocffi'] = None` 으로 차단 → pycairo로 fallback |
| **svglib 폰트 매핑** | SVG `font-family="sans-serif"` → reportlab의 Helvetica로 fallback → 한글 □□□ | svg2rlg() 결과 트리 walk + String.fontName 강제 override |
| **누락 글리프** | Malgun Gothic이 `↳ − ≈` 3개 누락 (99% 커버) | Arial Unicode MS fallback (100%) + SVG 사전 치환 |
| **PowerPoint Korean 변환 버그** | font-family·@font-face 모두 무시, Korean text 누락 | **텍스트→path outline (Option B)** 으로 우회 |
| **style 속성 quote 중첩** | XML `attr=""` 안에 CSS `font-family:"..."` → quote 충돌 | style 내부는 single-quote: `style="font-family:'Malgun Gothic','맑은 고딕'"` |
| **NFC vs NFD 한글** | 분해형(NFD) 한글이 일부 도구에서 인식 안 됨 | `unicodedata.normalize('NFC', text)` |
| **SVG Y축** | TTF glyph는 bottom-up, SVG는 top-down | `scale(s, -s)` transform으로 Y 반전 |
| **text-anchor 조정** | middle/end 위치 보정 | total_width × scale 계산 후 x 조정 |
| **PowerPoint SVG 삽입 요구** | Office 2019 이상 + SVG insert 기능 | Office 365 또는 2019/2021 권장 |

---

## 7. 6개 도면 통계 (참조)

micro-LED EL 검사 발명 예시:

| 파일 | XML 라인 | text 개수 | path 개수 (outline 후) |
|------|---------|---------|---------------------|
| fig1_top_view_contact_pattern.svg | ~160 | 23 | 740 |
| fig2_side_view_rolling_direction.svg | ~80 | 16 | 551 |
| fig3_axial_cross_section.svg | ~90 | 15 | 424 |
| fig4_single_chip_closeup.svg | ~100 | 42 | 1,077 |
| fig5_self_aligning_ridge.svg | ~110 | 20 | 838 |
| fig6_roll_circumferential_lines.svg | ~80 | 18 | 465 |

평균: 텍스트 1개당 약 30 glyph paths 생성.

---

## 8. 권장 통합 workflow (Phase 6b 적용)

```
[Phase 6 출력 — 발명내용설명서 MD §9 도면 목록]
        ↓
[Phase 6b: 도면 생성]
  ├─ 옵션 1: 손코딩 SVG (LLM이 Write tool로 직접 작성)
  │   ├─ 디자인 컨벤션 §2 적용
  │   ├─ Primitives §3 활용
  │   └─ 워크플로우 §4 따라
  │
  └─ 옵션 2: matplotlib PNG (데이터 플롯 한정)
  
        ↓
[변환 파이프라인 — 용도별 분기]
  ├─ HWPX 임베드 → scripts/svg2png.py
  ├─ PowerPoint metafile → scripts/svg2emf.py (Inkscape 필요)
  └─ PowerPoint Convert-to-Shape → scripts/outline_svg_text.py ⭐
        ↓
[최종 산출물]
  ├─ figures/fig*.svg (원본)
  ├─ diagrams/fig*.png (HWPX용 — matplotlib PNG와 공용 취합 폴더)
  ├─ figures/emf/fig*.emf (PowerPoint 그림용)
  └─ figures/pptx/fig*.svg (PowerPoint 도형 변환용, outlined)
```

---

## 9. 관련 자원

- 검증 발명: micro-LED COW/COC 고속 EL 전수 검사 (KIMM, 2026-05)
- 검증 디렉토리: `LLM_wiki/to-do/patent_micro-LED_EL_test/figures/`
- 변환 파이프라인 통합: `scripts/convert_hwpx.py` (PNG 임베드)
- 관련 reference: `hwpx-format-insights.md` (HWPX paraPrIDRef·intent 규칙)
