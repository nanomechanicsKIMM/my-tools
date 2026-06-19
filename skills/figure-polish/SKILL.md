---
name: figure-polish
description: "matplotlib로 만든 과학·기술 도표를 전문 디자이너 수준으로 다듬고(Pretendard 폰트, 인쇄 가독성 폰트 크기, 순수 색 배치, 레이아웃 정돈) 편집 가능한 PowerPoint(pptx) 슬라이드로 변환하는 워크플로우 스킬. '그림 개선', '도표 다듬기', '그림 폰트 키우기', '논문 그림 정리', '그림 디자인', 'figure polish', 'pptx 변환', '편집 가능한 슬라이드', 'matplotlib 그림 다듬기', '도표 색 순수 원색', '그림 가독성' 등의 키워드가 나오면 이 스킬을 사용할 것."
---

# figure-polish — 과학 도표 다듬기 + pptx 변환 워크플로우

matplotlib로 생성하는 과학·기술 도표(보통 `make_figN_*.py` 형태)를 ① 인쇄 가독성 높은
타이포그래피·색·레이아웃으로 다듬고, ② 편집 가능한 PowerPoint 슬라이드(네이티브 도형/텍스트/표)
로 변환하는 절차를 제공한다.

## 핵심 원칙

- **검증된 최소 변경**: 색·구조는 유지하고 폰트·여백만 손대 회귀를 막는다. 결과는 항상 PNG(또는 pptx)로 렌더해 **육안 확인**한다.
- **하드코딩 폰트 크기가 병목**: 대부분의 도표 스크립트는 `fontsize=`/`fs=`가 함수·파일마다 흩어져 있다. 공유 모듈로 토큰화하는 것이 작업의 본질이다.
- **그림 유형을 먼저 구분**: 도식형(사각형·원·화살표·텍스트)은 네이티브 도형화가 깔끔하고, 데이터 그래프(곡선·산점)는 이미지가 현실적이다.

## 사전 준비

```bash
pip install matplotlib adjustText python-pptx
python scripts/fetch_pretendard.py fonts   # Pretendard OTF 4종을 ./fonts/ 에 받음 (SIL OFL)
```
`assets/figstyle.py`, `assets/pptx_figkit.py`를 작업 폴더로 복사하고, `fonts/`가 그 옆에 있게 둔다.

## 자산 (assets/)

| 파일 | 용도 |
|---|---|
| `figstyle.py` | 공유 스타일 모듈: Pretendard 등록 + rcParams(벡터 임베드·크기 상향) + Okabe-Ito 색 토큰 + 폰트크기 토큰 + `save_png()`(600dpi PNG 출력 일원화) |
| `pptx_figkit.py` | matplotlib 좌표를 16:9 슬라이드에 균일 스케일 1:1 매핑하는 python-pptx 키트(`Slide`/`Ax`: rect·oval·arrow·line·freeform·text·banner·table·image) |
| `fig1_slide_reference.py` | 도식형 그림을 키트로 재구성한 **워크드 예제**(새 figN_slide.py의 본보기) |
| `build_deck_reference.py` | 여러 그림을 한 덱으로 조립하는 마스터 예제(도식=네이티브, 표=네이티브, 복잡 데이터=이미지) |
| `scripts/fetch_pretendard.py` | Pretendard 정적 OTF(Regular/Medium/SemiBold/Bold) 다운로드 |

---

## Phase 1 — 진단

1. 폴더의 그림 파일과 생성 스크립트를 파악한다(SVG/PDF/PNG, `make_*.py`).
2. 각 그림이 **도식형**인지 **데이터 그래프**인지 분류한다.
3. 현재 폰트(예: Malgun Gothic = 시스템 기본 → 약함), 폰트 크기, 색 팔레트, 출력 포맷을 확인한다.
4. **용도 확인**(저널 인쇄 vs 발표/포스터)은 폰트 크기 기준을 정반대로 만든다 — 반드시 사용자에게 확정받는다. 저널이면 현재 대비 **+2~3pt**가 적정(포스터급 대형 금지).

## Phase 2 — 타이포그래피 + 공유 스타일 적용

1. `figstyle.py`를 작업 폴더에 두고 `OUT_DIR`(기본 `figures_v2`)·폰트 크기 토큰을 용도에 맞게 조정.
2. 각 `make_figN_*.py`를 보존하고 `make_figN_*_v2.py` 사본을 만든다:
   - 기존 `mpl.rcParams.update({...})` 호출 **삭제**, 상단에 `import figstyle as fs` 추가(`import matplotlib as mpl`은 유지).
   - 로컬 색 변수는 그대로 둔다(값 동일).
   - **하드코딩 폰트 크기를 일괄 +2~3pt**(`fontsize=`, `fs=`, `set_title/xlabel/ylabel(fontsize=)`, `legend(fontsize=)`, `tick_params(labelsize=)`). **폰트 크기 외 숫자(lw/markersize/dpi/좌표/xlim·ylim/figsize/alpha)는 절대 변경 금지.**
   - 모든 `savefig`(.svg/.pdf/_preview 등)·출력 경로·print를 `fs.save_png(fig, "<base>")` 한 줄로 교체(요구가 PNG-only일 때). 다중 그림 스크립트는 그림별 1회.
3. 렌더 후 **PNG를 직접 읽어** 두부(글리프 누락)·오버플로·라벨 충돌을 확인한다.

## Phase 3 — 색·레이아웃 다듬기

- **폰트 키운 뒤 충돌**: 축 좌표는 그대로 두고 **그림 높이를 +20~30%** 키우면 동일 폰트가 축 단위로 더 작게 차지해 세로 겹침이 준다. 가로는 폭 고정이므로 박스 확대 또는 폰트 소폭 하향으로 해결.
- **데이터 그래프 라벨 겹침**: `adjustText`로 자동 회피.
- **순수 원색 요구**(서브픽셀/컬러필터): `#FF0000/#00FF00/#0000FF`로. 단 **순수 녹색 `#00FF00`은 흰 배경의 얇은 텍스트·화살표엔 거의 안 보인다** → 채움은 순수, 얇은 요소는 가독 변형 `#00A651` 분리. 채움이 `alpha<1`로 희미하면 alpha 제거. 순수색 위 라벨은 대비에 맞춰 글자색 선택(순수 녹 위=검정, 순수 적/청 위=흰색).
- 박스 텍스트 오버플로: 박스 폭 확대(+가용공간) 또는 본문 폰트 소폭 하향. 정렬 변경은 텍스트 박스 `ha`로.
- 색 팔레트는 Okabe-Ito(색맹 안전)를 기본으로 — 별도 색 라이브러리 불필요.

## Phase 4 — 편집 가능한 pptx 변환

그림 유형별로 슬라이드를 만들어 한 덱으로 조립한다(`build_deck_reference.py` 참고).

| 유형 | 처리 |
|---|---|
| 도식형(사각·원·화살표·텍스트) | `pptx_figkit`로 **네이티브 도형+텍스트박스** 재구성 (`fig1_slide_reference.py` 본보기) |
| 표 | PowerPoint **네이티브 표**(`Slide.table`) |
| 단순 막대/선 | 도형 기반 차트(로그축은 `Ax(..., ylog=True)`, 막대=rect, 기준선=dashed line) |
| 복잡 데이터(곡선·산점 다수) | 600dpi PNG **이미지**로 전면 배치(`Slide.image`) |

재구성 규칙(충실도 핵심): **v2 스크립트의 좌표·색·크기를 1:1로 번역**한다(검증된 PNG와 동일 비율 보장).
- 그림별 모듈 `figN_slide.py`에 `def add_slide(prs, img_dir=None):` 정의, `pptx_figkit`의 `Slide`/`Ax` 사용.
- `Slide(prs, fig_w_mm, fig_h_mm)` → `s.axes(left,right,bottom,top, xlim, ylim[, xlog, ylog])` → `ax.rect/oval/arrow/line/freeform/text`.
- 곡선은 같은 수식에서 40~60점 샘플링해 `ax.freeform(points)`.
- 위첨자는 `^{n}` 표기 → 진짜 PPT 윗첨자 런으로 렌더(특수 글리프 불필요).

## Phase 5 — 검증

- **PNG**: 직접 읽어 두부·오버플로·충돌·색을 육안 확인(필수).
- **pptx**: 렌더러(PowerPoint/LibreOffice)가 없으면 **이미지 렌더 검증 불가**. 대신 구조 검증(슬라이드별 도형 수, 폰트=Pretendard, 위첨자 런)과 **좌표 경계 검사**(슬라이드 밖 도형·비-선 도형의 0/음수 크기 탐지; 수직/수평 화살표 connector는 한 변이 0인 게 정상)로 총체적 오류만 차단. 최종 시각 확인은 PowerPoint에서. 렌더 검증이 필요하면 LibreOffice headless(`soffice --headless --convert-to png`) 설치를 사용자에 제안.

## 작업 규율

- 원본 스크립트·출력은 보존하고 `_v2`/새 폴더로 산출(되돌리기 가능).
- 그림이 많으면 그림별 독립 모듈로 나눠 **병렬 서브에이전트**로 이행하고, 어셈블·검증은 한곳에서.
- 매 단계 렌더·검증 전에는 "완료" 단정 금지.
