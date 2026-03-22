#!/usr/bin/env python3
"""
Aggregate a Google Patents CSV and produce structured data for the patent strategy report.
Outputs: JSON (for template filling) and optional partial Markdown (tables + ASCII charts).

**분석 기간**: CSV에 포함된 모든 행을 사용하며, 연도별 집계는 우선일/공개일 기준으로
CSV 내 실제 존재하는 연도 전부를 반영한다. 검색 시 입력한 기간(예: 15년)과 일치하려면
검색식 생성 시 generate_query.py --years 15 로 URL을 만들고, 해당 URL로 다운로드한
CSV를 사용하면 된다.

Usage: python aggregate_csv_report.py <csv_path> [--output-dir DIR] [--report-title "Title"] [--rfp-path RFP.md]
"""
import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


def load_csv(path: str) -> tuple[list[dict], list[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    # Google Patents export sometimes has "search URL:,..." on line 1; real header is line 2
    start = 0
    if lines and lines[0].strip().lower().startswith("search url"):
        start = 1
    if start >= len(lines):
        return [], []
    header = next(csv.reader([lines[start]]))
    rows = list(csv.DictReader(lines[start + 1 :], fieldnames=header))
    return rows, header


def parse_year(date_val: str) -> int | None:
    if not date_val:
        return None
    s = str(date_val).strip()
    # YYYY-MM-DD or YYYY/MM/DD or YYYY
    m = re.match(r"(\d{4})", s)
    if not m:
        return None
    year = int(m.group(1))
    return year if 1900 <= year <= 2100 else None


def col_find(row: dict, *candidates: str) -> str:
    for c in candidates:
        if c in row and row[c]:
            return str(row[c]).strip()
    return ""


def aggregate_by_year(rows: list[dict], *col_candidates: str) -> dict[int, int]:
    by_year = Counter()
    for row in rows:
        y = parse_year(col_find(row, *col_candidates))
        if y:
            by_year[y] += 1
    return dict(sorted(by_year.items()))


def aggregate_by_priority_year(rows: list[dict]) -> dict[int, int]:
    return aggregate_by_year(rows, "priority date", "Priority Date", "priority_date", "filing_date")


def aggregate_by_publication_year(rows: list[dict]) -> dict[int, int]:
    return aggregate_by_year(rows, "publication date", "Publication Date", "publication_date", "pub_date")


# 법인 접미사만 단독으로 나온 경우 이전 토큰에 붙임 (회사명 일부)
LEGAL_SUFFIXES = frozenset(
    {"Ltd.", "Ltd", "Inc.", "Inc", "Llc", "LLC", "L.L.C.", "Co.", "Limited", "Corporation", "Corp.", "Corp", "GmbH", "AG"}
)

# 출원인명 → 영어 통일명 (동일 회사 한/중/일·영문 변형 통합)
CANONICAL_APPLICANT_EN = {
    # Samsung Display 계열
    "samsung display co. ltd.": "Samsung Display",
    "samsung display co.": "Samsung Display",
    "samsung display": "Samsung Display",
    "삼성디스플레이 주식회사": "Samsung Display",
    "삼성디스플레이주식회사": "Samsung Display",
    "삼성디스플레이": "Samsung Display",
    "三星显示有限公司": "Samsung Display",
    "三星显示": "Samsung Display",
    # Samsung Electronics 계열
    "samsung electronics co. ltd.": "Samsung Electronics",
    "samsung electronics co.": "Samsung Electronics",
    "samsung electronics": "Samsung Electronics",
    "삼성전자주식회사": "Samsung Electronics",
    "삼성전자 주식회사": "Samsung Electronics",
    "삼성전자": "Samsung Electronics",
    "三星电子株式会社": "Samsung Electronics",
    "三星电子": "Samsung Electronics",
    # LG Display 계열
    "lg display co. ltd.": "LG Display",
    "lg display co.": "LG Display",
    "lg display": "LG Display",
    "엘지디스플레이 주식회사": "LG Display",
    "엘지디스플레이": "LG Display",
    "乐金显示有限公司": "LG Display",
    "乐金显示": "LG Display",
    # LG Electronics 계열
    "엘지전자 주식회사": "LG Electronics",
    "엘지전자": "LG Electronics",
    "lg전자": "LG Electronics",
    "lg electronics co. ltd.": "LG Electronics",
    "lg electronics": "LG Electronics",
    # BOE Technology 계열
    "京东方科技集团股份有限公司": "BOE Technology Group",
    "京东方科技集团": "BOE Technology Group",
    "京东方": "BOE Technology Group",
    "boe technology group co. ltd.": "BOE Technology Group",
    "boe technology group": "BOE Technology Group",
    # Govisionox (昆山国显光电)
    "昆山国显光电有限公司": "Govisionox",
    "昆山国显光电": "Govisionox",
    "国显光电": "Govisionox",
    "govisionox (chongqing) co. ltd.": "Govisionox",
    "govisionox": "Govisionox",
    # NHK (日本放送協会)
    "日本放送協会": "NHK",
    "nippon hoso kyokai <nhk>": "NHK",
    "nippon hoso kyokai": "NHK",
    "nhk": "NHK",
    # OPPO 계열
    "oppo广东移动通信有限公司": "OPPO",
    "广东欧珀移动通信有限公司": "OPPO",
    "oppo mobile telecommunications": "OPPO",
    "oppo": "OPPO",
    # Huawei 계열
    "huawei technologies co. ltd.": "Huawei Technologies",
    "huawei technologies co.": "Huawei Technologies",
    "huawei technologies": "Huawei Technologies",
    "华为技术有限公司": "Huawei Technologies",
    "华为": "Huawei Technologies",
    # Apple
    "apple inc.": "Apple",
    "apple": "Apple",
    "苹果公司": "Apple",
    # Google
    "google llc": "Google",
    "google": "Google",
    # Intel
    "intel corporation": "Intel",
    "intel": "Intel",
    # 일본 기타
    "株式会社大一商会": "Daiichi Shoji",
    "株式会社半導体エネルギー研究所": "Semiconductor Energy Laboratory",
    "semiconductor energy laboratory co., ltd.": "Semiconductor Energy Laboratory",
    "semiconductor energy laboratory": "Semiconductor Energy Laboratory",
    # 三洋物産 (일본)
    "株式会社三洋物産": "Sanyo Bussan",
    "三洋物産": "Sanyo Bussan",
    # Tianma Microelectronics (天马)
    "上海天马微电子有限公司": "Tianma Microelectronics",
    "天马微电子有限公司": "Tianma Microelectronics",
    "厦门天马微电子有限公司": "Tianma Microelectronics",
    "tianma microelectronics co. ltd.": "Tianma Microelectronics",
    "tianma microelectronics": "Tianma Microelectronics",
    # Visionox (维信诺)
    "合肥维信诺科技有限公司": "Visionox",
    "维信诺科技股份有限公司": "Visionox",
    "维信诺": "Visionox",
    "visionox co. ltd.": "Visionox",
    "visionox": "Visionox",
    # Innolux
    "innolux corporation": "Innolux",
    "innolux": "Innolux",
    "群創光電股份有限公司": "Innolux",
    # AU Optronics
    "au optronics corporation": "AU Optronics",
    "au optronics": "AU Optronics",
    "友達光電股份有限公司": "AU Optronics",
    # Sharp
    "sharp corporation": "Sharp",
    "sharp kabushiki kaisha": "Sharp",
    "シャープ株式会社": "Sharp",
    # Japan Display
    "japan display inc.": "Japan Display",
    "japan display": "Japan Display",
    "株式会社ジャパンディスプレイ": "Japan Display",
    # TCL / CSOT
    "tcl china star optoelectronics technology co. ltd.": "TCL CSOT",
    "tcl华星光电技术有限公司": "TCL CSOT",
    "深圳市华星光电技术有限公司": "TCL CSOT",
    # Royole
    "royole corporation": "Royole",
    "柔宇科技": "Royole",
    # 한국 대학·연구기관
    "서울대학교산학협력단": "Seoul National University",
    "한국과학기술원": "KAIST",
    "포항공과대학교": "POSTECH",
    "연세대학교 산학협력단": "Yonsei University",
    "성균관대학교산학협력단": "Sungkyunkwan University",
    "한국전자통신연구원": "ETRI",
    "한국화학연구원": "KRICT",
}


_COMPACT_SUFFIX_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r",?\s*Co\.?\s*,\s*Ltd\.?\s*$",
        r",?\s*Co\.?\s*Ltd\.?\s*$",
        r",?\s*Ltd\.?\s*$",
        r",?\s*LLC\s*$",
        r",?\s*Inc\.?\s*$",
        r",?\s*Gmb[Hh]\s*$",
        r",?\s*Corporation\s*$",
        r",?\s*Corp\.?\s*$",
    )
)
_COMPACT_GMBH_MID = re.compile(r"\s+Gmb[Hh]\s+", re.IGNORECASE)
_COMPACT_SPACES = re.compile(r"\s+")


def compact_applicant_display(name: str) -> str:
    """출원인 표시명에서 LLC, Inc., Ltd., Co., Ltd., Gmbh, Corporation 등 일반 접미사 제거."""
    if not name or not name.strip():
        return name
    s = name.strip()
    for p in _COMPACT_SUFFIX_PATTERNS:
        s = p.sub("", s)
    # 중간의 Gmbh 제거 (예: Cilag Gmbh International → Cilag International)
    s = _COMPACT_GMBH_MID.sub(" ", s)
    s = s.strip().rstrip(".,")
    s = _COMPACT_SPACES.sub(" ", s).strip()
    return s if s else name.strip()


# 모듈 로드 시 canonical 표시명을 한 번만 계산 (매 호출마다 compact_applicant_display 재실행 방지)
_CANONICAL_DISPLAY: dict[str, str] = {k: compact_applicant_display(v) for k, v in CANONICAL_APPLICANT_EN.items()}


def _canonical_assignee_english(raw: str) -> str:
    """동일 회사 통합 + 영어 통일. 매핑에 없으면 법인 접미사만 제거한 형태로 반환."""
    if not raw or not raw.strip():
        return "Unknown"
    n = raw.strip()
    key = n.lower()
    if key in _CANONICAL_DISPLAY:
        return _CANONICAL_DISPLAY[key]
    # 접두사 매칭: Semiconductor Energy Laboratory 계열 통합
    if key.startswith("semiconductor energy laboratory"):
        return "Semiconductor Energy Laboratory"
    # 매핑 없음: 법인 접미사 제거
    suffixes = (" co. ltd.", " co., ltd.", " ltd.", " inc.", " llc.", " llc", " co.", " corp.", " gmbh", " ag")
    for suf in suffixes:
        if key.endswith(suf):
            n = n[: -len(suf)].strip().rstrip(".,")
            break
    n = n if n else raw.strip()
    # LG 계열 대소문자 통일
    if n.lower() in ("lg electronics", "lg display"):
        return "LG Electronics" if "electronics" in n.lower() else "LG Display"
    # BOE 계열 통일
    if n.lower().startswith("boe ") or n.lower() == "boe technology group":
        return "BOE Technology Group"
    return compact_applicant_display(n)


def _parse_assignee_cell(cell: str) -> list[str]:
    """Split assignee cell by delimiters; merge legal-suffix-only tokens with previous (e.g. 'Ltd.', 'Inc.').
    Splits only on ';' and '|' to avoid breaking names with internal commas (e.g. 'Co., Ltd.')."""
    if not cell or not cell.strip():
        return []
    parts = [p.strip() for p in re.split(r"[;|]", cell) if p.strip()]
    result = []
    for p in parts:
        if p in LEGAL_SUFFIXES:
            if result:
                result[-1] = result[-1] + " " + p
            # else: 접미사만 단독이면 건너뜀(회사명 아님)
        else:
            result.append(p)
    return result


def aggregate_applicants(rows: list[dict], top_n: int = 10) -> list[dict]:
    assignees = Counter()
    for row in rows:
        a = col_find(row, "assignee", "Assignee", "applicant", "Applicant", "owner")
        if not a:
            a = col_find(row, "assignees", "Applicants")
        if a:
            for name in _parse_assignee_cell(a):
                canonical = _canonical_assignee_english(name)
                assignees[canonical] += 1
    top = assignees.most_common(top_n)
    total = sum(assignees.values())
    return [{"name": n, "count": c, "pct": round(100 * c / total, 1) if total else 0} for n, c in top]


def aggregate_countries(rows: list[dict]) -> list[dict]:
    by_country = Counter()
    for row in rows:
        c = col_find(row, "country", "Country", "office", "jurisdiction", "country_code")
        if not c and "publication number" in row:
            # Extract from pub number e.g. US12345 -> US
            pub = str(row.get("publication number", row.get("Publication number", "")))
            if len(pub) >= 2:
                c = pub[:2].upper()
        if not c and "id" in row:
            pid = str(row.get("id", "")).strip()
            if len(pid) >= 2:
                c = pid.split("-")[0].upper() if "-" in pid else pid[:2].upper()
        if c:
            by_country[c.upper()] += 1
    total = sum(by_country.values())
    return [{"code": k, "count": v, "pct": round(100 * v / total, 1) if total else 0} for k, v in by_country.most_common()]


# 유럽 국가 코드 통합 및 한글 명칭 (보고서용)
EUROPE_CODES = {"EP", "ES", "DE", "GB", "FR", "NL", "DK", "BE"}
CODE_TO_KOREAN = {
    "US": "미국", "CN": "중국", "JP": "일본", "KR": "한국", "TW": "대만", "AU": "호주",
    "WO": "PCT", "RU": "러시아", "CA": "캐나다", "BR": "브라질", "EU": "유럽",
}


def aggregate_countries_for_report(rows: list[dict]) -> list[dict]:
    """유럽 국가를 '유럽'으로 통합하고, 모든 항목에 한글 명칭(name_ko)을 부여한 목록 반환."""
    raw = aggregate_countries(rows)
    by_code = {c["code"]: dict(c) for c in raw}
    europe_count = 0
    for co in EUROPE_CODES:
        if co in by_code:
            europe_count += by_code[co]["count"]
            del by_code[co]
    if europe_count:
        by_code["EU"] = {"code": "EU", "count": europe_count, "pct": 0}
    total = sum(c["count"] for c in by_code.values())
    result = []
    for code in sorted(by_code.keys(), key=lambda k: -by_code[k]["count"]):
        c = by_code[code]
        pct = round(100 * c["count"] / total, 1) if total else 0
        name_ko = CODE_TO_KOREAN.get(code, code)
        result.append({"code": code, "count": c["count"], "pct": pct, "name_ko": name_ko})
    return result


def table_priority_by_year(by_year: dict[int, int]) -> tuple[str, list[dict]]:
    rows_list = []
    prev = None
    total = sum(by_year.values())
    for y, c in sorted(by_year.items()):
        pct = round(100 * c / total, 1) if total else 0
        delta = ""
        if prev is not None and prev != 0:
            pct_change = round(100 * (c - prev) / prev, 1)
            delta = f"{pct_change:+.1f}%" if pct_change != 0 else "—"
        rows_list.append({"year": y, "count": c, "pct": pct, "yoy": delta})
        prev = c
    lines = [f"| {r['year']} | {r['count']:,} | {r['pct']}% | {r['yoy']} |" for r in rows_list]
    return "\n".join(lines), rows_list


def table_publication_by_year(by_year: dict[int, int]) -> str:
    lines = [f"| {y} | {c:,} | |" for y, c in sorted(by_year.items())]
    return "\n".join(lines)


def ascii_bar(data: list[tuple[str, float]], width: int = 40) -> str:
    """data = [(label, pct), ...]. Returns multi-line string."""
    max_pct = max((p for _, p in data), default=1)
    lines = []
    for label, pct in data:
        bar_len = int(width * pct / max_pct) if max_pct else 0
        bar = "█" * bar_len
        lines.append(f"{label[:20]:20} {bar} {pct}%")
    return "\n".join(lines)


def ascii_bar_years(years_dict: dict[int, int], width: int = 35) -> str:
    if not years_dict:
        return ""
    max_c = max(years_dict.values())
    lines = ["     │"]
    for y, c in sorted(years_dict.items()):
        bar_len = int(width * c / max_c) if max_c else 0
        lines.append(f"  {c:5} │" + "█" * bar_len)
    xs = " ".join(str(y) for y in sorted(years_dict.keys()))
    lines.append("   0 └" + "─" * min(width, 60) + "\n      " + xs)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="Path to filtered Google Patents CSV")
    ap.add_argument("--output-dir", "-o", default=os.getcwd())
    ap.add_argument("--report-title", default="세계 특허 현황 분석 보고서")
    ap.add_argument("--rfp-path", help="Optional RFP path for reference")
    ap.add_argument("--search-query", help="Final search query for report")
    ap.add_argument("--search-url", help="Final search URL for report")
    args = ap.parse_args()

    rows, cols = load_csv(args.csv_path)
    if not rows:
        raise SystemExit("No rows in CSV")

    total = len(rows)
    by_priority = aggregate_by_priority_year(rows)
    by_pub = aggregate_by_publication_year(rows)
    applicants = aggregate_applicants(rows, 10)
    countries = aggregate_countries_for_report(rows)

    table_pri_str, table_pri_data = table_priority_by_year(by_priority)
    table_pub_str = table_publication_by_year(by_pub)

    # ASCII charts
    ascii_priority = ascii_bar_years(by_priority)
    ascii_applicants = ascii_bar([(a["name"], a["pct"]) for a in applicants])
    ascii_countries = ascii_bar([(c["code"], c["pct"]) for c in countries])

    year_min = min(by_priority.keys()) if by_priority else 0
    year_max = max(by_priority.keys()) if by_priority else 0
    date_range = f"우선일 {year_min}.01.01 ~ {year_max}.12.31"

    out = {
        "total_count": total,
        "date_range": date_range,
        "table_priority_by_year": table_pri_str,
        "table_priority_data": table_pri_data,
        "table_publication_by_year": table_pub_str,
        "ascii_chart_priority": ascii_priority,
        "ascii_chart_applicants": ascii_applicants,
        "ascii_chart_country": ascii_countries,
        "top_applicants": applicants,
        "countries": countries,
        "report_title": args.report_title,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "search_query": args.search_query or "",
        "search_url": args.search_url or "",
        "rfp_reference": args.rfp_path or "",
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "aggregate_report_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Partial MD (tables only) for agent to merge into template
    md_path = out_dir / "aggregate_tables.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("## 2.1 우선일 기준 출원 건수\n\n")
        f.write("| 연도 | 출원 건수 | 비중 (%) | 전년 대비 증감 |\n|------|-----------|----------|----------------|\n")
        f.write(table_pri_str + "\n\n")
        f.write("```\n우선일 기준 연도별 출원 건수\n" + ascii_priority + "\n```\n\n")
        f.write("## 2.2 공개일 기준\n\n| 연도 | 공개 건수 | 비고 |\n|------|-----------|------|\n")
        f.write(table_pub_str + "\n\n")
        f.write("## 3.1 통합 출원인 순위\n\n")
        f.write("| 순위 | 출원인 | 통합 건수 | 비중 |\n|------|--------|-----------|------|\n")
        for i, a in enumerate(applicants, 1):
            f.write(f"| {i} | {a['name']} | {a['count']} | {a['pct']}% |\n")
        f.write("\n## 4.1 국가별 건수\n\n")
        f.write("| 국가/지역 | 건수 | 비중 |\n|----------|------|------|\n")
        for c in countries:
            f.write(f"| {c['code']} | {c['count']} | {c['pct']}% |\n")

    print(json_path)
    print(md_path)
    print("TOTAL_COUNT:", total)
    print("DATE_RANGE:", date_range)


if __name__ == "__main__":
    main()
