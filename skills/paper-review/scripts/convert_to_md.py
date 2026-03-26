"""논문 문서(docx/pdf)를 markdown으로 누락 없이 변환하는 스크립트."""
import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _get_hyperlinks(para):
    """단락에서 하이퍼링크 URL과 텍스트를 추출."""
    from docx.oxml.ns import qn

    links = {}
    for hyperlink in para._element.findall(qn("w:hyperlink")):
        # External hyperlink via relationship
        r_id = hyperlink.get(qn("r:id"))
        url = None
        if r_id:
            try:
                url = para.part.rels[r_id].target_ref
            except (KeyError, AttributeError):
                pass
        # Collect hyperlink text
        text = "".join(
            node.text or "" for node in hyperlink.findall(qn("w:r") + "/" + qn("w:t"))
        )
        if url:
            links[text] = url
    return links


def _para_to_markdown(para):
    """단락을 markdown 문자열로 변환 (하이퍼링크 포함)."""
    from docx.oxml.ns import qn

    hyperlinks = _get_hyperlinks(para)
    result = ""

    for child in para._element:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "hyperlink":
            # Hyperlink element
            r_id = child.get(qn("r:id"))
            url = None
            if r_id:
                try:
                    url = para.part.rels[r_id].target_ref
                except (KeyError, AttributeError):
                    pass
            h_text = "".join(
                node.text or "" for node in child.findall(qn("w:r") + "/" + qn("w:t"))
            )
            if url and h_text:
                result += url  # DOI URL을 직접 삽입
            elif url:
                result += url
            else:
                result += h_text

        elif tag == "r":
            # Normal run
            texts = child.findall(qn("w:t"))
            t = "".join(node.text or "" for node in texts)
            if not t:
                continue
            rpr = child.find(qn("w:rPr"))
            is_bold = rpr is not None and rpr.find(qn("w:b")) is not None
            is_italic = rpr is not None and rpr.find(qn("w:i")) is not None
            if is_bold and is_italic:
                t = f"***{t}***"
            elif is_bold:
                t = f"**{t}**"
            elif is_italic:
                t = f"*{t}*"
            result += t

    return result


def convert_docx(input_path):
    """docx 파일을 markdown으로 변환."""
    from docx import Document

    doc = Document(input_path)
    lines = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue

        # Heading detection
        if para.style and para.style.name.startswith("Heading"):
            try:
                level = int(para.style.name.replace("Heading", "").strip())
            except ValueError:
                level = 1
            lines.append(f"{'#' * level} {text}")
            continue

        # Convert with hyperlinks
        formatted = _para_to_markdown(para)
        if formatted.strip():
            lines.append(formatted)
        else:
            lines.append(text)

    return "\n".join(lines)


def convert_pdf(input_path):
    """pdf 파일을 markdown으로 변환."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF(fitz) 패키지가 필요합니다. 설치: pip install PyMuPDF", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(input_path)
    lines = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    text = ""
                    for span in line["spans"]:
                        t = span["text"]
                        size = span["size"]
                        flags = span["flags"]
                        # bold = flags & 2^4, italic = flags & 2^1
                        is_bold = flags & 16
                        is_italic = flags & 2
                        if is_bold and is_italic:
                            t = f"***{t}***"
                        elif is_bold:
                            t = f"**{t}**"
                        elif is_italic:
                            t = f"*{t}*"
                        text += t
                    if text.strip():
                        lines.append(text.strip())
            elif block["type"] == 1:  # image block
                lines.append(f"![Image on page {page_num + 1}]()")
                lines.append("")

        # Page separator
        lines.append("")
        lines.append(f"<!-- Page {page_num + 1} -->")
        lines.append("")

    doc.close()
    return "\n".join(lines)


def extract_doi_list(md_text):
    """markdown 텍스트에서 DOI 목록을 추출."""
    doi_pattern = r"(10\.\d{4,9}/[^\s,;\]\"'>]+)"
    dois = re.findall(doi_pattern, md_text)
    # Clean trailing punctuation
    cleaned = []
    for doi in dois:
        doi = doi.rstrip(".")
        cleaned.append(doi)
    return list(dict.fromkeys(cleaned))  # deduplicate preserving order


def main():
    parser = argparse.ArgumentParser(description="논문 문서를 markdown으로 변환")
    parser.add_argument("--input", required=True, help="입력 파일 경로 (docx/pdf)")
    parser.add_argument("--output", required=True, help="출력 폴더 경로")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".docx":
        md_text = convert_docx(input_path)
    elif ext == ".pdf":
        md_text = convert_pdf(input_path)
    else:
        print(f"ERROR: 지원하지 않는 형식: {ext} (docx/pdf만 지원)", file=sys.stderr)
        sys.exit(1)

    # Save manuscript.md
    md_path = os.path.join(output_dir, "manuscript.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"변환 완료: {md_path}")

    # Extract and save DOI list
    dois = extract_doi_list(md_text)
    if dois:
        doi_path = os.path.join(output_dir, "doi_list.txt")
        with open(doi_path, "w", encoding="utf-8") as f:
            for i, doi in enumerate(dois, 1):
                f.write(f"{i:02d}\t{doi}\n")
        print(f"DOI 추출: {len(dois)}개 → {doi_path}")
    else:
        print("경고: DOI를 찾지 못했습니다. 참고문헌에 DOI가 포함되어 있는지 확인하세요.")


if __name__ == "__main__":
    main()
