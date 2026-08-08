# Phase G1: Graph Schema Builder

## Input

- `invention_manifest.json`
- source corpus list
- optional user constraints

## Task

Create `graph_schema.json` for the technology domain.

1. Identify domain-specific node subtypes for `component`, `function`, `parameter`, `effect`, `constraint`, and `claim_element`.
2. Build a synonym and abbreviation map. Normalize Korean/English terms when both appear.
3. Define forbidden merges, especially between cause/effect, component/function, and user idea/prior art.
4. Define claim-readiness criteria for this domain.
5. Define quantity/unit normalization rules.

## Output

Write JSON with:

- `domain`
- `node_type_guidance`
- `edge_type_guidance`
- `synonyms`
- `unit_rules`
- `claim_readiness_rules`
- `quality_checks`

Do not draft claims in this phase.
