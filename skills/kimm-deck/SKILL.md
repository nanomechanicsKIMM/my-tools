---
name: kimm-deck
description: "KIMM 보고·워크숍용 4:3 PPTX 덱을 design.kimm 디자인 시스템(네이비 구조색 + 시맨틱 상태색, 아키타입 8종)으로 생성하는 스킬. python-pptx 헬퍼(kimm_deck.py)와 검증된 예제 포함. 'kimm 덱', 'kimm-deck', 'design.kimm 양식', 'KIMM 보고 덱', '워크숍 발표자료', '과제 보고 ppt', '연차 보고 덱', 'KIAT 보고 양식', '4:3 보고서 슬라이드' 등의 키워드가 나오면 이 스킬을 사용할 것. 16:9 범용 코드 덱은 pptx-layout-kits, HTML 슬라이드는 frontend-slides 사용."
---

# kimm-deck — KIMM 보고 덱 디자인 시스템 (4:3)

국제 공동 R&D 과제 보고·워크숍 덱에서 추출·검증한 디자인 시스템으로
같은 양식의 PPTX를 생성한다. 흰 배경 + 네이비(#1F3864) 구조색 +
시맨틱 상태색(녹=달성 / 황=격차 / 청=예정 / 주황=미달 / 적=경고).

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

- KIMM 보고·워크숍 **4:3 양식** → **이 스킬**
- 16:9 범용 컨설턴트 덱(레이아웃 10종 교체형) → `pptx-layout-kits`
- 애니메이션 HTML 슬라이드 → `frontend-slides`
- 기존 pptx 편집·분석 → `pptx` 스킬
