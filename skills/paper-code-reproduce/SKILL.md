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
    ├── state.md  spec.md  missing.md  assumptions.md  targets.json  decisions.md
    ├── paper_figs/   iterations/NN/   test_log.json
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
init → extract → spec + targets(FROZEN) + assumptions register → missing ledger
                                              │
                             HIGH unresolved? → refs → still? → ★ASK USER (halt)
                                              │
                      implement + per-module tests (testgate GREEN: paired+passed+fresh)
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
   **Then (Phase 1.5) harvest the assumptions register** — `.pcr/assumptions.md`, see
   `references/assumptions.md`: the paper's validity conditions, approximations, and definitional
   statements, each with a verbatim citation, a quantitative form, and a computed check in
   `code/tests/test_assumptions.py`. The register is the backbone of the logical-consistency
   audit: at verdict time every load-bearing target lists the assumptions it depends on
   (HOLDS / MARGINAL / VIOLATED / UNTESTABLE), and a MARGINAL/VIOLATED entry must be tested
   against the observed failure direction — it explains misses, never widens tolerances (R2).
   A paper whose own setup violates its own assumption is a finding to report, not a knob to fix.
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
   function must recover a planted ground truth). **Every module is paired with its test in the same
   step that creates it** — `pcr_testgate.py` enforces pairing, runs the suite, and voids any pass
   claim once a file changes after the recorded run (freshness). Gate order: `pcr_lint.py` clean →
   `pcr_testgate.py` GREEN → only then a figure verdict.
   Verify success by **artifact existence, never exit code**.
   Read `references/coding-pitfalls.md` before translating any equation or transform into code — a
   correctly-sourced constant can still be wrong if a convention (2π, FFT sign, harmonic vs
   arithmetic mean, angular vs ordinary wavenumber) was silently changed in translation; the linter
   passes and the physics is wrong. The check: round-trip one of the paper's own worked numbers
   through your code path.
   > Why: a failed `cd` silently skipped an entire `&&` chain while the trailing `echo` reported 0.
5. **compare** — `pcr_compare.py`. See `references/compare.md`. **Pin the figure recipe first**
   (`.pcr/paper_figs/figNN_recipe.md`): every display degree of freedom — axes, grid, normalisation,
   dynamic range/colormap — pinned `@src` or ledgered, so a mismatch on an unpinned display DOF is
   never mistaken for a physics finding. **Draw your reproduction panel with the verdict's resolved
   parameters** (Step 0b): the ledger-resolved/user-supplied window and estimator the verdict uses,
   stamped on the figure — not a leftover exploratory default. A figure computed with different
   parameters silently contradicts your own verdict (head-wave: the panel printed 2183 m/s while the
   verdict was 3180). Then: axis calibration from **evidence, not assumption**;
   compare at the **coarser native grid**; bound any shift search inside one lattice period; always
   render side-by-side + difference map and **look at it**. Read failure directions against the
   assumptions register first.
6. **iterate (≤3/round)** — each writes `.pcr/iterations/NN/prereg.md` first: hypothesis, prediction,
   falsification device, the **one** variable, and its `@src`. A refutation is a result, not a failure.
7. **critic (after 3)** — `references/critic.md`. Unprimed: give paper + code + spec **only**.
   Default: **codex and opus crossed**. Verify claims against primary sources — and verify your
   refutations too (check field *names*, not rounded values).
8. **report** — `output/REPORT.md`: what matched, what didn't, ledger status, **assumption audit
   table** (id, statement, computed status, consequence observed?), **self-corrections**,
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
| `pcr_status.py` | render `.pcr/state.md` summary + **print the gate decision** so it can't be skipped; **fails closed** — unparseable impact → HIGH, unrecognised status → not cleared |
| `pcr_testgate.py` | **per-module test gate**: every `src/` module paired with a test, suite run + recorded, and **freshness** — any file changed after the recorded run voids the pass claim; fails closed on a missing record |
| `test_pcr.py` | **self-tests for the tools above** — run once before trusting them |

Run with the project's own interpreter; scripts need only numpy/scipy/matplotlib (+PyMuPDF or
poppler for extraction).

**Run `python scripts/test_pcr.py` first.** R5 applies to this skill's own tools before anything else
— and it earned its keep immediately: the planted-shift test caught `pcr_compare` reporting **every
offset with the sign flipped**; the citation test caught `pcr_extract` quoting the start of a
two-column line so the citation pointed at text **not containing its own number** (fake provenance —
in a skill whose entire premise is provenance); and the gate test caught `pcr_status` reading the
ledger's own re-grade syntax `Impact: HIGH → MED` as **HIGH** and `Impact: **HIGH**` (bold) as
**nothing** — the second silently reported the gate OPEN while two HIGH unknowns were still open. All
were found by running the tests, not by reading the code.

**The gate fails closed.** `pcr_status.py` is a safety device: an entry whose `Impact` it cannot
parse is treated as **HIGH and blocking**, and any `Status` keyword it does not recognise counts as
**not cleared**. A gate that opens when it is confused is worse than no gate — it launders "I could
not read this" into "there is nothing to read." If it blocks on something you believe is resolved,
fix the entry's *formatting* (see `references/ledger.md`), never loosen the tool.

## Stop conditions

Reproduction is **graded, not binary.** Separate two verdicts and report both — never let one hide
the other: the **method** verdict (does the technique qualitatively work — right regime identified,
physical invariants hold, estimators land in the right neighbourhood?) and the **number** verdict
(is each `load_bearing` target inside its frozen tolerance?).

- **REPRODUCED**: every `load_bearing` target inside its frozen tolerance.
- **METHOD-REPRODUCED, TARGET NOT**: the technique demonstrably works (e.g. every estimator lands
  within a few % of truth and identifies the right physical regime) but a load-bearing number misses
  its frozen tolerance and no orthogonal axis remains to close it. State **both** — the qualitative
  success and the exact quantitative miss (e.g. "bone speed recovered to ~1%, but the paper's 0.5 m/s
  precision is not reproduced: best 3179.8, 20 m/s = 10× the frozen tolerance"). Do **not** widen the
  tolerance to absorb the miss (R2), and do **not** let "the method works" quietly stand in for
  "the number reproduced." This is the head-wave outcome; it is a legitimate terminal state.
- **HONEST LIMIT**: 3 rounds exhausted **and** the Phase-8 checklist passes (orthogonal axes ablated,
  HIGH ledger items escalated to the user, control case checked, failure direction analysed).
- **BLOCKED**: a HIGH ledger item needs the user. Say so and stop — do not guess to keep moving.

> **Resolving the gate ≠ reproducing the figure.** When the user or a reference supplies a blocking
> HIGH unknown, the gate opens onto *whatever the verdict actually is* — often
> METHOD-REPRODUCED-TARGET-NOT, not REPRODUCED. Supplying the missing input removes the *blocker*; it
> does not make the number match. Re-run the verdict against the frozen tolerance; do not report
> "unblocked" as if it were "reproduced."
