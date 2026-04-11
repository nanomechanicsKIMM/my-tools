#!/usr/bin/env python3
"""fetch_reference_pdf.py — 학회 Advance Program PDF 다운로드 및 참고자료 보관

학회 공식 Advance Program PDF를 `references/` 디렉터리에 저장하고
`manifest.json`을 갱신한다. 동일 URL 재다운로드 시 SHA256 비교로 변경 감지.

Usage:
    PYTHONUTF8=1 python fetch_reference_pdf.py \\
        --url "https://www.displayweek.org/files/advance_program.pdf" \\
        --output-dir references/ \\
        [--filename DisplayWeek2026_AP.pdf]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 180
USER_AGENT = "Mozilla/5.0 (overseas-trip-plan skill; PDF reference fetcher)"


def _derive_filename(url: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    parsed = urlparse(url)
    last = unquote(parsed.path.rstrip("/").split("/")[-1])
    if not last or "." not in last:
        return "advance_program.pdf"
    if not last.lower().endswith(".pdf"):
        return last + ".pdf"
    return last


def _compute_sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        return {"references": []}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[WARN] manifest.json 손상, 새로 생성", file=sys.stderr)
        return {"references": []}


def _save_manifest(manifest_path: Path, manifest: dict) -> None:
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_pdf(
    url: str,
    output_dir: str | Path,
    filename: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict | None:
    """PDF를 다운로드하고 manifest.json을 갱신한다.

    Returns:
        성공 시 레코드 딕셔너리, 실패 시 None.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = _derive_filename(url, filename)
    output_path = out_dir / filename
    manifest_path = out_dir / "manifest.json"

    print(f"[FETCH] {url}")
    print(f"[OUT  ] {output_path}")

    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=min(timeout, MAX_TIMEOUT)) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
    except HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"[ERROR] URL error: {e.reason}", file=sys.stderr)
        return None
    except TimeoutError:
        print(f"[ERROR] Timeout ({timeout}s)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected: {e}", file=sys.stderr)
        return None

    # PDF 매직 바이트 확인 (%PDF)
    is_pdf = data[:4] == b"%PDF"
    if not is_pdf:
        print(
            f"[WARN] PDF magic bytes not found (Content-Type: {content_type}). "
            "파일은 저장되지만 PDF가 아닐 수 있음.",
            file=sys.stderr,
        )

    sha256 = _compute_sha256(data)
    size = len(data)

    # 중복 체크
    manifest = _load_manifest(manifest_path)
    for existing in manifest.get("references", []):
        if existing.get("sha256") == sha256:
            print(f"[SKIP ] 동일 파일 이미 존재: {existing.get('filename')} (SHA256 일치)")
            return existing

    # 파일 저장
    output_path.write_bytes(data)

    record = {
        "filename": filename,
        "url": url,
        "sha256": sha256,
        "size_bytes": size,
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        "is_pdf": is_pdf,
        "content_type": content_type,
    }
    manifest.setdefault("references", []).append(record)
    _save_manifest(manifest_path, manifest)

    print(f"[OK   ] 저장 완료 ({size:,} bytes)")
    print(f"        SHA256: {sha256[:16]}...")
    print(f"        manifest: {manifest_path}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="학회 Advance Program PDF 다운로드 → references/ 저장"
    )
    parser.add_argument("--url", required=True, help="PDF 공식 URL")
    parser.add_argument(
        "--output-dir",
        default="references",
        help="저장 디렉터리 (기본: ./references)",
    )
    parser.add_argument("--filename", help="저장 파일명 (기본: URL에서 추출)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP 타임아웃 초 (최대 {MAX_TIMEOUT})",
    )
    args = parser.parse_args()

    result = fetch_pdf(args.url, args.output_dir, args.filename, args.timeout)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
