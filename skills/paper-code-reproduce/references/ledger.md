# The missing-info ledger — `.pcr/missing.md`

**The rule this file enforces: the agent never assumes information the paper does not give.**

This is the gate. Everything else in the skill is downstream of it.

---

## Why this is the centre of the skill

In the source project, the three things that were still unresolved at the end —
the acquisition time origin, a normalisation-count convention, and whether a depth gain entered the
metrics — were **all "information the paper does not state"**. Each was guessed at, repeatedly, across
several sessions. Each guess looked reasonable. Each consumed days.

Had they been written down as *open questions on day one* and put to the user, they would have been
answered in minutes, or declared unavailable and reported as limits from the start.

⇒ **An unanswerable question, identified early, is cheap. The same question, guessed at, is the most
expensive thing in the project.**

---

## Entry format

```markdown
### M003 — acquisition time origin (t=0 convention)
- **Needed for**: DAS sampling origin. Enters every target depth.
- **Paper says**: nothing. methods §2.3 gives lens thickness and speed only.
- **Candidates + grounds**:
  - (a) excess delay 2h(1/c_lens − 1/c0) = 15.98 samples — [derivation, physical]
  - (b) whole transit 2h/c_lens = 24.78 samples — [convention, no source]
- **Impact**: HIGH — a wrong value translates the whole image in depth
- **Discriminating observable**: none found (depth and coherence proved independent knobs)
- **Resolution attempts**: paper ✗ → supplementary ✗ → refs[2] ✗ → **ASK USER**
- **Status**: UNRESOLVED
```

Required fields: `Needed for`, `Paper says`, `Candidates + grounds`, `Impact`, `Status`.

`Impact` ∈ {HIGH, MED, LOW}:
- **HIGH** — a wrong value changes the figure verdict. **Blocks.**
- **MED** — changes a secondary metric only.
- **LOW** — cosmetic.

`Status` ∈ {UNRESOLVED, RESOLVED[source], USER-SUPPLIED[date], UNRESOLVABLE[reported as limit]}.

---

## Resolution order (do not skip a level)

1. **Paper body** — search text, equations, captions, tables.
2. **Supplementary / appendix.**
3. **Author artifacts** if present (config, logs, released code) — but remember **R3**: these describe
   *a* run and lose to the paper body on conflict.
4. **Cited references** — identify *which* citation would carry it from the context in which the paper
   cites it. Fetch via the `paper-pdf-download` skill into `refs/`; record in `refs/_manifest.md`
   which reference resolved which ID.
   ⚠️ A reference gives *that paper's* convention. Mark the entry `RESOLVED[ref, inferred]`, not
   `RESOLVED[paper]` — it is an inference, and it must stay marked as one downstream.
5. **Ask the user.** Stop and ask. This is a success path, not a failure.

---

## The gate

Before any figure verdict is issued:

```
any(entry.impact == HIGH and entry.status == UNRESOLVED)  →  DO NOT ISSUE A VERDICT
```

Instead: report `BLOCKED`, list the HIGH entries with their candidates, and ask the user.

Code depending on an unresolved item must:
- expose the value as an **explicit parameter** (never a buried literal),
- tag it `@missing{M003}` so `pcr_lint.py` sees it,
- and be **excluded from any "reproduced" claim**.

## What the gate is not

The gate is **not** "stop all work". Implementation continues around unresolved items; only the
**verdict** is blocked. You may run the figure with a candidate value to *explore* — but the run is
labelled `EXPLORATORY` in `.pcr/iterations/NN/` and **cannot** be cited as reproduction.

## Demoting a HIGH unknown on evidence — the verdict-invariance test

`Impact: HIGH` means "a wrong value **changes the figure verdict**" — not merely "changes the
value". So a HIGH unknown legitimately demotes to MED, opening the gate, when you can **show** that
every admissible reading of it lands on the same side of the verdict.

Procedure (this is evidence, not a loophole):
1. Enumerate the admissible values (the pre-registered set — enlarging it now is R2 fitting).
2. Run the verdict under each.
3. If **all** give the same PASS/FAIL against the frozen tolerance, the unknown moves the value but
   not the verdict → demote to MED, and record the spread.

**Worked case.** With the extraction range user-supplied, the "high intensity region" estimator was
still unstated (M003). Its four readings gave 3127 / 3135 / 3180 / 3297 m/s — a 170 m/s spread — but
**none** fell inside the frozen 3200.5 ± 2.0 window. So M003 changed the number, never the
"NOT REPRODUCED" verdict. It demoted from HIGH to MED and the gate opened onto an honest verdict
instead of staying `BLOCKED` forever.

**The trap this is not.** Do not confuse "all readings give the same verdict" (legitimate demotion)
with "one reading gives the verdict I want" (R2 fitting). The first is invariance across the whole
admissible set; the second is selection. If the readings **straddle** the tolerance — some PASS,
some FAIL — the unknown *is* verdict-deciding, stays HIGH, and blocks. See references/simulation.md
SIM-2 for the better move in that case: a more robust estimator that removes the sensitivity.

### Writing a re-grade so the gate reads it (doc ↔ tool contract)

When you demote on evidence, write it as an **arrow** re-grade — the new grade goes *after* the
arrow (`→` or `->`), on the same line, and the rationale follows as prose. `pcr_status.py` reads the
grade after the last arrow as the current one:

```
- **Impact**: HIGH → MED (re-graded 2026-07-18: all four readings miss the window, so it changes
  the value but not the verdict)
```

The arrow matters because a second convention shares the line. A **dual-scope** grade —
`LOW for this run's target / HIGH for Fig. 5` — has *no* arrow, and the gate (scoped to this run's
load-bearing target) reads the **first** grade. So: **arrow ⇒ the grade after it wins** (a re-grade
over time); **no arrow ⇒ the first grade wins** (primary scope). Never write a re-grade without the
arrow, or it will be read as a dual-scope entry and the *old* grade will stand.

Two more formatting rules the gate depends on, each from a real near-miss:
- **Never bold or italicise the grade itself.** `**Impact**: **HIGH**` parses to *nothing* — the
  gate then silently opens on an unknown it should have blocked. Bold the label (`**Impact**:`),
  never the value.
- **The `Status` keyword must lead the line**, from the set `RESOLVED` / `USER-SUPPLIED` /
  `UNRESOLVED` / `UNRESOLVABLE`; trailing prose is fine (`UNRESOLVED, impact MED`). Anything the tool
  cannot match to that set is treated as **not cleared** and blocks — so a typo fails safe, but check
  `pcr_status.py`'s warning line rather than assuming the gate is wrong.

The gate **fails closed**: unparseable impact → HIGH; unrecognised status → not cleared. If it blocks
something you believe is resolved, the entry is mis-formatted; fix the entry, never the tool.

---

## The trap this gate exists to prevent

The tempting move is to try candidates and keep the one that makes the figure match.

**That is R2 metric fitting, and it is banned here specifically.** Selecting among candidates by
"which reproduces the figure" is not evidence — it is assuming the conclusion. The figure is the thing
being tested; it cannot also be the thing that decides the input.

**A candidate may only be adopted if an observable independent of the target discriminates it.**

Worked case: the data preferred a lens offset of 7.4 samples because at that value the depth error
vanished. A sweep then showed depth and coherence were independent knobs — no second observable moved
with it. Nothing but the target itself supported 7.4. It stayed `UNRESOLVED` and the gap was reported
as unexplained. That was the correct outcome, and it cost less than the alternative: shipping a fitted
number as a reproduction.

---

## Escalation template (to the user)

```
BLOCKED — the paper does not specify N item(s) the reproduction needs.

M003 — acquisition time origin
  Needed for: every target depth
  Paper: silent (methods §2.3 gives lens thickness/speed only)
  Candidates: (a) 15.98 samples [excess-delay derivation]
              (b) 24.78 samples [whole transit, no source]
  Why I will not choose: no observable independent of the figure discriminates them;
                         picking the one that matches would be fitting (R2).
  What would resolve it: the acquisition t=0 convention, or the vendor's delay definition.
```

State what is needed, what you tried, and **why you are not guessing**. Then stop.
