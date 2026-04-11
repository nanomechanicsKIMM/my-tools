#!/usr/bin/env python3
"""typo_scanner.py — 한국 특허 명세서 오탈자·부호·수식 스캐너

Patent-draft-review 스킬의 Phase 5(proofreader)에서 사용.
reference/korean-patent-typo-patterns.md 의 패턴 DB를 로드하여
MD 텍스트를 스캔하고 proofread.json 을 생성한다.

=== 사용법 ===

    python typo_scanner.py <input.md> <output.json> [--patterns <path>]

=== 출력 스키마 ===

    {
      "source": "<input.md path>",
      "total_lines": N,
      "scanned_at": "<ISO timestamp>",
      "findings": [
        {
          "line": L,
          "pattern_id": "T-EN-001",
          "category": "english_typo",
          "severity": "critical",
          "current": "matched text",
          "suggested": "position-dependent",
          "needs_llm_review": false
        },
        ...
      ],
      "reference_number_analysis": {
        "duplicates": [{"number": "121", "assignments": ["두개골 표면", "공액면"], "locations": [...]}],
        "missing_from_legend": [{"number": "200", "body_name": "초음파 프로브", "locations": [...]}]
      },
      "term_mix_analysis": [
        {"pattern_id": "V-MIX-001", "terms": {"conjugate surface": 3, "conjugate plane": 2}}
      ],
      "summary": {
        "total_findings": N,
        "by_severity": {"critical": N, "warning": N, "info": N},
        "by_category": {"english_typo": N, ...}
      }
    }

=== 재사용 자산 ===

  패턴 DB: reference/korean-patent-typo-patterns.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_PATTERN_DB = (
    Path(__file__).resolve().parent.parent
    / "reference"
    / "korean-patent-typo-patterns.md"
)

# ---------------------------------------------------------------------------
# Fallback 내장 패턴 (reference DB 로드 실패 시 최소 동작 보장)
# ---------------------------------------------------------------------------
FALLBACK_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "T-EN-001",
        "regex": r"\bposition-dependetn\b",
        "severity": "critical",
        "category": "english_typo",
        "fix": "position-dependent",
    },
    {
        "id": "T-EN-002",
        "regex": r"\bindepdent(ly)?\b",
        "severity": "critical",
        "category": "english_typo",
        "fix": "independent",
    },
    {
        "id": "T-KO-001",
        "regex": r"두\s+개골",
        "severity": "warning",
        "category": "korean_spacing",
        "fix": "두개골",
    },
    {
        "id": "T-KO-003",
        "regex": r"공액\s+면",
        "severity": "warning",
        "category": "korean_spacing",
        "fix": "공액면",
    },
    {
        "id": "F-BRK-001",
        "regex": r"\s{3,}[가-힣A-Za-z]",
        "severity": "warning",
        "category": "formula_broken",
        "needs_llm_review": True,
    },
    {
        "id": "D-DOC-001",
        "regex": r"대한민국\s*(공개|등록)?\s*특허\s*제\s*10-\d{4}-\d{7}(?!\s*호)",
        "severity": "critical",
        "category": "patent_doc_format",
        "fix": "(끝에 '호' 추가)",
    },
]

TERM_MIX_PAIRS: list[tuple[str, list[str]]] = [
    ("V-MIX-001", ["conjugate surface", "conjugate plane"]),
    ("V-MIX-002", [r"송신기저", r"송신\s기저"]),
    ("V-MIX-003", [r"수신기저", r"수신\s기저"]),
]

# 본문에서 (구성요소명)(부호) 형식을 추출 (예: "초음파 프로브(200)")
# P1 개선 (Architect review M2 피드백): 공백 제외하여 관형어/조사 혼입 방지
# 예: "상기 초음파 프로브(200)" → "프로브"만 매칭 (직전 한글 명사 1개)
BODY_REF_RE = re.compile(r"([가-힣]{2,15}|[A-Za-z][A-Za-z_]{1,20})\s*\((\d{2,4})\)")
# 선행 stopword — 구성요소명이 아닌 관형어/조사
REF_STOPWORDS = frozenset({
    "상기", "본", "해당", "그", "이", "저", "및", "또는", "와", "과",
    "의", "을", "를", "에", "로", "으로", "는", "은", "가",
    "도", "만", "하고", "되어", "하여", "인한", "위한", "일부",
    "실시", "상세", "이상", "이하", "이전", "이후",
})
# 부호의 설명 섹션의 한 줄 (예: "100 : 대상체")
LEGEND_LINE_RE = re.compile(r"^\s*(\d{2,4})\s*[:：]\s*(.+?)\s*$")


def load_patterns(db_path: Path) -> list[dict[str, Any]]:
    """reference/korean-patent-typo-patterns.md 의 `patterns:` YAML 블록을 파싱.

    파싱 실패 시 FALLBACK_PATTERNS 반환.
    """

    if not db_path.is_file():
        print(f"[typo_scanner] DB not found, using fallback: {db_path}", file=sys.stderr)
        return FALLBACK_PATTERNS

    text = db_path.read_text(encoding="utf-8")

    # ```yaml\npatterns: ... ``` 블록만 추출
    yaml_block_re = re.compile(
        r"```yaml\s*\npatterns:\s*\n(.*?)```",
        re.DOTALL,
    )
    match = yaml_block_re.search(text)
    if not match:
        print(
            "[typo_scanner] `patterns:` YAML block not found, using fallback",
            file=sys.stderr,
        )
        return FALLBACK_PATTERNS

    yaml_body = match.group(1)

    # 간단 YAML 파서 (PyYAML 미의존)
    patterns: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw in yaml_body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- id:"):
            if current:
                patterns.append(current)
            current = {"id": line.split("- id:", 1)[1].strip()}
            continue
        if current is not None and ":" in line:
            key, _, value = line.strip().partition(":")
            key = key.strip()
            value = value.strip()
            # 작은따옴표 제거
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if value.lower() in {"true", "false"}:
                current[key] = value.lower() == "true"
            else:
                current[key] = value

    if current:
        patterns.append(current)

    # regex 필드만 있는 항목만 반환 (알고리즘 기반은 별도 처리)
    regex_patterns = [p for p in patterns if p.get("regex")]

    if not regex_patterns:
        print(
            "[typo_scanner] No regex patterns parsed, using fallback",
            file=sys.stderr,
        )
        return FALLBACK_PATTERNS

    return regex_patterns


def scan_regex_patterns(
    md_text: str, patterns: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """정규식 기반 패턴 스캔."""

    findings: list[dict[str, Any]] = []
    lines = md_text.splitlines()

    for pat in patterns:
        try:
            regex = re.compile(pat["regex"])
        except re.error as exc:
            print(
                f"[typo_scanner] invalid regex in {pat.get('id')}: {exc}",
                file=sys.stderr,
            )
            continue

        for line_no, line in enumerate(lines, start=1):
            for m in regex.finditer(line):
                findings.append({
                    "line": line_no,
                    "pattern_id": pat.get("id", "UNKNOWN"),
                    "category": pat.get("category", "unknown"),
                    "severity": pat.get("severity", "info"),
                    "current": m.group(0),
                    "suggested": pat.get("fix", ""),
                    "needs_llm_review": bool(pat.get("needs_llm_review", False)),
                })

    return findings


def analyze_reference_numbers(
    md_text: str, legend_text: str
) -> dict[str, Any]:
    """부호 중복 + 부호의 설명 누락 분석."""

    lines = md_text.splitlines()
    body_assignments: dict[str, dict[str, list[int]]] = {}

    for line_no, line in enumerate(lines, start=1):
        for m in BODY_REF_RE.finditer(line):
            name = m.group(1).strip()
            number = m.group(2)
            # P1 개선: stopword 필터
            if not name or not number or name in REF_STOPWORDS:
                continue
            entry = body_assignments.setdefault(number, {})
            entry.setdefault(name, []).append(line_no)

    # 부호의 설명 파싱
    legend: dict[str, str] = {}
    for line in legend_text.splitlines():
        m = LEGEND_LINE_RE.match(line.strip())
        if m:
            legend[m.group(1)] = m.group(2).strip()

    # R-DUP-001: 같은 부호가 2개 이상의 구성요소에 부여
    duplicates = []
    for number, assignments in body_assignments.items():
        if len(assignments) > 1:
            duplicates.append({
                "pattern_id": "R-DUP-001",
                "severity": "critical",
                "number": number,
                "assignments": list(assignments.keys()),
                "locations": sorted(
                    {ln for locs in assignments.values() for ln in locs}
                )[:10],
            })

    # R-MISS-001: 본문에 있으나 부호의 설명에 없는 부호
    missing = []
    for number, assignments in body_assignments.items():
        if number not in legend:
            names = list(assignments.keys())
            missing.append({
                "pattern_id": "R-MISS-001",
                "severity": "critical",
                "number": number,
                "body_name": names[0] if names else "",
                "locations": sorted(
                    {ln for locs in assignments.values() for ln in locs}
                )[:5],
            })

    return {
        "duplicates": duplicates,
        "missing_from_legend": missing,
    }


def analyze_term_mix(md_text: str) -> list[dict[str, Any]]:
    """용어 혼용 탐지 (V-MIX-*)."""

    results = []
    for pattern_id, terms in TERM_MIX_PAIRS:
        counts: dict[str, int] = {}
        for term in terms:
            try:
                matches = re.findall(term, md_text)
            except re.error:
                continue
            if matches:
                counts[term] = len(matches)

        # 두 가지 이상이 공존하면 혼용 플래그
        if len(counts) >= 2:
            results.append({
                "pattern_id": pattern_id,
                "severity": "warning",
                "terms": counts,
                "suggestion": f"전역 통일 필요: {' ↔ '.join(counts.keys())}",
            })

    return results


def compute_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info")
        cat = f.get("category", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total_findings": len(findings),
        "by_severity": by_severity,
        "by_category": by_category,
    }


def split_body_and_legend(md_text: str) -> tuple[str, str]:
    """본문과 '부호의 설명' 섹션을 분리.

    부호의 설명 섹션 헤더가 없으면 전체를 본문으로 간주하고 legend는 빈 문자열.
    """

    legend_header_re = re.compile(r"^(##\s*)?부호의\s*설명\s*$", re.MULTILINE)
    match = legend_header_re.search(md_text)
    if not match:
        return md_text, ""

    body = md_text[: match.start()]
    legend = md_text[match.end():]
    return body, legend


def main() -> int:
    parser = argparse.ArgumentParser(
        description="한국 특허 명세서 오탈자·부호 스캐너"
    )
    parser.add_argument("input", help="입력 MD 파일 경로")
    parser.add_argument("output", help="출력 JSON 파일 경로")
    parser.add_argument(
        "--patterns",
        default=str(DEFAULT_PATTERN_DB),
        help="패턴 DB 경로 (기본: reference/korean-patent-typo-patterns.md)",
    )
    args = parser.parse_args()

    src = Path(args.input).resolve()
    out = Path(args.output).resolve()
    db = Path(args.patterns).resolve()

    if not src.is_file():
        print(f"Error: input file not found: {src}", file=sys.stderr)
        return 1

    md_text = src.read_text(encoding="utf-8")
    total_lines = len(md_text.splitlines())

    patterns = load_patterns(db)
    findings = scan_regex_patterns(md_text, patterns)

    body, legend = split_body_and_legend(md_text)
    ref_analysis = analyze_reference_numbers(body, legend)
    term_mix = analyze_term_mix(md_text)

    out.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "source": str(src),
        "total_lines": total_lines,
        "scanned_at": dt.datetime.now().isoformat(timespec="seconds"),
        "patterns_loaded": len(patterns),
        "findings": findings,
        "reference_number_analysis": ref_analysis,
        "term_mix_analysis": term_mix,
        "summary": compute_summary(findings),
    }

    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = result["summary"]
    print(
        f"[typo_scanner] Scanned {src}\n"
        f"  patterns: {len(patterns)}\n"
        f"  findings: {summary['total_findings']}\n"
        f"  by_severity: {summary['by_severity']}\n"
        f"  reference duplicates: {len(ref_analysis['duplicates'])}\n"
        f"  missing from legend: {len(ref_analysis['missing_from_legend'])}\n"
        f"  term mix warnings: {len(term_mix)}\n"
        f"  → {out}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
