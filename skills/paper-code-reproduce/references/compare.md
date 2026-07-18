# Figure 1:1 comparison protocol

Comparing a reproduced figure to a published one is where reproductions are most often declared
successful without being successful — and, less obviously, most often declared failed while being
essentially right. Both happened in the source project.

---

## Step 0 — Pin the figure recipe before comparing ★

Before rendering your own version, write `.pcr/paper_figs/figNN_recipe.md`: every degree of freedom
that shapes the published panel — axis ranges/units, sampling grid, normalisation (global vs
per-panel), dynamic range / colormap / log-linear compression, and every number printed on the panel
(labels are targets too) — each pinned `@src` or entered in the ledger.

Two payoffs, both from the source project:
- A mismatch on an **unpinned display DOF is a display finding, never a physics finding** — the
  Fig. 3 colorbar (0–50, units unstated) made pixel-level agreement unjudgeable by construction, and
  discovering that mid-comparison wasted a round that a recipe would have redirected on day one.
- The recipe decides **what is judgeable at all**: metrics compare where the recipe is pinned;
  where it is not, only structure (event positions, symmetry, ordering) can honestly be compared.
  Say which in the report.

## Step 1 — Extract the published figure honestly

- Render at **≥600 dpi** (`pdftoppm -r 600`) if vector; if the PDF embeds a bitmap, take it at its
  **native** size (`pdfimages -all`). **Never up-sample.**
- Locate panel bounding boxes; store in `.pcr/paper_figs/panels.json`.
- Note what the render destroyed: a published panel is typically 8-bit, log-compressed, per-panel
  normalised. **You can only compare what survives rendering.** Say so in the report.
- **Assumption to declare, not hide**: the gray→value mapping (gamma) is usually unknown. Assume
  linear, and record it as an unverified assumption.

## Step 2 — Axis calibration from **evidence**, never assumption ★

**This step dominates the conclusion.** In the source project a 2.5 mm calibration difference
**flipped which panel was judged wrong**. A conclusion that a calibration choice can invert is not
carried by that comparison at all.

Use every available line of evidence and **cross-check them**:

1. **The paper states the axes** → use it. (Highest.)
2. **Internal ruler** — a known physical spacing in the image (grid pitch, scale bar). Measure it in
   pixels. This is a *measurement*, not an assumption.
3. **Square-pixel / aspect test** — if the paper says `dx = dz`, the calibration must yield it.
4. **Cross-panel consistency** — if two panels share an axis, features common to both must land on the
   same pixels.

Worked case: a self-calibration gave 67.2 mm width; the config said 65 mm. The 65 mm choice produced
near-square pixels (0.1171 vs 0.1186 mm/px, 1.3% apart) matching the stated `dx = dz`, while 67.2 mm
was 4.1% off. Independently, the wire-row pitch measured 84.6 px = 10 mm → 0.1183 mm/px, agreeing with
the config to **0.3%**. Two independent measurements agreeing settled it.

Same case, cross-panel: two panels' rows coincided within 3–4 px. Had they used different axis
origins, they would have differed by **56 px**. That falsified the "different origins" reading.

**If two calibrations give opposite conclusions and no evidence separates them → report that the
comparison cannot decide. Do not pick.**

## Step 3 — Compare on the **coarser native grid**

The published panel's pixel size is a *display* choice; the underlying reconstruction is usually
coarser. Resample the **published** panel down to the reproduction's native grid — do **not** up-sample
the reproduction.

> Why: up-sampling the reproduction with nearest-neighbour manufactured block artifacts that
> **depressed the correlation** and made a decent match look like a failure. Never invent resolution.

Absolute level is meaningless (each panel is self-normalised) → remove a global offset before
computing residuals, and say you did.

## Step 4 — Sparse targets break correlation ★

On sparse point targets (wires, beads), 2-D correlation is **all-or-nothing**:

- offset > one target width (~1 mm) → correlation ≈ **0**
- offset ≈ half a lattice period → targets land *between* targets → correlation goes **negative**

So a low correlation does **not** mean "unrelated images". Measure the offset first:

- Search over shifts and report **the correlation at the best alignment, plus the offset**.
- **Bound the search inside one lattice period.** Outside it you pick aliases.
  > Case: an unbounded search returned dz = −5.00 mm — exactly half the 10 mm row pitch — as "optimal".
- If the optimum lands **on the search boundary**, the search failed. Report it as a failure, **not as
  a measurement**.
  > Case: two aberrated panels hit the ±4 mm boundary with correlations of 0.25–0.27; those offsets
  > were not measurements and were not quoted.

## Step 5 — Three levels, always all three (R6)

1. **Paper-defined metrics** (`targets.json`) — verdict table, frozen tolerances.
2. **Pixel level** — best-alignment correlation, RMS/MAE after offset removal, **difference map**.
3. **The picture** — side-by-side + difference map, and **actually look at it**.

> Why all three: a summary score matched the authors' to **1.1%** while pixel correlation was **0.25**.
> Both true; each alone misleads. The *figure* resolved it — the images were visually similar and the
> mismatch decomposed into sub-mm offsets, one pipeline-specific artifact, and background texture.
> The difference map is often the most informative artifact in the entire project.

## Step 6 — Use the control case ★

Identify the **simplest** panel — the one with the least machinery (no correction applied, no
aberrator, plain reconstruction). If your pipeline matches the authors', **that panel should match
best**.

> Case: the ground-truth panel (no aberrator, no algorithm — plain beamforming) reached only 0.577.
> That is a finding: **something differs upstream of the method under test**, in the basic
> reconstruction/render path. Without a control panel this would have been misattributed to the
> algorithm.

If the control fails, stop debugging the method. The problem is upstream.

## Step 7 — Read the direction of failure ★

A mismatch's **direction** carries information; a single upstream cause often explains several
mismatches at once.

> Case: the reproduced *uncorrected* image was visibly **less degraded** than the published one. That
> one observation simultaneously explained four separate discrepancies: a low enhancement ratio (a
> better starting point leaves less to gain), a *higher* similarity score for the baseline, an
> unexpected **success** where the paper reported failure, and a low amplitude ratio.
> The right sentence was not "our correction is weak" but **"our degradation is not as degraded as
> theirs"** — a completely different investigation.

When several metrics miss, ask: *is there one upstream difference that predicts all of these signs?*

---

## Verdict

```
REPRODUCED   ⟺  every target with load_bearing=true is inside its FROZEN tolerance
```

Tolerances come from the paper's own reported precision, set at extract time, **frozen**. Widening one
to pass is R2 fitting. Not matching is a result — write it down.
