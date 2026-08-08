# Phase G2: Technology Graph Builder

## Input

- `graph_schema.json`
- `invention_manifest.json`
- source corpus files
- `reference/graph-schema.md`

## Task

Extract a source-backed technology graph.

1. Split the corpus into atomic technical assertions.
2. Create nodes for needs, functions, components, parameters, effects, constraints, prior-art disclosures, principles, claim elements, and market actors.
3. Create typed edges only when the relationship is explicit or technically necessary.
4. Preserve source provenance in `source_refs[]`.
5. Mark unsupported inferences as `origin: inference` and `confidence <= 0.55`.
6. Merge duplicate nodes only when synonyms and technical role both match.

## Quality Gate

Flag degraded mode when:

- total nodes < 30
- total edges < 40
- claim-ready elements < 8
- more than 30% of graph-important edges are unsupported inferences

## Output

Write `technology_graph.json` matching `reference/graph-schema.md`.
