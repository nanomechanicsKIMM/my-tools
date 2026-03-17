#!/usr/bin/env python3
"""
Fill the report template with aggregate data. Narrative placeholders are set to
short prompts so the agent/LLM can replace them.

Usage: python fill_report.py <aggregate_report_data.json> [--template PATH] [--output PATH] [--topic "센서융합디스플레이"]
"""
import argparse
import json
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_template(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def table_top_applicants(applicants: list[dict]) -> str:
    lines = []
    for i, a in enumerate(applicants, 1):
        name = a.get("name", "")
        count = a.get("count", 0)
        pct = a.get("pct", 0)
        lines.append(f"| {i} | **{name}** | — | {count:,}건 | {pct}% |")
    return "\n".join(lines)


def table_country(countries: list[dict]) -> str:
    """국가별 건수 표. name_ko가 있으면 한글만 사용, 없으면 code 사용."""
    lines = []
    for c in countries:
        count = c.get("count", 0)
        pct = c.get("pct", 0)
        label = c.get("name_ko") or c.get("code", "")
        lines.append(f"| {label} | {count:,} | **{pct}%** | |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to aggregate_report_data.json")
    ap.add_argument("--template", "-t", default=None, help="Path to report-template.md")
    ap.add_argument("--output", "-o", default=None, help="Output report path")
    ap.add_argument("--topic", default="특허", help="Topic slug for title/aliases")
    ap.add_argument("--generated-by", default="Claude (Anthropic)에 의해 자동 분석·작성되었습니다.")
    args = ap.parse_args()

    data = load_json(args.json_path)
    script_dir = Path(__file__).resolve().parent
    template_path = args.template or script_dir.parent / "templates" / "report-template.md"
    tpl = load_template(str(template_path))

    report_title = data.get("report_title", "세계 특허 현황 분석 보고서")
    analysis_date = data.get("analysis_date", "")
    total = data.get("total_count", 0)
    date_range = data.get("date_range", "")
    search_query = data.get("search_query", "")
    search_url = data.get("search_url", "")
    rfp_ref = data.get("rfp_reference", "")

    applicants = data.get("top_applicants", [])
    countries = data.get("countries", [])

    replacements = {
        "{{REPORT_TITLE}}": report_title,
        "{{REPORT_DATE}}": analysis_date,
        "{{TAG1}}": args.topic,
        "{{TAG2}}": "Google-Patents",
        "{{ALIAS}}": f"{args.topic} 특허분석",
        "{{ANALYSIS_DATE}}": analysis_date,
        "{{SEARCH_QUERY}}": search_query or "(검색식 없음)",
        "{{DATE_RANGE}}": date_range,
        "{{TOTAL_COUNT}}": f"{total:,}",
        "{{TABLE_PRIORITY_BY_YEAR}}": data.get("table_priority_by_year", ""),
        "{{TABLE_PUBLICATION_BY_YEAR}}": data.get("table_publication_by_year", ""),
        "{{ASCII_CHART_PRIORITY}}": data.get("ascii_chart_priority", ""),
        "{{TABLE_TOP_APPLICANTS}}": table_top_applicants(applicants),
        "{{ASCII_CHART_APPLICANTS}}": data.get("ascii_chart_applicants", ""),
        "{{TABLE_COUNTRY}}": table_country(countries),
        "{{ASCII_CHART_COUNTRY}}": data.get("ascii_chart_country", ""),
        "{{SEARCH_URL}}": search_url or "(URL 없음)",
        "{{RFP_REFERENCE}}": rfp_ref or "(관련 RFP 없음)",
        "{{GENERATED_BY}}": args.generated_by.rstrip(".") + ".",
        # Narrative placeholders – replace with LLM or leave as prompt
        "{{OVERVIEW_PARAGRAPH}}": "[본 보고서는 RFP 기술 영역의 세계 특허 데이터를 분석하여 기술 추이, 주요 출원인, 국가별 전략을 도출합니다. 위 총 특허 건수와 데이터 출처를 반영하여 1~2문단으로 작성하세요.]",
        "{{LIMITATION_NOTE}}": "[Google Patents 검색 특성상 관련 없는 특허가 일부 포함될 수 있음. 검색 쿼리 범위를 고려한 상대적 비교로 해석할 것.]",
        "{{INTERPRETATION_PUBLAG}}": "[우선일 기준 연도별 추이와 공개 지연(18~24개월)을 설명하고, 기술 단계(성장기/성숙기)를 판단하는 문단.]",
        "{{CONCLUSION_PHASE}}": "[기술 성장기/성숙기/퇴조기 결론 및 R&D 투자 구간 해석.]",
        "{{APPLICANT_INTRO}}": "동일 기업의 다양한 법인명을 통합하여 실질적 경쟁 순위를 산출했다.",
        "{{TABLE_APPLICANT_STRATEGY}}": "[상위 10개 출원인별 전략 특성 표: 각 출원인당 한 행씩, 컬럼은 출원인|강점·주요 포트폴리오|RFP 연관성|차별화·선행 회피 포인트. 초록·대표청구항 기반으로 작성.]",
        "{{STRATEGY_BY_REGION}}": "[한국/미국/중국/일본 등 지역별 주요 출원인 전략 특성 2~3문단.]",
        "{{COUNTRY_STRATEGY}}": "[국가별 점유율과 특성(미국 IP 시장, 중국 추격, 한국 질적 우위 등) 분석.]",
        "{{TECH_PHASE}}": "[공개일 기준 성장 추이와 기술 발전 단계 해석.]",
        "{{COMPETITION_DIAGRAM}}": "[지정학적 경쟁 구도 ASCII 다이어그램 또는 요약.]",
        "{{RND_IMPLICATIONS}}": "[국내 R&D 과제 기획 시 시사점 3~4개 번호 목록.]",
        "{{RELATED_DOCS}}": "[관련 심층 분석 문서 링크 또는 없음 시 생략.]",
    }

    out = tpl
    for k, v in replacements.items():
        out = out.replace(k, v)

    output_path = args.output
    if not output_path:
        output_path = Path(args.json_path).parent / f"{args.topic}_세계특허현황_분석보고서.md"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(output_path)


if __name__ == "__main__":
    main()
