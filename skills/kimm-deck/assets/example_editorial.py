"""example_editorial — design.editorial(16:9) 레퍼런스 덱 5장.

editorial_deck.py의 장치를 전부 한 번씩 쓴다: cover · stat · panel · bar_row ·
scale · card · timeline · closer. 내용은 중립적인 예시(가상의 계측 장비 개발 보고)다.

실행: python3 example_editorial.py [출력경로]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_deck import *  # noqa: F403

OUT = (sys.argv[1] if len(sys.argv) > 1
       else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "example_editorial.pptx"))
FOOT = "예시 덱 · design.editorial 레퍼런스"

prs = new_deck(total=5)

# --- 1. 표지 --------------------------------------------------------------
s = add_slide(prs)
cover(s,
      kicker="KIMM · 예시 프로젝트",
      date="2026년 8월",
      title_lines=["측정 불확도를", "절반으로 줄인다"],
      subtitle="정밀 변위 계측 모듈 개발 — 진행상황 보고 (예시 데이터)",
      meta=[("과제", "정밀 계측 모듈", "2년차 / 3년"),
            ("기간", "2026-03 착수", "6개월차"),
            ("규모", "시제 3대 · 시험 412회", "설계 반복 9회"),
            ("현재 판정", "목표 근접 · 일부 미달", "PARTIAL")],
      thesis="구조는 목표를 넘었다. ",
      thesis_tail="남은 것은 열 안정성이다.")
foot(s, FOOT)

# --- 2. 규모와 규율 (stat + panel) ----------------------------------------
s = add_slide(prs)
header(s, 2, "접근", "먼저 재는 법부터 검증했다",
       "측정기 자체를 신뢰할 수 없으면 개선 여부도 판정할 수 없다")
for x, v, u, lab, note in [
        (M, "412", "회", "반복 시험", "동일 조건 재현성 확인까지 포함"),
        (3.85, "9", "회", "설계 반복", "반복마다 목표와 판정 기준을 먼저 고정"),
        (6.95, "27", "건", "동결 목표", "값과 허용오차를 시험 전에 고정"),
        (10.05, "38", "건", "자동 점검", "전건 통과 — 계측 코드부터 검증")]:
    stat(s, x, 1.95, 2.85, v, u, lab, note)
rule(s, M, 4.20, R - M)
panel(s, 4.45, "판정을 지키는 세 가지 규율",
      ["결과를 본 뒤에 기준을 고치지 않는다 — 허용오차를 넓혀 통과시킨 항목은 없다.",
       "근거가 없는 값은 '미확인'으로 원장에 남긴다.",
       "검증은 종료코드가 아니라 산출물 존재로 한다."],
      h=1.72)
closer(s, "기준을 먼저 동결했기 때문에 결과를 그대로 보고할 수 있다")
foot(s, FOOT)

# --- 3. 달성 항목 (bar_row) ------------------------------------------------
s = add_slide(prs)
header(s, 3, "결과 ①", "구조 지표는 목표를 넘었다",
       "설계 목표를 준 항목 중 정적 성능은 전부 목표를 만족했다")
bar_head(s, left="항목", mid="목표 (위) vs 실측 (아래)", right="판정")
for i, (nm, ref, our, fr, fo, vd) in enumerate([
        ("강성 ↑", "120 N/µm", "138 N/µm", 0.87, 1.00, "초과"),
        ("반복도 ↓", "0.20 µm", "0.14 µm", 1.00, 0.70, "초과"),
        ("직진도 ↓", "1.0 µm/100 mm", "0.9 µm", 1.00, 0.90, "만족"),
        ("응답 지연 ↓", "5.0 ms", "4.8 ms", 1.00, 0.96, "만족")]):
    bar_row(s, 2.20 + 0.78 * i, nm, ref, our, fr, fo, vd, TEAL)
rule(s, M, 5.72, R - M)
text(s, M, 5.92, 11.5, 0.45,
     [[("↓ 작을수록 좋은 지표 · ↑ 클수록 좋은 지표.", {"bold": True, "color": INK}),
       ("  막대 길이는 행마다 따로 정규화한다 — 행끼리 길이를 비교하지 말 것.",
        {"color": MUTE})]], size=14)
closer(s, "정적 성능은 목표 달성 — 여기까지는 설계가 맞았다", TEAL)
foot(s, FOOT)

# --- 4. 미달 항목 (bar_row + scale) ---------------------------------------
s = add_slide(prs)
header(s, 4, "결과 ②", "열 안정성은 아직 미달이다",
       "8시간 연속 운전에서 드리프트가 허용 범위를 벗어난다")
bar_head(s, left="항목", mid="목표 (위) vs 실측 (아래)", right="판정")
for i, (nm, ref, our, fr, fo, vd) in enumerate([
        ("8h 드리프트 ↓", "0.5 µm", "1.7 µm", 0.29, 1.00, "3.4배"),
        ("예열 시간 ↓", "30 min", "75 min", 0.40, 1.00, "2.5배")]):
    bar_row(s, 2.20 + 0.78 * i, nm, ref, our, fr, fo, vd, CORAL)
rule(s, M, 3.90, R - M)
scale(s, 4.05, 0, 2000, [0, 500, 1000, 1500, 2000],
      span=(900, 1700, "시험 5회 산포 800 nm"),
      band=(450, 550, "목표 500 ± 50 nm — 띠 폭이 곧 허용오차"),
      title="같은 축에 올려놓으면 — 8시간 드리프트 (nm)")
closer(s, "가장 좋은 시험도 목표 창 밖 — 산포가 허용오차의 8배다", CORAL)
foot(s, FOOT)

# --- 5. 진단과 계획 (card + timeline) -------------------------------------
s = add_slide(prs)
header(s, 5, "진단·계획", "원인은 둘로 좁혀졌다",
       "각각 실험으로 분리했고, 대책은 이미 일정에 올라와 있다")
card(s, M, 1.88, 3.30, 3.35, CORAL, "①", "열원 비대칭", "구동부 발열 — 미해소",
     ["구동부를 끄면 드리프트가", "1.7 → 0.4 µm로 붕괴한다.", "= 발열 경로가 지배 요인."],
     next_line="다음 수 — 열 분리 구조 (9월)")
card(s, 4.30, 1.88, 3.30, 3.35, AMBER, "②", "재료 시상수", "선팽창 — 부분 규명",
     ["예열 곡선이 재료 시상수와", "일치한다. 설계 변경 없이는", "예열 단축이 어렵다."],
     next_line="다음 수 — 소재 대안 비교 (10월)")
timeline(s, [("9월", CORAL, "열 분리 구조", "구동부 열원 분리"),
             ("10월", AMBER, "소재 대안 비교", "저팽창 소재 3종"),
             ("11월", TEAL, "통합 재시험", "8시간 연속 판정")],
         x=7.90, y=1.95, step=1.05, when_w=1.00)
closer(s, "원인이 다르면 대책도 다르다 — 열원부터 끊는다")
foot(s, FOOT)

print("saved:", save(prs, OUT))
issues = audit(OUT)
print("audit:", "문제 없음" if not issues else issues)
