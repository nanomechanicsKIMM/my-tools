# -*- coding: utf-8 -*-
"""patent_svg 스타일 정의 — 출원용 흑백(patent_bw)과 내부 검토용(kimm_semantic).

svg-figure-creation.md §2 디자인 컨벤션을 계승한다.
"""

# 따옴표 없는 패밀리 목록 — cairosvg는 quoted 목록을 해석하지 못함(2026-08-08 파일럿 실측).
# 순서: macOS(Apple SD Gothic Neo/AppleGothic) → Windows(Malgun Gothic) → generic.
FONT_STACK = "Apple SD Gothic Neo, AppleGothic, Malgun Gothic, sans-serif"

PATENT_BW = dict(
    name="patent_bw",
    stroke="#000000",
    stroke_primary=2.2,     # 주 구조 외곽선
    stroke_secondary=1.2,   # 보조 구조
    stroke_leader=0.7,      # 지시선
    stroke_dashed="6,4",    # 가상선(초점면·생략선)
    fill_none="none",
    fill_hatch="#000000",
    font_family=FONT_STACK,
    font_size=15,
    font_size_title=19,
    text_color="#000000",
    beam_fill="#d9d9d9",    # 광선 다발 연회색(흑백 인쇄 안전)
    beam_opacity=0.55,
)

KIMM_SEMANTIC = dict(PATENT_BW)
KIMM_SEMANTIC.update(
    name="kimm_semantic",
    # svg-figure-creation.md §2.1 의미 팔레트 계승(내부 검토용)
    color_structure="#1f4e79",   # 구조(네이비)
    color_active="#c00000",      # 발광·활성(적)
    color_optical="#2e75b6",     # 광선(청)
    color_annot="#595959",       # 주석(회)
    beam_fill="#bdd7ee",
)


def get_style(name="patent_bw"):
    return dict(PATENT_BW) if name == "patent_bw" else dict(KIMM_SEMANTIC)
