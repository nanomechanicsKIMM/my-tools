# Phase G4: Candidate Path Generator

## Input

- `technology_graph.json`
- `graph_opportunities.json`
- user goal

## Task

Convert opportunities into 3-10 patent candidate paths.

Each candidate must be more than an idea label. It needs:

- problem
- technical means
- concrete configuration or process sequence
- technical effect
- independent-claim core
- dependent-claim fallback elements
- prior-art risk hypothesis
- detectability grade

Avoid candidates that are only desired results, business goals, or unimplemented aspirations.

## Output

Write `candidate_paths.json`.

If fewer than 3 candidates are credible, explain why and identify what source data is missing.
