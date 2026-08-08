# Graph Schema Reference

Use this schema for `technology_graph.json`. Keep IDs stable and deterministic enough to trace across phases.

## Top Level

```json
{
  "schema_version": "0.1-draft",
  "domain": "",
  "created": "YYYY-MM-DD",
  "source_corpus": [],
  "normalization": {
    "synonyms": {},
    "units": {},
    "excluded_terms": []
  },
  "nodes": [],
  "edges": [],
  "quality": {
    "node_count": 0,
    "edge_count": 0,
    "claim_element_count": 0,
    "unsupported_inference_count": 0,
    "degraded": false,
    "notes": []
  }
}
```

## Node

```json
{
  "id": "n_component_001",
  "type": "component",
  "label": "",
  "description": "",
  "origin": "user_idea|source_doc|prior_art|inference",
  "properties": {
    "parameters": {},
    "detectability": "A|B|C|unknown",
    "claim_ready": false
  },
  "source_refs": [
    {"file": "", "locator": "page/section/line", "quote": ""}
  ],
  "confidence": 0.0,
  "notes": ""
}
```

## Edge

```json
{
  "id": "e_001",
  "type": "improves",
  "from": "n_function_001",
  "to": "n_effect_001",
  "description": "",
  "directionality": "directed",
  "source_refs": [],
  "confidence": 0.0,
  "notes": ""
}
```

## Candidate Path

```json
{
  "candidate_id": "C1",
  "title": "",
  "one_sentence_invention": "",
  "path_nodes": [],
  "path_edges": [],
  "core_claim_elements": [],
  "fallback_claim_elements": [],
  "distinguishing_features": [],
  "technical_effects": [],
  "detectability_grade": "A|B|C",
  "known_prior_art_risks": [],
  "source_refs": [],
  "graph_rationale": ""
}
```

## Confidence Rules

- `0.80-1.00`: directly supported by source or verified patent/NPL metadata
- `0.60-0.79`: supported by multiple indirect facts
- `0.40-0.59`: plausible inference, must be verified before final claim reliance
- `<0.40`: brainstorming only; do not use as final differentiator
