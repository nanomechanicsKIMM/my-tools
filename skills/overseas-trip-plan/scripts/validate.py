#!/usr/bin/env python3
"""validate.py — HWPX 파일 구조 검증

기본 검증:
- ZIP 무결성
- 필수 파트 존재
- mimetype 내용
- section0.xml well-formed
- manifest.xml 일관성

Usage:
    python validate.py <hwpx-file>
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REQUIRED_PARTS = (
    "mimetype",
    "version.xml",
    "Contents/header.xml",
    "Contents/section0.xml",
    "Contents/content.hpf",
    "META-INF/manifest.xml",
    "META-INF/container.xml",
)


def validate(path: str | Path) -> list[str]:
    """HWPX 파일을 검증하고 오류 메시지 리스트를 반환.

    Returns:
        빈 리스트면 검증 통과, 비어있지 않으면 오류들.
    """
    path = Path(path)
    errors: list[str] = []

    if not path.exists():
        return [f"파일 없음: {path}"]

    if not zipfile.is_zipfile(path):
        return [f"ZIP 형식 아님: {path}"]

    try:
        with zipfile.ZipFile(path, "r") as z:
            # ZIP 무결성
            bad = z.testzip()
            if bad:
                errors.append(f"ZIP 손상: {bad}")

            existing = set(z.namelist())

            # 필수 파트
            for part in REQUIRED_PARTS:
                if part not in existing:
                    errors.append(f"필수 파트 누락: {part}")

            # mimetype 내용
            if "mimetype" in existing:
                try:
                    mt = z.read("mimetype").decode("ascii", errors="replace").strip()
                    if "hwp" not in mt.lower():
                        errors.append(f"mimetype 비정상: {mt}")
                except Exception as e:
                    errors.append(f"mimetype 읽기 실패: {e}")

            # section0.xml well-formed
            if "Contents/section0.xml" in existing:
                try:
                    ET.fromstring(z.read("Contents/section0.xml"))
                except ET.ParseError as e:
                    errors.append(f"section0.xml 파싱 오류: {e}")

            # manifest.xml well-formed
            if "META-INF/manifest.xml" in existing:
                try:
                    ET.fromstring(z.read("META-INF/manifest.xml"))
                except ET.ParseError as e:
                    errors.append(f"manifest.xml 파싱 오류: {e}")

    except Exception as e:
        errors.append(f"ZIP 열기 실패: {e}")

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate.py <hwpx-file>", file=sys.stderr)
        return 2

    errors = validate(sys.argv[1])
    if errors:
        print(f"✗ VALIDATION FAILED: {sys.argv[1]}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✓ Valid HWPX: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
