# The assumptions register — `.pcr/assumptions.md`

**The rule this file enforces: every core assumption the paper's claim rests on is written down,
quantified, and checked in code — before the verdict, not after the miss.**

The ledger (`missing.md`) guards against information the paper *does not give*. This register guards
against the opposite: information the paper **does give** — its validity conditions, approximations,
idealisations, definitional conventions — that the reproduction silently ignores. An algorithm can be
coded perfectly and still fail (or "succeed") for a reason the paper's own assumptions already
predict.

Every rule below is a real event from the head-wave reproduction (Mozaffarzadeh et al., IEEE TUFFC
2022). The register systematises what that project found **by accident, late**:

> The paper's own caveat — "the method is accurate if the thickness of the aberrator is larger than
> the wavelength" (p.2) — was only connected to the model *after* rounds of estimator sweeps. One
> ratio (plate = 2.1–4.1 mm = **1.6–3.2 λ**, marginal) explained the dominant contaminant (a
> ~2000 m/s guided event no estimator could shake) and reframed the entire residual. Had A-rules
> below been run at spec time, that check costs one line of arithmetic on day one.

---

## Entry format

```markdown
### A003 — aberrator thicker than wavelength
- **Statement (verbatim)**: "The method is accurate if the thickness of the aberrator is larger
  than the wavelength" [p.2 §I]
- **Kind**: validity-condition        # validity-condition | approximation | idealisation |
                                      # convention | definitional | implicit
- **Quantitative form**: t_plate / λ (λ = c_bone / f_c) — HOLDS if > 1 with margin, MARGINAL near 1
- **Applies to**: fig3_headwave_speed (load-bearing), extraction-window choice (M002)
- **Check**: computed in `code/tests/test_assumptions.py::test_a003` from model geometry + source band
- **Status**: MARGINAL — t = 1.6–3.2 λ (computed this session)
- **Consequence if violated**: plate/guided modes contaminate the transform; predicts a slow
  (< c_bone), dispersive competitor in f-k — OBSERVED (~2000 m/s ridge dominates W1)
```

Required fields: `Statement (verbatim)` with citation (or `implicit` with grounds), `Kind`,
`Quantitative form`, `Applies to`, `Check`, `Status`, `Consequence if violated`.

`Status` ∈ {**HOLDS**, **MARGINAL**, **VIOLATED**, **UNTESTABLE**} — always with the computed number
or the reason it cannot be computed. A status without a number is a vibe, not an audit.

---

## A-1 — Harvest at spec time, from three places

Sweep the paper once, when writing `spec.md`, for:

1. **Caveat language**: "assuming", "provided that", "valid when/if", "we neglect", "in the limit",
   "approximately", "ideal(ised)". Each hit is a candidate entry.
2. **Derivation conditions**: every equation the reproduction uses carries the conditions of its own
   derivation (small-angle, far-field, single-mode, lossless…). If the paper cites the equation from
   a reference, the condition lives in the reference — fetch it (Phase 3) or ledger it.
3. **Definitional statements**: sentences that *define* a quantity ("the head wave is the first
   arriving signal") are assumptions the algorithm may lean on — and provenance for algorithmic
   choices (see A-5).

Unstated-but-load-bearing assumptions (plane wave, weak scattering, stationarity…) are entered as
`Kind: implicit` **with grounds for why the method needs them** — an implicit entry without grounds
is an invention (R1 applied to assumptions).

## A-2 — Quantify and check in code, not by eyeball

Every entry whose quantitative form is computable from the model/data gets a **computed check** —
preferably a test in `code/tests/test_assumptions.py` so the test gate (Phase 4) re-runs it whenever
the model changes. The audit is an instrument; R5 applies (a check that cannot fail on a
counter-example is not a check).

`UNTESTABLE` is a legitimate status — **declared**, never silently dropped, and reported as a limit.

## A-3 — The consistency chain at verdict time

Before any figure verdict, for **each load-bearing target**, write the chain:

```
target ← estimator ← transform ← data ← model
          each link: which A-entries does it depend on? status of each?
```

- All HOLDS → an eventual miss must be explained elsewhere (implementation, unknowns, paper error).
- Any **MARGINAL / VIOLATED** → derive the **predicted failure direction** from the violation and
  compare it with the observed one (compare.md Step 7). A violation that *predicts the observed
  sign and scale* is the leading explanation — and converts "mysterious residual" into "regime
  effect the paper itself warned about."
  > Head-wave: MARGINAL thin plate predicts a slow dispersive competitor → observed ~2000 m/s ridge;
  > SIM-1 symmetry (α = 0 ⇒ V1 = V2) predicts any V1/V2 asymmetry is estimator noise → both the
  > paper's asymmetry and ours were noise; only the harmonic mean was meaningful (CP-3).
- A MARGINAL/VIOLATED assumption is **never** a licence to widen a tolerance (R2). It explains a
  miss; it does not absorb one.

## A-4 — An assumption is not a knob

If the paper's **own stated setup violates its own assumption** (as in the thin-plate case), do
**not** alter the model away from the paper's setup to make the assumption hold — the paper's setup
wins (R3). The self-violation is a **finding about the paper**: record it beside the
internal-inconsistency rows in `spec.md` and report it. Conversely, if only *your* modelling choice
violates an assumption the paper's setup satisfies, that is your bug — fix the model, not the
register.

## A-5 — Assumptions are provenance for algorithmic choices

When an implementation choice is justified by a paper assumption, tag it
`@src{assumption A00N, p.X}` — this is legitimate provenance, not invention, **iff** the entry holds
a verbatim citation.

> Head-wave: the first-arrival mute in the semblance estimator was licensed by the paper's own
> definition "head wave = the first arriving signal" — which is what made the mute non-circular.
> Without the register entry, the same mute is an unprovenanced choice that happens to help (R2 bait).

---

## Integration

- **Written**: Phase 1.5 (workflow.md), right after `targets.json` is frozen — the assumptions and
  the tolerances are frozen by the same discipline, before any run.
- **Checked**: Phase 4 — `test_assumptions.py` runs under the test gate with everything else.
- **Consulted**: Phase 5 Step 7 (failure direction) and every iteration prereg — a hypothesis that
  contradicts a HOLDS entry, or ignores a VIOLATED one, is mis-aimed before it runs.
- **Reported**: Phase 8 — the register table (id, statement, status, consequence-observed?) goes in
  `REPORT.md`; the HONEST-LIMIT checklist requires the audit to have been done.

The register does **not** mechanically block the verdict (that stays with the ledger gate). It blocks
something subtler: calling a regime effect a mystery, or a mystery a regime effect, without ever
having written down which one the paper's own physics predicts.
