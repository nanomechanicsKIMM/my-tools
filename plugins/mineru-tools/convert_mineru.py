#!/usr/bin/env python3.12
"""Convert PDF to Markdown using MinerU (opendatalab/MinerU)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _patch_transformers():
    """Patch transformers for MinerU compatibility.

    MinerU's unimernet uses find_pruneable_heads_and_indices which was
    removed in transformers >= 4.46, but MinerU's layout model requires >= 4.46
    for hgnet_v2 support.
    """
    try:
        from transformers import pytorch_utils
        if not hasattr(pytorch_utils, "find_pruneable_heads_and_indices"):
            import torch

            def find_pruneable_heads_and_indices(heads, n_heads, head_size, already_pruned_heads):
                mask = torch.ones(n_heads, head_size)
                heads = set(heads) - already_pruned_heads
                for head in heads:
                    head = head - sum(1 if h < head else 0 for h in already_pruned_heads)
                    mask[head] = 0
                mask = mask.view(-1).contiguous().eq(1)
                index = torch.arange(len(mask))[mask].long()
                return heads, index

            pytorch_utils.find_pruneable_heads_and_indices = find_pruneable_heads_and_indices
    except ImportError:
        pass


_patch_transformers()


def convert_file(input_path: str, output_dir: str | None = None) -> str:
    """Convert a single PDF file to Markdown using MinerU CLI."""
    input_path = Path(input_path).resolve()
    stem = input_path.stem
    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent

    # 1. MinerU 실행 (임시 디렉토리에 출력)
    #    MinerU CLI: mineru -p <path> -o <output> -b pipeline
    python312 = "C:/Users/JHKIM/AppData/Local/Programs/Python/Python312/python.exe"
    mineru_exe = str(Path(python312).parent / "Scripts" / "mineru.EXE")
    temp_dir = tempfile.mkdtemp(prefix="mineru_")
    try:
        result = subprocess.run(
            [mineru_exe, "-p", str(input_path), "-o", temp_dir, "-b", "pipeline"],
            capture_output=True,
            text=True,
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
