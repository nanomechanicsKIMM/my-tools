#!/usr/bin/env python3
"""claim_parser.py — 한국 특허 청구항 구조·종속 관계 파서

Patent-draft-review 스킬의 Phase 3(claim structure)에서 사용.
청구항 섹션 텍스트 또는 spec_structure.json 을 입력받아 각 청구항의
독립/종속 관계, 카테고리(시스템/방법/물건), 전문부 존재 여부,
"것을 특징으로 하는" 표현 사용 여부를 구조화하여 출력.

=== 사용법 ===

    # 청구항 섹션 텍스트 파일에서 직접
    python claim_parser.py --claims-md <claims.md> --output <out.json>

    # spec_structure.json 의 claims 섹션 사용
    python claim_parser.py --spec <spec_structure.json> --output <out.json>

=== 출력 스키마 ===

    {
      "source": "<input path>",
      "total_claims": N,
      "independent_claims": [1, 9],
      "dependent_claims": [2, 3, 4, ...],
      "claims": [
        {
          "num": 1,
          "dependent_of": null,
          "category": "system | method | product | use | unknown",
          "length_chars": 456,
          "has_preamble": true,
          "uses_characterizing_expression": false,
          "preamble_text": "...",
          "body_text": "...",
          "sub_bullets": ["적어도 하나 이상의 초음파 프로브", ...],
          "text": "전체 텍스트"
        }
      ],
      "dependency_tree": {
        "1": [2, 3, 4, 5, 6, 7, 8],
        "9": [10, 11, 12, ...]
      },
      "summary": {
        "independent_count": N,
        "dependent_count": N,
        "system_count": N,
        "method_count": N,
        "max_depth": N
      }
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 정규식
# ---------------------------------------------------------------------------
# 청구항 헤더: "## 청구항 N" 또는 "청구항 N" 또는 "[청구항 N]"
CLAIM_HEADER_RE = re.compile(r"^(?:##\s*|\[)?\s*청구항\s*(\d+)\s*\]?\s*$")

# 종속 표현: "제N항에 있어서"
CLAIM_DEPENDENCY_RE = re.compile(r"제\s*(\d+)\s*항\s*에\s*있어서")

# 카테고리 추정: 청구항 말미 표현 기반
CATEGORY_PATTERNS = [
    ("system",  re.compile(r"(?:시스템|장치|디바이스|기기|회로|기판)\s*\.?\s*$")),
    ("method",  re.compile(r"(?:방법|공정|프로세스|복원방법)\s*\.?\s*$")),
    ("product", re.compile(r"(?:조성물|화합물|소재|재료|물품|제품)\s*\.?\s*$")),
    ("use",     re.compile(r"(?:용도|사용\s*방법)\s*\.?\s*$")),
]

# "것을 특징으로 하는" 고정 표현
CHARACTERIZING_EXPR_RE = re.compile(r"것을\s*특징으로\s*하는")

# 청구항 전문부 탐지: 첫 줄에 "~로서," 또는 "~으로서,"
PREAMBLE_RE = re.compile(r"^.{5,200}?(?:으?로서|에\s*있어서)\s*[,.]\s*$")

# 서브 불릿 / 구성요소 세미콜론 분리
SUB_BULLET_SPLIT_RE = re.compile(r"(?:[;；]\s*및?\s*\n?|\n\s*-\s*|\n\s*·\s*)")


def extract_claims_from_text(text: str) -> list[dict[str, Any]]:
    """청구항 섹션 MD 텍스트에서 개별 청구항 파싱."""

    lines = text.splitlines()
    claims: list[dict[str, Any]] = []
    current_num: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_num is None:
            return
        raw_body = "\n".join(current_lines).strip()
        claim = build_claim(current_num, raw_body)
        claims.append(claim)

    for line in lines:
        stripped = line.strip()
        m = CLAIM_HEADER_RE.match(stripped)
        if m:
            flush()
            current_num = int(m.group(1))
            current_lines = []
        elif current_num is not None:
            current_lines.append(line)

    flush()
    return claims


def build_claim(num: int, body: str) -> dict[str, Any]:
    """청구항 본문을 분석하여 구조화된 dict 반환."""

    body_clean = body.strip()
    dep_match = CLAIM_DEPENDENCY_RE.search(body_clean)
    dependent_of = int(dep_match.group(1)) if dep_match else None

    category = classify_category(body_clean)
    has_char_expr = bool(CHARACTERIZING_EXPR_RE.search(body_clean))

    # 첫 줄 기반 preamble 판정 (독립항에만 의미 있음)
    first_line = body_clean.splitlines()[0] if body_clean else ""
    has_preamble = bool(PREAMBLE_RE.match(first_line)) if dependent_of is None else False

    preamble_text = first_line if has_preamble else ""
    remainder = body_clean[len(first_line):].lstrip() if has_preamble else body_clean

    # 서브 불릿 분할 (구성요소별)
    sub_bullets = [
        s.strip().rstrip(".").rstrip(";")
        for s in SUB_BULLET_SPLIT_RE.split(remainder)
        if s.strip() and len(s.strip()) > 3
    ]

    return {
        "num": num,
        "dependent_of": dependent_of,
        "category": category,
        "length_chars": len(body_clean),
        "has_preamble": has_preamble,
        "uses_characterizing_expression": has_char_expr,
        "preamble_text": preamble_text,
        "body_text": remainder[:500],
        "sub_bullets": sub_bullets[:20],
        "text": body_clean[:1000],
    }


def classify_category(text: str) -> str:
    """청구항 카테고리 추정."""

    # 마지막 몇 줄만 검사 (카테고리 표현이 말미에 위치)
    tail = "\n".join(text.splitlines()[-5:]).strip()
    for name, pat in CATEGORY_PATTERNS:
        if pat.search(tail):
            return name
    return "unknown"


def build_dependency_tree(claims: list[dict[str, Any]]) -> dict[str, list[int]]:
    """독립항별 종속항 트리 구축."""

    tree: dict[str, list[int]] = {}
    for c in claims:
        if c["dependent_of"] is None:
            tree.setdefault(str(c["num"]), [])

    for c in claims:
        if c["dependent_of"] is not None:
            # 루트 독립항 찾기 (재귀 traverse)
            root = find_root_independent(c["num"], claims)
            if root is not None:
                tree.setdefault(str(root), []).append(c["num"])

    # 종속항 번호 정렬
    for k in tree:
        tree[k].sort()

    return tree


def find_root_independent(
    num: int, claims: list[dict[str, Any]], visited: set[int] | None = None
) -> int | None:
    """주어진 청구항 번호에서 출발하여 최상위 독립항 찾기."""

    if visited is None:
        visited = set()
    if num in visited:
        return None  # 순환 종속 방지
    visited.add(num)

    claim = next((c for c in claims if c["num"] == num), None)
    if claim is None:
        return None
    if claim["dependent_of"] is None:
        return claim["num"]
    return find_root_independent(claim["dependent_of"], claims, visited)


def compute_max_depth(claims: list[dict[str, Any]]) -> int:
    """종속 관계의 최대 깊이 계산."""

    max_d = 0
    for c in claims:
        depth = 0
        cur: int | None = c["num"]
        visited: set[int] = set()
        while cur is not None and cur not in visited:
            visited.add(cur)
            parent = next(
                (cc["dependent_of"] for cc in claims if cc["num"] == cur),
                None,
            )
            if parent is None:
                break
            depth += 1
            cur = parent
        max_d = max(max_d, depth)
    return max_d


def analyze_claims(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """청구항 배열 종합 분석."""

    independents = [c["num"] for c in claims if c["dependent_of"] is None]
    dependents = [c["num"] for c in claims if c["dependent_of"] is not None]

    category_counts: dict[str, int] = {}
    for c in claims:
        category_counts[c["category"]] = category_counts.get(c["category"], 0) + 1

    tree = build_dependency_tree(claims)
    max_depth = compute_max_depth(claims)

    return {
        "total_claims": len(claims),
        "independent_claims": sorted(independents),
        "dependent_claims": sorted(dependents),
        "claims": claims,
        "dependency_tree": tree,
        "summary": {
            "independent_count": len(independents),
            "dependent_count": len(dependents),
            "system_count": category_counts.get("system", 0),
            "method_count": category_counts.get("method", 0),
            "product_count": category_counts.get("product", 0),
            "use_count": category_counts.get("use", 0),
            "unknown_count": category_counts.get("unknown", 0),
            "max_depth": max_depth,
        },
    }


def load_claims_input(
    claims_md: Path | None, spec_json: Path | None
) -> tuple[str, str]:
    """입력 소스 결정: claims md 우선, 없으면 spec_structure.json의 claims 섹션."""

    if claims_md:
        return str(claims_md), claims_md.read_text(encoding="utf-8")

    if spec_json:
        data = json.loads(spec_json.read_text(encoding="utf-8"))
        claims_section = data.get("sections", {}).get("claims", {})
        text = claims_section.get("text", "")
        if not text:
            raise ValueError(
                f"spec_structure.json 에 claims 섹션이 없거나 비어 있음: {spec_json}"
            )
        return str(spec_json), text

    raise ValueError("--claims-md 또는 --spec 중 하나를 지정해야 합니다")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="한국 특허 청구항 구조·종속 관계 파서"
    )
    parser.add_argument("--claims-md", type=Path, help="청구항 섹션 MD 파일")
    parser.add_argument("--spec", type=Path, help="spec_structure.json 파일")
    parser.add_argument(
        "--output", "-o", type=Path, required=True, help="출력 JSON 파일"
    )
    args = parser.parse_args()

    try:
        source, text = load_claims_input(args.claims_md, args.spec)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    claims = extract_claims_from_text(text)
    result = analyze_claims(claims)
    result["source"] = source

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    s = result["summary"]
    print(
        f"[claim_parser] Parsed {source}\n"
        f"  total: {result['total_claims']}\n"
        f"  independent: {s['independent_count']} ({result['independent_claims']})\n"
        f"  dependent: {s['dependent_count']}\n"
        f"  by_category: sys={s['system_count']} method={s['method_count']} "
        f"prod={s['product_count']} use={s['use_count']} unknown={s['unknown_count']}\n"
        f"  max_depth: {s['max_depth']}\n"
        f"  → {args.output}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
