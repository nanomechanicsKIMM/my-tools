# Phases 0–8 in detail

`.pcr/state.md` is the single source of truth. **Re-read it at the start of every phase.**
> Why: carried-forward prompt state went stale in the source project and kept re-asserting claims that
> had already been refuted. A prompt is a message; state is a file.

---

## Phase 0 — init + extract

```bash
python scripts/pcr_init.py <paper-folder>
python scripts/pcr_extract.py <paper-folder>
```

`pcr_init` scaffolds the tree and writes a skeleton `state.md`.
`pcr_extract` produces:
- `.pcr/paper_text.md` — full text with page markers (citation anchors)
- `.pcr/paper_figs/figNN_p<page>.png` — **≥600 dpi, never resampled**
- `.pcr/targets.json` — **draft**, needs your review
- `.pcr/spec.md` — skeleton

Then **you** write `spec.md` properly: paper statement → implementation requirement, each with
`[p.N §X]`. This is the contract the code is checked against.

## Phase 1 — targets.json, frozen ★

Scrape **every number the paper reports** — body text, tables, captions — not just figure panels.

```json
{"fig2b_amp": {"value": 2.19, "tol": 0.05, "kind": "ratio",
               "src": "p.4 'reaching 2.19-fold ... at the final iteration'",
               "load_bearing": true}}
```

- `tol` comes from the paper's own precision (a stated `4.03 ± 0.15` gives its own tolerance).
- **Freeze now.** Widening later to pass is R2 fitting.
- `load_bearing: true` = the reproduction claim depends on it.

> Numbers in the body are often **stronger oracles than the figure**: they are exact, unrendered, and
> untunable. In the source project a logged value matching a reported one to 5 significant figures is
> what **proved which run produced the figure** — an inference no pixel comparison could have made.

### Audit the paper against itself — and let it set the tolerance ★

Before you trust a headline number as an oracle, **recompute it from the paper's own figure labels /
table entries through the paper's own equation.** The residual is doubly useful: it audits the paper
*and* it floors your tolerance.

> **Case (head-wave).** The text states the numerical head-wave speed as **3200.5 m/s**. Recomputing
> it from Fig. 3's own printed labels (V1 = 3138, V2 = 3263, α = 0) through the paper's Eq. (1) gives
> **3199.3 m/s**, and propagating the labels' integer rounding (±0.5) gives an interval
> [3198.5, 3199.8] that **excludes 3200.5**. The paper is internally self-consistent only to ≈1.2 m/s
> — so the frozen tolerance on that target was set to 2.0 m/s. **Requiring your reimplementation to
> match the paper more tightly than the paper matches itself is demanding more precision than the
> paper contains.**

Two rules make this trustworthy, not a licence to inflate tolerance:

1. **Validate the audit tool on a case that passes.** The same Eq. (1) check on Fig. 6
   (3439, 2762, α = 3.3° → 3058.5 vs the reported 3058) *agrees*. That is what lets you attribute the
   Fig. 3 residual to the paper, not to your arithmetic. Never derive a tolerance from a
   recomputation you have not validated elsewhere in the same paper.
2. **The tolerance is floored by the paper's self-consistency, never widened to pass** (R2). A
   self-consistency residual of 1.2 m/s justifies a 2.0 m/s window; it does not justify a 20 m/s one
   to absorb a miss. Freeze it now, at extract time, from the audit — not later, from the gap.

Record every such recomputation in `spec.md` as an internal-inconsistency row (paper says X; its own
labels/tables give Y; grounds). These rows are findings in their own right and belong in the report.

## Phase 1.5 — the assumptions register ★

See `references/assumptions.md`. Immediately after freezing `targets.json`, harvest the paper's
**core assumptions** into `.pcr/assumptions.md`: caveat language ("assuming", "valid when", "we
neglect"), the derivation conditions of every equation the reproduction uses, and definitional
statements ("the head wave is the first arriving signal"). Each entry gets a verbatim citation (or
`implicit` + grounds), a **quantitative form**, and a **computed check** — preferably a test in
`code/tests/test_assumptions.py` so the Phase-4 gate re-runs it whenever the model changes.

Why here, not later: the source project connected the paper's own thin-plate caveat (p.2) to its
model (plate = 1.6–3.2 λ, **MARGINAL**) only after rounds of estimator sweeps — one line of
arithmetic at spec time would have predicted the dominant contaminant on day one. The register is
consulted again at Phase 5 Step 7 (does a MARGINAL/VIOLATED entry predict the observed failure
direction?), in every iteration prereg, and in the report. It explains misses; it never widens a
tolerance (R2), and a paper whose own setup violates its own assumption is a **finding**, recorded
beside the internal-inconsistency rows (A-4).

## Phase 2 — the ledger gate

See `references/ledger.md`. **No invented values.** HIGH + UNRESOLVED blocks the verdict (not the work).

## Phase 3 — references

Per unresolved item, judge which citation carries it from the **context in which the paper cites it**.

```bash
bash ~/.claude/skills/paper-pdf-download/scripts/get_paper.sh <DOI-or-URL> -d <folder>/refs
```
That skill resolves DOI→PDF, dedups against the existing library, handles bot-blocked/subscription
journals through an authenticated browser session, and writes the standard `(YYYY Author) Title.pdf`.

**Never improvise a downloader.** If a PDF cannot be obtained (paywall, no OA), write it into
`refs/_manifest.md` as "user must supply" and continue: an unobtainable reference is a **ledger
entry**, not a licence to guess.

Record which reference resolved which ID. Mark it `RESOLVED[ref, inferred]` — a reference gives *that*
paper's convention, and the inference must stay visible downstream.

## Phase 4 — implement + test

**Implement** each unit against a `spec.md` item, with `@src` on every constant (R1).

**Unit tests** — known-answer: analytic limits, degenerate inputs, symmetry, conservation.

**Instrument tests (R5)** — every *measurement* function must recover a **planted** ground truth:

```python
def test_detect_rows_recovers_planted():
    img = plant_rows_at([11.0, 21.0, 31.0])      # mm
    assert np.allclose(detect_rows(img), [11.0, 21.0, 31.0], atol=0.3)
```
> Four separate instrument bugs in the source project were each nearly reported as physics
> (a lattice alias, an assumed calibration, an `argmax` that always returned iteration 1, a
> resampling-direction error). Plant a known answer, or the tool is the finding.

**Per-module pairing — no untested module feeds a figure.** Every module in `code/src/` gets its
test file `code/tests/test_<module>.py` **in the same step that creates the module**, not in a later
"testing pass": the four instrument bugs above were each caught (or would have been) at the moment
the module first ran, and each wore the face of a physics finding until then. Assumption checks from
Phase 1.5 live in `code/tests/test_assumptions.py` and run under the same gate.

`pcr_testgate.py` mechanises the gate — pairing, the run itself, and **freshness** (recorded run vs
current file mtimes):

```bash
python scripts/pcr_testgate.py <paper-folder>            # pairing + run suite + record
python scripts/pcr_testgate.py <paper-folder> --check    # is the recorded pass still valid?
python scripts/pcr_testgate.py <paper-folder> --cmd "…"  # project's own runner if not pytest
```

**Gates**: `pcr_lint.py` clean → `pcr_testgate.py` GREEN (paired + passed + **fresh**) → only then a
figure verdict.

**Verify by artifact existence, never exit code.**
```bash
python code/run_figure.py ... > run.log 2>&1
ls output/figures/fig2.png >/dev/null 2>&1 && echo OK || { echo FAILED; tail -5 run.log; }
```
> A failed `cd` silently skipped an entire `&&` chain while the trailing `echo` reported success.

**A pass count is read from the last run, never from memory.** State "N/N pass" only from the output
of a run you did *after* your last code change. If any action came between the edit and the claim,
that interval is unverified — re-run.
> A report drafted "code/tests: 13/13 pass". It was false: the tests had last been run before a fix,
> a control run intervened, and the real state was 11/13 (two failing). "I fixed it" had been
> promoted to "it passes" with no run in between. Re-running is cheaper than a false verification
> story — and a false one poisons everything downstream that trusts it.

`pcr_testgate.py --check` makes that interval mechanical: any file under `code/` changed after the
recorded run voids the pass claim (STALE), and a missing record fails closed. Run it before writing
any "N/N pass" sentence into a report.

## Phase 5 — reproduce + compare

**Write the figure recipe before rendering** — `.pcr/paper_figs/figNN_recipe.md`: every degree of
freedom that shapes the published panel, each pinned `@src` or entered in the ledger — axis ranges
and units, sampling grid, normalisation (global vs per-panel), dynamic range / colormap / log-linear
compression, and every number printed on the figure (labels are targets too). An unpinned display
DOF found *during* comparison is a ledger entry discovered late; a mismatch on one is a **display
finding, never a physics finding**.
> Why: the source project's Fig. 3 colorbar (0–50, units unstated) surfaced only at compare time
> (M010) — pixel-level agreement was unjudgeable by construction, and knowing that *before* the run
> would have redirected effort to the numbers that were judgeable.

```bash
python code/run_figure.py
python scripts/pcr_compare.py <paper-folder>
```
See `references/compare.md`. Non-negotiable: evidence-based axis calibration; compare on the coarser
native grid; bound shift searches inside one lattice period; render the difference map **and look at
it**; check the **control panel** (the simplest one) first. At Step 7 (failure direction), consult
`.pcr/assumptions.md` first: a MARGINAL/VIOLATED entry that predicts the observed sign and scale is
the leading explanation (A-3).

## Phase 6 — iterate (≤3 per round)

Each iteration begins by writing `.pcr/iterations/NN/prereg.md`:

```markdown
## H: <one sentence>
## Prediction (fixed before looking): metric X moves A→B; if it doesn't, REJECT
## Falsification device: Y must NOT change; if Y moves, my reasoning is wrong and this test is void
## Variable changed (exactly one): ...
## @src: ...            ← no source ⇒ this change is banned (R2)
```

Then run, then record the outcome honestly. **A refutation is a result.** Four hypotheses died this
way in the source project; every one of them would have survived a narrative told after the fact.

One variable at a time. Append the outcome to `decisions.md` with grounds.

## Phase 7 — unprimed critic

See `references/critic.md`. Default: **codex + opus crossed**. Verify claims **and** your refutations
of them.

## Phase 8 — stop

The verdict is **graded, not binary** (SKILL.md "Stop conditions"): report the **method** verdict and
the **number** verdict separately, and never let one stand in for the other.

**REPRODUCED** — every load-bearing target within its frozen tolerance → `output/REPORT.md`.

**METHOD-REPRODUCED, TARGET NOT** — the technique demonstrably works (right regime identified,
invariants hold, estimators land within a few % of truth) but a load-bearing number misses its frozen
tolerance and no orthogonal axis remains. Report **both** the qualitative success and the exact
quantitative miss; do not widen the tolerance (R2). Note that a user- or reference-supplied HIGH
unknown *opens the gate onto this verdict* — resolving the blocker is not reproducing the number.

**HONEST LIMIT** — only after this checklist (R8, against *false failure*):

1. **Orthogonal axes ablated?** List what you have **not** touched: preprocessing/band, display vs
   estimation, normalisation convention, time windows, aperture/f-number, metric definition.
   > A metric shortfall was twice declared a physical floor while the **band axis had never been
   > touched**. The band was the real lever, both times.
2. **HIGH ledger items escalated to the user?**
3. **Control case checked?** If the simplest panel fails, the problem is upstream of the method.
4. **Failure direction analysed?** Does one upstream difference predict *all* the mismatch signs?
5. **Assumption register audited?** Every entry in `.pcr/assumptions.md` carries a computed status;
   any MARGINAL/VIOLATED entry has been tested against the observed failure direction (A-3). A
   "limit" declared while a violated assumption predicts exactly the observed miss is not a limit —
   it is an unread register.

**BLOCKED** — a HIGH ledger item needs the user. Say so and stop; do not guess to keep moving.

### REPORT.md

- **Lead with the graded verdict**, in the first lines: the method verdict and the number verdict,
  stated together (e.g. "method reproduced — bone speed to ~1%; headline 0.5 m/s precision NOT
  reproduced — best miss 20 m/s = 10× the frozen tolerance"). A reader must not be able to come away
  with only the half that flatters the result.
- What matched / what didn't (verdict table vs `targets.json`)
- Ledger status — including what remains unresolved and why it could not be resolved
- **Assumption audit table** — id, statement, computed status, and whether its predicted consequence
  was observed; MARGINAL/VIOLATED entries beside the misses they explain
- **Self-corrections** — every claim you made and later overturned, with what it damaged
- Honest limits, and what information would resolve them

> The most valuable section of the source project's final report was its **15 self-corrections** —
> above all the ones where a *previous correction* was itself wrong, and where a *rule* had been built
> on a false positive. Write them.
