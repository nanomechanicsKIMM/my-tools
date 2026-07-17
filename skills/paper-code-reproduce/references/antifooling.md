# R1–R8 — the eight rules and the real errors behind them

Every rule below is followed by the actual event that produced it (A-CLASS Fig.2 reproduction,
2026-07-13~17). Read the cases, not just the rules: the rules are cheap to agree with and easy to
violate while agreeing.

---

## R1 — No unprovenanced value

Every numeric literal and algorithmic choice in `code/src/` carries `@src{...}` or `@missing{ID}`.

```python
C0 = 1549.0        # @src{paper:methods p.7 "recorded speed of sound was 1549 m/s"}
LENS_T0 = 15.98    # @missing{M003}   ← blocks the verdict gate
WINDOW = "hann"    # ← untagged → pcr_lint FAIL. This is an invention.
```

**Case.** A lens-delay constant was derived from a plausible-sounding formula (whole transit
`2h/c_lens`) that nobody had written down. It was wrong — the correct quantity was the *excess over
the homogeneous path it displaces*. Because the value carried no derivation in the code, the error
survived multiple sessions and silently biased every depth. A `@src` tag forces the derivation to be
written where it can be checked.

**Why untagged == invented**: if you cannot name the source, you chose it. Choosing is inventing.

---

## R2 — No metric fitting  ★the most important rule

> **If the only reason you can justify a value is that it makes the metric match, it is banned.**

Distinguish two things that look identical in a diff:

| | |
|---|---|
| **Consequence (allowed)** | You fix a defect the paper mandates; a metric moves toward the target as a *side effect*. The justification stands without the metric. |
| **Aiming (banned)** | You turn a free knob until the target is hit. Remove the target and the justification vanishes. |

**Case A — allowed.** The paper stated "Tx/Rx aperture-supported" sampling and its focusing weight
was indexed by transmit basis. The code applied the aperture on the receive axis only. Fixing that
was mandated by the text; CF then moved from 2.06 toward the paper's 1.50 — a consequence. Adopted.

**Case B — banned.** The data "wanted" a lens offset of 7.4 samples: at that value the depth error
went to zero. No principled candidate produced 7.4. A sweep then showed depth and coherence were
**independent knobs** — nothing but the target itself supported 7.4. Rejected; the depth gap was
reported as unexplained.

**Case C — banned.** With one convention the coherence factor read 0.1137, with another ~0.08; the
paper's value 0.0770 sat **between them**. Picking the closer one would have "matched". Rejected —
when candidates *bracket* the target, the metric cannot discriminate and choosing is fitting.

**Case D — the scar.** A genuine bug (a regularisation epsilon referenced to the wrong statistic)
made CF land on 1.50 — *exactly* the paper's value — by coincidence. Had that been read as success,
a real bug would have been shipped as a reproduction. **One metric hitting is not evidence.**

---

## R3 — Source hierarchy

**paper body > supplementary > author config/log > cited refs > convention.** Higher wins on conflict.

**Case.** A tool config listed a convergence threshold of `1e-3 periods`. Trusting it, a previously
**correct** judgement ("we miss the paper's criterion by a hair") was "corrected" into a **wrong** one
("we miss it by 2×"). The paper's own body said plainly: *"below 0.01 rad for at least five
consecutive iterations"* — exactly the implemented criterion. A config value had overridden the text
that the figure was actually described by.

⇒ Configs and logs describe *a* run. The paper body describes *the* claim.

---

## R4 — Pre-register

Before looking at data, write in `.pcr/iterations/NN/prereg.md`:
- the hypothesis, in one sentence;
- the **prediction** ("if this is the cause, X moves A→B; if it doesn't move, I reject");
- a **falsification device**: something that **must not change** if the reasoning is right;
- the single variable being changed, and its `@src`.

**Case (it worked).** Four attractive hypotheses were killed by their own pre-registered predictions
— reverberation clutter (predicted −39% on a baseline metric, got −4.5%, and the second metric moved
the *wrong way*), a time-origin hypothesis, a bandwidth hypothesis, and an amplitude-accumulation
hypothesis. Judged after the fact, any of them could have been narrated into a story.

**Case (the device worked).** Testing a depth-gain change, the run also printed a coherence ratio that
**must** be invariant under it (a per-pixel gain cancels in that ratio). It printed identically —
the test was valid. Had it moved, the reasoning was wrong and the test void.

**Corollary — don't over-generalise a passed device.** That invariance held for the *whole-image*
statistic but **not** for the top-percentile one, whose mask is brightness-ranked and therefore does
move. The device passed; the sentence written about it was too broad.

---

## R5 — Distrust instruments

A measurement function is not trusted until it recovers a **planted** ground truth.

**Cases — four instrument bugs, each nearly reported as physics:**
1. A registration tool's lateral offset locked onto a **half-period lattice alias**; the reported
   value was an artifact of the target's own periodicity.
2. A panel comparison's axis calibration was assumed; a 2.5 mm choice **flipped which panel was
   judged wrong**. A conclusion that a calibration choice can invert cannot be carried by that tool.
3. A stored "transition iteration" field was `argmax` over all iterations and therefore returned the
   **start-up transient (iteration 1) every single time**. The real value had been read by hand for
   weeks.
4. A figure comparison up-sampled the *reproduction* onto the published display grid, manufacturing
   block artifacts that **depressed the correlation**. The published panel was itself an enlargement;
   the right move was to return it to the native grid.
5. (head-wave sim) A velocity picker returned **~2600 m/s for every planted velocity** — an f-k wedge
   required `k>0` while numpy's FFT convention puts a forward event at `k<0`. Only the planted test,
   run at three different velocities, exposed it; a single planted value would have looked plausible.
6. (head-wave sim) A planted test passed while the tool was broken, because the **plant was cleaner /
   weaker than the real data** — see references/simulation.md SIM-3. The plant has to contain the
   real record's dominant competitor at real strength, or a green test certifies a broken tool.

⇒ Plant a known answer — at more than one value, and containing the real data's loudest competitor.
If the tool can't find it, the tool is the finding. For simulation instruments, references/
simulation.md (SIM-1..SIM-4) is the fuller treatment.

---

## R6 — Summary statistic ≠ identity

**Case.** A structural-similarity score against ground truth matched the authors' to **1.1%** — while
the direct pixel correlation between the two figures was **0.25**. Both numbers are true. Read alone,
each is a lie: the first says "reproduced", the second says "unrelated".

Looking at the figure resolved it: the images were visually similar and the mismatch decomposed into
(i) sub-millimetre target offsets — on sparse point targets, an offset of one target width drives
correlation to zero — (ii) an artifact unique to our pipeline, and (iii) background texture.

⇒ Report metrics **and** pixels **and** look at the picture. Two different images can score the same.

---

## R7 — Unprimed verification

Never hand a critic your conclusion.

**Case (priming).** A critic was asked to check a conclusion that was *stated in the prompt*. It
agreed. The agreement was worthless and the conclusion was wrong. Asked cold later, the same critic
produced the single most valuable finding of the project.

**Case (the false accusation).** The critic cited a log field by its **rounded** value ("3.38"). A grep
for `3.38` returned nothing — the stored value was `3.37751341`, which that string cannot match. It
was declared a fabrication. A standing rule ("this critic hallucinates") was then built on that false
positive and used to dismiss its later, correct points. The field existed all along.

⇒ Verify claims **and** verify your refutations. Check field **names**, not rounded values. When your
evidence is "grep found nothing", suspect the grep first.

---

## R8 — Resist both pressures

Two opposite failures, one rule.

**False success** — claiming a match you don't have. Guarded by R1/R2.

**False failure** — promoting "not yet" to "impossible". **Case:** a metric shortfall was declared a
physical floor after ablating six levers — but the ablation had been thorough on one family of
parameters and had **skipped the frequency/band axis entirely**. The band was the real lever. The same
error then repeated on a second metric. Persistent refusal to accept the early "impossible" verdict is
what overturned both.

⇒ Before writing "limit", **enumerate the orthogonal axes you have not touched**: preprocessing/band,
display vs estimation, normalisation convention, time windows, aperture/f-number, metric definition.

**Case (invariant beats sweep).** A simulated record had energy arriving *before* `offset / c_max` —
physically impossible. A multi-round sweep of the *estimator's* parameters never explained it; one
**causality invariant** on the raw data found it immediately (an FFT-periodic solver wrapping around a
too-small domain). When a result resists a parameter sweep, assert a physical invariant instead — it
localises the artifact in one step. See references/simulation.md SIM-1.

---

## The meta-lesson

The source project's most valuable deliverable was not the reproduction — it was the **list of 15
self-corrections**. Of those, the ones that mattered most were where a *previous correction* was
itself wrong (a right judgement "fixed" into a wrong one), and where a *rule* had been built on a
false positive.

Being willing to write "I was wrong, and here is what I damaged with it" is the load-bearing habit.
This skill exists to make that habit structural rather than optional.
