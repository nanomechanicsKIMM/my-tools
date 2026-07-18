#!/usr/bin/env python3
"""Scaffold a paper-code-reproduce workspace around a folder containing one paper PDF.

Usage:  python pcr_init.py <paper-folder>

Creates code/{src,tests}, output/{figures,compare}, refs/, .pcr/ and seeds state.md.
Idempotent: never overwrites an existing file.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

DIRS = ["refs", "code/src", "code/tests", "output/figures", "output/compare",
        ".pcr/paper_figs", ".pcr/iterations"]

STATE = """# .pcr/state.md — THE SINGLE SOURCE OF TRUTH

> Re-read this file at the start of every phase. Never carry state in a prompt: prompts go stale and
> re-assert claims that have already been refuted (this happened, repeatedly, in the source project).

## Paper
- file: {pdf}
- title: (fill after extract)

## Phase
- current: INIT
- rounds used: 0 / 3    · iterations this round: 0 / 3

## Verdict
- status: NOT_ATTEMPTED     # NOT_ATTEMPTED | BLOCKED | NOT_REPRODUCED | REPRODUCED | HONEST_LIMIT

## Established (with source)
<!-- only things with a citation. no beliefs. -->

## Refuted (do not revisit)
<!-- hypothesis -> what killed it. keeps the loop from re-running dead ideas. -->

## Open / blocked
<!-- mirror of missing.md HIGH items -->

## Self-corrections
<!-- claims I made and later overturned, and what they damaged -->
"""

MISSING = """# .pcr/missing.md — missing-info ledger  (THE GATE)

**The agent never assumes information the paper does not give.**
Format and rules: skill `references/ledger.md`.

Gate: any entry with `Impact: HIGH` and `Status: UNRESOLVED` **blocks the figure verdict**
(it does not block implementation — exploratory runs are allowed but may never be cited as
reproduction).

---

<!-- ### M001 — <short name>
- **Needed for**:
- **Paper says**:
- **Candidates + grounds**:
- **Impact**: HIGH | MED | LOW
- **Discriminating observable**:   <- if none, you may NOT pick by "which one matches" (R2)
- **Resolution attempts**: paper ? -> supplementary ? -> refs ? -> ask user
- **Status**: UNRESOLVED
-->
"""

SPEC = """# .pcr/spec.md — paper statement -> implementation requirement

Every row needs a citation. A row without one is not a requirement, it is a guess.

| # | Paper statement (verbatim) | Cite | Implementation requirement | Code |
|---|---|---|---|---|
| S001 | | [p. §] | | `src/…` |
"""

ASSUMPTIONS = """# .pcr/assumptions.md — core-assumption register

**Every core assumption the paper's claim rests on: written down, quantified, checked in code.**
Format and rules: skill `references/assumptions.md` (A-1..A-5).

Harvest at spec time from: caveat language ("assuming", "valid when", "we neglect"),
derivation conditions of every equation used, and definitional statements.
Status ∈ {HOLDS, MARGINAL, VIOLATED, UNTESTABLE} — always with the computed number.
A MARGINAL/VIOLATED entry explains a miss (predicted failure direction); it never widens
a tolerance (R2). Computable checks live in `code/tests/test_assumptions.py`.

---

<!-- ### A001 — <short name>
- **Statement (verbatim)**: "..." [p.N §X]   <- or Kind: implicit + grounds
- **Kind**: validity-condition | approximation | idealisation | convention | definitional | implicit
- **Quantitative form**:
- **Applies to**: <targets / ledger ids>
- **Check**: `code/tests/test_assumptions.py::test_a001`  <- computed, not eyeballed
- **Status**: UNTESTED
- **Consequence if violated**: <predicted failure direction>
-->
"""

DECISIONS = """# .pcr/decisions.md

Adopted / rejected, with grounds. Rejections matter as much as adoptions.

| date | change | grounds (@src or defect) | verdict | note |
|---|---|---|---|---|
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f"not a folder: {root}")
        return 2
    pdfs = sorted(p for p in root.glob("*.pdf"))
    if not pdfs:
        print(f"no PDF in {root} — put the paper there first")
        return 2
    pdf = pdfs[0]
    if len(pdfs) > 1:
        print(f"! {len(pdfs)} PDFs found; using {pdf.name}. Move the others into refs/.")

    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    seeds = {
        ".pcr/state.md": STATE.format(pdf=pdf.name),
        ".pcr/missing.md": MISSING,
        ".pcr/spec.md": SPEC,
        ".pcr/assumptions.md": ASSUMPTIONS,
        ".pcr/decisions.md": DECISIONS,
        ".pcr/targets.json": json.dumps({}, indent=2) + "\n",
        "refs/_manifest.md": "# refs/_manifest.md\n\n| ref | resolves | how obtained |\n|---|---|---|\n",
    }
    for rel, body in seeds.items():
        p = root / rel
        if p.exists():
            print(f"  = {rel} (kept)")
            continue
        p.write_text(body, encoding="utf-8")
        print(f"  + {rel}")

    print(f"\nscaffolded {root}")
    print(f"paper: {pdf.name}")
    print("next:  python pcr_extract.py " + str(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
