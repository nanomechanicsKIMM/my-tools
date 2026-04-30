"""Run 15-year query generation for RFP and print URL."""
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
skill_root = script_dir.parent
repo_root = skill_root.parent.parent.parent  # Patent_Analysis
rfp_path = repo_root / "(2026)_RFP_센서_융합_디스플레이_기술.md"
if not rfp_path.exists():
    rfp_path = repo_root / "./(2026)_RFP_센서_융합_디스플레이_기술.md"
if not rfp_path.exists():
    print("RFP not found", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(script_dir))
import generate_query as gq

rfp_text = gq.read_rfp(str(rfp_path))
after = "priority:20110101"
before = "priority:20251231"
query_string, search_url = gq.build_query(rfp_text, technology_domain="디스플레이", after=after, before=before)
print("QUERY_STRING:")
print(query_string)
print()
print("SEARCH_URL:")
print(search_url)
print()
print("DATE_RANGE: priority 2011.01.01 - 2025.12.31 (15 years)")
