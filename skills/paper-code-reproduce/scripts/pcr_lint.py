#!/usr/bin/env python3
"""Provenance linter — enforces R1 ("no unprovenanced value") mechanically.

Usage:  python pcr_lint.py <paper-folder> [--strict]

An untagged constant IS an invention. Instructions alone do not stop that; a gate does.

A module-level / class-level numeric assignment in code/src/ must carry, on its line or the line
above, one of:
    @src{...}        provenance: paper / supplementary / ref / user
    @missing{ID}     a declared unknown, present in .pcr/missing.md

Exit: 0 clean · 1 violations · 2 usage error

Deliberately NOT flagged (these are not claims about the paper):
  0, 1, -1, 2, 0.0, 1.0, 0.5   structural constants
  values inside tests/          tests assert, they do not assume
  indices/slices, __version__, and pure-integer loop bounds
"""
from __future__ import annotations
import ast
import re
import sys
from pathlib import Path

SRC_TAG = re.compile(r"@src\{[^}]+\}")
MISSING_TAG = re.compile(r"@missing\{([A-Za-z0-9_\-]+)\}")
BENIGN = {0, 1, -1, 2, 0.0, 1.0, -1.0, 0.5, 100, 100.0}


def declared_missing(root: Path) -> set[str]:
    p = root / ".pcr" / "missing.md"
    if not p.exists():
        return set()
    return set(re.findall(r"^###\s+([A-Za-z0-9_\-]+)", p.read_text(encoding="utf-8"), re.M))


def numeric_assignments(tree: ast.AST):
    """Yield (lineno, name, value) for module/class-level numeric assignments."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        val = node.value
        if val is None:
            continue
        nums = []
        if isinstance(val, ast.Constant) and isinstance(val.value, (int, float)) \
                and not isinstance(val.value, bool):
            nums = [val.value]
        elif isinstance(val, (ast.List, ast.Tuple)):
            nums = [e.value for e in val.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, (int, float))
                    and not isinstance(e.value, bool)]
        if not nums:
            continue
        if all(n in BENIGN for n in nums):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                yield node.lineno, t.id, nums


def lint_file(path: Path, known: set[str]):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [(e.lineno or 0, "SYNTAX", f"cannot parse: {e.msg}")]
    out = []
    for lineno, name, nums in numeric_assignments(tree):
        ctx = "\n".join(lines[max(0, lineno - 2):lineno])   # this line + the one above
        if SRC_TAG.search(ctx):
            continue
        m = MISSING_TAG.search(ctx)
        if m:
            mid = m.group(1)
            if mid not in known:
                out.append((lineno, name, f"@missing{{{mid}}} not declared in .pcr/missing.md"))
            continue
        out.append((lineno, name, f"unprovenanced constant {nums} — add @src{{...}} or @missing{{ID}}"))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    strict = "--strict" in sys.argv
    src = root / "code" / "src"
    if not src.is_dir():
        print(f"no code/src in {root}")
        return 2

    known = declared_missing(root)
    files = sorted(p for p in src.rglob("*.py"))
    violations = 0
    for f in files:
        for lineno, name, msg in lint_file(f, known):
            print(f"{f.relative_to(root)}:{lineno}: {name}: {msg}")
            violations += 1

    open_missing = sorted(known)
    print(f"\nscanned {len(files)} file(s) · {violations} violation(s)")
    if open_missing:
        print(f"declared unknowns: {', '.join(open_missing)}  (gate: HIGH+UNRESOLVED blocks the verdict)")
    if violations:
        print("\nFAIL — an untagged constant is an invention (R1).")
        return 1
    if strict and open_missing:
        print("\nFAIL(strict) — unknowns still open.")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
