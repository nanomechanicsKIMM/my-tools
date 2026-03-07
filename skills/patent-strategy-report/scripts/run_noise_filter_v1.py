#!/usr/bin/env python3
"""
Run noise filter on v1 CSV, derive improved search query, and save for next round.
No CLI encoding issues: paths and query are set in code.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
# Patent_Analysis (project root where CSV/RFP live)
REPO_ROOT = SKILL_ROOT.parent.parent

CSV_NAME = "gp-search-20260306_v1.csv"
RFP_NAME = "(2026)_RFP_센서_융합_디스플레이_기술.md"
CURRENT_QUERY = (
    "(Display OR Transformable OR Deformation OR sensing OR User OR interface OR User OR Experience "
    "OR display OR panel OR screen OR OLED OR LED OR flexible OR stretchable OR foldable OR rollable "
    "OR backplane OR TFT OR pixel)"
)
CURRENT_URL = (
    "https://patents.google.com/?q=%28Display+OR+Transformable+OR+Deformation+OR+sensing+OR+User+OR+interface"
    "+OR+User+OR+Experience+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable+OR+foldable"
    "+OR+rollable+OR+backplane+OR+TFT+OR+pixel%29&after=priority:20110101&before=priority:20261231"
)


def main():
    root = REPO_ROOT
    csv_path = root / CSV_NAME
    rfp_path = root / RFP_NAME
    if not csv_path.exists() and (root.parent / CSV_NAME).exists():
        root = root.parent
        csv_path = root / CSV_NAME
        rfp_path = root / RFP_NAME
    if not csv_path.exists():
        for p in root.iterdir():
            if "v1" in p.name and p.suffix == ".csv":
                csv_path = p
                break
    if not csv_path.exists():
        print("CSV not found:", root / CSV_NAME, file=sys.stderr)
        sys.exit(1)
    if not rfp_path.exists():
        for p in root.iterdir():
            if "RFP" in p.name and p.suffix == ".md":
                rfp_path = p
                break
    if not rfp_path.exists():
        print("RFP not found:", root / RFP_NAME, file=sys.stderr)
        sys.exit(1)

    out_dir = SKILL_ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    filtered_path = out_dir / "filtered_v1.csv"

    # Run filter_noise in-process and capture stdout
    old_argv, old_stdout = sys.argv, sys.stdout
    buf = io.StringIO()
    sys.argv = [
        "filter_noise", str(csv_path), str(rfp_path),
        "-o", str(filtered_path), "--threshold", "0.05",
        "--current-query", CURRENT_QUERY, "--suggest-top-n", "8",
    ]
    sys.stdout = buf
    try:
        import filter_noise
        filter_noise.main()
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv

    raw_stdout = buf.getvalue()
    print(raw_stdout)
    (out_dir / "noise_filter_raw_output.txt").write_text(raw_stdout, encoding="utf-8")

    removal_ratio = None
    suggested_terms = None
    improved_query = None
    for line in raw_stdout.splitlines():
        if line.startswith("REMOVAL_RATIO:"):
            try:
                removal_ratio = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("SUGGESTED_NOT_TERMS:"):
            suggested_terms = line.split(":", 1)[1].strip()
        elif line.startswith("IMPROVED_QUERY_SUGGESTION:"):
            improved_query = line.split(":", 1)[1].strip()

    out_file = out_dir / "noise_filter_개선검색식_v1.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# 노이즈 필터 결과 (v1 CSV 기준) – 개선 검색식\n\n")
        f.write(f"**REMOVAL_RATIO**: {removal_ratio}\n\n" if removal_ratio is not None else "REMOVAL_RATIO: (파싱 실패)\n\n")
        f.write(f"**SUGGESTED_NOT_TERMS**: {suggested_terms}\n\n" if suggested_terms else "")
        f.write(f"**IMPROVED_QUERY_SUGGESTION**:\n```\n{improved_query}\n```\n\n" if improved_query else "")
        if improved_query and removal_ratio is not None and removal_ratio > 0.10:
            new_q = quote_plus(improved_query)
            improved_url = re.sub(r"q=[^&]*", "q=" + new_q, CURRENT_URL, count=1)
            f.write("**IMPROVED_SEARCH_URL** (다음 라운드 CSV 다운로드용):\n")
            f.write(improved_url + "\n\n")
            f.write("---\n다음 단계: 위 URL로 Google Patents 검색 후 Download (CSV) → 새 CSV로 파이프라인 재실행.\n")

    print("\nSaved:", out_file)
    if removal_ratio is not None and removal_ratio > 0.10 and improved_query:
        print("\n>>> REMOVAL_RATIO > 10%: 개선 검색식이", out_file, "에 저장되었습니다. 해당 URL로 재검색 후 새 CSV로 반복하세요.")


if __name__ == "__main__":
    main()
