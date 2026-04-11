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
import sys
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

    Returns:
        (replacements, missing_fields)
    """
    replacements: dict[str, str] = {}
    missing: list[str] = []

    applicant = data.get("applicant", {})  # {"제출일자": ..., "소속": ..., ...}

    # 논리 필드명 → 값
    field_values: dict[str, str] = {}
    for kr_key, logical in APPLICANT_KEY_MAP.items():
        if kr_key in applicant:
            field_values[logical] = applicant[kr_key]

    # placeholder 맵 순회
    fields = pmap.get("fields", {})
    for logical, spec in fields.items():
        placeholder = spec.get("placeholder", "")
        value = field_values.get(logical)
        if value and placeholder:
            # 동일 placeholder에 중복 지정 시 마지막 값이 우선
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
