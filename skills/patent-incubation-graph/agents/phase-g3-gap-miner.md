# Phase G3: Gap and Bridge Miner

## Input

- `technology_graph.json`
- `graph_schema.json`
- user goal from manifest

## Task

Find graph structures that can become patentable invention opportunities.

Search patterns:

1. Bottleneck: `need -> blocked_by -> constraint` plus a plausible bypass `function/component`.
2. Bridge: two high-value subgraphs with no explicit prior-art bridge and no strong motivation to combine.
3. Pareto move: improves a target parameter without degrading the dominant constraint.
4. Detectable effect: a claim element leading to a product-visible or measurable effect.
5. Design-around weakness: a likely competitor bypass path that can be blocked with a fallback element.

## Output

Create:

- `graph_opportunities.json`
- `graph_gap_report.md`

For every opportunity include graph node IDs, why it matters, likely claim angle, evidence, and risks.
