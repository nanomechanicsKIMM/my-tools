#!/usr/bin/env python3
"""One-off: generate 15-year stretchable display search from repo RFP (avoids CLI encoding)."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
# Patent_Analysis (workspace root where RFP lives)
REPO_ROOT = SKILL_ROOT.parent.parent.parent

# RFP in project root (current folder)
RFP_NAME = "(2026)_RFP_센서_융합_디스플레이_기술.md"
rfp_path = REPO_ROOT / RFP_NAME
if not rfp_path.exists():
    # try with dot-prefix path seen on some systems
    for p in REPO_ROOT.iterdir():
        if "RFP" in p.name and p.suffix == ".md":
            rfp_path = p
            break
    else:
        rfp_path = None
if not rfp_path or not rfp_path.exists():
    print("RFP not found:", REPO_ROOT / RFP_NAME, file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(SCRIPT_DIR))
from generate_query import read_rfp, build_query

END_YEAR = 2026
years = 15
start_year = END_YEAR - years
after = f"priority:{start_year}0101"
before = f"priority:{END_YEAR}1231"

rfp_text = read_rfp(str(rfp_path))
query_string, search_url = build_query(
    rfp_text,
    technology_domain="디스플레이",
    after=after,
    before=before,
)

print("QUERY_STRING:")
print(query_string)
print()
print("SEARCH_URL:")
print(search_url)
print()
print("DATE_RANGE:", f"priority {start_year}.01.01 - {END_YEAR}.12.31")

out_dir = SKILL_ROOT / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "search_url_15yr_신축디스플레이.txt").write_text(
    f"# 15년 신축/센서융합 디스플레이 검색 (RFP 기준)\n"
    f"DATE_RANGE: priority {start_year}.01.01 - {END_YEAR}.12.31\n\n"
    f"QUERY_STRING:\n{query_string}\n\n"
    f"SEARCH_URL:\n{search_url}\n",
    encoding="utf-8",
)
print("\nSaved:", out_dir / "search_url_15yr_신축디스플레이.txt")
