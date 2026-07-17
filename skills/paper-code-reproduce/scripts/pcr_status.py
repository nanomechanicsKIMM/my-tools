#!/usr/bin/env python3
"""Summarise .pcr/ state: phase, ledger gate, targets verdict readiness.

Usage:  python pcr_status.py <paper-folder>

Prints the gate decision so it cannot be quietly skipped.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    pcr = root / ".pcr"
    if not pcr.is_dir():
        print(f"no .pcr in {root} — run pcr_init.py")
        return 2

    state = (pcr / "state.md").read_text(encoding="utf-8") if (pcr / "state.md").exists() else ""
    phase = re.search(r"^- current:\s*(\S+)", state, re.M)
    verdict = re.search(r"^- status:\s*(\S+)", state, re.M)
    rounds = re.search(r"^- rounds used:\s*(.+)$", state, re.M)

    missing = (pcr / "missing.md").read_text(encoding="utf-8") if (pcr / "missing.md").exists() else ""
    entries = re.findall(r"^###\s+(\S+)\s+—\s*(.+?)$(.*?)(?=^###|\Z)", missing, re.M | re.S)
    high_open = []
    for mid, name, body in entries:
        impact = re.search(r"\*\*Impact\*\*:\s*(\w+)", body)
        status = re.search(r"\*\*Status\*\*:\s*(\S+)", body)
        if impact and status and impact.group(1) == "HIGH" and status.group(1) == "UNRESOLVED":
            high_open.append((mid, name.strip()))

    tf = pcr / "targets.json"
    targets = json.loads(tf.read_text()) if tf.exists() and tf.stat().st_size > 2 else {}
    load_bearing = [k for k, v in targets.items() if v.get("load_bearing") is True]
    unfrozen = [k for k, v in targets.items()
                if v.get("load_bearing") is True and v.get("tol") in (None, "")]

    print(f"phase   : {phase.group(1) if phase else '?'}")
    print(f"rounds  : {rounds.group(1) if rounds else '?'}")
    print(f"verdict : {verdict.group(1) if verdict else '?'}")
    print(f"targets : {len(targets)} total · {len(load_bearing)} load-bearing")
    if unfrozen:
        print(f"  ! {len(unfrozen)} load-bearing target(s) have no frozen tol: {', '.join(unfrozen)}")
    print(f"ledger  : {len(entries)} entr(ies) · {len(high_open)} HIGH+UNRESOLVED")
    for mid, name in high_open:
        print(f"    - {mid}: {name}")

    print()
    if high_open:
        print("GATE: BLOCKED — HIGH unknowns are open. Ask the user; do not guess to keep moving.")
        return 0
    if unfrozen:
        print("GATE: NOT READY — freeze tolerances before any verdict (widening later = R2 fitting).")
        return 0
    if not load_bearing:
        print("GATE: NOT READY — no load-bearing targets. Without an oracle there is nothing to be "
              "right or wrong about.")
        return 0
    print("GATE: OPEN — a verdict may be issued.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
