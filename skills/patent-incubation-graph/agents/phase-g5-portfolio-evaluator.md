# Phase G5: Portfolio Evaluator

## Input

- `candidate_paths.json`
- `technology_graph.json`
- `reference/graph-evaluation.md`

## Task

Score and rank candidates.

For each candidate:

1. Score the six weighted axes from `reference/graph-evaluation.md`.
2. Write a concise positive rationale.
3. Write a devil's-advocate attack.
4. Assign `go`, `revise`, `hold`, or `drop`.
5. Recommend independent/dependent claim strategy.

## Output

Write `portfolio_evaluation.json` with sorted candidates and a `recommended_selection`.
