"""
Build 규격서.hwpx + 용도설명서.hwpx from skill templates and a JSON payload.

Usage:
    python build_forms.py <input.json> <output_dir>

input.json schema (single file used for both forms):
{
    "spec": {
        "품명": "...",
        "규격": "...",
        "단위": "EA",
        "수량": "1",
        "sections": [
            {"title": "1. 제품 개요", "body": "본문..." or ["line1", "line2"]},
            {"title": "2. 주요 사양", "body": "..."},
            ...
        ]
    },
    "purpose": {
        "품명": "...",
        "수량단위": "1 EA",
        "금액": "9,900,000원",
        "모델명": "...",
        "HSK": "8471.30-0000",
        "연구명": "...",
        "연구기간": "2026.01.01.-2026.12.31",
        "연구책임자": "김재현",
        "자금명": "연구비(NK266F)",
        "용도개요": "본 과제 ...\n  - 주요 사용 목적 ...",
        "활용빈도": "1500시간/년",
        "기보유량": "확인 불가능",
        "공동활용": "없음",
        "장비구분": "컴퓨터/노트북",
        "설치장소": "연구○동 ○호",
        "특기사항": "",
        "부서명": "나노디스플레이연구실",
        "연구책임자_서명": "김재현"
    },
    "output_basename": "(20260417 LLM) 메타초음파 영상 복원 계산 하드웨어"
}

Both spec and purpose are optional — if a key is missing the corresponding form
is skipped.  All values must already be plain text suitable for HWPX (no XML).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Iterable, Sequence

from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}
HP = "{%s}" % NS["hp"]


# ---------------------------------------------------------------------------
# Generic HWPX helpers
# ---------------------------------------------------------------------------

def _unzip(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src) as z:
        z.extractall(dst)


def _rezip(src_dir: Path, out: Path) -> None:
    if out.exists():
        out.unlink()
    # mimetype must be the first entry, stored uncompressed.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        mimetype = src_dir / "mimetype"
        if mimetype.exists():
            z.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, _, files in os.walk(src_dir):
            for name in files:
                full = Path(root) / name
                rel = full.relative_to(src_dir).as_posix()
                if rel == "mimetype":
                    continue
                z.write(full, rel)


def _load_section(template_dir: Path) -> tuple[etree._ElementTree, Path]:
    section_path = template_dir / "Contents" / "section0.xml"
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(section_path), parser)
    return tree, section_path


def _save_section(tree: etree._ElementTree, path: Path) -> None:
    tree.write(str(path), xml_declaration=True, encoding="UTF-8", standalone=True)


def _all_cells(root: etree._Element) -> Iterable[etree._Element]:
    return root.iter(HP + "tc")


def _cell_addr(cell: etree._Element) -> tuple[int, int]:
    addr = cell.find(HP + "cellAddr")
    if addr is None:
        return (-1, -1)
    return (int(addr.get("rowAddr", -1)), int(addr.get("colAddr", -1)))


def _cell_text_runs(cell: etree._Element) -> list[etree._Element]:
    return list(cell.iter(HP + "t"))


def _set_cell_text(cell: etree._Element, value: str) -> None:
    """Replace the cell's text content with `value`.

    The cell must already contain at least one <hp:t> (the template guarantees
    this).  Extra <hp:t> elements after the first are emptied so that the cell
    ends up with exactly `value` as its visible text.
    """
    runs = _cell_text_runs(cell)
    if not runs:
        # fall back: append a paragraph (unlikely with template)
        sublist = cell.find(HP + "subList")
        if sublist is None:
            return
        p = etree.SubElement(sublist, HP + "p")
        run = etree.SubElement(p, HP + "run")
        t = etree.SubElement(run, HP + "t")
        t.text = value
        return
    runs[0].text = value
    for extra in runs[1:]:
        extra.text = ""


def _cell_paragraphs(cell: etree._Element) -> list[etree._Element]:
    sublist = cell.find(HP + "subList")
    if sublist is None:
        return []
    return list(sublist.findall(HP + "p"))


def _replace_cell_paragraphs(
    cell: etree._Element,
    title_template: etree._Element,
    body_template: etree._Element,
    sections: Sequence[dict],
) -> None:
    """Rewrite the cell body with a sequence of (title, body) paragraph pairs.

    title_template and body_template are reference <hp:p> elements harvested
    from the original template; they are deep-copied for each insertion and
    their <hp:t> text is rewritten.
    """
    sublist = cell.find(HP + "subList")
    if sublist is None:
        return
    for child in list(sublist):
        sublist.remove(child)
    for sec in sections:
        title = sec.get("title", "").strip()
        body = sec.get("body", "")
        body_lines = body if isinstance(body, list) else [
            line for line in str(body).splitlines() if line.strip()
        ]

        if title:
            tp = deepcopy(title_template)
            _set_paragraph_text(tp, " " + title)
            sublist.append(tp)

        if not body_lines:
            empty = deepcopy(body_template)
            _set_paragraph_text(empty, "")
            sublist.append(empty)
            continue
        for line in body_lines:
            bp = deepcopy(body_template)
            _set_paragraph_text(bp, line)
            sublist.append(bp)


def _set_paragraph_text(paragraph: etree._Element, value: str) -> None:
    runs = list(paragraph.iter(HP + "t"))
    if not runs:
        run = paragraph.find(HP + "run")
        if run is None:
            run = etree.SubElement(paragraph, HP + "run")
        t = etree.SubElement(run, HP + "t")
        t.text = value
        return
    runs[0].text = value
    for extra in runs[1:]:
        extra.text = ""


def _strip_layout_caches(root: etree._Element) -> None:
    """Drop every <hp:linesegarray> so 한컴 recomputes text layout on open.

    Cloning paragraphs (or rewriting their text) leaves the original line-segment
    cache in place — every cloned paragraph then claims the same vertical
    position and the lines stack on top of each other when the file is opened.
    Removing the cache forces 한컴 to lay text out from scratch, which is the
    behavior we want.
    """
    for la in list(root.iter(HP + "linesegarray")):
        parent = la.getparent()
        if parent is not None:
            parent.remove(la)


def _reset_paragraph_ids(root: etree._Element) -> None:
    """Clear duplicate paragraph IDs introduced by deepcopy."""
    seen: set[str] = set()
    for p in root.iter(HP + "p"):
        pid = p.get("id")
        if pid and pid not in seen:
            seen.add(pid)
            continue
        # Duplicate or missing — let 한컴 reassign.
        p.set("id", "0")


def _expand_cell_to_fit(root: etree._Element, addr: tuple[int, int],
                        per_paragraph: int = 1800, padding: int = 2000) -> None:
    """Grow a cell (and its enclosing table) to accommodate its current paragraph count.

    한컴 stores cell heights in HWPUnits.  When we add paragraphs to a body cell
    the original ``cellSz`` may be too small, causing later table rows or page
    elements to overlap.  We compute a generous lower bound and expand both the
    cell and the parent table by the delta if needed.
    """
    target = None
    for c in root.iter(HP + "tc"):
        a = c.find(HP + "cellAddr")
        if a is None:
            continue
        if (int(a.get("rowAddr", -1)), int(a.get("colAddr", -1))) == addr:
            target = c
            break
    if target is None:
        return
    sublist = target.find(HP + "subList")
    n = len(list(sublist.iter(HP + "p"))) if sublist is not None else 0
    if n == 0:
        return
    sz = target.find(HP + "cellSz")
    if sz is None:
        return
    old_h = int(sz.get("height", "0"))
    needed = n * per_paragraph + padding
    if needed <= old_h:
        return
    delta = needed - old_h
    sz.set("height", str(needed))
    parent = target
    while parent is not None and parent.tag != HP + "tbl":
        parent = parent.getparent()
    if parent is not None:
        tsz = parent.find(HP + "sz")
        if tsz is not None:
            tsz.set("height", str(int(tsz.get("height", "0")) + delta))


def _find_paragraph_with_text(root: etree._Element, fragment: str) -> etree._Element | None:
    for p in root.iter(HP + "p"):
        for el in p.iter():
            if el.text and fragment in el.text:
                return p
            if el.tail and fragment in el.tail:
                return p
    return None


def _replace_label_value(paragraph: etree._Element, label: str, new_value: str) -> bool:
    """Replace the value following ``<label> :`` in a paragraph.

    HWPX often stores footer text as `<hp:t>...<hp:tab/>...텍스트</hp:t>` where
    the visible text is split between ``<hp:t>.text`` and ``<hp:tab>.tail``.
    This walks every text/tail attribute under the paragraph and rewrites the
    first one that contains ``label``, preserving any leading whitespace and
    keeping a single space before/after the colon.
    """
    for el in paragraph.iter():
        for attr in ("text", "tail"):
            value = getattr(el, attr)
            if value is None or label not in value:
                continue
            idx = value.find(label)
            head = value[:idx]
            after_label = value[idx + len(label):]
            # Drop existing colon (if any) and the value after it.
            colon_idx = after_label.find(":")
            if colon_idx >= 0:
                tail_keep = ""  # drop everything after colon
            else:
                tail_keep = ""
            new_text = f"{head}{label} : {new_value}{tail_keep}"
            setattr(el, attr, new_text)
            return True
    return False


# ---------------------------------------------------------------------------
# Spec form (규격서)
# ---------------------------------------------------------------------------

def fill_spec(template_root: Path, output_path: Path, data: dict) -> None:
    work = Path(tempfile.mkdtemp(prefix="hwpx_spec_"))
    try:
        _unzip(template_root, work)
        tree, section_path = _load_section(work)
        root = tree.getroot()

        # Header table cells (row 2 = first data row): No=0, 품명=1, 규격=2, 단위=3, 수량=4
        cells_by_addr = {_cell_addr(c): c for c in _all_cells(root)}

        if (2, 0) in cells_by_addr:
            _set_cell_text(cells_by_addr[(2, 0)], "1")
        if (2, 1) in cells_by_addr:
            _set_cell_text(cells_by_addr[(2, 1)], data.get("품명", ""))
        if (2, 2) in cells_by_addr:
            _set_cell_text(cells_by_addr[(2, 2)], data.get("규격", ""))
        if (2, 3) in cells_by_addr:
            _set_cell_text(cells_by_addr[(2, 3)], data.get("단위", "EA"))
        if (2, 4) in cells_by_addr:
            _set_cell_text(cells_by_addr[(2, 4)], str(data.get("수량", "1")))

        # Body cell = merged row 3 (5-col span)
        body_cell = cells_by_addr.get((3, 0))
        if body_cell is None:
            raise RuntimeError("규격서 본문 셀(row=3, col=0)을 찾지 못했습니다.")

        existing_paras = _cell_paragraphs(body_cell)
        # Identify a heading-style paragraph (starts with " 1." in template) and
        # a body-style paragraph (▷ ... or - ... lines in template) for cloning.
        title_proto = None
        body_proto = None
        for p in existing_paras:
            text = "".join(t.text or "" for t in p.iter(HP + "t"))
            if title_proto is None and text.lstrip().startswith(("1.", "2.", "3.", "4.", "5.")):
                title_proto = p
            elif body_proto is None and text.strip():
                body_proto = p
            if title_proto is not None and body_proto is not None:
                break

        if title_proto is None or body_proto is None:
            raise RuntimeError("규격서 본문 paragraph 원형(title/body)을 찾지 못했습니다.")

        sections = data.get("sections") or []
        _replace_cell_paragraphs(body_cell, title_proto, body_proto, sections)

        _expand_cell_to_fit(root, (3, 0))
        _reset_paragraph_ids(root)
        _strip_layout_caches(root)

        _save_section(tree, section_path)
        _rezip(work, output_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# Purpose form (용도설명서)
# ---------------------------------------------------------------------------

# Anchors used to locate cells whose values must be replaced.  Each entry is
# (label-text-fragment-in-left-cell, target-cell-row-offset-from-label-cell).
# All purpose-form cells live on the same row as their label.
PURPOSE_LABELS = {
    "품         명": ("품명",),
    "수 량  /  단위": ("수량단위",),
    "모    델    명": ("모델명",),
    "연    구    명": ("연구명",),
    "연 구 책 임 자": ("연구책임자", "자금명"),
    "용  도  개  요": ("용도개요",),
    "활용예상빈도": ("활용빈도",),
    "기  보 유 량": ("기보유량", "공동활용_dummy"),  # second column actually holds 기보유량_2 in sample
    "공동활용가능성": ("공동활용", "공동활용_2"),
    "장  비  구  분": ("장비구분",),
    "설치 사용 장소": ("설치장소",),
    "기타 특기 사항": ("특기사항",),
}


def _purpose_cell_value(cell: etree._Element) -> str:
    runs = _cell_text_runs(cell)
    return "".join((t.text or "") for t in runs)


def _purpose_set_multiline(cell: etree._Element, value: str, paragraph_proto: etree._Element | None = None) -> None:
    """Replace cell content with arbitrary multi-line text (one <hp:p> per line)."""
    sublist = cell.find(HP + "subList")
    if sublist is None:
        _set_cell_text(cell, value)
        return
    paragraphs = list(sublist.findall(HP + "p"))
    proto = paragraph_proto or (paragraphs[0] if paragraphs else None)
    if proto is None:
        _set_cell_text(cell, value)
        return
    for child in paragraphs:
        sublist.remove(child)
    lines = value.splitlines() if value else [""]
    for line in lines:
        p = deepcopy(proto)
        _set_paragraph_text(p, line)
        sublist.append(p)


def fill_purpose(template_root: Path, output_path: Path, data: dict) -> None:
    work = Path(tempfile.mkdtemp(prefix="hwpx_purpose_"))
    try:
        _unzip(template_root, work)
        tree, section_path = _load_section(work)
        root = tree.getroot()

        # Locate each row by finding the cell whose text contains the label.
        # Then update siblings on the same row.
        rows_by_index: dict[int, list[etree._Element]] = {}
        for cell in _all_cells(root):
            row, _ = _cell_addr(cell)
            rows_by_index.setdefault(row, []).append(cell)
        for cells in rows_by_index.values():
            cells.sort(key=lambda c: _cell_addr(c)[1])

        def find_row(label_fragment: str) -> list[etree._Element] | None:
            for cells in rows_by_index.values():
                if not cells:
                    continue
                first = cells[0]
                text = _purpose_cell_value(first).replace(" ", "")
                if label_fragment.replace(" ", "") in text:
                    return cells
            return None

        # 품명 — row label "품 명", value cell is the merged 6-col second cell
        row = find_row("품명")
        if row and len(row) >= 2:
            _set_cell_text(row[1], data.get("품명", ""))

        # 수량 / 단위 + 금액
        row = find_row("수량/단위")
        if row and len(row) >= 4:
            _set_cell_text(row[1], data.get("수량단위", ""))
            _set_cell_text(row[3], data.get("금액", ""))

        # 모델명 + HSK
        row = find_row("모델명")
        if row and len(row) >= 4:
            _set_cell_text(row[1], data.get("모델명", "-"))
            _set_cell_text(row[3], data.get("HSK", ""))

        # 연구명 + 연구기간
        row = find_row("연구명")
        if row and len(row) >= 4:
            _set_cell_text(row[1], data.get("연구명", ""))
            _set_cell_text(row[3], data.get("연구기간", ""))

        # 연구책임자 + 자금명
        row = find_row("연구책임자")
        if row:
            if len(row) >= 2:
                _set_cell_text(row[1], data.get("연구책임자", ""))
            if len(row) >= 4:
                _set_cell_text(row[3], data.get("자금명", ""))

        # 용도개요 (merged 6-col cell, multi-line body)
        row = find_row("용도개요")
        if row and len(row) >= 2:
            _purpose_set_multiline(row[1], data.get("용도개요", ""))

        # 활용예상빈도
        row = find_row("활용예상빈도")
        if row and len(row) >= 2:
            _set_cell_text(row[1], data.get("활용빈도", ""))

        # 기보유량 + 공동활용가능성_extra (sample shows "확인 불가능" 두 번)
        row = find_row("기보유량")
        if row and len(row) >= 3:
            _set_cell_text(row[1], data.get("기보유량", ""))
            _set_cell_text(row[2], data.get("기보유량_2", data.get("기보유량", "")))

        # 공동활용가능성
        row = find_row("공동활용가능성")
        if row and len(row) >= 3:
            _set_cell_text(row[1], data.get("공동활용", ""))
            _set_cell_text(row[2], data.get("공동활용_2", data.get("공동활용", "")))

        # 장비구분
        row = find_row("장비구분")
        if row and len(row) >= 2:
            _set_cell_text(row[1], data.get("장비구분", ""))

        # 설치 사용 장소
        row = find_row("설치사용장소")
        if row and len(row) >= 2:
            _set_cell_text(row[1], data.get("설치장소", ""))

        # 기타 특기 사항
        row = find_row("기타특기사항")
        if row and len(row) >= 2:
            _set_cell_text(row[1], data.get("특기사항", ""))

        # Footer paragraphs: 구매요구부서명 / 연구책임자
        for label, key in (("구매요구부서명", "부서명"), ("연구책임자", "연구책임자_서명")):
            p = _find_paragraph_with_text(root, label)
            if p is not None:
                _replace_label_value(p, label, data.get(key, ""))

        # Expand 용도개요 cell (row 5, col 1) when its body grew beyond the
        # template's prepared height.
        _expand_cell_to_fit(root, (5, 1))
        _reset_paragraph_ids(root)
        _strip_layout_caches(root)

        _save_section(tree, section_path)
        _rezip(work, output_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: build_forms.py <input.json> <output_dir>", file=sys.stderr)
        return 2

    payload_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    with payload_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    skill_root = Path(__file__).resolve().parent.parent
    spec_template = skill_root / "assets" / "templates" / "spec_template.hwpx"
    purpose_template = skill_root / "assets" / "templates" / "purpose_template.hwpx"

    basename = payload.get("output_basename", "purchase_form")

    spec = payload.get("spec")
    if spec:
        out = out_dir / f"{basename} 규격서.hwpx"
        fill_spec(spec_template, out, spec)
        print(f"[purchase-requisition] wrote {out}")

    purpose = payload.get("purpose")
    if purpose:
        out = out_dir / f"{basename} 용도설명서.hwpx"
        fill_purpose(purpose_template, out, purpose)
        print(f"[purchase-requisition] wrote {out}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv))
