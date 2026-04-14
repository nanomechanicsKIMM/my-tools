#!/usr/bin/env python3
"""build_trip_plan.py — 국외출장계획서 HWPX 자동 생성 (메인 엔트리)

워크플로우:
1. user_input.md 파싱 (parse_user_input)
2. trip_type 결정 (frontmatter 또는 --type)
3. 해당 템플릿 선택 (assets/template_{type}.hwpx)
4. placeholder_maps/{type}.json 로드
5. 치환 맵 생성 (user_input 필드 → 원본 플레이스홀더)
6. zip_replace 로 HWPX 치환
7. validate 로 구조 검증

Usage:
    PYTHONUTF8=1 python build_trip_plan.py \\
        --input user_input.md \\
        --output 국외출장계획서.hwpx \\
        [--type conference|meeting|auto] \\
        [--pdf-ref references/advance_program.pdf]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_SCRIPT_DIR))

from parse_user_input import parse_user_input  # noqa: E402
from zip_replace import zip_replace  # noqa: E402
from validate import validate  # noqa: E402


# user_input 섹션 §1 키 → 논리 필드명
APPLICANT_KEY_MAP = {
    "제출일자": "submission_date",
    "소속": "applicant.department",
    "직급": "applicant.position",
    "성명": "applicant.name",
}


def _parse_year_from_date(date_str: str) -> int | None:
    """'2025.05.04.(월)' 형태에서 연도 4자리 추출."""
    if not date_str:
        return None
    m = re.search(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def _parse_date(date_str: str) -> datetime | None:
    """'2025.05.04.(월)' 또는 '2025.05.04' 파싱."""
    if not date_str:
        return None
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date_str.strip())
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _compute_duration(start: str, end: str) -> str:
    """시작·종료 문자열 → 'N박 M일'. 실패 시 빈 문자열."""
    s = _parse_date(start)
    e = _parse_date(end)
    if not s or not e or e < s:
        return ""
    days = (e - s).days + 1
    nights = days - 1
    return f"{nights}박 {days}일"


def _detect_trip_type(data: dict[str, Any], cli_type: str | None) -> str:
    """trip_type 결정 우선순위: CLI --type > frontmatter > auto detect."""
    if cli_type and cli_type != "auto":
        return cli_type
    fm_type = data.get("frontmatter", {}).get("trip_type", "auto")
    if fm_type in ("meeting", "conference"):
        return fm_type

    # auto 휴리스틱: 섹션 4 conference URL 또는 키워드
    fm = data.get("frontmatter", {})
    if fm.get("conference_url") or fm.get("program_urls"):
        return "conference"

    # 본문 전체 텍스트에서 학회 키워드 탐색
    raw_all = " ".join(
        s.get("raw", "") for s in data.get("sections", {}).values()
    )
    conf_kws = ("학회", "전시회", "Display Week", "SID", "CES", "SEMICON", "Symposium")
    meet_kws = ("기관 방문", "면담", "MOU", "협약", "포럼 개최")
    conf_score = sum(raw_all.count(k) for k in conf_kws)
    meet_score = sum(raw_all.count(k) for k in meet_kws)
    return "conference" if conf_score >= meet_score else "meeting"


def _load_placeholder_map(trip_type: str) -> dict[str, dict]:
    """assets/placeholder_maps/{type}.json 로드."""
    map_path = _SKILL_DIR / "assets" / "placeholder_maps" / f"{trip_type}.json"
    if not map_path.exists():
        raise FileNotFoundError(f"플레이스홀더 맵 없음: {map_path}")
    with open(map_path, encoding="utf-8") as f:
        return json.load(f)


def _build_replacements(
    data: dict[str, Any], pmap: dict[str, dict]
) -> tuple[dict[str, str], list[str]]:
    """user_input 데이터 + 플레이스홀더 맵 → 치환 딕셔너리 생성.

    Phase 4A: 신청자(4) + 출장개요(2) + 섹션 제목(2) + 출장자 일정(최대 3) 필드.

    Returns:
        (replacements, missing_fields)
    """
    replacements: dict[str, str] = {}
    missing: list[str] = []

    applicant = data.get("applicant", {})
    overview = data.get("trip_overview", {})
    companions = data.get("companions", [])
    frontmatter = data.get("frontmatter", {})
    sections = data.get("sections", {})

    field_values: dict[str, str] = {}

    # --- 1. 신청자 정보 (기존) ---
    for kr_key, logical in APPLICANT_KEY_MAP.items():
        if kr_key in applicant:
            field_values[logical] = applicant[kr_key]

    # --- 2. 출장 개요: 국가·도시 ---
    country = (overview.get("출장 국가") or "").strip()
    city = (overview.get("방문 도시") or "").strip()
    if country and city:
        field_values["overview.country_city"] = (
            f"  ○ 출장국가 및 출장도시 : {country}({city})"
        )
    elif country:
        field_values["overview.country_city"] = (
            f"  ○ 출장국가 및 출장도시 : {country}"
        )

    # --- 3. 출장 개요: 주 목적 한 줄 ---
    purpose = (overview.get("주 목적 한 줄") or "").strip()
    if purpose:
        field_values["overview.purpose_oneline"] = f"  ○ 출장목적: {purpose}"

    # --- 4. 행사 연도 결정 (frontmatter > 시작일에서 추출) ---
    start_date = (overview.get("출장 기간 (시작)") or "").strip()
    end_date = (overview.get("출장 기간 (종료)") or "").strip()
    conf_year = frontmatter.get("conference_year")
    if not conf_year:
        conf_year = _parse_year_from_date(start_date)

    # --- 5. 섹션 2 제목: 행사명 + 연도 ---
    sec4_kv = sections.get(4, {}).get("kv", {}) if isinstance(sections, dict) else {}
    event_name = (sec4_kv.get("행사명") or "Display Week").strip()
    if conf_year:
        # 원본 템플릿은 trailing space 포함 ("2. Display Week 2025 주요 행사 ")
        field_values["event.section_title"] = (
            f"2. {event_name} {conf_year} 주요 행사 "
        )

    # --- 6. 섹션 4 제목: 최근 3년 범위 ---
    if conf_year:
        y_start, y_end = int(conf_year) - 3, int(conf_year) - 1
        field_values["event.past_trips_title"] = (
            f"4. 최근 3년간 국외출장 실적({y_start}~{y_end})"
        )

    # --- 7. 출장자 일정 라인 (최대 3명) ---
    duration_label = (overview.get("일수 라벨") or "").strip()
    if not duration_label:
        duration_label = _compute_duration(start_date, end_date)

    for idx, row in enumerate(companions[:3], start=1):
        name = (
            row.get("성명")
            or row.get("이름")
            or row.get("No")
            or ""
        ).strip()
        if not name or not start_date or not end_date:
            continue
        if duration_label:
            line = f"    - {name} : {start_date} - {end_date}, ({duration_label})"
        else:
            line = f"    - {name} : {start_date} - {end_date}"
        field_values[f"traveler.line_{idx}"] = line

    # --- 8. placeholder 맵 순회 → 치환 딕셔너리 ---
    fields = pmap.get("fields", {})
    for logical, spec in fields.items():
        placeholder = spec.get("placeholder", "")
        value = field_values.get(logical)
        if value and placeholder:
            replacements[placeholder] = value
        elif spec.get("required") and not value:
            missing.append(logical)

    return replacements, missing


def build(
    input_path: str | Path,
    output_path: str | Path,
    trip_type: str | None = None,
    pdf_ref: str | None = None,
) -> dict[str, Any]:
    """출장계획서 HWPX를 생성한다.

    Returns:
        {
            "output": str,
            "trip_type": str,
            "replacements_count": int,
            "missing_fields": [...],
            "pdf_ref": str | None,
            "validation_errors": [...]
        }
    """
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {input_path}")

    # 1. user_input 파싱
    print(f"[STEP 1] 파싱: {input_path}")
    data = parse_user_input(input_path)

    # 2. trip_type 결정
    detected = _detect_trip_type(data, trip_type)
    print(f"[STEP 2] trip_type = {detected}")

    # 3. 템플릿 경로
    template_path = _SKILL_DIR / "assets" / f"template_{detected}.hwpx"
    if not template_path.exists():
        raise FileNotFoundError(f"템플릿 없음: {template_path}")
    print(f"[STEP 3] template = {template_path.name}")

    # 4. 플레이스홀더 맵
    pmap = _load_placeholder_map(detected)
    print(f"[STEP 4] placeholder fields = {len(pmap.get('fields', {}))}")

    # 5. 치환 딕셔너리
    replacements, missing = _build_replacements(data, pmap)
    print(f"[STEP 5] replacements = {len(replacements)}")
    for old, new in replacements.items():
        print(f"          {old!r} -> {new!r}")
    if missing:
        print(f"[WARN ] 필수 필드 누락: {missing}")

    # 6. ZIP 치환
    output_path.parent.mkdir(parents=True, exist_ok=True)
    zip_replace(template_path, output_path, replacements)
    print(f"[STEP 6] 생성: {output_path}")

    # 7. 검증
    errors = validate(output_path)
    if errors:
        print(f"[FAIL ] 검증 실패:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"[STEP 7] 검증 통과 ✓")

    # PDF 참고자료 기록
    pdf_ref_path = None
    if pdf_ref:
        pdf_ref_abs = Path(pdf_ref).resolve()
        if pdf_ref_abs.exists():
            pdf_ref_path = str(pdf_ref_abs)
            print(f"[INFO ] PDF 참고자료: {pdf_ref_path}")
        else:
            print(f"[WARN ] PDF 참고자료 경로 없음: {pdf_ref}")

    return {
        "output": str(output_path),
        "trip_type": detected,
        "replacements_count": len(replacements),
        "missing_fields": missing,
        "pdf_ref": pdf_ref_path,
        "validation_errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="국외출장계획서 HWPX 자동 생성")
    parser.add_argument("--input", required=True, help="user_input.md 경로")
    parser.add_argument("--output", required=True, help="출력 HWPX 경로")
    parser.add_argument(
        "--type",
        choices=["meeting", "conference", "auto"],
        default="auto",
        help="출장 유형 (기본: auto)",
    )
    parser.add_argument("--pdf-ref", help="Advance Program PDF 경로 (참고자료)")
    args = parser.parse_args()

    try:
        result = build(args.input, args.output, args.type, args.pdf_ref)
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        return 1

    if result["validation_errors"]:
        return 1

    print(f"\n✓ 생성 완료: {result['output']}")
    print(f"  타입: {result['trip_type']}")
    print(f"  치환 수: {result['replacements_count']}")
    if result["missing_fields"]:
        print(f"  (경고) 미입력 필수 필드: {', '.join(result['missing_fields'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
