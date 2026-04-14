#!/usr/bin/env python3
"""dump_tables.py — 지정된 <hp:tbl> 의 셀 내용을 dump.

Usage:
    PYTHONUTF8=1 python dump_tables.py <section0.xml> <tbl_index> [<tbl_index> ...]

각 cell 텍스트를 최대 80자까지 출력하며, 셀 내부의 multi-line(`\\n`) 은
' ↵ ' 로 축약 표시. 편집 전후 diff 검증에 활용.

예:
    # scan_tables.py 결과에서 T02, T06 만 확인
    PYTHONUTF8=1 python dump_tables.py section0.xml 2 6
"""
from __future__ import annotations

import sys
from pathlib import Path
from lxml import etree

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from table_utils import hp, element_text  # noqa: E402


def dump(xml_path: Path, target_indices: list[int]) -> None:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    hits = set(target_indices)
    for i, tbl in enumerate(root.iter(hp("tbl"))):
        if hits and i not in hits:
            continue
        rowCnt = tbl.get("rowCnt", "?")
        colCnt = tbl.get("colCnt", "?")
        print(f"=== T{i:02d} ({rowCnt} rows × {colCnt} cols) ===")
        for r, row in enumerate(tbl.findall(hp("tr"))):
            cells = row.findall(hp("tc"))
            texts = [
                element_text(c).strip()[:80].replace("\n", " ↵ ")
                for c in cells
            ]
            print(f"  r{r}: {texts}")
        print()


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: dump_tables.py <section0.xml> <tbl_index> [<tbl_index> ...]",
            file=sys.stderr,
        )
        return 1
    xml_path = Path(sys.argv[1]).resolve()
    indices = [int(x) for x in sys.argv[2:]]
    dump(xml_path, indices)
    return 0


if __name__ == "__main__":
    sys.exit(main())
