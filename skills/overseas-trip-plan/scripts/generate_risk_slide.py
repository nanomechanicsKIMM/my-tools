#!/usr/bin/env python3
"""generate_risk_slide.py — NotebookLM 스타일 '위험-대응' 슬라이드 PNG 생성.

4행 [위험 요인 ▶ KIMM 대응 전략] 레이아웃. 본 스킬의 HWPX 삽입 파이프라인과
함께 사용.

사용 예:
  from generate_risk_slide import render_risk_slide

  render_risk_slide(
      out_path="mt8600_risk.png",
      title_line1="위험요인 분석 및 대응 전략:",
      title_line2="시장 위협 대비 KIMM 기술의 포지셔닝 (MT8600)",
      rows=[
          (["Wafer-level mass transfer", "선행 상용화 (Aledia 등)"],
           ["Yield/Throughput 지표 공개 시,", "8인치 롤 전사 우위 수치화."]),
          # ... up to 4 pairs
      ],
  )

CLI 사용:
  PYTHONUTF8=1 uv run python generate_risk_slide.py \\
      --out risk.png \\
      --title "제목" \\
      --subtitle "부제목" \\
      --json rows.json    # [[["위험 l1","l2"], ["대응 l1","l2"]], ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


# ===== 레이아웃 상수 =====

W, H = 1280, 720
BG = "#0c2e36"
TITLE_WHITE = "#ffffff"
TITLE_YELLOW = "#f5d547"
RISK_BG = "#d4dee0"
RISK_FG = "#1a1a1a"
RISK_LABEL = "#0c2e36"
RESPONSE_BG = "#5db8bc"
RESPONSE_FG = "#0c2e36"
ARROW_COLOR = "#f5d547"
FOOTER = "#6b8a92"

FONT_REG_DEFAULT = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD_DEFAULT = "C:/Windows/Fonts/malgunbd.ttf"

TITLE_SIZE = 30
SUBTITLE_SIZE = 30
LABEL_SIZE = 17
BODY_SIZE = 16
FOOTER_SIZE = 11


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _draw_arrow(draw, cx: int, cy: int, size: int = 20) -> None:
    """오른쪽 방향 화살표 (블록 + 삼각형)."""
    bw, bh = size, 10
    th = 20
    pts = [
        (cx - bw, cy - bh // 2),
        (cx, cy - bh // 2),
        (cx, cy - th // 2),
        (cx + th, cy),
        (cx, cy + th // 2),
        (cx, cy + bh // 2),
        (cx - bw, cy + bh // 2),
    ]
    draw.polygon(pts, fill=ARROW_COLOR)


def _draw_rounded_rect(draw, x1, y1, x2, y2, radius, fill):
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)
    except AttributeError:
        draw.rectangle([x1, y1, x2, y2], fill=fill)


def _draw_multiline_in_box(
    draw, lines, box, font_bold, font_reg,
    label: str, label_color: str, text_color: str,
) -> None:
    """박스 내부 세로 중앙 정렬 + 라벨(굵게) + 본문 여러 줄."""
    x1, y1, x2, y2 = box
    pad_x = 20

    ascent, descent = font_reg.getmetrics()
    line_h = ascent + descent + 4

    total_h = line_h * len(lines)
    start_y = y1 + (y2 - y1 - total_h) // 2

    cur_y = start_y
    for idx, line in enumerate(lines):
        cur_x = x1 + pad_x
        if idx == 0 and label:
            draw.text((cur_x, cur_y), label, fill=label_color, font=font_bold)
            lbl_w = font_bold.getlength(label)
            draw.text((cur_x + lbl_w + 4, cur_y), line, fill=text_color, font=font_reg)
        else:
            draw.text((cur_x, cur_y), line, fill=text_color, font=font_reg)
        cur_y += line_h


def render_risk_slide(
    out_path: str | Path,
    title_line1: str,
    title_line2: str,
    rows: Iterable[tuple[list[str], list[str]]],
    footer_text: str = "",
    font_regular: str = FONT_REG_DEFAULT,
    font_bold: str = FONT_BOLD_DEFAULT,
    risk_label: str = "위험 요인: ",
    response_label: str = "KIMM 대응 전략: ",
) -> Path:
    """4행 위험-대응 슬라이드를 PNG 로 저장.

    Args:
        out_path: 저장 경로 (예: "mt8600_risk.png")
        title_line1: 흰색 첫 줄 제목
        title_line2: 노란색 둘째 줄 제목
        rows: [(risk_lines, response_lines), ...] 리스트 (최대 4). 각 항목은
            박스 내부에 표시할 줄 리스트 (1~2줄 권장).
        footer_text: 우측 하단 footer (기본 "")
        font_regular / font_bold: TTF 경로. Windows 표준 Malgun Gothic.
        risk_label / response_label: 각 박스 좌측 굵은 라벨.

    Returns:
        저장된 PNG 파일 Path.
    """
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    font_t = _load_font(font_bold, TITLE_SIZE)
    font_sub = _load_font(font_bold, SUBTITLE_SIZE)
    font_label = _load_font(font_bold, LABEL_SIZE)
    font_body = _load_font(font_regular, BODY_SIZE)
    font_footer = _load_font(font_regular, FOOTER_SIZE)

    # 타이틀
    draw.text((58, 38), title_line1, fill=TITLE_WHITE, font=font_t)
    draw.text((58, 80), title_line2, fill=TITLE_YELLOW, font=font_sub)

    # 최대 4행 강제
    rows_list = list(rows)[:4]
    row_top = 160
    row_h = 120
    row_gap = 14
    risk_x1, risk_x2 = 58, 530
    arrow_cx = 555
    resp_x1, resp_x2 = 600, 1222

    for i, (risk_lines, resp_lines) in enumerate(rows_list):
        y1 = row_top + i * (row_h + row_gap)
        y2 = y1 + row_h
        cy = (y1 + y2) // 2

        _draw_rounded_rect(draw, risk_x1, y1, risk_x2, y2, 4, RISK_BG)
        _draw_multiline_in_box(
            draw, risk_lines, (risk_x1, y1, risk_x2, y2),
            font_label, font_body,
            label=risk_label, label_color=RISK_LABEL, text_color=RISK_FG,
        )

        _draw_arrow(draw, arrow_cx, cy, size=20)

        _draw_rounded_rect(draw, resp_x1, y1, resp_x2, y2, 4, RESPONSE_BG)
        _draw_multiline_in_box(
            draw, resp_lines, (resp_x1, y1, resp_x2, y2),
            font_label, font_body,
            label=response_label, label_color=RESPONSE_FG, text_color=RESPONSE_FG,
        )

    if footer_text:
        draw.text((W - 250, H - 26), footer_text, fill=FOOTER, font=font_footer)

    out_path = Path(out_path)
    img.save(out_path, "PNG", optimize=True)
    return out_path


# ===========================================================================
# CLI
# ===========================================================================

def _main() -> int:
    parser = argparse.ArgumentParser(description="위험-대응 슬라이드 PNG 생성")
    parser.add_argument("--out", required=True, help="출력 PNG 경로")
    parser.add_argument("--title", required=True, help="첫 줄 제목 (흰색)")
    parser.add_argument("--subtitle", required=True, help="둘째 줄 제목 (노란색)")
    parser.add_argument(
        "--json", required=True,
        help='rows JSON 경로. 형식: [[["위험 l1","l2"],["대응 l1","l2"]], ...] 최대 4쌍',
    )
    parser.add_argument("--footer", default="", help="우측 하단 footer")
    args = parser.parse_args()

    rows_raw = json.loads(Path(args.json).read_text(encoding="utf-8"))
    rows = [(r[0], r[1]) for r in rows_raw]
    path = render_risk_slide(
        out_path=args.out,
        title_line1=args.title,
        title_line2=args.subtitle,
        rows=rows,
        footer_text=args.footer,
    )
    print(f"[OK] {path} ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
