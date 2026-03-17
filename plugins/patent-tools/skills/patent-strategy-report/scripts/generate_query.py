#!/usr/bin/env python3
"""
Generate a Google Patents search query and URL from an RFP markdown file.
To keep result count manageable (e.g. under 5000), uses AND between required concept groups
and/or user-provided core keywords (필수 단어).

Usage:
  python generate_query.py [path_or_.] [technology_domain] [--years 10]
  python generate_query.py . 디스플레이 --years 12   # 사용자 지정 기간(12년) 우선
  python generate_query.py . 디스플레이 --required-terms "stretchable,sensor,display"
  python generate_query.py . 디스플레이 --exclude-terms "rigid substrate,drug"   # 필수 제외 단어
  python generate_query.py . 디스플레이 --exclude-terms "OLED,LCD"   # 센서 융합 디스플레이 RFP 시 OLED·LCD 제외 권장
  python generate_query.py . 디스플레이 --ask-required   # prompt for core keywords
  python generate_query.py . 디스플레이 --ask-exclude    # prompt for exclude terms (빼야 할 단어)
"""
import argparse
import re
import sys
from urllib.parse import quote_plus

import datetime
END_YEAR = datetime.datetime.now().year
DEFAULT_YEARS = 10  # 검색 기간 기본값(최근 N년). 사용자가 --years N 을 주면 그 값이 우선.
MAX_TERMS_PER_GROUP = 10  # cap per AND group to avoid huge queries

# Domain synonyms (subset; full table in reference.md)
DOMAIN_SYNONYMS = {
    "디스플레이": [
        "display", "panel", "screen", "OLED", "LED", "flexible", "stretchable",
        "foldable", "rollable", "backplane", "TFT", "pixel", "substrate"
    ],
    "반도체": ["semiconductor", "wafer", "transistor", "CMOS", "process", "lithography"],
    "배터리": ["battery", "cell", "electrode", "electrolyte", "lithium", "solid-state"],
    "센서": ["sensor", "sensing", "strain", "deformation", "touch", "embedded", "detection", "transformable"],
}

# 필수 개념 그룹: 검색 건수 축소를 위해 AND로 묶을 때 사용 (그룹별 최소 1개 필수)
CONCEPT_GROUP_DISPLAY = [
    "display", "panel", "screen", "OLED", "LED", "flexible", "stretchable",
    "foldable", "rollable", "backplane", "TFT", "pixel"
]
CONCEPT_GROUP_SENSOR_DEFORM = [
    "sensor", "sensing", "deformation", "transformable", "strain", "touch",
    "detection", "deformable", "stretchable"
]
CONCEPT_GROUP_UI = [
    "user", "interface", "experience", "UX", "interaction"
]


def read_rfp(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_keywords_eng(text: str) -> list:
    """Find 영문: or English keyword list."""
    for pattern in [
        r"영문\s*[:\s]+([^\n#\-]+)",
        r"영문:\s*([^\n]+)",
        r"\*\*영문\*\*[:\s]*([^\n]+)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            return [t.strip() for t in re.split(r"[,،\s]+", raw) if t.strip()]
    return []


def extract_rfp_name(text: str) -> str:
    m = re.search(r"RFP명\s*\n?\s*([^\n#|]+)", text)
    if not m:
        m = re.search(r"\*\*RFP명\*\*[^\n]*\n?\s*([^\n#|]+)", text)
    return m.group(1).strip() if m else ""


def _normalize_term(t: str) -> str:
    return t.strip().lower() if t else ""


def extract_concept_groups(rfp_text: str, technology_domain: str | None) -> list:
    """
    RFP와 도메인에서 필수 개념 그룹을 추출. 각 그룹은 AND로 연결해 검색 건수 축소(목표 5000건 이하).
    반환: [ [그룹1_용어들], [그룹2_용어들], ... ]
    """
    rfp_lower = (rfp_text or "").lower()
    rfp_name = extract_rfp_name(rfp_text).lower()
    kw_eng = [t.lower() for t in extract_keywords_eng(rfp_text)]
    combined = " ".join([rfp_lower, rfp_name] + kw_eng)
    groups = []

    if "디스플레이" in rfp_text or "display" in combined or (technology_domain and "디스플레이" in (technology_domain or "")):
        groups.append(list(CONCEPT_GROUP_DISPLAY)[:MAX_TERMS_PER_GROUP])

    if (
        "센서" in rfp_text or "변형" in rfp_text or "형태" in rfp_text
        or any(x in combined for x in ("sensor", "sensing", "deformation", "transformable", "strain"))
        or (technology_domain and "센서" in (technology_domain or ""))
    ):
        existing = set(groups[0]) if groups else set()
        g = [t for t in CONCEPT_GROUP_SENSOR_DEFORM if t not in existing][:MAX_TERMS_PER_GROUP]
        if g:
            groups.append(g)

    if not groups and technology_domain and technology_domain.strip() in DOMAIN_SYNONYMS:
        groups.append(DOMAIN_SYNONYMS[technology_domain.strip()][:MAX_TERMS_PER_GROUP])

    # RFP 영문 키워드 보강: 그룹2에 없는 것만 그룹1 앞에 추가해 그룹1이 지나치게 넓어지지 않게 함
    group2_set = set(groups[1]) if len(groups) > 1 else set()
    for w in kw_eng:
        w = _normalize_term(w)
        if not w or len(w) < 2 or w in group2_set:
            continue
        if groups and w not in groups[0]:
            groups[0].insert(0, w)
            groups[0][:] = groups[0][:MAX_TERMS_PER_GROUP]
    return groups


def build_query(
    rfp_text: str,
    technology_domain: str | None = None,
    after: str | None = None,
    before: str | None = None,
    exclude_phrases: list = None,
    use_and_groups: bool = True,
    required_terms: list | None = None,
    required_terms_all: bool = False,
) -> tuple:
    """
    Build Google Patents query string and full URL.
    use_and_groups=True: 필수 개념 그룹을 AND로 묶어 검색 건수 축소.
    required_terms: 사용자 제공 핵심 키워드. required_terms_all=False면 (term1 OR term2), True면 (term1 AND term2).
    Returns (query_string, search_url).
    """
    if after is None:
        after = f"priority:{END_YEAR - DEFAULT_YEARS}0101"
    if before is None:
        before = f"priority:{END_YEAR}1231"
    if exclude_phrases is None:
        exclude_phrases = []
    if required_terms is None:
        required_terms = []
    kw_eng = extract_keywords_eng(rfp_text)
    rfp_name = extract_rfp_name(rfp_text)

    # 사용자 제공 필수 단어 블록: 가장 먼저 AND로 붙여 검색 건수 축소
    user_required_block = None
    if required_terms:
        terms = [t.strip() for t in required_terms if t and t.strip()]
        if terms:
            terms = [f'"{t}"' if " " in t else t for t in terms[:MAX_TERMS_PER_GROUP]]
            if required_terms_all:
                user_required_block = "(" + " AND ".join(terms) + ")"  # 모두 필수
            else:
                user_required_block = "(" + " OR ".join(terms) + ")"  # 하나 이상 필수

    if use_and_groups:
        concept_groups = extract_concept_groups(rfp_text, technology_domain)
        if len(concept_groups) >= 2:
            blocks = []
            for g in concept_groups:
                terms = [f'"{t}"' if " " in t else t for t in g[:MAX_TERMS_PER_GROUP] if t]
                if terms:
                    blocks.append("(" + " OR ".join(terms) + ")")
            if blocks:
                core_block = " AND ".join(blocks)
                query_parts = [core_block]
            else:
                use_and_groups = False
        else:
            use_and_groups = False

    if not use_and_groups:
        core_terms = list(kw_eng) if kw_eng else []
        if technology_domain and technology_domain.strip() in DOMAIN_SYNONYMS:
            for t in DOMAIN_SYNONYMS[technology_domain.strip()]:
                if t not in core_terms:
                    core_terms.append(t)
        if not core_terms and rfp_name:
            words = re.findall(r"[a-zA-Z가-힣0-9]+", rfp_name)[:5]
            core_terms = words if words else ["patent"]
        core_block = " OR ".join(f'"{t}"' if " " in t else t for t in core_terms[:15])
        if len(core_terms) > 15:
            core_block = "(" + core_block + " OR " + " OR ".join(core_terms[15:20]) + ")"
        else:
            core_block = "(" + core_block + ")"
        query_parts = [core_block]
    if exclude_phrases:
        not_part = " NOT (" + " OR ".join(f'"{p}"' for p in exclude_phrases) + ")"
        query_parts.append(not_part)

    # 사용자 제공 필수 단어가 있으면 맨 앞에 AND 블록으로 추가
    if user_required_block:
        query_parts = [user_required_block] + query_parts
        query_string = " AND ".join(query_parts)
    else:
        query_string = " ".join(query_parts)

    base = "https://patents.google.com/?"
    params = ["q=" + quote_plus(query_string)]
    if after:
        a = after if after.startswith("priority:") else "priority:" + after
        params.append("after=" + a)
    if before:
        b = before if before.startswith("priority:") else "priority:" + before
        params.append("before=" + b)
    search_url = base + "&".join(params)

    return query_string, search_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rfp_path", nargs="?", default=".", help="Path to RFP markdown file, or '.' to use RFP in current directory")
    parser.add_argument("technology_domain", nargs="?", default=None, help="e.g. 디스플레이, 반도체")
    parser.add_argument("--years", "-y", type=int, default=DEFAULT_YEARS, help="Years back from current year for search (default 10). User-specified value overrides default. Report analyzes all years present in the CSV.")
    parser.add_argument("--no-and-groups", action="store_true", help="Use single OR block only (legacy; may yield 100k+ results)")
    parser.add_argument("--required-terms", "-r", type=str, default=None, help="Comma-separated core keywords (필수 단어); one or more must appear (OR within block)")
    parser.add_argument("--required-all", action="store_true", help="With -r: all listed terms must appear (AND). e.g. -r stretchable,display --required-all")
    parser.add_argument("--ask-required", action="store_true", help="Prompt for core keywords (핵심 키워드) interactively")
    parser.add_argument("--exclude-terms", "-e", type=str, default=None, help="Comma-separated terms to exclude (필수 제외 단어). Added as NOT (term1 OR term2 OR ...). Phrases with spaces use quotes in query.")
    parser.add_argument("--ask-exclude", action="store_true", help="Prompt for exclude terms (빼야 할 단어, 쉼표 구분) interactively")
    args = parser.parse_args()

    required_terms = []
    if args.required_terms:
        required_terms = [t.strip() for t in args.required_terms.split(",") if t.strip()]
    elif args.ask_required:
        try:
            prompt = "핵심 키워드(필수 단어, 쉼표 구분): "
            line = input(prompt).strip()
            required_terms = [t.strip() for t in line.split(",") if t.strip()]
        except EOFError:
            pass

    exclude_phrases = []
    if getattr(args, "exclude_terms", None):
        exclude_phrases = [t.strip() for t in args.exclude_terms.split(",") if t.strip()]
    elif getattr(args, "ask_exclude", False):
        try:
            prompt = "빼야 할 단어(제외 단어, 쉼표 구분): "
            line = input(prompt).strip()
            exclude_phrases = [t.strip() for t in line.split(",") if t.strip()]
        except EOFError:
            pass

    rfp_path = args.rfp_path or "."
    if rfp_path in (".", "current"):
        import os
        from pathlib import Path
        cwd = Path(os.getcwd())
        candidates = list(cwd.glob("*RFP*.md"))
        if not candidates:
            print("ERROR: No *RFP*.md file found in current directory:", cwd, file=sys.stderr)
            sys.exit(1)
        rfp_path = str(candidates[0])
        print("Using RFP:", rfp_path, "\n")

    start_year = END_YEAR - args.years
    after = f"priority:{start_year}0101"
    before = f"priority:{END_YEAR}1231"

    rfp_text = read_rfp(rfp_path)
    query_string, search_url = build_query(
        rfp_text,
        technology_domain=args.technology_domain,
        after=after,
        before=before,
        exclude_phrases=exclude_phrases if exclude_phrases else None,
        use_and_groups=not args.no_and_groups,
        required_terms=required_terms if required_terms else None,
        required_terms_all=getattr(args, "required_all", False),
    )

    if required_terms:
        mode = " (모두 필수 AND)" if getattr(args, "required_all", False) else " (하나 이상 필수 OR)"
        print("REQUIRED_TERMS (필수 단어):", ", ".join(required_terms), mode, "\n")
    if exclude_phrases:
        print("EXCLUDE_TERMS (필수 제외 단어):", ", ".join(exclude_phrases), "\n")
    print("QUERY_STRING:")
    print(query_string)
    print()
    print("SEARCH_URL:")
    print(search_url)
    print()
    print("DATE_RANGE:", f"priority {start_year}.01.01 - {END_YEAR}.12.31")


if __name__ == "__main__":
    main()
