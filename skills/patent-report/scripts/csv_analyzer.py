"""
csv_analyzer.py — Google Patents CSV 분석 엔진
사용법: PYTHONUTF8=1 uv run python csv_analyzer.py --help
"""
import argparse
import csv
import io
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ─── 데이터 로드 ─────────────────────────────────────────────────────────────

def load_csv(paths: list[str]) -> list[dict]:
    """CSV 파일 로드 (복수 파일 병합 + id 기준 중복 제거).
    Google Patents CSV 특성: 첫 행은 검색 URL, 두 번째 행이 헤더."""
    rows = []
    seen_ids = set()
    for path in paths:
        path = path.strip()
        if not os.path.exists(path):
            print(f"[경고] 파일 없음: {path}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            lines = f.readlines()
        # 첫 행이 'search URL:' 로 시작하면 건너뜀
        start = 1 if lines and lines[0].startswith("search URL:") else 0
        reader = csv.DictReader(lines[start:])
        for row in reader:
            pid = row.get("id", "").strip()
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                rows.append(row)
    return rows


# ─── 출원인 정규화 ───────────────────────────────────────────────────────────

# 법인 접미어 패턴: CO LTD / CORP / INC / 주식회사 / 株式会社 / 有限公司 등
_CORP_SUFFIX_RE = re.compile(
    r"[\s,]*(co[\.,]?\s*ltd[\.,]?|corp[\.,]?|inc[\.,]?|llc[\.,]?|"
    r"limited|holdings?|group|gmbh|s\.?a\.?|b\.?v\.?|plc|"
    r"주식회사|\(주\)|㈜|株式会社|有限公司|有限责任公司)\s*$",
    re.IGNORECASE,
)


def _normalize_assignee(name: str) -> str:
    """법인 접미어 제거 + 대소문자 통일로 표기 정규화."""
    name = name.strip()
    for _ in range(3):  # "CO., LTD." 같은 복합 접미어 반복 제거
        prev = name
        name = _CORP_SUFFIX_RE.sub("", name).strip().rstrip(".,")
        if name == prev:
            break
    return name.upper()


# ─── 노이즈 필터 ─────────────────────────────────────────────────────────────

def sample_titles(rows: list[dict], n: int = 50) -> None:
    """타이틀 샘플 출력 (노이즈 분석용)."""
    import random
    sample = random.sample(rows, min(n, len(rows)))
    print(f"\n{'#'*60}")
    print(f"  타이틀 샘플 {len(sample)}건 (전체 {len(rows)}건 중 무작위)")
    print(f"{'#'*60}")
    print(f"{'No':>4}  {'연도':6}  {'국가':4}  {'출원인':25}  제목")
    print("-" * 100)
    for i, row in enumerate(sample, 1):
        year = _extract_year(row.get("priority date", ""))
        country = _extract_country(row.get("id", ""))
        assignee = (row.get("assignee", "") or "")[:25]
        title = (row.get("title", "") or "")[:60]
        print(f"{i:>4}  {year:6}  {country:4}  {assignee:25}  {title}")


def apply_noise_filter(
    rows: list[dict],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> tuple[list[dict], dict]:
    """타이틀 기반 노이즈 필터 적용. 연도별 제거 통계 포함."""
    original = len(rows)
    year_before: Counter = Counter(
        _extract_year(r.get("priority date", "")) for r in rows
    )
    if exclude_keywords:
        excl_lower = [k.lower() for k in exclude_keywords]
        rows = [r for r in rows
                if not any(k in (r.get("title", "") or "").lower() for k in excl_lower)]
    if include_keywords:
        incl_lower = [k.lower() for k in include_keywords]
        rows = [r for r in rows
                if any(k in (r.get("title", "") or "").lower() for k in incl_lower)]
    removed = original - len(rows)
    year_after: Counter = Counter(
        _extract_year(r.get("priority date", "")) for r in rows
    )
    year_removed = {
        y: year_before[y] - year_after.get(y, 0)
        for y in year_before
        if year_before[y] - year_after.get(y, 0) > 0
    }
    stats = {
        "original": original,
        "filtered": len(rows),
        "removed": removed,
        "remove_pct": removed / original * 100 if original else 0,
        "year_removed": dict(sorted(year_removed.items())),
    }
    return rows, stats


# ─── 집계 함수 ───────────────────────────────────────────────────────────────

def _extract_year(date_str: str) -> str:
    if not date_str:
        return ""
    return date_str.strip()[:4]


def _extract_country(patent_id: str) -> str:
    """특허 ID 앞 2자리로 국가 추출. 예: 'US-12345-B2' → 'US'"""
    pid = (patent_id or "").strip()
    if len(pid) >= 2:
        return pid[:2].upper()
    return "??"


COUNTRY_NAMES = {
    "US": "미국", "CN": "중국", "JP": "일본", "KR": "한국",
    "EP": "유럽(EP)", "WO": "PCT(WO)", "DE": "독일", "TW": "대만",
    "GB": "영국", "FR": "프랑스", "AU": "호주", "CA": "캐나다",
    "IN": "인도", "RU": "러시아", "BR": "브라질",
}


def compute_filing_trends(rows: list[dict]) -> dict[str, int]:
    """우선일(priority date) 기준 연도별 집계."""
    counter: dict[str, int] = defaultdict(int)
    for row in rows:
        y = _extract_year(row.get("priority date", ""))
        if y and y.isdigit():
            counter[y] += 1
    return dict(sorted(counter.items()))


def compute_publication_trends(rows: list[dict]) -> dict[str, int]:
    """공개일(publication date) 기준 연도별 집계."""
    counter: dict[str, int] = defaultdict(int)
    for row in rows:
        y = _extract_year(row.get("publication date", ""))
        if y and y.isdigit():
            counter[y] += 1
    return dict(sorted(counter.items()))


def compute_top_assignees(rows: list[dict], top_n: int = 10) -> list[tuple[str, int]]:
    """출원인 순위 (정규화 후 집계, 가장 많이 등장한 원래 표기명으로 출력)."""
    norm_counter: Counter = Counter()
    norm_to_orig: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        assignee = (row.get("assignee", "") or "").split(",")[0].strip()
        if assignee:
            norm = _normalize_assignee(assignee)
            norm_counter[norm] += 1
            norm_to_orig[norm][assignee] += 1
    result = []
    for norm, cnt in norm_counter.most_common(top_n):
        orig = norm_to_orig[norm].most_common(1)[0][0]
        result.append((orig, cnt))
    return result


def compute_geographic_distribution(rows: list[dict], top_n: int = 10) -> list[tuple[str, int]]:
    """국가별 특허 건수 (특허 ID 앞 2자리)."""
    counter: Counter = Counter()
    for row in rows:
        country = _extract_country(row.get("id", ""))
        if country and country != "??":
            counter[country] += 1
    return counter.most_common(top_n)


# ─── ASCII 차트 ──────────────────────────────────────────────────────────────

def _bar(value: int, max_val: int, width: int = 40) -> str:
    if max_val == 0:
        return ""
    filled = int(value / max_val * width)
    return "█" * filled


def build_filing_trends_chart(trends: dict[str, int], title: str = "연도별 출원 건수") -> str:
    if not trends:
        return ""
    max_val = max(trends.values())
    lines = [f"\n```\n{title}"]
    for year, cnt in sorted(trends.items()):
        bar = _bar(cnt, max_val)
        lines.append(f"{year}  {bar} {cnt:,}")
    lines.append("```\n")
    return "\n".join(lines)


def build_assignee_chart(assignees: list[tuple[str, int]], title: str = "주요 출원인 Top 10") -> str:
    if not assignees:
        return ""
    max_val = assignees[0][1] if assignees else 1
    total = sum(c for _, c in assignees)
    lines = [f"\n```\n{title}"]
    for name, cnt in assignees:
        bar = _bar(cnt, max_val, 30)
        pct = cnt / total * 100 if total else 0
        label = name[:30]
        lines.append(f"{label:32}  {bar}  {cnt:,}건 ({pct:.1f}%)")
    lines.append("```\n")
    return "\n".join(lines)


def build_geo_chart(geo: list[tuple[str, int]], title: str = "국가별 분포") -> str:
    if not geo:
        return ""
    total = sum(c for _, c in geo)
    max_val = geo[0][1] if geo else 1
    lines = [f"\n```\n{title}"]
    for code, cnt in geo:
        name = COUNTRY_NAMES.get(code, code)
        bar = _bar(cnt, max_val, 35)
        pct = cnt / total * 100 if total else 0
        lines.append(f"{name:12}({code:2})  {bar}  {cnt:,}건 ({pct:.1f}%)")
    lines.append("```\n")
    return "\n".join(lines)


# ─── 보고서 생성 ─────────────────────────────────────────────────────────────

def build_full_report(
    rows: list[dict],
    technology: str,
    search_query: str,
    analysis_period: str,
    tags: list[str],
    filter_stats: dict | None = None,
) -> str:
    filing = compute_filing_trends(rows)
    pub = compute_publication_trends(rows)
    assignees = compute_top_assignees(rows)
    geo = compute_geographic_distribution(rows)
    today = date.today().strftime("%Y-%m-%d")
    total = len(rows)

    filter_note = ""
    if filter_stats and filter_stats.get("removed", 0) > 0:
        year_detail = ""
        yr = filter_stats.get("year_removed", {})
        if yr:
            year_detail = " | " + ", ".join(f"{y}년: {c:,}건" for y, c in yr.items())
        filter_note = (
            f"\n> **필터 적용**: 원본 {filter_stats['original']:,}건 → "
            f"분석 대상 {filter_stats['filtered']:,}건 "
            f"(노이즈 {filter_stats['removed']:,}건, {filter_stats['remove_pct']:.1f}% 제거{year_detail})"
        )

    tag_str = ", ".join(tags) if tags else "특허분석, IP전략"

    # 공개 지연 보정: analysis_period 끝년도 기준 최근 2년 결정
    try:
        end_year = int(analysis_period.split("-")[-1].strip())
    except (ValueError, AttributeError):
        end_year = max((int(y) for y in filing if y.isdigit()), default=0)
    lag_years = {str(end_year), str(end_year - 1)} if end_year else set()

    # 연도별 전년 대비 변화 계산 (최근 2년 공개 지연 경고 포함)
    filing_table_rows = []
    prev = None
    for year, cnt in sorted(filing.items()):
        if prev is None:
            chg = "—"
        else:
            delta = (cnt - prev) / prev * 100 if prev else 0
            chg = f"**{delta:+.1f}%**" if delta > 0 else f"{delta:+.1f}%"
        lag_marker = " ⚠️" if year in lag_years else ""
        filing_table_rows.append(f"| {year}{lag_marker} | {cnt:,} | {chg} |")
        prev = cnt
    filing_table = "\n".join(filing_table_rows)

    # 출원인 표
    assignee_table_rows = []
    for rank, (name, cnt) in enumerate(assignees, 1):
        assignee_table_rows.append(f"| {rank} | {name} | {cnt:,} |")
    assignee_table = "\n".join(assignee_table_rows)

    # 국가별 표
    total_geo = sum(c for _, c in geo)
    geo_table_rows = []
    for code, cnt in geo:
        name = COUNTRY_NAMES.get(code, code)
        pct = cnt / total_geo * 100 if total_geo else 0
        geo_table_rows.append(f"| {name} ({code}) | {cnt:,} | {pct:.1f}% |")
    geo_table = "\n".join(geo_table_rows)

    filing_chart = build_filing_trends_chart(filing, "우선일 기준 연도별 출원 건수")
    pub_chart = build_filing_trends_chart(pub, "공개일 기준 연도별 공개 건수")
    assignee_chart = build_assignee_chart(assignees)
    geo_chart = build_geo_chart(geo)

    report = f"""---
title: {technology} 세계 특허 현황 분석 보고서
date: {today}
tags: [{tag_str}]
aliases: [{technology} 특허분석]
---

# {technology} 세계 특허 현황 분석 보고서

> **분석 기준일**: {today}
> **데이터 출처**: Google Patents (https://patents.google.com)
> **검색 쿼리**: `{search_query}`
> **분석 대상 기간**: {analysis_period}
> **총 특허 건수**: {total:,}건{filter_note}

---

## 1. 개요

본 보고서는 {technology} 관련 기술의 세계 특허 데이터를 분석하여, 기술 성장 추이, 주요 출원인의 경쟁 구도, 국가별 기술 확보 전략을 도출한다.

> **⚠️ 분석 한계**: Google Patents CSV 특성상 검색식 범위에 따라 일부 노이즈 특허가 포함될 수 있다. 상대적 비교 분석으로 해석할 것을 권장한다.

---

## 2. 연도별 출원 추이 분석

### 2.1 우선일(Priority Date) 기준 출원 건수

| 연도 | 출원 건수 | 전년 대비 |
|------|-----------|-----------|
{filing_table}

{filing_chart}

### 2.2 공개일(Publication Date) 기준 공개 건수

{pub_chart}

### 2.3 해석: 특허 공개 지연 효과(Publication Lag)

우선일 기준의 최근 2~3년 출원 건수 감소는 **특허 공개 지연(통상 18~24개월)**에 기인한다. 출원 후 공개까지 기간이 걸리므로, {end_year - 1}~{end_year}년 우선일 특허(표의 ⚠️ 연도)는 아직 상당수 미공개 상태다. 실제 출원 활동은 표의 수치보다 높을 가능성이 크다.

> **해석 포인트**: 공개일 기준 추이(§2.2)가 실제 기술 활성도를 더 정확히 반영한다.

---

## 3. 주요 출원인 분석

### 3.1 통합 출원인 순위 (Top {len(assignees)})

| 순위 | 출원인 | 건수 |
|------|--------|------|
{assignee_table}

### 3.2 출원인 점유율

{assignee_chart}

### 3.3 주요 출원인 전략 특성

_fill_ [Claude가 작성: 상위 출원인을 국가 그룹별로 묶어 각 그룹의 기술 전략 패턴을 분석. 단순 나열이 아닌, 각 기업이 집중하는 기술 영역과 그 의미를 서술.]

---

## 4. 국가별 특허 출원 분포

### 4.1 출원 국가별 건수

| 국가 | 건수 | 비중 |
|------|------|------|
{geo_table}

{geo_chart}

### 4.2 국가별 전략 분석

_fill_ [Claude가 작성: 상위 국가별 출원 전략 특성 분석 (예: 미국=시장 방어, 중국=양적 추격, 일본=소재·원천, 한국=원천+다국 출원). 각 국가의 특허 출원 패턴이 시사하는 IP 전략적 의미를 서술.]

---

## 5. 종합 전략적 시사점

### 5.1 기술 발전 단계

_fill_ [Claude가 작성: 공개일 기준 추이 데이터를 근거로 태동기/성장기/성숙기 중 어디에 해당하는지 판단. 구체적인 수치 근거 포함.]

### 5.2 지정학적 IP 경쟁 구도

_fill_ [Claude가 작성: 주요 국가·기업 간 경쟁·협력 구도 분석. ASCII 다이어그램이나 텍스트로 시각화.]

### 5.3 R&D 과제 기획 시사점

_fill_ [Claude가 작성: (1) 공백 영역/블루오션, (2) 선점 기회 기술, (3) 다국 출원 전략, (4) RFP 목표 달성을 위한 구체적 IP 행동 권고. 일반론이 아닌 이 데이터에서 읽히는 구체적 권고 사항 4~5가지.]

---

## 6. 참고 데이터

- **검색 쿼리**: `{search_query}`
- **분석 기간**: {analysis_period}
- **데이터 출처**: Google Patents CSV 다운로드
- **방법론 주의**: CSV 1,000건 한도 / 공개 지연 18~24개월 / 출원인 표기 불일치 가능

*본 보고서는 {today} Claude Code (Anthropic) 특허 전략 보고서 스킬로 자동 분석·작성되었습니다.*
"""
    return report


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Google Patents CSV → 한국어 특허 전략 보고서 생성"
    )
    parser.add_argument("--csv-path", required=True,
                        help="CSV 파일 경로 (쉼표로 복수 지정)")
    parser.add_argument("--technology", default="미지정 기술",
                        help="기술명 (보고서 제목에 사용)")
    parser.add_argument("--search-query", default="",
                        help="사용한 Google Patents Boolean 검색식")
    parser.add_argument("--analysis-period", default="",
                        help="분석 기간 (예: 2016-2025)")
    parser.add_argument("--tags", default="특허분석,IP전략",
                        help="보고서 태그 (쉼표 구분)")
    parser.add_argument("--output", default="",
                        help="출력 파일 경로 (.md). 미지정 시 stdout 출력")
    parser.add_argument("--show-sample", type=int, default=0, metavar="N",
                        help="타이틀 샘플 N건 출력 후 종료 (노이즈 분석용)")
    parser.add_argument("--exclude-keywords", default="",
                        help="제외 키워드 (쉼표 구분, 타이틀 매칭)")
    parser.add_argument("--include-keywords", default="",
                        help="포함 필수 키워드 (쉼표 구분, 타이틀 매칭)")
    args = parser.parse_args()

    paths = [p.strip() for p in args.csv_path.split(",") if p.strip()]
    rows = load_csv(paths)
    if not rows:
        print("[오류] 분석할 데이터가 없습니다.", file=sys.stderr)
        sys.exit(1)

    print(f"[로드] 총 {len(rows):,}건 (중복 제거 후)", file=sys.stderr)

    # 노이즈 분석 모드
    if args.show_sample > 0:
        sample_titles(rows, args.show_sample)
        return

    # 필터 적용
    excl = [k.strip() for k in args.exclude_keywords.split(",") if k.strip()]
    incl = [k.strip() for k in args.include_keywords.split(",") if k.strip()]
    filter_stats = None
    if excl or incl:
        rows, filter_stats = apply_noise_filter(rows, incl, excl)
        print(
            f"[필터] {filter_stats['original']:,}건 → {filter_stats['filtered']:,}건 "
            f"({filter_stats['removed']:,}건 제거, {filter_stats['remove_pct']:.1f}%)",
            file=sys.stderr,
        )

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    report = build_full_report(
        rows=rows,
        technology=args.technology,
        search_query=args.search_query,
        analysis_period=args.analysis_period,
        tags=tags,
        filter_stats=filter_stats,
    )

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[완료] 보고서 저장: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
