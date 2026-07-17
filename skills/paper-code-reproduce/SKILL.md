---
name: paper-code-reproduce
description: Reproduce a paper's figures from its PDF alone — scaffolds code/output folders, extracts a machine-checkable target spec, forbids invented values via a missing-info ledger and provenance linter, validates instruments, compares figures 1:1 at high resolution, and iterates with pre-registered hypotheses; escalates to an unprimed critic after 3 failed iterations.
argument-hint: "<paper-folder> [--phase init|extract|implement|reproduce|compare|iterate|critic|report] [--max-rounds 3]"
level: 4
---

<Purpose>
Given a folder containing one paper PDF, build code that reproduces the paper's figures, and iterate
until reproduced — or until an honest limit is reached and reported as such.

The hard part is not writing code. It is **not believing wrong things**. Every rule below exists
because it actually caught a real error, or because its absence actually caused one, in the A-CLASS
Fig.2 reproduction project (2026-07-13~17). None of it is invented.
</Purpose>

<Use_When>
- The user drops a paper/manuscript PDF in a folder and wants its figures reproduced from scratch
- An existing reproduction disagrees with a paper and the disagreement must be diagnosed honestly
- Any task where "did we actually reproduce it, or did we tune until it matched?" is the real question
</Use_When>

<Do_Not_Use_When>
- The goal is to *use* a method, not to *verify* a paper's figure — this skill's gates are overhead then
- No target figure or reported numbers exist to check against (nothing to be right or wrong about)
</Do_Not_Use_When>

## Folder contract

The user supplies only `paper.pdf` (any filename; first PDF found). Everything else is created:

```
<paper-folder>/
├── paper.pdf         ← user drops this
├── refs/             ← cited reference PDFs (resolve missing info)
├── code/{src,tests}/ ← implementation; every constant carries a provenance tag
├── output/{figures,compare}/ + REPORT.md
└── .pcr/             ← durable state; state.md is the single source of truth
    ├── state.md  spec.md  missing.md  targets.json  decisions.md
    ├── paper_figs/   iterations/NN/
```

**`.pcr/state.md` is the only truth.** Never carry state in a prompt.
> Why: in the source project, carried-forward loop prompts went stale and kept re-asserting claims
> that had already been refuted. Re-read `state.md` at the start of every phase.

## The eight rules (the spine)

Read `references/antifooling.md` for the full case behind each.

- **R1 — No unprovenanced value.** Every numeric literal / algorithmic choice in `code/src/` carries
  `@src{...}` or `@missing{ID}`. `scripts/pcr_lint.py` enforces it. An untagged constant *is* an
  invention.
- **R2 — No metric fitting.** *If the only reason you can justify a value is that it makes the metric
  match, it is banned.* Fixing a paper-mandated defect and having a metric follow is a **consequence**
  (allowed). Turning a free knob until a target is hit is **aiming** (banned).
- **R3 — Source hierarchy.** paper body > supplementary > author config/log > cited refs > convention.
  On conflict, the higher wins.
- **R4 — Pre-register.** Fix the prediction *before* looking, and ship a falsification device with it.
- **R5 — Distrust instruments.** A measurement tool is not trusted until it recovers a planted answer.
- **R6 — Summary statistic ≠ identity.** Report metrics *and* pixels *and* look at the figure.
- **R7 — Unprimed verification.** Never hand a critic your conclusion. Verify its claims *and* your
  refutations of them.
- **R8 — Resist both pressures.** Don't claim a match you don't have; don't promote "not yet" to
  "impossible" before ablating every orthogonal axis.

## Flow

```
init → extract → spec + targets(FROZEN) → missing ledger
                                              │
                             HIGH unresolved? → refs → still? → ★ASK USER (halt)
                                              │
                                    implement + unit & instrument tests (all pass)
                                              │
        ┌────────────────→ run figure → compare 1:1 → verdict vs targets.json
        │                                     │
        │                             REPRODUCED? ──yes──→ report
        │                                     │no
        │                            pre-registered iteration (≤3/round)
        │                                     │
        └──── rounds<3 ───── unprimed critic (codex + opus, crossed) ←── 3 failures
                                              │
                                    3 rounds failed → Phase 8 checklist
                                              │
                              orthogonal axis left? ──yes──→ back to loop
                                              │no
                                       ★ honest-limit report
```

## Phases

Details in `references/workflow.md`. Summary:

0. **init/extract** — `pcr_init.py`, `pcr_extract.py`. Figures at **≥600 dpi, never resampled**.
   Write `spec.md` (paper statement → implementation requirement, each with `[p.N §X]`).
1. **targets.json — the oracle, frozen now.** Scrape *every* number the paper reports (text, tables,
   captions — not just figures). Set tolerances from the paper's own precision **and freeze them**.
   Widening a tolerance later to pass is R2 fitting.
   > A reported number matching exactly is what identifies which run/config a figure came from.
2. **missing.md — THE GATE.** See `references/ledger.md`. No invented values, ever. Resolution order:
   paper → supplementary → refs → **ask the user**. HIGH+UNRESOLVED blocks the verdict.
3. **refs** — delegate to the `paper-pdf-download` skill (verified present; it is explicitly built to
   be called by other skills as a reference-collection engine, handles bot-blocked/subscription
   journals via an authenticated browser, dedups against the library, and emits the standard
   `(YYYY Author) Title.pdf` name):
   ```bash
   bash ~/.claude/skills/paper-pdf-download/scripts/get_paper.sh <DOI-or-URL> -d <folder>/refs
   ```
   Never improvise a downloader. If a PDF cannot be obtained (paywall, no OA), list it in
   `refs/_manifest.md` as "user must supply" and continue — an unobtainable reference is a ledger
   entry, not a reason to guess.
4. **implement + test** — unit tests (known-answer) **and instrument tests** (R5: a measurement
   function must recover a planted ground truth). All green before any figure verdict.
   Verify success by **artifact existence, never exit code**.
   > Why: a failed `cd` silently skipped an entire `&&` chain while the trailing `echo` reported 0.
5. **compare** — `pcr_compare.py`. See `references/compare.md`. Establish axis calibration from
   **evidence, not assumption**; compare at the **coarser native grid**; bound any shift search
   inside one lattice period; always render side-by-side + difference map and **look at it**.
6. **iterate (≤3/round)** — each writes `.pcr/iterations/NN/prereg.md` first: hypothesis, prediction,
   falsification device, the **one** variable, and its `@src`. A refutation is a result, not a failure.
7. **critic (after 3)** — `references/critic.md`. Unprimed: give paper + code + spec **only**.
   Default: **codex and opus crossed**. Verify claims against primary sources — and verify your
   refutations too (check field *names*, not rounded values).
8. **report** — `output/REPORT.md`: what matched, what didn't, ledger status, **self-corrections**,
   honest limits.
   > The most valuable section of the source project's final report was its list of self-corrections.

**If you build the forward model yourself** (simulating the data from a geometry the paper only
draws — k-Wave/FDTD/any solver — then running the paper's estimator on it), read
`references/simulation.md` **before Phase 4**. It carries four rules the supplied-data cases don't:
assert physical invariants (causality, symmetry) on the raw simulated data and run the domain/PML as
a pre-registered control (SIM-1); prefer a **coherence** estimator over amplitude-maximum for reading
a slope/velocity, and use it to test whether an unstated parameter still matters (SIM-2); make every
plant contain the real data's dominant competitor at real strength (SIM-3); validate the figure-to-
geometry reader against independently-stated numbers (SIM-4).

## Scripts

| script | role |
|---|---|
| `pcr_init.py` | scaffold folders + `.pcr/state.md` |
| `pcr_extract.py` | PDF → text, high-res figures, `targets.json` draft, `spec.md` skeleton |
| `pcr_lint.py` | **R1 enforcement**: untagged constants / `@missing` still open |
| `pcr_compare.py` | **1:1**: axis calibration, native-grid resample, bounded shift search, diff map, verdict |
| `pcr_status.py` | render `.pcr/state.md` summary + **print the gate decision** so it can't be skipped |
| `test_pcr.py` | **self-tests for the tools above** — run once before trusting them |

Run with the project's own interpreter; scripts need only numpy/scipy/matplotlib (+PyMuPDF or
poppler for extraction).

**Run `python scripts/test_pcr.py` first.** R5 applies to this skill's own tools before anything else
— and it earned its keep immediately: the planted-shift test caught `pcr_compare` reporting **every
offset with the sign flipped**, and the citation test caught `pcr_extract` quoting the start of a
two-column line so the citation pointed at text **not containing its own number** (fake provenance —
in a skill whose entire premise is provenance). Both were found by running the tests, not by reading
the code.

## Stop conditions

- **REPRODUCED**: every `load_bearing` target inside its frozen tolerance.
- **HONEST LIMIT**: 3 rounds exhausted **and** the Phase-8 checklist passes (orthogonal axes ablated,
  HIGH ledger items escalated to the user, control case checked, failure direction analysed).
- **BLOCKED**: a HIGH ledger item needs the user. Say so and stop — do not guess to keep moving.
