# Phase D1: Graph-Based Disclosure Writer

## Input

- selected candidate from `candidate_paths.json`
- `portfolio_evaluation.json`
- `technology_graph.json`
- `prior_art.json`
- original source corpus
- `reference/claim-drafting.md`
- `reference/user-philosophy.md`

## Task

Write `selected_invention.md` in the same KIMM invention disclosure structure used by `patent-incubation-auto`.

## Required Structure

- YAML frontmatter
- §1 발명(고안)의 명칭
- §2 논문발표/외부공개 여부
- §3 발명(고안)의 배경(동기)
- §4 종래기술 및 문제점
- §5 발명(고안)의 목적
- §6 발명(고안)의 구성
- §7 발명(고안)의 효과
- §8 보호받고자 하는 사항(청구범위)
- 요약서
- §9 추가자료
- 부록 A: 그래프 기반 도출 로그
- 부록 B: 선행특허 대비 및 청구항 매핑
- 부록 C: 참고문헌

## Writing Rules

- Do not expose graph-mining jargon in §1-§9.
- Do not expose TRIZ jargon in §1-§9.
- Every independent claim element must map to at least one graph node.
- Every stated effect must map to an `effect` node or be phrased as expected/anticipated.
- Include fallback dependent claims for design-around routes.
- Keep drawing labels free of reference numerals.

## Output

Write `selected_invention.md` and `claim_graph_map.json`.
