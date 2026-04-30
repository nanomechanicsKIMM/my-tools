#!/usr/bin/env python3
"""apply-config.py - Render claude-config templates and deploy to ~/.claude/

Cross-platform replacement for the previous sed/PowerShell-based scripts.
Python handles backslash-heavy paths safely.

Placeholders rendered:
    {{USER_HOME_POSIX}} → /c/Users/<user>      (MSYS / Git Bash)
    {{USER_HOME_BS}}    → C:\\\\Users\\\\<user> (escaped backslash for JSON)
    {{USER_HOME}}       → C:/Users/<user>      (forward slashes)

Usage:
    python apply-config.py            # apply
    python apply-config.py --dry-run  # render and validate only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 console output even on Windows cp949 default
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def detect_user_home() -> str:
    """Return raw user home (USERPROFILE on Windows, HOME elsewhere)."""
    return os.environ.get("USERPROFILE") or os.environ["HOME"]


def to_native(raw: str) -> str:
    """Forward-slash form, JSON-friendly. C:\\Users\\foo → C:/Users/foo"""
    return raw.replace("\\", "/")


def to_bs(raw: str) -> str:
    """Escaped backslash form for JSON literals. C:\\Users\\foo → C:\\\\Users\\\\foo"""
    if "\\" in raw:
        return raw.replace("\\", "\\\\")
    # On Unix the original is /home/foo; emit unchanged
    return raw


def to_posix(native: str) -> str:
    """Git Bash / MSYS form. C:/Users/foo → /c/Users/foo. Unix paths pass through."""
    if len(native) > 2 and native[1] == ":":
        return "/" + native[0].lower() + native[2:]
    return native


def render(text: str, mapping: dict[str, str]) -> str:
    # Order: longest token first to prevent {{USER_HOME}} consuming {{USER_HOME_POSIX}}
    for key in sorted(mapping, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", mapping[key])
    return text


def backup(path: Path, stamp: str) -> None:
    if path.exists():
        bak = path.with_name(path.name + f".backup-{stamp}")
        shutil.copy2(path, bak)
        print(f"[apply-config] backup -> {bak}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render templates and validate JSON; do not write to ~/.claude/",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="my-tools repo root (default: parent of this script)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    config_dir = repo_root / "claude-config"
    commands_src = repo_root / "commands"

    user_home_raw = detect_user_home()
    mapping = {
        "USER_HOME": to_native(user_home_raw),
        "USER_HOME_BS": to_bs(user_home_raw),
        "USER_HOME_POSIX": to_posix(to_native(user_home_raw)),
    }

    print(f"[apply-config] USER_HOME       = {mapping['USER_HOME']}")
    print(f"[apply-config] USER_HOME_BS    = {mapping['USER_HOME_BS']}")
    print(f"[apply-config] USER_HOME_POSIX = {mapping['USER_HOME_POSIX']}")
    if args.dry_run:
        print("[apply-config] DRY RUN -- no files will be written")

    claude_dir = Path(user_home_raw) / ".claude"
    if not args.dry_run:
        claude_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # 1. settings.json (validate as JSON before writing)
    src = config_dir / "settings.json.template"
    dst = claude_dir / "settings.json"
    rendered = render(src.read_text(encoding="utf-8"), mapping)
    try:
        json.loads(rendered)
    except json.JSONDecodeError as exc:
        print(f"[apply-config] ERROR: rendered settings.json invalid JSON: {exc}")
        return 1
    print("[apply-config] settings.json: rendered + JSON-valid")
    if not args.dry_run:
        backup(dst, stamp)
        dst.write_text(rendered, encoding="utf-8")
        print(f"[apply-config]   written -> {dst}")

    # 2. CLAUDE.md (verbatim; may need user-specific edits afterwards)
    src = config_dir / "CLAUDE.md.template"
    dst = claude_dir / "CLAUDE.md"
    if src.exists():
        if not args.dry_run:
            backup(dst, stamp)
            shutil.copy2(src, dst)
            print(f"[apply-config] CLAUDE.md -> {dst}")
        else:
            print(f"[apply-config] CLAUDE.md: would copy from {src}")

    # 3. commands/
    if commands_src.exists():
        dst_dir = claude_dir / "commands"
        if not args.dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(commands_src.glob("*.md")):
            target = dst_dir / f.name
            if not args.dry_run:
                if target.exists():
                    shutil.copy2(target, target.with_name(target.name + f".backup-{stamp}"))
                shutil.copy2(f, target)
            print(f"[apply-config] command -> {f.name}")

    print("[apply-config] done. Restart Claude Code to pick up new settings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
