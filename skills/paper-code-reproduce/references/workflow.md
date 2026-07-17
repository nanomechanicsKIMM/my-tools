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

**Gates**: `pcr_lint.py` clean → all tests green → only then a figure verdict.

**Verify by artifact existence, never exit code.**
```bash
python code/run_figure.py ... > run.log 2>&1
ls output/figures/fig2.png >/dev/null 2>&1 && echo OK || { echo FAILED; tail -5 run.log; }
```
> A failed `cd` silently skipped an entire `&&` chain while the trailing `echo` reported success.

## Phase 5 — reproduce + compare

```bash
python code/run_figure.py
python scripts/pcr_compare.py <paper-folder>
```
See `references/compare.md`. Non-negotiable: evidence-based axis calibration; compare on the coarser
native grid; bound shift searches inside one lattice period; render the difference map **and look at
it**; check the **control panel** (the simplest one) first.

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

**REPRODUCED** — every load-bearing target within its frozen tolerance → `output/REPORT.md`.

**HONEST LIMIT** — only after this checklist (R8, against *false failure*):

1. **Orthogonal axes ablated?** List what you have **not** touched: preprocessing/band, display vs
   estimation, normalisation convention, time windows, aperture/f-number, metric definition.
   > A metric shortfall was twice declared a physical floor while the **band axis had never been
   > touched**. The band was the real lever, both times.
2. **HIGH ledger items escalated to the user?**
3. **Control case checked?** If the simplest panel fails, the problem is upstream of the method.
4. **Failure direction analysed?** Does one upstream difference predict *all* the mismatch signs?

**BLOCKED** — a HIGH ledger item needs the user. Say so and stop; do not guess to keep moving.

### REPORT.md

- What matched / what didn't (verdict table vs `targets.json`)
- Ledger status — including what remains unresolved and why it could not be resolved
- **Self-corrections** — every claim you made and later overturned, with what it damaged
- Honest limits, and what information would resolve them

> The most valuable section of the source project's final report was its **15 self-corrections** —
> above all the ones where a *previous correction* was itself wrong, and where a *rule* had been built
> on a false positive. Write them.
