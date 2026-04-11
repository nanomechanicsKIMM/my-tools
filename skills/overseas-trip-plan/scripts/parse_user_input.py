#!/usr/bin/env python3
"""parse_user_input.py — user_input.md → dict 파서

Obsidian 마크다운 양식(YAML frontmatter + ## 섹션 + 표·불릿)을
파싱하여 빌더가 사용할 수 있는 딕셔너리로 변환한다.

Usage:
    # CLI
    python parse_user_input.py --input user_input.md --output data.json

    # Import
    from parse_user_input import parse_user_input
    data = parse_user_input("user_input.md")
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML이 필요합니다: pip install PyYAML", file=sys.stderr)
    sys.exit(2)


# 플레이스홀더로 간주할 패턴 (값으로 채우지 않음)
_PLACEHOLDER_PATTERNS = (
    re.compile(r"^예\s*:"),
    re.compile(r"^__.*__$"),
    re.compile(r"^\s*$"),
)


def _is_placeholder(value: str) -> bool:
    """값이 미작성 플레이스홀더인지 판정."""
    if not value:
        return True
    stripped = value.strip()
    if not stripped or stripped in ("-", "—", "–"):
        return True
    # 백틱 제거
    stripped = stripped.strip("`")
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def _clean_cell(text: str) -> str:
    """표 셀 내용 정제."""
    text = text.strip()
    # 백틱 코드 블록 제거
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    # <br> 태그 제거
    text = text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    return text.strip()


def _parse_kv_table(section_text: str) -> dict[str, str]:
    """마크다운 key-value 표 파싱.

    입력 형식:
        | 항목 | 값 |
        |------|----|
        | 제출일자 | 2025.05.01. |
        | 소속 | 나노디스플레이연구실 |
    """
    kv: dict[str, str] = {}
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # 구분선(|---|---|) 스킵
        if re.match(r"^\|[\s\-|:]+\|$", line):
            continue
        cells = [_clean_cell(c) for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, value = cells[0], cells[1]
        # 헤더 행 스킵
        if key in ("항목", "필드", "Field", "Key"):
            continue
        if _is_placeholder(value):
            continue
        kv[key] = value
    return kv


def _parse_multirow_table(section_text: str) -> list[dict[str, str]]:
    """다중 행 표 파싱. 첫 데이터 행을 헤더로 간주."""
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False
    header_seen = False
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if in_table:
                break  # 표 종료
            continue
        # 구분선
        if re.match(r"^\|[\s\-|:]+\|$", line):
            continue
        cells = [_clean_cell(c) for c in line.strip("|").split("|")]
        if not header_seen:
            headers = cells
            header_seen = True
            in_table = True
            continue
        if all(_is_placeholder(c) for c in cells):
            continue  # 빈 행
        row = {h: c for h, c in zip(headers, cells) if h}
        if row and any(v for v in row.values()):
            rows.append(row)
    return rows


def _parse_bullets(section_text: str) -> list[str]:
    """불릿 리스트 파싱 (`- ...` / `* ...`)."""
    bullets: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            value = stripped[2:].strip()
            if value and not _is_placeholder(value):
                bullets.append(value)
    return bullets


def _split_sections(body: str) -> dict[int, tuple[str, str]]:
    """본문을 `## N. 제목` 단위로 분할.

    Returns:
        {섹션번호: (제목, 본문 텍스트)}
    """
    sections: dict[int, tuple[str, str]] = {}
    current_num: int | None = None
    current_title: str = ""
    current_lines: list[str] = []

    for line in body.splitlines():
        m = re.match(r"^##\s+(\d+)\.\s+(.+)$", line)
        if m:
            if current_num is not None:
                sections[current_num] = (current_title, "\n".join(current_lines))
            current_num = int(m.group(1))
            current_title = m.group(2).strip()
            current_lines = []
        elif current_num is not None:
            current_lines.append(line)
    if current_num is not None:
        sections[current_num] = (current_title, "\n".join(current_lines))
    return sections


def parse_user_input(md_path: str | Path) -> dict[str, Any]:
    """user_input.md 파일을 파싱하여 딕셔너리로 반환.

    Returns:
        {
            "frontmatter": { "trip_type": ..., "conference_url": ..., ... },
            "sections": { 1: { "title": "...", "raw": "...", "kv": {...}, "bullets": [...], "rows": [...] }, ... },
            "applicant": { "제출일자": ..., "소속": ..., "직급": ..., "성명": ... },
            "trip_overview": { "출장 기간 (시작)": ..., ... },
            "purpose_bullets": [...],
            ...
        }
    """
    md_path = Path(md_path)
    content = md_path.read_text(encoding="utf-8")

    # Frontmatter 분리
    frontmatter: dict[str, Any] = {}
    body = content
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                print(f"[WARN] frontmatter YAML 파싱 실패: {e}", file=sys.stderr)
            body = parts[2]

    # 섹션 분할
    raw_sections = _split_sections(body)

    result: dict[str, Any] = {
        "_source": str(md_path),
        "frontmatter": frontmatter,
        "sections": {},
    }

    # 섹션별 구조화
    for num, (title, raw) in raw_sections.items():
        result["sections"][num] = {
            "title": title,
            "raw": raw,
            "kv": _parse_kv_table(raw),
            "bullets": _parse_bullets(raw),
            "rows": _parse_multirow_table(raw),
        }

    # 편의 필드 — 핵심 섹션을 최상위로 승격
    if 1 in result["sections"]:
        result["applicant"] = result["sections"][1]["kv"]
    if 2 in result["sections"]:
        result["trip_overview"] = result["sections"][2]["kv"]
    if 3 in result["sections"]:
        result["purpose_bullets"] = result["sections"][3]["bullets"]
    if 6 in result["sections"]:
        result["companions"] = result["sections"][6]["rows"]
    if 7 in result["sections"]:
        result["schedule"] = result["sections"][7]["rows"]
    if 9 in result["sections"]:
        result["past_trips"] = result["sections"][9]["rows"]
    if 10 in result["sections"]:
        result["budget"] = {
            "meta": result["sections"][10]["kv"],
            "rows": result["sections"][10]["rows"],
        }

    # trip_type 정규화
    trip_type = (frontmatter.get("trip_type") or "auto").strip().lower()
    if trip_type not in ("meeting", "conference", "auto"):
        trip_type = "auto"
    result["trip_type"] = trip_type

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="user_input.md → JSON 파서")
    parser.add_argument("--input", required=True, help="입력 md 파일")
    parser.add_argument("--output", help="출력 JSON 파일 (없으면 stdout)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"[ERROR] 입력 파일 없음: {args.input}", file=sys.stderr)
        return 2

    data = parse_user_input(args.input)
    # YAML date/datetime/etc → 문자열로 직렬화
    json_text = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(json_text, encoding="utf-8")
        print(f"✓ JSON 저장: {args.output}")
    else:
        print(json_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
