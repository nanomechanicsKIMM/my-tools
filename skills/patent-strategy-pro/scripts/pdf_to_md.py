#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF to Markdown converter for RFP documents.
Preserves document structure: headings, tables, lists, Korean text.
Uses pdfplumber for reliable text extraction.

Key behaviors:
  - Table regions are excluded from raw text extraction to prevent duplicates
  - Tables are separately extracted as structured Markdown tables
  - "RFP명" cell value is used as YAML title when available
  - Heading detection is conservative: only numbered headings, not sentence fragments

Usage:
  python pdf_to_md.py <input.pdf> -o <output.md> [--title "RFP Title"]
  python pdf_to_md.py rfp.pdf -o rfp.md
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def extract_with_pdfplumber(pdf_path: Path) -> list[dict]:
    """
    Extract pages as structured dicts with text and tables.
    Text extraction excludes table regions to prevent duplicate content.
    """
    try:
        import pdfplumber
    except ImportError:
        print("pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_data = {"page": page_num, "text": "", "tables": []}

            # Find tables and their bounding boxes
            table_objs = page.find_tables()
            table_bboxes = [t.bbox for t in table_objs]

            # Extract tables as structured data
            for t in table_objs:
                table = t.extract()
                if table:
                    page_data["tables"].append(table)

            # Extract text OUTSIDE table regions only (avoids duplicate content)
            if table_bboxes:
                def not_in_any_table(obj):
                    for bbox in table_bboxes:
                        x0, top, x1, bottom = bbox
                        # Small tolerance (2pt) for floating-point bbox edges
                        if (obj.get("x0", 0) >= x0 - 2 and
                                obj.get("x1", 0) <= x1 + 2 and
                                obj.get("top", 0) >= top - 2 and
                                obj.get("bottom", 0) <= bottom + 2):
                            return False
                    return True

                filtered_page = page.filter(not_in_any_table)
                text = filtered_page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            else:
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            page_data["text"] = text
            pages.append(page_data)

    return pages


def clean_text_line(line: str) -> str:
    """Clean a single line of extracted text."""
    line = re.sub(r"\s{3,}", "  ", line)
    line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", line)
    return line.strip()


def detect_heading_level(line: str) -> int:
    """
    Detect markdown heading level from text patterns.
    Conservative: only well-formed numbered headings, NOT sentence fragments.
    Returns 0 if not a heading.
    """
    stripped = line.strip()
    if not stripped:
        return 0

    # Never treat lines starting with bullet chars as headings
    if re.match(r"^[-*•◦·▪▸ㅇ\-]\s", stripped):
        return 0

    # Never treat lines that are mid-sentence fragments (don't end at a natural break
    # and are longer than a typical heading)
    if len(stripped) > 70:
        return 0

    # Level 1: "제1장", Roman numerals
    if re.match(r"^(제\s*\d+\s*장|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.?\s+\S)", stripped):
        return 1

    # Level 2: "1. 제목" (number + dot + space + Korean/English capital)
    # Must be a complete short phrase, not mid-sentence
    if (re.match(r"^\d+\.\s+[가-힣A-Z]", stripped) and
            len(stripped) < 60 and
            not stripped.endswith(("하고,", "있으며,", "되어,", "하여,", "위해,"))):
        return 2

    # Level 3: "1.1 제목"
    if re.match(r"^\d+\.\d+\.?\s+[가-힣A-Z]", stripped) and len(stripped) < 60:
        return 3

    # Level 4: "1.1.1", "①"
    if re.match(r"^\d+\.\d+\.\d+\.?\s+", stripped) and len(stripped) < 60:
        return 4
    if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s+", stripped):
        return 4

    return 0


def table_to_markdown(table: list[list]) -> str:
    """Convert pdfplumber table to Markdown table format."""
    if not table:
        return ""

    rows = []
    for row in table:
        cleaned = []
        for cell in row:
            if cell is None:
                cleaned.append("")
            else:
                # Normalize whitespace within cell
                cell_str = str(cell).strip()
                cell_str = re.sub(r"\s*\n\s*", " ", cell_str)
                cleaned.append(cell_str)
        rows.append(cleaned)

    if not rows:
        return ""

    col_count = max(len(r) for r in rows)
    rows = [r + [""] * (col_count - len(r)) for r in rows]

    lines = []
    header = rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * col_count) + "|")
    for row in rows[1:]:
        if any(c.strip() for c in row):
            lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def is_list_item(line: str) -> bool:
    """Check if line looks like a list item (including Korean bullets)."""
    return bool(
        re.match(r"^[-*•◦·▪▸ㅇ]\s+", line.strip()) or
        re.match(r"^[가나다라마바사아자차카타파하]\.\s+", line.strip())
    )


def extract_rfp_title_from_tables(tables: list[list[list]]) -> str:
    """
    Look for 'RFP명' key in tables and return the adjacent cell value.
    Korean RFPs typically have a header table with RFP명 → title.
    """
    for table in tables:
        for row in table:
            if not row:
                continue
            for i, cell in enumerate(row):
                cell_str = str(cell).strip() if cell else ""
                if "RFP명" in cell_str:
                    # Search subsequent cells in the same row for the title value
                    for j in range(i + 1, len(row)):
                        val = str(row[j]).strip() if row[j] else ""
                        if val and len(val) > 10 and "RFP명" not in val:
                            # Clean up newlines and whitespace
                            val = re.sub(r"\s*\n\s*", " ", val).strip()
                            # Remove TRL annotations
                            val = re.sub(r"\s*\(TRL[^)]*\)", "", val).strip()
                            if len(val) > 10:
                                return val
    return ""


def extract_title_from_pages(pages: list[dict]) -> str:
    """
    Extract document title. Priority:
    1. 'RFP명' cell in first-page tables
    2. First substantial non-fragment line from page text
    """
    if not pages:
        return ""

    # Priority 1: RFP명 cell from tables (most reliable for Korean RFPs)
    for page_data in pages[:2]:  # Check first 2 pages
        title = extract_rfp_title_from_tables(page_data.get("tables", []))
        if title:
            return title

    # Priority 2: first substantial line from page text
    first_text = pages[0].get("text", "") or ""
    lines = [l.strip() for l in first_text.split("\n") if l.strip()]
    for line in lines[:10]:
        if len(line) > 10 and not line.startswith("http"):
            # Skip lines that look like table header fragments
            if not re.match(r"^(목적|내용|성과물|특성|지원유형|관리번호|유형코드)", line):
                return line
    return ""


def pages_to_markdown(pages: list[dict], title: str = "") -> str:
    """Convert extracted pages to Markdown text."""
    today = datetime.now().strftime("%Y-%m-%d")
    frontmatter = f"""---
title: "{title or 'RFP Document'}"
created: "{today}"
tags: [RFP, 특허분석, IP전략]
---

"""
    blocks = []

    for page_data in pages:
        text = page_data.get("text", "")
        lines = text.split("\n") if text else []
        page_blocks = []

        for line in lines:
            line = clean_text_line(line)
            if not line:
                continue

            heading_level = detect_heading_level(line)
            if heading_level > 0:
                prefix = "#" * heading_level
                page_blocks.append(f"\n{prefix} {line}\n")
            elif is_list_item(line):
                item_text = re.sub(r"^[-*•◦·▪▸ㅇ]\s+", "", line.strip())
                item_text = re.sub(r"^[가나다라마바사아자차카타파하]\.\s+", "", item_text)
                page_blocks.append(f"- {item_text}")
            else:
                page_blocks.append(line)

        # Add tables
        for table in page_data.get("tables", []):
            table_md = table_to_markdown(table)
            if table_md:
                page_blocks.append(f"\n{table_md}\n")

        if page_blocks:
            blocks.extend(page_blocks)

    content = "\n".join(blocks)
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    content = re.sub(r"(\n#+\s)", r"\n\1", content)

    return frontmatter + content


def main():
    ap = argparse.ArgumentParser(
        description="Convert PDF RFP to Markdown for patent strategy analysis"
    )
    ap.add_argument("input_pdf", help="Input PDF file path")
    ap.add_argument("-o", "--output", required=True, help="Output Markdown file path")
    ap.add_argument("--title", type=str, default=None,
                    help="Document title (auto-detected from RFP명 cell if not given)")
    args = ap.parse_args()

    pdf_path = Path(args.input_pdf)
    out_path = Path(args.output)

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting PDF: {pdf_path}", file=sys.stderr)
    pages = extract_with_pdfplumber(pdf_path)
    print(f"Extracted {len(pages)} pages.", file=sys.stderr)

    title = args.title or extract_title_from_pages(pages)
    if title:
        print(f"Title detected: {title}", file=sys.stderr)

    md_content = pages_to_markdown(pages, title=title)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_content, encoding="utf-8")
    print(f"Converted: {out_path} ({len(md_content)} chars, {len(pages)} pages)")


if __name__ == "__main__":
    main()
