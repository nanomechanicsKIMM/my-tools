#!/usr/bin/env python
"""
pdf_to_md.py — opendataloader-pdf wrapper for the pdf-to-md skill.

Why a wrapper:
- Verifies Java availability up-front with a clear error.
- Forces UTF-8 stdout on Windows consoles so logs aren't garbled.
- Batches multi-input into a single convert() call (one JVM cold start,
  not N).
- Adds optional Obsidian YAML frontmatter without touching upstream code.

Use from the skill — the README documents typical invocations.
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional


def _force_utf8_stdout() -> None:
    """Windows 콘솔에서 한글/이모지 깨짐 방지."""
    if sys.platform.startswith("win"):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
        except Exception:
            pass


def _ensure_java_on_path() -> None:
    """Locate java and inject its directory into PATH if missing.

    Why: opendataloader_pdf shells out to `java` via subprocess, which
    relies on PATH. On Windows, JDKs are often installed but not on PATH
    (Adoptium installer, conda's bundled openjdk, JetBrains JBR, etc.).
    Probing the common locations lets the skill "just work" without the
    user editing system env vars.
    """
    if shutil.which("java") is not None:
        return

    candidates: List[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin" / "java.exe")
    # Same Python's conda env (most common on this machine)
    candidates.append(Path(sys.prefix) / "Library" / "bin" / "java.exe")
    # Generic conda fallback (any user)
    candidates.append(Path.home() / "miniconda3" / "Library" / "bin" / "java.exe")
    candidates.append(Path.home() / "miniconda3" / "bin" / "java")

    for cand in candidates:
        if cand.exists():
            os.environ["PATH"] = str(cand.parent) + os.pathsep + os.environ.get("PATH", "")
            return

    sys.stderr.write(
        "[pdf-to-md] ERROR: 'java' not found in PATH or known locations.\n"
        "opendataloader-pdf requires Java 11+.\n"
        "  Install: https://adoptium.net/  "
        "(or: winget install EclipseAdoptium.Temurin.21.JDK)\n"
        "  Or set JAVA_HOME to an existing JDK install.\n"
    )
    sys.exit(2)


def _expand_inputs(inputs: List[str]) -> List[str]:
    """Resolve directories to their .pdf children (non-recursive),
    pass through files as-is. opendataloader also accepts directories
    natively, but expanding here gives clearer error messages."""
    out: List[str] = []
    for raw in inputs:
        p = Path(raw)
        if not p.exists():
            sys.stderr.write(f"[pdf-to-md] WARNING: not found: {raw}\n")
            continue
        if p.is_dir():
            out.append(str(p))  # let convert() handle directory recursion
        else:
            out.append(str(p))
    return out


def _add_obsidian_frontmatter(md_path: Path, source_pdf: Path) -> None:
    if not md_path.exists():
        return
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if text.lstrip().startswith("---"):
        return  # already has frontmatter
    fm = (
        "---\n"
        f'source: "{source_pdf.name}"\n'
        f"converted: {date.today().isoformat()}\n"
        "tool: opendataloader-pdf\n"
        "type: pdf-import\n"
        "---\n\n"
    )
    md_path.write_text(fm + text, encoding="utf-8")


def _post_process_obsidian(output_dir: Path, inputs: List[str]) -> None:
    """For each input PDF, locate the produced .md and prepend frontmatter."""
    pdf_stems = []
    for raw in inputs:
        p = Path(raw)
        if p.is_file() and p.suffix.lower() == ".pdf":
            pdf_stems.append(p)
        elif p.is_dir():
            pdf_stems.extend(p.glob("*.pdf"))
    for pdf in pdf_stems:
        # opendataloader writes <stem>.md next to the PDF or under output_dir
        candidate = output_dir / f"{pdf.stem}.md"
        if not candidate.exists():
            candidate = pdf.with_suffix(".md")
        if candidate.exists():
            _add_obsidian_frontmatter(candidate, pdf)


def main(argv: Optional[List[str]] = None) -> int:
    _force_utf8_stdout()

    ap = argparse.ArgumentParser(
        prog="pdf_to_md",
        description="Convert PDF(s) to Markdown via opendataloader-pdf.",
    )
    ap.add_argument(
        "--input", "-i", nargs="+", required=True,
        help="One or more PDF files or directories.",
    )
    ap.add_argument(
        "--output", "-o", default=None,
        help="Output directory. Default: same folder as input PDF.",
    )
    ap.add_argument(
        "--format", "-f", default="markdown-with-images",
        choices=[
            "markdown",
            "markdown-with-html",
            "markdown-with-images",
        ],
        help="Markdown variant. Default: markdown-with-images.",
    )
    ap.add_argument("--pages", default=None, help='e.g. "1,3,5-7"')
    ap.add_argument("--password", default=None, help="Password for encrypted PDFs.")
    ap.add_argument(
        "--table-method", default="default", choices=["default", "cluster"],
        help="Use 'cluster' for borderless tables.",
    )
    ap.add_argument("--use-struct-tree", action="store_true",
                    help="Trust tagged-PDF reading order if available.")
    ap.add_argument("--keep-line-breaks", action="store_true")
    ap.add_argument("--include-header-footer", action="store_true")
    ap.add_argument("--sanitize", action="store_true",
                    help="Mask emails / phones / IPs / cards / URLs.")
    ap.add_argument(
        "--obsidian", action="store_true",
        help="Prepend YAML frontmatter to each produced .md (Obsidian-friendly).",
    )
    ap.add_argument("--quiet", "-q", action="store_true")

    args = ap.parse_args(argv)

    _ensure_java_on_path()

    try:
        import opendataloader_pdf  # noqa: WPS433
    except ImportError:
        sys.stderr.write(
            "[pdf-to-md] ERROR: opendataloader_pdf not installed.\n"
            "  Install: pip install -U opendataloader-pdf\n"
        )
        return 2

    inputs = _expand_inputs(args.input)
    if not inputs:
        sys.stderr.write("[pdf-to-md] ERROR: no valid input paths.\n")
        return 2

    output_dir = Path(args.output) if args.output else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    convert_kwargs = {
        "input_path": inputs,
        "format": args.format,
        "table_method": args.table_method,
        "quiet": args.quiet,
    }
    if output_dir:
        convert_kwargs["output_dir"] = str(output_dir)
    if args.pages:
        convert_kwargs["pages"] = args.pages
    if args.password:
        convert_kwargs["password"] = args.password
    if args.use_struct_tree:
        convert_kwargs["use_struct_tree"] = True
    if args.keep_line_breaks:
        convert_kwargs["keep_line_breaks"] = True
    if args.include_header_footer:
        convert_kwargs["include_header_footer"] = True
    if args.sanitize:
        convert_kwargs["sanitize"] = True

    print(f"[pdf-to-md] converting {len(inputs)} input(s) → {output_dir or 'in-place'}")
    try:
        opendataloader_pdf.convert(**convert_kwargs)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[pdf-to-md] CLI failed (exit {e.returncode})\n")
        return e.returncode or 1
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[pdf-to-md] ERROR: {type(e).__name__}: {e}\n")
        return 1

    if args.obsidian:
        target_dir = output_dir if output_dir else Path(inputs[0]).parent
        _post_process_obsidian(target_dir, inputs)
        print("[pdf-to-md] Obsidian frontmatter applied.")

    print("[pdf-to-md] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
