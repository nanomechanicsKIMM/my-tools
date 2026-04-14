#!/usr/bin/env python3
"""scan_tables.py — section0.xml 내 <hp:tbl> 목록 스캔.

각 테이블에 대해 다음 정보를 출력한다:
  - 인덱스, 소스 라인 번호
  - rowCnt × colCnt
  - 헤더 row 첫 cell 텍스트들 (최대 30자씩)
  - 선행 paragraph 텍스트 (최대 60자)

Usage:
    PYTHONUTF8=1 python scan_tables.py <section0.xml>

편집할 테이블을 찾아 anchor 를 결정할 때 사용.
"""
from __future__ import annotations

import sys
from pathlib import Path
from lxml import etree

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from table_utils import hp, element_text  # noqa: E402


def scan(xml_path: Path) -> None:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    for i, tbl in enumerate(root.iter(hp("tbl"))):
        rowCnt = tbl.get("rowCnt", "?")
        colCnt = tbl.get("colCnt", "?")
        rows = tbl.findall(hp("tr"))
        header = [
            element_text(tc).strip()[:30]
            for tc in (rows[0].findall(hp("tc")) if rows else [])
        ]

        # 테이블을 포함하는 <hp:p> 탐색 → 소스 라인 추출
        anc = tbl
        while anc is not None and anc.tag != hp("p"):
            anc = anc.getparent()
        line = getattr(anc, "sourceline", "?") if anc is not None else "?"

        # 선행 paragraph 탐색 (최대 3개 위)
        prev_text = "(none)"
        if anc is not None:
            prev = anc.getprevious()
            cnt = 0
            while prev is not None and cnt < 3:
                txt = element_text(prev).strip()
                if txt:
                    prev_text = txt[:60]
                    break
                prev = prev.getprevious()
                cnt += 1

        print(f"T{i:02d}  line={line}  rowCnt={rowCnt} colCnt={colCnt}")
        print(f"      prev:   {prev_text}")
        print(f"      header: {header}")
        print()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: scan_tables.py <section0.xml>", file=sys.stderr)
        return 1
    scan(Path(sys.argv[1]).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
