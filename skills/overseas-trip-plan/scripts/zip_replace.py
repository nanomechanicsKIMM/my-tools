#!/usr/bin/env python3
"""zip_replace.py — HWPX ZIP 내 텍스트 치환

HWPX ZIP 컨테이너 내부의 모든 XML/RDF/HPF 파트에서
지정한 문자열을 치환한다. 이미지·바이너리 파일은 무손실 복사.

Usage:
    from zip_replace import zip_replace
    zip_replace("input.hwpx", "output.hwpx", {"old": "new", ...})

또는 CLI:
    python zip_replace.py input.hwpx output.hwpx --pairs '{"old":"new"}'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

TEXT_EXTS = (".xml", ".rdf", ".hpf", ".rels")


def zip_replace(src_path: str | Path, dst_path: str | Path, replacements: dict[str, str]) -> None:
    """HWPX ZIP 내 모든 텍스트 파트에서 치환 수행.

    - `mimetype` 파트는 항상 첫 번째에 위치하고 uncompressed(ZIP_STORED)로 유지.
    - 텍스트 파트(.xml/.rdf/.hpf/.rels)는 UTF-8로 디코드 → 치환 → 재인코드.
    - 이미지·바이너리는 원본 그대로 복사.
    """
    src_path = str(src_path)
    dst_path = str(dst_path)
    tmp_path = dst_path + ".tmp"

    # 치환 대상이 없으면 단순 복사
    if not replacements:
        import shutil
        shutil.copy2(src_path, tmp_path)
    else:
        with zipfile.ZipFile(src_path, "r") as zin:
            # 원본의 파일 순서를 유지 (mimetype first)
            infolist = zin.infolist()
            with zipfile.ZipFile(tmp_path, "w") as zout:
                for item in infolist:
                    data = zin.read(item.filename)

                    # 텍스트 파트만 치환
                    if item.filename.lower().endswith(TEXT_EXTS):
                        try:
                            text = data.decode("utf-8")
                            for old, new in replacements.items():
                                if old:
                                    text = text.replace(old, new)
                            data = text.encode("utf-8")
                        except UnicodeDecodeError:
                            # 치환 실패 시 원본 유지
                            pass

                    # mimetype은 STORED, 나머지는 DEFLATED
                    compress_type = (
                        zipfile.ZIP_STORED
                        if item.filename == "mimetype"
                        else zipfile.ZIP_DEFLATED
                    )

                    new_info = zipfile.ZipInfo(
                        filename=item.filename,
                        date_time=item.date_time,
                    )
                    new_info.compress_type = compress_type
                    new_info.external_attr = item.external_attr
                    zout.writestr(new_info, data)

    # 원자적 교체
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.rename(tmp_path, dst_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="HWPX ZIP-level 텍스트 치환")
    parser.add_argument("src", help="원본 HWPX 파일")
    parser.add_argument("dst", help="출력 HWPX 파일")
    parser.add_argument(
        "--pairs",
        help='치환 쌍 JSON. 예: {"old":"new","foo":"bar"}',
        default="{}",
    )
    parser.add_argument(
        "--pairs-file",
        help="치환 쌍 JSON 파일 경로 (--pairs 와 병합)",
    )
    args = parser.parse_args()

    replacements: dict[str, str] = json.loads(args.pairs)
    if args.pairs_file:
        with open(args.pairs_file, encoding="utf-8") as f:
            replacements.update(json.load(f))

    if not Path(args.src).exists():
        print(f"[ERROR] 원본 파일 없음: {args.src}", file=sys.stderr)
        return 2

    zip_replace(args.src, args.dst, replacements)
    print(f"✓ 치환 완료: {args.dst} ({len(replacements)}개 키)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
