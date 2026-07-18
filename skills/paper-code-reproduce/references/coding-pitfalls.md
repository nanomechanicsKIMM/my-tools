# Translating the paper's math into code — errors that survive a clean lint

R1 (provenance) and R2 (no fitting) guard against *invented* values. This file is about the
opposite failure: a **correctly-sourced value that is still wrong** because the translation from the
paper's math/physics into code silently changed a convention. Every constant below carried a valid
`@src` and passed `pcr_lint`, and still produced a wrong or misleading number. Provenance proves you
did not invent a value; it does not prove you coded the equation the paper meant.

Every case is a real event from the head-wave reproduction (Mozaffarzadeh et al., IEEE TUFFC 2022).

The one test that catches all four: **reproduce one of the paper's own worked numbers through your
code path, and anchor every result to a physical scale, before trusting either on your own data.**

---

## CP-1 — Transform-domain conventions: the axis label can lie.

A figure axis is a *label*, not a specification. Pin every transform-domain unit to a quantity the
paper actually plots — never to the printed axis.

**Case (angular vs ordinary wavenumber).** Fig. 3(c)(d) printed the k-axis as `[1/m]`. The line fit
`V = 2π·slope` only closes if that axis is **angular** wavenumber (rad/m) — a hidden 2π. It was
confirmed not by trusting the label but by asking which quantity lands on the plotted scale: at
f = 3 MHz, `2πf/3138 = 6006 rad/m` sits where the ridge is drawn, while `f/3138 = 956` would be
off-scale. The label said `1/m`; the physics said `rad/m`.

**Case (FFT sign).** A forward-propagating event sits at **k < 0** under numpy's FFT sign
convention. An f-k wedge mute that required `k > 0` silently deleted the head wave and returned
**~2600 m/s for every planted velocity** (antifooling R5 #5). The sign was a convention, not a bug in
the math — but the code assumed the other convention.

Rule: before masking or fitting in a transform domain, **plant a known event and confirm its sign,
its 2π factor, and the FFT normalisation in your library's convention.** Determine these from where a
plotted quantity actually falls, not from the axis text.

---

## CP-2 — Equation interpretation: reduce it symbolically, then check it on the paper's own number.

**Case.** Eq. (1) is `c = 2·V1·V2·cos α / (V1 + V2)`. At the numerical model's α = 0 this reduces to
the **harmonic mean** of V1 and V2 — *not* the arithmetic mean. When V1 ≠ V2 that is a tens-of-m/s
difference, exactly the scale of the target's tolerance. Coding `(V1+V2)/2` would have missed by more
than the whole frozen window while looking innocent.

The safeguard that made the interpretation trustworthy: **run one of the paper's own worked examples
through the implemented equation.** Fig. 6's labels (V1 = 3439, V2 = 2762, α = 3.3°) give 3058.5 vs
the paper's reported 3058 m/s. That single check confirmed the equation, the units, and the angle
term at once — and it is *what licensed attributing the Fig. 3 discrepancy to the paper rather than
to our arithmetic* (see CP-3 of the self-consistency audit in workflow.md Phase 1).

Rule: implement the paper's equation, then **reproduce a number the paper computes with it** before
running it on your own data. An equation validated only on your data is untested.

---

## CP-3 — Match at the altitude the paper claims, not below it.

The paper stakes a number on the **combined** speed c (the harmonic mean), not on V1 and V2
individually. In the reproduction the per-element V1/V2 disagreed with the paper's and even had the
**opposite asymmetry** (paper V1 < V2; ours V1 > V2) — yet c is the only quantity the paper reports.
Checking against V1/V2 separately would have invented a stricter target the paper never claimed and
manufactured a "failure" out of estimator noise.

Rule: the oracle is the **exact quantity the paper reports**, at the exact altitude it reports it.
Do not synthesise a sub-target the paper never claims. But do not hide it either — when the
sub-components disagree, report that as an honest residual (the head-wave report did: "individual
V1/V2 are estimator-noise-dominated; only their harmonic mean is meaningful").

---

## CP-4 — Unit/scale sanity against a physical anchor.

Before any velocity or length enters a figure, anchor its magnitude to one known physical quantity.

**Case.** λ_bone = 3200 / 2.5e6 = 1.28 mm; the modelled plate is 2.1–4.1 mm = **1.6–3.2 λ**. That
single ratio connects to the paper's own caveat — "the method is accurate if the thickness of the
aberrator is larger than the wavelength" (p.2) — and flags that the thin-plate regime here is
**marginal**, a physical limit a pure number-match would never surface. It also framed the
unexplained ~2000 m/s guided event as a plausible thin-plate artifact rather than a mystery.

Rule: restate the unit at every step and check one magnitude against a physical anchor — a
wavelength, a transit time (`offset / c`), a Nyquist or critical-distance limit — before it enters a
figure. Watch conversions across the paper's own units (mm↔m, MHz↔Hz, samples↔time).

---

## The through-line

All four passed the provenance linter and all four produced wrong or misleading numbers. Sourcing a
constant is necessary and not sufficient. The two checks that are sufficient for *translation*
fidelity — distinct from the anti-fooling checks elsewhere in this skill:

1. **Round-trip a paper-computed number through your code** (CP-1, CP-2). If the paper does the
   arithmetic anywhere — a worked example, a second figure, a table entry — reproduce that before
   your own data.
2. **Anchor every result to a physical scale** (CP-4), and verify at the **altitude the paper
   actually claims** (CP-3).
