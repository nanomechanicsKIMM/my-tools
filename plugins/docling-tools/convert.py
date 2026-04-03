#!/usr/bin/env python3
"""Convert documents (PDF, DOCX, PPTX, XLSX, HTML, etc.) to Markdown using docling."""
import argparse
import os
import sys
from pathlib import Path


def _patch_ssl_for_hf():
    """Bypass SSL verification for HuggingFace Hub (corporate proxy workaround)."""
    try:
        import httpx
        _orig_init = httpx.Client.__init__
        def _patched_init(self, *args, **kwargs):
            kwargs.setdefault("verify", False)
            return _orig_init(self, *args, **kwargs)
        httpx.Client.__init__ = _patched_init
    except ImportError:
        pass


def convert_file(input_path: str, output_path: str | None = None) -> str:
    """Convert a single file to Markdown."""
    _patch_ssl_for_hf()

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    pipeline_options = PdfPipelineOptions()
    # Windows symlink 권한 문제 우회: 테이블 구조 모델 비활성화
    # 개발자 모드 활성화 시 True로 변경 가능
    pipeline_options.do_table_structure = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    result = converter.convert(input_path)
    md_content = result.document.export_to_markdown()

    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".md"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convert documents to Markdown")
    parser.add_argument("input", nargs="+", help="Input file(s) to convert")
    parser.add_argument("-o", "--output", help="Output file (single input only)")
    parser.add_argument(
        "--table-structure",
        action="store_true",
        help="Enable table structure model (requires Windows Developer Mode)",
    )
    args = parser.parse_args()

    if args.output and len(args.input) > 1:
        print("Error: -o/--output can only be used with a single input file", file=sys.stderr)
        sys.exit(1)

    for input_file in args.input:
        if not os.path.isfile(input_file):
            print(f"Error: {input_file} not found", file=sys.stderr)
            continue

        output = args.output if args.output else None
        out_path = convert_file(input_file, output)
        print(f"Converted: {input_file} -> {out_path}")


if __name__ == "__main__":
    main()
