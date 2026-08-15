---
name: kimm-deck
description: "KIMM 보고·워크숍 PPTX 덱을 검증된 디자인 시스템으로 생성하는 스킬. 두 양식 — design.kimm(4:3 보고서, 네이비 + 상태색, 아키타입 8종)과 design.editorial(16:9 설득형, 슬라이드당 메시지 1개 + 이중 막대·실축척 스케일). python-pptx 헬퍼와 검증된 예제 포함. 'kimm 덱', 'kimm-deck', 'design.kimm 양식', 'KIMM 보고 덱', '워크숍 발표자료', '과제 보고 ppt', '연차 보고 덱', '진행상황 보고 덱', '설득력 있는 덱', '16:9 보고 덱', '4:3 보고서 슬라이드' 등의 키워드가 나오면 이 스킬을 사용할 것. 16:9 범용 코드 덱은 pptx-layout-kits, HTML 슬라이드는 frontend-slides 사용."
---

# kimm-deck — KIMM 보고 덱 디자인 시스템

실제 과제 보고·워크숍 덱에서 추출·검증한 두 개의 디자인 시스템. **먼저 양식을 고른다.**

| 상황 | 양식 | 스펙 · 헬퍼 |
|---|---|---|
| 기록·배포용 보고서 덱. 항목을 빠짐없이 담아야 함 | **design.kimm** (4:3) | `assets/design.kimm.md` · `kimm_deck.py` |
| 발표·심의·경영층 보고. 설득해야 함 | **design.editorial** (16:9) | `assets/design.editorial.md` · `editorial_deck.py` |

- design.kimm — 흰 배경 + 네이비(#1F3864) 구조색 + 상태색 6종, 칩·제목·➡ 배너, 아키타입 A~H.
- design.editorial — 잉크/종이 지배 + 의미색 3종(청록=달성 · 코랄=미달 · 앰버=진행),
  좌측 라벨 컬럼 + 가로 헤어라인 + 하단 결론 스트립. **슬라이드당 메시지 1개**,
  수치는 표가 아니라 **이중 막대·대형 스탯·실축척 스케일**로 보여준다.
- 두 시스템은 좌표계가 다르다 — **혼용 금지**. 같은 내용을 두 양식으로 각각 만드는 것은 가능.

아래 절차는 design.kimm 기준이며, editorial은 §"에디토리얼 양식" 절을 따른다.

## 사용 절차

1. **스펙 로드**: `assets/design.kimm.md`를 읽는다 — 색 토큰 15종, 타이포,
   공통 크롬(칩·제목·배너·푸터), 아키타입 A~H 좌표, 작성 수칙.
2. **콘텐츠 → 아키타입 매핑**: 각 슬라이드를 아키타입에 배정한다.
   - A 표지 / B 목표-실적 표 / C 요약 2박스 / D 스탯 카드 2×2 /
     E 타임라인+요청 카드 / F 파트너 소개 / G 3열 상태 보드 / H 클로징
   - 모든 콘텐츠 슬라이드는 칩 + 제목 + (해당 시) ➡ 결론 배너 + 푸터를 갖는다.
3. **스크립트 작성**: `assets/example_deck.py`를 작업 폴더로 복사해 출발점으로
   삼고, `assets/kimm_deck.py`의 헬퍼만 사용한다 (hex 하드코딩 금지, 색은 토큰).

   ```python
   from kimm_deck import *          # kimm_deck.py를 같은 폴더에 복사
   prs = new_deck()                 # 10 × 7.5 in (4:3)
   s = add_slide(prs)
   chrome(s, "Outputs", "제목", n=2, footer_text="deck name")
   banner(s, "한 문장 결론")
   save(prs, "out.pptx")            # 저장 + 테마 그림자 제거 후처리 포함
   ```

4. **QA (필수)**: 렌더 → 전 슬라이드 육안 확인 → 수정 → 재렌더.
   최소 1회 수정-재검증 사이클 전에는 완료 선언 금지.

   ```bash
   soffice --headless --convert-to pdf out.pptx && pdftoppm -jpeg -r 100 out.pdf slide
   ```

## 에디토리얼 양식 (design.editorial, 16:9)

1. `assets/design.editorial.md`를 읽는다 — 그리드, 의미색 3종, 아키타입 A~G, 작성 수칙.
2. 슬라이드마다 **결론 한 문장**을 먼저 정하고 그것을 헤드라인으로 쓴다
   ("결과 요약" ✗ → "방법은 재현됐다" ○). 그 다음에 근거를 배치한다.
3. `assets/example_editorial.py`를 출발점으로 복사해 헬퍼만 사용한다.

   ```python
   from editorial_deck import *        # editorial_deck.py를 같은 폴더에 복사
   prs = new_deck(total=8)             # 13.333 × 7.5 in
   s = add_slide(prs)
   header(s, 2, "결과", "구조 지표는 목표를 넘었다", "부제 한 줄")
   bar_row(s, 2.2, "반복도 ↓", "0.20 µm", "0.14 µm", 1.0, 0.70, "초과", TEAL)
   scale(s, 4.05, 0, 2000, [0, 500, 1000, 1500, 2000],
         span=(900, 1700, "시험 산포 800 nm"), band=(450, 550, "목표 500 ± 50 nm"))
   closer(s, "한 문장 결론", TEAL)
   foot(s, "덱 이름 · 날짜")
   save(prs, "out.pptx")
   ```

4. **검증 2단**: `audit(out)`로 캔버스 이탈·그림자·비번들 폰트 0건을 확인한 뒤,
   렌더 QA로 전 슬라이드를 육안 검수한다.

**설득 장치를 정직하게 쓰는 법** (이 양식에서 가장 자주 나는 사고)
- 막대 길이는 행마다 따로 정규화 — 행끼리 비교하는 그림이 아니다.
- 지표 방향이 섞이면 항목명에 `↓`/`↑`를 붙이고 각주에 범례를 단다.
- **범위(산포)와 단일값을 같은 막대에 그리지 말 것** — 산포는 `scale()`로 옮긴다.
- `scale()`의 목표 창은 폭이 곧 허용오차다. 잘 보이라고 굵게 그리면 그림이 거짓이 된다.

## 핵심 수칙 (위반 시 실제로 깨졌던 항목)

- **폰트**: 제목·칩·배너는 Trebuchet MS Bold. HY헤드라인M·나눔스퀘어 등
  비번들 폰트 금지(치환 깨짐). 한글 본문은 테마 기본(맑은 고딕/Apple SD).
- **표는 모든 셀 한 줄**: 한 셀이 2줄로 꺾이면 행높이가 늘어나 우측 담당
  라벨 정렬이 전부 틀어진다. 표 본문 14pt 고정(16pt는 푸터 침범).
- **그림자 금지**: 도형 그림자는 `save()`가 `<p:style>` 제거로 처리한다 —
  반드시 `prs.save()` 대신 `save(prs, out)`를 쓸 것.
- **한글 공백 들여쓰기 금지**: 줄바꿈 시 정렬이 깨진다. 문장을 한 줄로 줄일 것.
- 배경 이미지가 필요한 표지/클로징은 어두운 톤 이미지를 쓰고, 없으면
  `assets/bg_title.png`·`bg_close.png`(중립 성야 그라디언트)를 재사용.

## 의존성

- Python: `python-pptx` (`pip install python-pptx`)
- QA 렌더: LibreOffice(`soffice`) + poppler(`pdftoppm`) — 생성에는 불필요

## 유사 스킬 라우팅

- KIMM 보고·워크숍 **4:3 기록용** → **이 스킬 / design.kimm**
- KIMM **16:9 설득·발표용** → **이 스킬 / design.editorial**
- 16:9 범용 컨설턴트 덱(레이아웃 10종 교체형) → `pptx-layout-kits`
- 애니메이션 HTML 슬라이드 → `frontend-slides`
- 기존 pptx 편집·분석 → `pptx` 스킬
