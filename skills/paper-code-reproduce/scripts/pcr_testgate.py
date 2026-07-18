#!/usr/bin/env python3
"""Per-module test gate — mechanises two rules that were each broken by hand.

Usage:
  python pcr_testgate.py <paper-folder>                 # pairing check + run suite + record
  python pcr_testgate.py <paper-folder> --check         # no run: is the recorded pass still valid?
  python pcr_testgate.py <paper-folder> --cmd "python -m pytest code/tests -q"   # override runner

Enforces:
 1. PAIRING — every module in code/src/ has a test file code/tests/test_<module>.py.
    Four instrument bugs in the source project each surfaced wearing the face of a physics
    finding (2600 / 2390 / 2000 m/s). An untested module is an untrusted instrument (R5);
    no untested module may feed a figure.
 2. FRESHNESS — a pass claim is valid only while no file under code/ has changed since the
    recorded run. A report once said "13/13 pass" while the true state was 11/13: the fix→claim
    interval contained other work and no re-run. This tool makes that interval mechanical —
    a pass count is read from the recorded run, never from memory.

Records .pcr/test_log.json: {when_utc, cmd, returncode, tail, snapshot{relpath: mtime_ns}}.
Exit: 0 gate green (paired + passed + fresh) · 1 gate red · 2 usage error

The gate fails closed: a missing/unreadable log, an unpaired module, or any changed file
means RED. If it blocks something you believe is green, re-run it — that is the point.
"""
from __future__ import annotations
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_REL = ".pcr/test_log.json"
TAIL_LINES = 25


def src_modules(root: Path) -> list[Path]:
    src = root / "code" / "src"
    if not src.is_dir():
        return []
    return sorted(p for p in src.rglob("*.py")
                  if p.name != "__init__.py" and not p.name.startswith("_"))


def unpaired(root: Path) -> list[str]:
    tests = root / "code" / "tests"
    have = {p.name for p in tests.rglob("test_*.py")} if tests.is_dir() else set()
    return [m.stem for m in src_modules(root) if f"test_{m.stem}.py" not in have]


def snapshot(root: Path) -> dict[str, int]:
    """mtime_ns of every .py under code/ — src, tests, and runners alike."""
    code = root / "code"
    out: dict[str, int] = {}
    if code.is_dir():
        for p in sorted(code.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            out[str(p.relative_to(root))] = p.stat().st_mtime_ns
    return out


def report_pairing(root: Path) -> bool:
    missing = unpaired(root)
    n = len(src_modules(root))
    if missing:
        print(f"PAIRING RED — {len(missing)}/{n} module(s) without a test file:")
        for m in missing:
            print(f"  code/src/{m}.py  →  expected code/tests/test_{m}.py")
        return False
    print(f"PAIRING OK — {n}/{n} module(s) have a test file")
    return True


def run(root: Path, cmd: str) -> int:
    paired = report_pairing(root)
    argv = shlex.split(cmd)
    print(f"RUN: {cmd}")
    r = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    tail = "\n".join(((r.stdout or "") + (r.stderr or "")).splitlines()[-TAIL_LINES:])
    print(tail)
    log = {
        "when_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cmd": cmd,
        "returncode": r.returncode,
        "tail": tail,
        "snapshot": snapshot(root),
    }
    (root / LOG_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / LOG_REL).write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"recorded → {LOG_REL}")
    ok = paired and r.returncode == 0
    print("GATE: GREEN (paired + passed + fresh)" if ok else "GATE: RED")
    if "No module named pytest" in tail:
        print("hint: pytest not installed — pass --cmd to use the project's own runner")
    return 0 if ok else 1


def check(root: Path) -> int:
    paired = report_pairing(root)
    p = root / LOG_REL
    try:
        log = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"CHECK RED — no readable {LOG_REL}: there is no recorded run to trust")
        return 1
    stale = []
    old, new = log.get("snapshot", {}), snapshot(root)
    for f in sorted(set(old) | set(new)):
        if old.get(f) != new.get(f):
            stale.append(f)
    passed = log.get("returncode", 1) == 0
    print(f"last run: {log.get('when_utc', '?')} · cmd: {log.get('cmd', '?')} · "
          f"returncode {log.get('returncode')}")
    if stale:
        print(f"STALE — {len(stale)} file(s) changed since the recorded run "
              f"(the pass claim is void; re-run):")
        for f in stale:
            print(f"  {f}")
    ok = paired and passed and not stale
    print("GATE: GREEN (paired + passed + fresh)" if ok else "GATE: RED")
    return 0 if ok else 1


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    cmd = f"{sys.executable} -m pytest code/tests -q"
    if "--cmd" in args:
        i = args.index("--cmd")
        try:
            cmd = args[i + 1]
        except IndexError:
            print("--cmd needs an argument")
            return 2
        del args[i:i + 2]
    do_check = "--check" in args
    if do_check:
        args.remove("--check")
    if not args:
        print(__doc__)
        return 2
    root = Path(args[0]).expanduser().resolve()
    if not (root / "code").is_dir():
        print(f"no code/ in {root}")
        return 2
    return check(root) if do_check else run(root, cmd)


if __name__ == "__main__":
    raise SystemExit(main())
