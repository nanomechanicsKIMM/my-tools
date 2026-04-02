#!/usr/bin/env python3
"""Convert PDF to Markdown using MinerU (opendatalab/MinerU)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def convert_file(input_path: str, output_dir: str | None = None) -> str:
    """Convert a single PDF file to Markdown using MinerU CLI."""
    input_path = Path(input_path).resolve()
    stem = input_path.stem
    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent

    # 1. MinerU 실행 (임시 디렉토리에 출력)
    temp_dir = tempfile.mkdtemp(prefix="mineru_")
    try:
        result = subprocess.run(
            ["mineru", str(input_path), "-o", temp_dir],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"Error: MinerU failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        # 2. 출력 파일 탐색
        #    MinerU 출력 구조: temp_dir/{stem}/{stem}.md + images/
        md_source = Path(temp_dir) / stem / f"{stem}.md"
        if not md_source.exists():
            # 대체 경로 탐색 (MinerU 버전에 따라 다를 수 있음)
            md_candidates = list(Path(temp_dir).rglob("*.md"))
            if md_candidates:
                md_source = md_candidates[0]
            else:
                print(f"Error: No MD output found in {temp_dir}", file=sys.stderr)
                sys.exit(1)

        images_source = md_source.parent / "images"

        # 3. MD 파일 이동
        md_target = target_dir / f"{stem}.md"
        shutil.copy2(str(md_source), str(md_target))

        # 4. images/ 이동 (존재 시)
        if images_source.exists() and any(images_source.iterdir()):
            images_target = target_dir / f"{stem}_images"
            if images_target.exists():
                shutil.rmtree(images_target)
            shutil.copytree(str(images_source), str(images_target))

            # 5. MD 내 이미지 경로 수정
            content = md_target.read_text(encoding="utf-8")
            content = content.replace("images/", f"{stem}_images/")
            md_target.write_text(content, encoding="utf-8")

        print(f"Converted: {input_path} -> {md_target}")
        return str(md_target)

    finally:
        # 6. 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using MinerU")
    parser.add_argument("input", nargs="+", help="Input PDF file(s)")
    parser.add_argument("-o", "--output", help="Output directory")
    args = parser.parse_args()

    for input_file in args.input:
        if not os.path.isfile(input_file):
            print(f"Error: {input_file} not found", file=sys.stderr)
            continue
        convert_file(input_file, args.output)


if __name__ == "__main__":
    main()
