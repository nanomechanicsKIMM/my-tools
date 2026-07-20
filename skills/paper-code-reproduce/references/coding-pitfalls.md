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

## CP-5 — Conditioning is not scale-invariant: a reduced/clean check gives the wrong answer for the real problem.

The single most expensive pattern of the IMPACT reproduction (Ali et al., IEEE TCI 2023). An
ill-posed inverse problem (ray tomography: a near-singular `D A` operator) was probed for stability
**four separate times on a reduced or sanitised version of itself, and every probe gave the wrong
answer for the full, real problem:**

1. A "robust" noise anchor, correct *as a noise estimate*, under-regularised the real solve → it
   diverged (dc −809 m/s in a ±60 m/s medium). The physics of the *noise* did not determine the
   physics of the *solve*.
2. A conjugate-gradient sanity check on **clean synthetic** delays (no outliers) said the
   regularisation scale did not matter — on the **real bimodal** delays it decided divergence.
3. A convergence table showing "CG tolerance is irrelevant" was run on a **small well-conditioned
   test grid**; at full scale (43×64×128) the operator is near-singular and the CG **stopping rule
   IS the regularisation** (semi-convergence).
4. A synthetic maxiter sweep showed updates of ~50 m/s; the **real** delays gave 800+ m/s at the
   same settings.

Each was caught the same way — by **physical sanity, not output plausibility**: "is a −809 m/s
update credible in a medium that varies ±60 m/s?" No, so the run is diverging regardless of how
reasonable the image looks. Conditioning (rank, singular-value spectrum, semi-convergence) depends on
the operator's **actual size and the data's actual noise structure**; a 10× smaller grid or an
outlier-free RHS is a *different operator*.

Rule: **validate numerics on the ACTUAL operator with the ACTUAL noisy data, never a reduced or
cleaned proxy.** A stability/conditioning result from a small grid or a clean synthetic RHS
transfers *nothing* to the full problem. And for any ill-posed iterative solve, ship a **fail-loud
divergence guard on a physical bound** (abort if an update exceeds ~3× the medium's real range),
saving the diverged state before aborting — it turns a silent garbage run into a clean iteration-0
stop. In IMPACT this guard caught two would-be-garbage figure runs at their first iteration.

## CP-6 — A regulariser is its SHAPE **and** its scale, normalisation, and grid — the paper usually gives only the shape.

The IMPACT paper specified its prior's *shape* (a 3 mm-FWHM Gaussian) and named "conjugate gradient".
It did **not** state: the prior's amplitude/variance, whether the kernel is normalised, the
measurement-noise scale, the CG stopping rule, or the grid the slowness is reconstructed on. Every
one of those is a separate free parameter that changes the **conditioning**, and the reproduction
linted the *shape* clean (3 mm FWHM, correctly sourced) while getting the numerics wrong. Comparison
with the released code showed the authors used an **unnormalised** kernel (≈235× gain, so the noise
term does real Tikhonov work), a hand-set relative-error noise scale, a fine reconstruction grid from
coarse measurements, and a fixed small CG cap — none in the paper.

Rule: when a paper names a regulariser, prior, or iterative solver, enter its **scale, its
normalisation, and the grid it acts on as separate `@missing` ledger items** — not just its shape.
A normalised-vs-unnormalised kernel flips the conditioning; "3 mm Gaussian" is a quarter of the
specification. See references/ledger.md for how to register these.

---

## The through-line

Six cases, all passing the provenance linter, all producing wrong or misleading numbers. Sourcing a
constant is necessary and not sufficient. The checks that are sufficient for *translation* fidelity —
distinct from the anti-fooling checks elsewhere in this skill:

1. **Round-trip a paper-computed number through your code** (CP-1, CP-2). If the paper does the
   arithmetic anywhere — a worked example, a second figure, a table entry — reproduce that before
   your own data.
2. **Anchor every result to a physical scale** (CP-4), and verify at the **altitude the paper
   actually claims** (CP-3).
3. **Validate conditioning on the real operator + real noisy data** (CP-5), and register a
   regulariser's scale/normalisation/grid, not only its shape (CP-6). A conditioning result from a
   reduced or cleaned proxy transfers nothing.
