# Reproducing a figure from a wave / physics simulation you build yourself

The A-CLASS cases (antifooling.md) come from reprocessing *supplied* data. A whole other
class of reproduction builds the **forward model** too: you simulate the data (k-Wave,
FDTD, a solver) from a geometry the paper only draws, then run the paper's estimator on it.
Everything in antifooling.md still applies; this file adds what only shows up when the
data is yours to generate.

Every rule below is an actual event from reproducing Fig. 3 of a transcranial ultrasound
paper (Mozaffarzadeh et al., IEEE TUFFC 2022) — a k-Wave simulation of a bidirectional
head-wave speed measurement, built from the paper's PDF alone. None is invented.

---

## SIM-1 — The solver has artifacts. Add a physical-invariant control, not a parameter sweep.

A simulator is an instrument (R5). Its output is trusted only after it passes a control
that a *real* medium would also pass.

**Case (the scar).** The paper's numerical model (Fig. 2(a)) was drawn ending 0.28 mm
outside the outermost array element. k-Wave's k-space solver is **FFT-periodic**; with a
sub-wavelength PML there, energy leaving one lateral edge re-entered at the other. Because
the source sat *at* the edge, that wrapped energy reached the far elements **before any
physical arrival**: the record showed envelope peaks at 6.9 and 7.8 µs on a trace whose
earliest physically possible arrival (offset / c_max) was 8.8 µs.

**The invariant that caught it in one step:** *nothing can arrive faster than
offset / c_max.* That single causality check found the artifact after a multi-round
parameter sweep of the estimator had not. Enumerate the invariants your physics guarantees
and assert them on the raw simulated data **before** running any estimator:
- causality: no coherent energy before `offset / c_max`;
- reciprocity / symmetry: a left-right symmetric model gives left-right symmetric data
  (here: element-1 and element-96 first breaks agreed to 0.01 µs — so a later "V1 vs V2"
  asymmetry was estimator noise, not physics);
- energy conservation in a lossless run;
- the control that removes the suspected artifact must **not** move the physical arrivals
  (here: widening the domain 8 mm killed the pre-causal peaks and left the head wave at
  13.46 vs 13.48 µs — unchanged, so the fix was clean).

**The reasoning error worth remembering:** the domain size was dismissed as "our choice,
not a claim about the paper, so it can't matter." *Our choice* and *doesn't matter* are
different statements. A parameter can be entirely yours to set **and** decide the result.

> Pre-register the control (references/workflow.md Phase 6): predict that the artifact
> vanishes AND that the physical arrivals do not move; the second is the falsification
> device. If the physical arrival moves with the domain, the geometry is wrong, not the box.

---

## SIM-2 — Coherence beats amplitude for measuring a slope / velocity.

When a paper reads a velocity or slope off a transform ("the slope of the line fit on the
**high intensity region**", an f-k ridge, a τ-p peak), an **amplitude / energy-maximum**
picker rails onto whatever is *brightest*, which is frequently not the event you want.

**Case.** The head-wave speed had to come from the moveout of a weak first arrival. Every
amplitude-based reading of "the high intensity region" (threshold, ridge-peak, energy-
weighted, centroid) railed onto a strong, **c-independent** near-surface guided wave
(~2000-2350 m/s apparent) that dominates the transform. Across the admissible extraction
ranges the four pickers swung over **1316 m/s** — the answer was set by an unstated
parameter, not by the physics.

**The fix (standard refraction-seismics, and the physically correct estimator):** mute the
near cone, keep the far-offset **first arrival**, and pick velocity by **semblance
(coherence)** — how well a moveout `t = τ + offset/v` *aligns* the traces — not by
amplitude. Coherence locks onto the weak-but-aligned head wave and ignores the strong-but-
wrong slow event. Result on the same data: **6 m/s** spread across all scan ranges, versus
the amplitude picker's 1316.

**The general payoff — this is the transferable finding:** *a robust estimator removes the
reproduction's dependence on an unspecified parameter.* The blocker was "the paper doesn't
say what velocity range / high-intensity region it used." A coherence estimator made the
answer nearly independent of both, converting a HIGH ledger unknown into a non-issue
**on evidence**. When an unstated estimator detail dominates your result, the first move is
a more robust estimator, not a guess at the detail.

> Caveat kept honest: the robust estimator here was also more *biased* (+76 m/s vs the
> amplitude picker's best-case −20) — it traded a lucky-close-but-unstable number for a
> stable-but-offset one. Report both; do not sell robustness as accuracy.

---

## SIM-3 — The plant must contain the data's DOMINANT failure mode (R5, sharpened).

R5 says a measurement tool must recover a planted ground truth. Sharpened for simulations:
the plant has to contain the specific structure that breaks the tool **on the real data**,
at the real strength and spacing — or it certifies a broken tool.

**Two cases, opposite directions, same lesson:**
1. A first-break picker was "validated" by a plant containing *only* the head wave. On real
   data the head wave was 7-24% of the trace peak and the picker locked onto a later, 4×
   stronger reverberation. The plant was **cleaner** than reality.
2. A coherence estimator was "validated" by a plant with a slow *guided* wave. On real data
   the true competitor was a slower *refracted* branch (a 1600 m/s skin head wave) that is
   both coherent and stronger than the target — the estimator railed to the scan floor. The
   plant was **weaker** than reality (missing the dominant competitor).

A plant can fail by being too clean **or** too weak. Before trusting a green planted test,
ask: *what is the single loudest / most-coherent thing in the real record that competes
with my target, and is it in the plant at that strength?* If not, the test proves nothing.

---

## SIM-4 — Build the geometry from the figure as a validated instrument.

When the model geometry lives only in a figure (layer thicknesses, a scatterer field, an
irregular boundary), reading it is a measurement (R5), and the figure-reader is an
instrument that must recover **numbers the paper states independently of that figure**.

**Case.** The lens thickness was never stated; it had to be read off Fig. 2(a). The reader
was trusted only after it recovered, from the same panel, the *stated* skin thickness
(2.1 mm → 2.14), skull min (2.1 → 2.00) and max (4.1 → 4.09), using a depth calibration
derived from the **axis tick labels alone** — independent of those thicknesses. Only then
was the unstated lens value (1.18 mm) used. Two wrong versions preceded the good one, each
mis-reading printed annotation ("Skull"/"Skin" text) as a layer boundary — caught precisely
because the stated thicknesses did not come back.

Rule: calibrate from the axes; validate against independently-stated quantities; keep any
figure-read value tagged as *measured from a figure* (`@missing` → `RESOLVED[fig, measured]`),
never silently promoted to a paper value.

---

## Checklist for a simulation-based reproduction

- [ ] Geometry instrument validated against independently-stated numbers (SIM-4).
- [ ] Causality + symmetry + conservation invariants asserted on RAW simulated data (SIM-1).
- [ ] Domain / boundary / PML run as a pre-registered control; physical arrivals unmoved.
- [ ] Estimator is coherence-based where a slope/velocity is read from a transform (SIM-2).
- [ ] Robust estimator used to test whether an unstated parameter still matters (SIM-2).
- [ ] Every planted test contains the real data's dominant competitor at real strength (SIM-3).
- [ ] Solver constants (dx, dt, PML, domain) tagged `@src` (from the paper) or `@missing`.
