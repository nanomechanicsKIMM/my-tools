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

# The gate is a safety device, so it FAILS CLOSED: anything it cannot parse is treated as a
# blocking HIGH+UNRESOLVED, never silently waved through. Two real near-misses forced this:
#   * `**Impact**: **HIGH**` parsed to None under the old `(\w+)` regex → item dropped → gate
#     falsely OPEN while the ledger declared two HIGH unknowns (source-project self-correction #6).
#   * `**Impact**: HIGH → MED` (the ledger's own prescribed re-grade syntax, ledger.md) parsed to
#     the FIRST token "HIGH"; only a stray trailing comma on the Status line kept it from blocking a
#     verdict the ledger had authoritatively demoted to MED.
GRADES = ("HIGH", "MED", "LOW")
# A status that means "this unknown is settled". Anything else (incl. an unparseable/typo'd token)
# leaves the item able to block — fail closed.
CLEARED = ("RESOLVED", "USER-SUPPLIED", "UNRESOLVABLE")
_EMPH = str.maketrans("", "", "*_`")


def _field_line(body: str, field: str) -> str | None:
    """The remainder of the `**Field**:` line, with markdown emphasis stripped."""
    m = re.search(rf"\*\*{field}\*\*:\s*(.*)", body)
    return m.group(1).translate(_EMPH).strip() if m else None


def parse_impact(body: str) -> str | None:
    """Effective impact grade for the gate. Two ledger conventions coexist on the Impact line and
    must not be conflated:
      * re-grade over time uses an ARROW — `HIGH → MED (...)` — the value AFTER the arrow is current;
      * dual-scope uses no arrow — `LOW (primary) / HIGH (Fig.5)` — the FIRST (primary-scope) grade
        is the one this run's gate is scoped to.
    So: if an arrow is present, take the first grade after the last arrow; otherwise the first grade.
    """
    line = _field_line(body, "Impact")
    if line is None:
        return None
    if "→" in line or "->" in line:
        tail = re.split(r"→|->", line)[-1]
        hits = [w for w in re.findall(r"[A-Z]+", tail) if w in GRADES]
        if hits:
            return hits[0]
    hits = [w for w in re.findall(r"[A-Z]+", line) if w in GRADES]
    return hits[0] if hits else None


def parse_status(body: str) -> str | None:
    """Leading status keyword, tolerant of trailing punctuation/prose (`UNRESOLVED, impact MED`,
    `RESOLVED[fig2a, measured]`, `UNRESOLVED[reported ...]`)."""
    line = _field_line(body, "Status")
    if line is None:
        return None
    tok = re.match(r"[A-Za-z\-]+", line)
    if not tok:
        return None
    word = tok.group(0).upper()
    for s in (*CLEARED, "UNRESOLVED"):        # UNRESOLVABLE before UNRESOLVED (prefix)
        if word == s or word.startswith(s):
            return s
    return word                                # unrecognised → surfaced as a warning, still blocks


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
    high_open = []          # (mid, name, reason) — impact HIGH or unparseable, and not cleared
    unknown_status = []     # (mid, token) — status keyword not in the known vocabulary
    for mid, name, body in entries:
        status = parse_status(body)
        impact = parse_impact(body)
        cleared = status in CLEARED
        if status is not None and status not in (*CLEARED, "UNRESOLVED"):
            unknown_status.append((mid, status))
        if cleared:
            continue
        # not cleared → impact decides; fail closed when impact is HIGH or could not be parsed
        if impact == "HIGH":
            high_open.append((mid, name.strip(), "HIGH"))
        elif impact is None:
            high_open.append((mid, name.strip(), "impact unparseable → treated as HIGH"))

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
    print(f"ledger  : {len(entries)} entr(ies) · {len(high_open)} blocking (HIGH/unparseable + not cleared)")
    for mid, name, reason in high_open:
        print(f"    - {mid}: {name}  [{reason}]")
    for mid, tok in unknown_status:
        print(f"  ! {mid}: unrecognised Status '{tok}' — use RESOLVED / USER-SUPPLIED / UNRESOLVED / "
              f"UNRESOLVABLE (unrecognised = not cleared, so it blocks)")

    # decisions.md should accumulate one row per iteration outcome (Phase 6). Surface, don't gate.
    iters = [p for p in (pcr / "iterations").glob("*") if p.is_dir()] if (pcr / "iterations").is_dir() else []
    dec = (pcr / "decisions.md").read_text(encoding="utf-8") if (pcr / "decisions.md").exists() else ""
    dec_rows = sum(1 for ln in dec.splitlines() if ln.lstrip().startswith("|")) - 2  # minus header+rule
    if iters and dec_rows <= 0:
        print(f"  ! {len(iters)} iteration(s) run but decisions.md has no entries — Phase 6 says "
              f"append each outcome (adopted/refuted) with its grounds.")

    print()
    if high_open:
        print("GATE: BLOCKED — a blocking unknown is open (HIGH, or impact could not be parsed so it "
              "is treated as HIGH). Resolve/re-grade it or fix its formatting; do not guess to keep moving.")
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
