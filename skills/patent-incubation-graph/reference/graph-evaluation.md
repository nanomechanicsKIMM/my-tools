# Graph Candidate Evaluation

Score every candidate on a 1-10 scale, then compute the weighted total.

| Axis | Weight | What To Reward | Penalize |
|---|---:|---|---|
| Novelty / Differentiation | 0.25 | clear `distinguishes` edges from close prior art | feature fully covered by one prior art node |
| Inventive Step | 0.20 | weak motivation to combine, teaching away, unexpected effect | routine substitution or aggregation |
| Claim Strength | 0.20 | compact independent claim, fallback dependent claims, support in spec | result-only claim, missing antecedent, single narrow embodiment |
| Detectability | 0.15 | product-visible feature or measurable process fingerprint | only internal settings visible to implementer |
| Business Usefulness | 0.10 | blocks competitor route or covers likely product/process | niche workaround with low adoption |
| Graph Evidence | 0.10 | high-confidence path with source-backed effects | speculative path or unsupported effect |

## Verdict

- `go`: total >= 7.5 and no critical prior-art risk
- `revise`: total >= 6.2 but claim or evidence needs strengthening
- `hold`: promising but missing source, market, or implementation evidence
- `drop`: low score, fully anticipated, or impossible to enforce

Always include one devil's-advocate paragraph for each `go` candidate.
