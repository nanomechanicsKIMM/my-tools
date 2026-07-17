# The unprimed critic (Phase 7)

Triggered when **3 iterations in a round** end without reproduction.

---

## Why unprimed is the whole point

> **Case.** A critic was asked to verify a conclusion **that was stated in the prompt**. It agreed. The
> agreement was worthless — and the conclusion was wrong. The same critic, asked cold later, produced
> the single most valuable finding of the project (an oracle of absolute values nobody had noticed).

A critic that can see your conclusion is a rubber stamp. The only thing it can tell you is that your
prose was persuasive.

## What the critic gets — and does not

| Give | Withhold |
|---|---|
| `paper.pdf` (+ `refs/`) | your reports, hypotheses, conclusions |
| `code/src/` | `.pcr/state.md`, `decisions.md`, `iterations/` |
| `.pcr/spec.md` | which metrics miss and by how much |
| the figure(s) to reproduce | your suspicions about the cause |

Code comments citing the paper (`@src{...}`) are fine — they are provenance, not conclusions.

Withhold the metric gaps too. "CF is 40% high" invites the critic to rationalise *that* number instead
of reading the paper against the code.

## Prompt template

```
You are auditing a from-scratch reimplementation of a paper against the paper itself.

Inputs: <paper.pdf>, <refs/>, <code/src/>, <spec.md>

Task: find DISCREPANCIES between what the paper specifies and what the code does.
For each: cite the paper (page/section/line) AND the code (file:line), and state
what the code would do differently if it followed the paper.

Rules:
- Do not seek agreement. Your job is to find what is wrong.
- Cite primary sources by FIELD/SECTION NAME, not by remembered values.
- If you are unsure, say "unverified" rather than asserting.
- Rank by whether the discrepancy could change the figure.
```

**Do not** append "we think the problem is X". That is the priming that voids the exercise.

## Default: cross two critics

Run **codex and opus** on the same unprimed brief, independently. Compare:
- **Both flag it** → highest priority.
- **One flags it** → verify before acting.
- **They disagree** → informative; the disagreement usually marks genuine ambiguity in the paper
  (a good `missing.md` candidate).

```
Skill({skill: "ask", args: "codex <unprimed brief>"})
Agent({subagent_type: "critic", model: "opus", prompt: "<same unprimed brief>"})
```

## Verifying the critic — **both directions** ★

Claims must be checked against primary sources before adoption. **So must your refutations.**

> **Case.** The critic cited a log field by its **rounded** value ("3.38"). A grep for `3.38` returned
> nothing — the stored value was `3.37751341`, which that string cannot match. It was declared a
> fabrication. Worse: a standing rule ("this critic hallucinates") was built on that false positive and
> used to dismiss its later, correct points. **The field existed all along, and the dismissed
> reinterpretation was right.**

Rules that follow:

1. **Check existence by field/section NAME, never by a rounded value.**
2. **When your evidence is "grep found nothing", suspect the grep first.** Absence of a search hit is
   evidence about your search string.
3. **Never build a standing rule from a single refutation.** If you conclude a critic erred, verify
   *that* conclusion as carefully as you would verify the claim.
4. A verified claim is adopted **regardless of who was right before**.

## After the critic

- Verified findings → `.pcr/decisions.md` with source citations.
- Findings that turn out to be genuine paper ambiguities → **`missing.md`**, not a guess.
- Then resume the loop: each fix still needs a pre-registration (R4) and an `@src` (R1).

**A critic finding is not a licence to skip R2.** If the critic proposes a value with no source and it
happens to make the metric match, it is still fitting.
