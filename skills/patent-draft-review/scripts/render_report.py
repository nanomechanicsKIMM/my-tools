#!/usr/bin/env python3
"""render_report.py — Handlebars-lite 템플릿 렌더링 엔진

Patent-draft-review 스킬의 Phase 7(report-writer)에서 사용.
improvement-plan-v1.md 또는 v2-delta.md 등의 템플릿과 Phase 1~5 JSON 출력을
결합하여 최종 개선방안 MD 파일을 생성한다.

=== 지원 문법 ===

  {{variable}}                    단순 치환
  {{variable.nested.path}}        dotted path 접근
  {{#each array}}...{{/each}}     배열 반복 (현재 item은 내부 context)
  {{#if condition}}...{{/if}}     조건부
  {{#if cond}}A{{else}}B{{/if}}   else 분기
  {{@index}} / {{index}}          현재 loop index (0-based)
  {{this}}                        현재 loop item (primitive)

  - 중첩 지원: each 내부 if, if 내부 each 등
  - HTML 주석 영역 중 TEMPLATE 포함 블록은 렌더링 전 제거
  - 누락된 경로는 빈 문자열 (Handlebars 기본 동작)
  - 외부 의존성 없음 (Python 표준 라이브러리만)

=== 사용법 ===

    python render_report.py \\
        --template <template.md> \\
        --data spec=spec_structure.json \\
        --data triz=triz_diagnosis.json \\
        --data claim=claim_analysis.json \\
        --data proofread=proofread.json \\
        --output <final.md>

=== 데이터 병합 규칙 ===

  --data key=path 로 지정된 각 JSON 파일의 내용은 context dict 에
  `{key: <json_content>}` 형태로 병합된다. 템플릿에서는
  {{spec.invention_title}}, {{triz.technical_contradictions}} 형식으로 접근.

=== 제한 사항 ===

  - {{{raw}}} 삼중 괄호 escape 미지원 (Markdown 은 기본 safe)
  - {{!-- comment --}} Handlebars 주석 미지원 (HTML 주석 사용)
  - Helper 함수 미지원 (lookup, unless, with 등)
  - 상위 scope 접근 {{../field}} 미지원
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------
# 템플릿 주석 블록 제거 (렌더링 전)
TEMPLATE_COMMENT_RE = re.compile(
    r"<!--[^-]*?TEMPLATE.*?-->|<!-- END OF[^>]*-->",
    re.DOTALL,
)

# Handlebars 태그 탐지
TAG_START_RE = re.compile(r"\{\{(?!\{)")


def strip_template_comments(template: str) -> str:
    """템플릿 가이드 주석(<!-- TEMPLATE ... -->) 제거."""

    return TEMPLATE_COMMENT_RE.sub("", template)


def tokenize(template: str) -> list[tuple[str, Any]]:
    """템플릿을 (type, value) 토큰 리스트로 분해.

    Types: text, var, each_start, each_end, if_start, if_end, else
    """

    tokens: list[tuple[str, Any]] = []
    pos = 0
    length = len(template)

    while pos < length:
        tag_match = TAG_START_RE.search(template, pos)
        if tag_match is None:
            tokens.append(("text", template[pos:]))
            break

        tag_start = tag_match.start()
        if tag_start > pos:
            tokens.append(("text", template[pos:tag_start]))

        end_idx = template.find("}}", tag_start + 2)
        if end_idx == -1:
            # 닫히지 않은 태그 — 원본 유지
            tokens.append(("text", template[pos:]))
            break

        inner = template[tag_start + 2:end_idx].strip()
        pos = end_idx + 2

        if inner.startswith("#each "):
            tokens.append(("each_start", inner[6:].strip()))
        elif inner.startswith("#if "):
            tokens.append(("if_start", inner[4:].strip()))
        elif inner == "/each":
            tokens.append(("each_end", None))
        elif inner == "/if":
            tokens.append(("if_end", None))
        elif inner == "else":
            tokens.append(("else", None))
        elif inner == "":
            continue
        else:
            tokens.append(("var", inner))

    return tokens


# ---------------------------------------------------------------------------
# AST parser (recursive descent)
# ---------------------------------------------------------------------------

Node = dict[str, Any]


def parse(
    tokens: list[tuple[str, Any]], start: int, end: int
) -> tuple[list[Node], int]:
    """토큰 범위를 AST 노드 리스트로 파싱.

    Returns (nodes, next_index).
    """

    nodes: list[Node] = []
    i = start

    while i < end:
        ttype, tvalue = tokens[i]

        if ttype == "text":
            nodes.append({"type": "text", "value": tvalue})
            i += 1
        elif ttype == "var":
            nodes.append({"type": "var", "path": tvalue})
            i += 1
        elif ttype == "each_start":
            path = tvalue
            body, next_i = parse_until(tokens, i + 1, end, block="each")
            nodes.append({"type": "each", "path": path, "body": body})
            i = next_i
        elif ttype == "if_start":
            path = tvalue
            then_body, else_body, next_i = parse_if(tokens, i + 1, end)
            nodes.append({
                "type": "if",
                "path": path,
                "then": then_body,
                "else": else_body,
            })
            i = next_i
        elif ttype in {"each_end", "if_end", "else"}:
            # 블록 바디 호출자가 처리
            return nodes, i
        else:
            i += 1

    return nodes, i


def parse_until(
    tokens: list[tuple[str, Any]], start: int, end: int, block: str
) -> tuple[list[Node], int]:
    """`block` 종료 태그까지 파싱 후 (body, next_i) 반환."""

    end_type = f"{block}_end"
    body, i = parse(tokens, start, end)

    if i >= end or tokens[i][0] != end_type:
        raise ValueError(
            f"Unmatched {block}_start at token {start}: expected {end_type}"
        )
    return body, i + 1


def parse_if(
    tokens: list[tuple[str, Any]], start: int, end: int
) -> tuple[list[Node], list[Node], int]:
    """if 블록의 then/else 바디 파싱."""

    then_body, i = parse(tokens, start, end)

    if i >= end:
        raise ValueError(f"Unmatched if_start at token {start}")

    ttype = tokens[i][0]
    if ttype == "if_end":
        return then_body, [], i + 1

    if ttype == "else":
        else_body, j = parse(tokens, i + 1, end)
        if j >= end or tokens[j][0] != "if_end":
            raise ValueError(f"Unmatched else at token {i}")
        return then_body, else_body, j + 1

    raise ValueError(f"Unexpected token {ttype} at {i} inside if block")


# ---------------------------------------------------------------------------
# Path resolver
# ---------------------------------------------------------------------------


def resolve_path(context: dict[str, Any], path: str) -> Any:
    """Dotted path 를 context 에서 해결."""

    path = path.strip()
    if not path:
        return ""

    # Special refs
    if path in {"@index", "index", "this"}:
        return context.get(path, "")

    parts = path.split(".")
    current: Any = context
    for part in parts:
        part = part.strip()
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return ""
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return ""
        else:
            return ""

    return current if current is not None else ""


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render_ast(nodes: list[Node], context: dict[str, Any]) -> str:
    """AST 노드 리스트를 렌더링하여 문자열 반환."""

    out: list[str] = []

    for node in nodes:
        ntype = node["type"]

        if ntype == "text":
            out.append(str(node["value"]))

        elif ntype == "var":
            value = resolve_path(context, node["path"])
            out.append(_stringify(value))

        elif ntype == "each":
            arr = resolve_path(context, node["path"])
            if isinstance(arr, list):
                for idx, item in enumerate(arr):
                    child_ctx = dict(context)
                    if isinstance(item, dict):
                        child_ctx.update(item)
                    child_ctx["this"] = item
                    child_ctx["index"] = idx
                    child_ctx["@index"] = idx
                    out.append(render_ast(node["body"], child_ctx))

        elif ntype == "if":
            value = resolve_path(context, node["path"])
            branch = node["then"] if _truthy(value) else node["else"]
            out.append(render_ast(branch, context))

    return "".join(out)


def _stringify(value: Any) -> str:
    """값을 문자열로 변환. 리스트/dict 는 빈 문자열."""

    if value is None or value == "" or value == []:
        return ""
    if isinstance(value, (list, dict)):
        return ""
    return str(value)


def _truthy(value: Any) -> bool:
    """Handlebars truthy 기준."""

    if value is None or value == "" or value == 0 or value is False:
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(template: str, context: dict[str, Any]) -> str:
    """템플릿 + context → 렌더링된 문자열."""

    cleaned = strip_template_comments(template)
    tokens = tokenize(cleaned)
    ast, _ = parse(tokens, 0, len(tokens))
    return render_ast(ast, context)


def load_data_files(data_specs: list[str]) -> dict[str, Any]:
    """--data key=path 인자 리스트를 병합 context dict 로 변환."""

    context: dict[str, Any] = {}

    for spec in data_specs:
        if "=" not in spec:
            raise ValueError(
                f"--data 인자는 key=path 형식이어야 합니다: {spec}"
            )
        key, path_str = spec.split("=", 1)
        key = key.strip()
        path = Path(path_str.strip())

        if not path.is_file():
            print(
                f"[render_report] Warning: data file not found: {path}",
                file=sys.stderr,
            )
            context[key] = {}
            continue

        try:
            context[key] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"[render_report] Warning: invalid JSON in {path}: {exc}",
                file=sys.stderr,
            )
            context[key] = {}

    return context


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Handlebars-lite 템플릿 렌더링 엔진"
    )
    parser.add_argument(
        "--template",
        required=True,
        type=Path,
        help="입력 템플릿 MD 파일",
    )
    parser.add_argument(
        "--data",
        action="append",
        default=[],
        help="key=path 형식의 JSON 데이터 파일 (여러 개 가능)",
    )
    parser.add_argument(
        "--context",
        type=Path,
        help="단일 JSON 파일을 root context 로 로드 (flat 접근 지원)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="출력 MD 파일",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="누락된 필드를 경고로 출력",
    )
    args = parser.parse_args()

    if not args.template.is_file():
        print(f"Error: template not found: {args.template}", file=sys.stderr)
        return 1

    template = args.template.read_text(encoding="utf-8")

    # --context 로드 (flat root)
    context: dict[str, Any] = {}
    if args.context:
        if not args.context.is_file():
            print(f"Error: context file not found: {args.context}", file=sys.stderr)
            return 1
        try:
            context = json.loads(args.context.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON in {args.context}: {exc}", file=sys.stderr)
            return 1

    # --data 병합 (prefixed access)
    if args.data:
        data_ctx = load_data_files(args.data)
        context.update(data_ctx)

    try:
        rendered = render(template, context)
    except ValueError as exc:
        print(f"[render_report] Parse error: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    # 잔존 Handlebars 태그 감지 (경고)
    residual = re.findall(r"\{\{[^{}]+?\}\}", rendered)
    residual_unique = sorted(set(residual))

    print(
        f"[render_report] Rendered {args.template.name} "
        f"→ {args.output.name}\n"
        f"  data_keys: {list(context.keys())}\n"
        f"  output_lines: {len(rendered.splitlines())}\n"
        f"  output_chars: {len(rendered)}\n"
        f"  residual_tags: {len(residual_unique)} "
        f"{'(' + ', '.join(residual_unique[:5]) + '...)' if residual_unique else ''}",
        file=sys.stderr,
    )

    if args.strict and residual_unique:
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
