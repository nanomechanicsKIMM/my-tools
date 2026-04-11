#!/usr/bin/env python3
"""hwpx_to_md.py — HWPX 특허 명세서를 MD + 섹션 JSON으로 파싱

Patent-draft-review 스킬의 Phase 1(spec parser)에서 사용.
hwpx-xml 스킬의 text_extract.py를 sys.path 조작으로 import하여
HWPX → MD 변환을 수행한 후, 한국 특허 명세서의 9개 표준 섹션을
정규식으로 인식하여 구조화된 JSON을 생성한다.

=== 사용법 ===

    python hwpx_to_md.py <input.hwpx> <output_dir>

=== 출력 ===

  {output_dir}/
    ├── full.md          # 전체 MD (text_extract.py extract_markdown 결과)
    └── sections.json    # 섹션 단위 파싱 결과

=== sections.json 스키마 ===

  {
    "invention_title": "...",
    "language": "ko",
    "source_hwpx": "<절대경로>",
    "total_lines": N,
    "sections": {
      "tech_field":      {"start": L1, "end": L2, "text": "..."},
      "background":      {"start": L1, "end": L2, "text": "..."},
      "problem":         {"start": L1, "end": L2, "text": "..."},
      "solution":        {"start": L1, "end": L2, "text": "..."},
      "effect":           {"start": L1, "end": L2, "text": "..."},
      "figure_brief":    {"start": L1, "end": L2, "text": "..."},
      "detailed":        {"start": L1, "end": L2, "text": "..."},
      "claims":          {"start": L1, "end": L2, "text": "..."},
      "abstract":        {"start": L1, "end": L2, "text": "..."},
      "reference_signs": {"start": L1, "end": L2, "text": "..."}
    },
    "claims_parsed": [
      {"num": 1, "dependent_of": null, "text": "..."},
      {"num": 2, "dependent_of": 1, "text": "..."},
      ...
    ],
    "reference_numbers": {
      "100": "대상체",
      "110": "두피",
      ...
    }
  }

=== 재사용 자산 ===

  hwpx-xml 스킬 경로:
    C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/text_extract.py

=== Phase 1 에이전트 호출 시나리오 ===

  phase1-spec-parser 에이전트가 Bash 도구로 본 스크립트 실행:

    python C:/Users/JHKIM/.claude/skills/patent-draft-review/scripts/hwpx_to_md.py \\
           <spec_file> <output_dir>

  결과 sections.json을 읽어 spec_structure.json에 통합.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# hwpx-xml 스킬 경로 (플랜 v1.4 기준)
# ---------------------------------------------------------------------------
HWPX_XML_SCRIPTS = Path(
    "C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts"
).resolve()

# ---------------------------------------------------------------------------
# 한국 특허 명세서 섹션 헤더 정규식 (우선순위 순)
# ---------------------------------------------------------------------------
# MD 변환 결과에서 줄 단위 매칭. 일반적으로 "## 섹션명" 또는 평문 라인.
SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tech_field",      re.compile(r"^(##\s*)?기술\s*분야\s*$")),
    ("background",      re.compile(r"^(##\s*)?(발명의\s*배경이\s*되는\s*기술|배경\s*기술)\s*$")),
    ("problem",         re.compile(r"^(##\s*)?해결하고자\s*하는\s*과제\s*$")),
    ("solution",        re.compile(r"^(##\s*)?과제의\s*해결\s*수단\s*$")),
    ("effect",           re.compile(r"^(##\s*)?발명의\s*효과\s*$")),
    ("figure_brief",    re.compile(r"^(##\s*)?도면의\s*간단한\s*설명\s*$")),
    ("detailed",        re.compile(r"^(##\s*)?발명을\s*실시하기\s*위한\s*구체적인\s*내용\s*$")),
    ("claims",          re.compile(r"^(##\s*)?(특허\s*)?청구\s*범위\s*$")),
    ("abstract",        re.compile(r"^(##\s*)?요약\s*$")),
    ("reference_signs", re.compile(r"^(##\s*)?부호의\s*설명\s*$")),
]

CLAIM_HEADER_RE = re.compile(r"^##\s*청구항\s*(\d+)\s*$")
CLAIM_DEPENDENCY_RE = re.compile(r"제\s*(\d+)\s*항에\s*있어서")
INVENTION_TITLE_RE = re.compile(r"^##\s*발명의\s*명칭\s*$")
REFERENCE_SIGN_RE = re.compile(r"^\s*(\d+)\s*[:：]\s*(.+?)\s*$")


def _import_text_extract() -> Any:
    """hwpx-xml/scripts/text_extract.py를 동적 로드."""

    if not HWPX_XML_SCRIPTS.is_dir():
        raise FileNotFoundError(
            f"hwpx-xml scripts directory not found: {HWPX_XML_SCRIPTS}. "
            "Plan v1.4 expects the hwpx-xml skill to be installed."
        )

    if str(HWPX_XML_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(HWPX_XML_SCRIPTS))

    try:
        import text_extract  # type: ignore
    except ImportError as exc:
        raise ImportError(
            f"Failed to import text_extract from {HWPX_XML_SCRIPTS}. "
            "Ensure the python-hwpx package is installed."
        ) from exc

    return text_extract


def extract_hwpx_to_md(hwpx_path: Path) -> str:
    """HWPX → MD 문자열 (hwpx-xml text_extract.extract_markdown 래핑)."""

    text_extract = _import_text_extract()
    return text_extract.extract_markdown(str(hwpx_path))


def parse_sections(md: str) -> dict[str, Any]:
    """MD 본문을 9개 섹션으로 정규식 분할."""

    lines = md.splitlines()
    total = len(lines)

    # {section_key: start_line_0indexed}
    section_starts: dict[str, int] = {}
    invention_title = ""

    for idx, line in enumerate(lines):
        stripped = line.strip()

        if INVENTION_TITLE_RE.match(stripped):
            # 다음 비어있지 않은 줄이 제목
            for j in range(idx + 1, min(idx + 5, total)):
                nxt = lines[j].strip()
                if nxt:
                    invention_title = nxt
                    break
            continue

        for key, pat in SECTION_PATTERNS:
            if key in section_starts:
                continue
            if pat.match(stripped):
                section_starts[key] = idx
                break

    # 각 섹션의 end를 다음 섹션 start - 1로 결정
    ordered = sorted(section_starts.items(), key=lambda kv: kv[1])
    sections: dict[str, dict[str, Any]] = {}
    for pos, (key, start) in enumerate(ordered):
        end = ordered[pos + 1][1] - 1 if pos + 1 < len(ordered) else total - 1
        text = "\n".join(lines[start:end + 1]).strip()
        sections[key] = {
            "start": start + 1,  # 1-indexed
            "end": end + 1,
            "text": text,
        }

    return {
        "invention_title": invention_title,
        "total_lines": total,
        "sections": sections,
    }


def parse_claims(md: str) -> list[dict[str, Any]]:
    """청구항 섹션을 파싱하여 독립/종속 관계 추출."""

    lines = md.splitlines()
    claims: list[dict[str, Any]] = []
    current_num: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_num is None:
            return
        text = " ".join(ln.strip() for ln in current_lines if ln.strip())
        dep_match = CLAIM_DEPENDENCY_RE.search(text)
        dependent_of = int(dep_match.group(1)) if dep_match else None
        claims.append({
            "num": current_num,
            "dependent_of": dependent_of,
            "text": text,
        })

    for line in lines:
        m = CLAIM_HEADER_RE.match(line.strip())
        if m:
            flush()
            current_num = int(m.group(1))
            current_lines = []
        elif current_num is not None:
            current_lines.append(line)

    flush()
    return claims


def parse_reference_numbers(reference_signs_text: str) -> dict[str, str]:
    """부호의 설명 섹션에서 {부호: 구성요소명} dict 추출."""

    result: dict[str, str] = {}
    for line in reference_signs_text.splitlines():
        m = REFERENCE_SIGN_RE.match(line.strip())
        if m:
            number = m.group(1)
            name = m.group(2).strip()
            if number and name:
                result[number] = name
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HWPX 특허 명세서 → MD + 섹션 JSON 파서"
    )
    parser.add_argument("input", help="입력 .hwpx 또는 .md 파일 경로")
    parser.add_argument("output_dir", help="출력 디렉토리 (없으면 생성)")
    parser.add_argument(
        "--format-hint",
        choices=["auto", "hwpx", "md"],
        default="auto",
        help="입력 포맷 힌트 (기본: 확장자로 자동 감지)",
    )
    args = parser.parse_args()

    src = Path(args.input).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not src.is_file():
        print(f"Error: input file not found: {src}", file=sys.stderr)
        return 1

    # 포맷 감지
    fmt = args.format_hint
    if fmt == "auto":
        fmt = "hwpx" if src.suffix.lower() in {".hwpx", ".hwp"} else "md"

    # MD 문자열 획득
    if fmt == "hwpx":
        md = extract_hwpx_to_md(src)
    else:
        md = src.read_text(encoding="utf-8")

    # full.md 저장
    full_md_path = out_dir / "full.md"
    full_md_path.write_text(md, encoding="utf-8")

    # 섹션 파싱
    parsed = parse_sections(md)
    claims_parsed: list[dict[str, Any]] = []
    reference_numbers: dict[str, str] = {}

    if "claims" in parsed["sections"]:
        claims_parsed = parse_claims(parsed["sections"]["claims"]["text"])

    if "reference_signs" in parsed["sections"]:
        reference_numbers = parse_reference_numbers(
            parsed["sections"]["reference_signs"]["text"]
        )

    result = {
        "invention_title": parsed["invention_title"],
        "language": "ko",
        "source_hwpx": str(src),
        "total_lines": parsed["total_lines"],
        "sections": parsed["sections"],
        "claims_parsed": claims_parsed,
        "reference_numbers": reference_numbers,
    }

    sections_json_path = out_dir / "sections.json"
    sections_json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Parsed: {src}\n"
        f"  → full.md ({full_md_path}, {len(md)} chars)\n"
        f"  → sections.json ({sections_json_path}, "
        f"{len(parsed['sections'])} sections, "
        f"{len(claims_parsed)} claims, "
        f"{len(reference_numbers)} reference numbers)",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
