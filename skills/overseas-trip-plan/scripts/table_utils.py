#!/usr/bin/env python3
"""table_utils.py — HWPX 테이블·문단 lxml 편집 유틸리티 (v0.2)

v0.1 에서 v0.2 로의 핵심 교훈을 응축한 모듈:

1. **Phantom paragraph 방지**: 셀 내 다중 <hp:p> 가 있을 때, 첫 번째에만 텍스트를
   넣고 나머지를 비우면 빈 <hp:p> + linesegarray 로 인해 한글이 파일을 로드하지
   못한다. → 여분의 <hp:p> 는 반드시 DOM 에서 제거.

2. **linesegarray 재계산 유도**: 기존 <hp:linesegarray>는 원본 텍스트의
   textpos/vertpos/horzsize 를 가리킨다. 텍스트를 바꾸면 HWP 가 **원본 위치
   메타데이터로 새 텍스트를 렌더**하여 인접 문단과 겹침(overlap) 발생.
   → 편집한 문단·셀의 `<hp:linesegarray>` 는 **완전히 제거**해 HWP 가 로드 시
   자동 재계산하도록 한다. (tor 스킬이 생성하는 `<hp:p>` 도 linesegarray 없음)

3. **테이블 행 삽입·삭제 후 필수 작업**:
   - `<hp:tbl rowCnt>` 속성을 실제 행 수로 갱신
   - 모든 `<hp:cellAddr rowAddr>` 를 행 위치 순으로 재부여 (중복 금지)
   - 병합 셀의 `<hp:cellSpan rowSpan>` 도 삽입/삭제에 맞춰 증감

4. **XML 선언**: `<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>`
   (double-quote, 공백 포함) — HWP 는 `lxml` 기본 single-quote 와 호환성 다름
   → 수동 직렬화로 v2 양식과 동일하게 출력.

Usage:
    from lxml import etree
    from table_utils import (
        set_cell_text_flow, set_p_text_flow, remove_paragraph,
        find_table_by_anchor, renumber_table, insert_row_clone,
        remove_row_safe, write_hwpx_xml,
    )
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable, Iterable, Optional

from lxml import etree

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"


def hp(tag: str) -> str:
    """hp: 네임스페이스 tag."""
    return f"{{{HP_NS}}}{tag}"


def hs(tag: str) -> str:
    """hs: 네임스페이스 tag."""
    return f"{{{HS_NS}}}{tag}"


# ===========================================================================
# 문자열 / 텍스트 헬퍼
# ===========================================================================

def element_text(elem) -> str:
    """element 하위 모든 <hp:t> 의 텍스트를 연결하여 반환."""
    return "".join(t.text or "" for t in elem.iter(hp("t")))


def cell_text(cell) -> str:
    """셀 텍스트 (strip 포함)."""
    return element_text(cell).strip()


# ===========================================================================
# linesegarray 처리
# ===========================================================================

def strip_linesegarray(p) -> bool:
    """<hp:p> 에서 <hp:linesegarray> 를 완전히 제거.

    HWP 는 로드 시 linesegarray 가 없으면 자동으로 layout 을 재계산한다.
    편집한 문단/셀에서는 반드시 호출해 겹침을 방지해야 한다.

    Returns:
        제거된 경우 True, 원래 없었으면 False.
    """
    lsa = p.find(hp("linesegarray"))
    if lsa is not None:
        p.remove(lsa)
        return True
    return False


# ===========================================================================
# 문단 텍스트 편집 (Section-level paragraphs)
# ===========================================================================

def set_p_text_flow(p, text: str) -> bool:
    """<hp:p> 텍스트를 교체하고 linesegarray 를 제거한다.

    - 첫 <hp:t> 에 `text` 설정, 나머지 <hp:t> 는 빈 문자열
    - <hp:linesegarray> 제거 → HWP 재계산

    주의: 이 함수는 문단 자체(<hp:p>)는 유지한다. 문단을 완전히 없애려면
    `remove_paragraph()` 를 사용할 것.
    """
    ts = list(p.iter(hp("t")))
    if not ts:
        return False
    ts[0].text = text
    for t in ts[1:]:
        t.text = ""
    strip_linesegarray(p)
    return True


def remove_paragraph(p) -> bool:
    """<hp:p> 를 parent 에서 완전히 제거.

    §3 등에서 "빈 줄로 만드는" 대신 문단 자체를 없앨 때 사용. 빈 <hp:p> 에
    남은 linesegarray 가 수직 공간을 예약해 아래 문단과 겹치는 문제를 방지.
    """
    parent = p.getparent()
    if parent is None:
        return False
    parent.remove(p)
    return True


# ===========================================================================
# 셀 텍스트 편집 (Table cells)
# ===========================================================================

def set_cell_text_flow(cell, text: str) -> bool:
    """<hp:tc> 텍스트를 교체하고 다음 작업을 수행한다:

    1. subList 내 **첫 번째 <hp:p> 만 유지**, 나머지 <hp:p> 는 제거
       (phantom paragraph 방지)
    2. 첫 <hp:p> 의 첫 <hp:t> 에 text 설정, 나머지 <hp:t> 는 빈 문자열
    3. **빈 셀 대응**: <hp:t> 가 아예 없으면(`<hp:run charPrIDRef=".."/>` 처럼
       self-closing 인 경우) 첫 <hp:run> 내부에 새 `<hp:t>` 를 injection 한다.
       <hp:run> 도 없으면 새로 생성.
    4. 첫 <hp:p> 의 <hp:linesegarray> 완전 제거
       → HWP 가 cellSz 기준으로 자동 레이아웃 재계산
    """
    sublist = cell.find(hp("subList"))
    if sublist is None:
        return False

    ps = sublist.findall(hp("p"))
    if not ps:
        return False

    first_p = ps[0]

    # 텍스트 설정 (<hp:t> 가 있으면 기존 것에, 없으면 생성)
    ts = list(first_p.iter(hp("t")))
    if ts:
        ts[0].text = text
        for t in ts[1:]:
            t.text = ""
    else:
        # <hp:t> 가 없는 빈 셀 → 첫 <hp:run> 내부에 주입
        runs = first_p.findall(hp("run"))
        if runs:
            target_run = runs[0]
        else:
            # <hp:run> 도 없으면 생성 (charPrIDRef 기본값 0)
            target_run = etree.SubElement(first_p, hp("run"))
            target_run.set("charPrIDRef", "0")
        new_t = etree.SubElement(target_run, hp("t"))
        new_t.text = text

    # linesegarray 제거 → HWP 재계산
    strip_linesegarray(first_p)

    # 추가 문단 제거 (phantom 방지)
    for p in ps[1:]:
        sublist.remove(p)

    return True


# ===========================================================================
# 테이블 탐색 / 수정
# ===========================================================================

def find_table_by_anchor(root, anchors: Iterable[str]):
    """테이블 내부 텍스트에 모든 anchor 문자열이 포함된 <hp:tbl> 을 찾는다.

    Args:
        root: XML 루트 또는 하위 element
        anchors: 모두 포함되어야 할 문자열 리스트

    Returns:
        일치하는 첫 <hp:tbl> 또는 None
    """
    anchors = list(anchors)
    for tbl in root.iter(hp("tbl")):
        text = element_text(tbl)
        if all(a in text for a in anchors):
            return tbl
    return None


def renumber_table(tbl) -> int:
    """테이블 내 모든 <hp:cellAddr rowAddr> 를 행 위치 순으로 재부여하고
    <hp:tbl rowCnt> 속성을 실제 행 수로 갱신한다.

    **행 삽입·삭제 직후 반드시 호출해야 한다.** 미호출 시 한글이 테이블
    구조를 해석하지 못해 파일 로드 실패.

    Returns:
        갱신된 rowCnt 값
    """
    rows = tbl.findall(hp("tr"))
    for row_idx, row in enumerate(rows):
        for cell in row.findall(hp("tc")):
            addr = cell.find(hp("cellAddr"))
            if addr is not None:
                addr.set("rowAddr", str(row_idx))
            # colAddr 는 rowspan 병합 구조를 유지하므로 건드리지 않는다
    tbl.set("rowCnt", str(len(rows)))
    return len(rows)


def get_rowspan(cell) -> int:
    """셀의 <hp:cellSpan rowSpan> 값. 없으면 1."""
    span = cell.find(hp("cellSpan"))
    if span is None:
        return 1
    return int(span.get("rowSpan", "1"))


def set_rowspan(cell, rowspan: int) -> bool:
    """셀의 <hp:cellSpan rowSpan> 값을 설정."""
    span = cell.find(hp("cellSpan"))
    if span is None:
        return False
    span.set("rowSpan", str(rowspan))
    return True


def insert_row_clone(
    reference_row,
    insert_after: bool = True,
    cell_modifier: Optional[Callable[[list], None]] = None,
):
    """`reference_row` 를 deepcopy 해서 앞/뒤로 삽입한다.

    - 복제 시 모든 child 요소(cellAddr, linesegarray 포함)가 그대로 복사되므로
      반드시 `cell_modifier` 에서 `set_cell_text_flow()` 를 호출해
      linesegarray 제거 + 텍스트 갱신을 한다.

    Args:
        reference_row: 복제 원본 <hp:tr>
        insert_after: True 면 reference 뒤에, False 면 앞에 삽입
        cell_modifier: `(new_cells: list[hp:tc]) -> None` 콜백

    Returns:
        삽입된 새 <hp:tr>

    주의: 호출 후 `renumber_table(parent_tbl)` 을 반드시 실행할 것.
    """
    new_row = deepcopy(reference_row)
    if cell_modifier is not None:
        new_cells = new_row.findall(hp("tc"))
        cell_modifier(new_cells)

    if insert_after:
        reference_row.addnext(new_row)
    else:
        reference_row.addprevious(new_row)
    return new_row


def remove_row_safe(row, decrement_rowspan_of=None) -> None:
    """<hp:tr> 를 parent 테이블에서 제거한다.

    Args:
        row: 제거할 <hp:tr>
        decrement_rowspan_of: (선택) 병합 셀이 있는 첫 행의 <hp:tc>.
            지정하면 rowSpan 을 1 감소.

    주의: 호출 후 `renumber_table(tbl)` 실행 필수.
    """
    if decrement_rowspan_of is not None:
        cur = get_rowspan(decrement_rowspan_of)
        set_rowspan(decrement_rowspan_of, max(cur - 1, 1))

    parent = row.getparent()
    if parent is not None:
        parent.remove(row)


# ===========================================================================
# XML 직렬화 (HWP 호환)
# ===========================================================================

def write_hwpx_xml(tree, path) -> None:
    """HWP 호환 XML 선언(double-quote)으로 section XML 을 저장.

    lxml 의 기본 `tree.write()` 는 `<?xml version='1.0' encoding='UTF-8' ?>`
    (single-quote) 를 출력. 한컴 한글은 원본 양식과 일치하지 않아도 대부분
    허용하지만, 안전을 위해 v2 양식과 동일한 double-quote 형식으로 맞춘다.
    """
    path = Path(path)
    body = etree.tostring(
        tree.getroot(), encoding="utf-8", xml_declaration=False
    ).decode("utf-8")
    decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    path.write_text(decl + body, encoding="utf-8")
