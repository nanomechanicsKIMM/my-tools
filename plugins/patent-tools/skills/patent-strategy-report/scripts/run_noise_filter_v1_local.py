# -*- coding: utf-8 -*-
"""Run noise filter Step 1 from Patent_Analysis: v1 -> top 5000 by title-RFP."""
import sys
from pathlib import Path

root = Path(r"c:\Users\JHKIM\Patent_Analysis")
sys.path.insert(0, str(root / ".codex" / "skills" / "patent-strategy-report" / "scripts"))

v1 = root / "gp-search-20260306_v1.csv"
rfp = next(root.glob("*RFP*디스플레이*.md"), None) or next(root.glob("*RFP*.md"), None)
out = root / ".codex" / "skills" / "patent-strategy-report" / "output" / "v1_top5000.csv"

if not v1.exists():
    print("v1 CSV not found:", v1, file=sys.stderr)
    sys.exit(1)
if not rfp or not rfp.exists():
    print("RFP not found", file=sys.stderr)
    sys.exit(1)

out.parent.mkdir(parents=True, exist_ok=True)

# Invoke filter_title_top_n
import filter_title_top_n as m
m.load_csv_with_header_skip = m.load_csv_with_header_skip
m.load_rfp_text = m.load_rfp_text
m.get_title = m.get_title

rows, header = m.load_csv_with_header_skip(str(v1))
if not rows:
    print("No rows", file=sys.stderr)
    sys.exit(1)

rfp_text = m.load_rfp_text(str(rfp))
titles = [m.get_title(r) for r in rows]

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

texts = [rfp_text] + titles
vectorizer = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95)
X = vectorizer.fit_transform(texts)
scores = cosine_similarity(X[1:], X[0:1]).ravel()

for i, row in enumerate(rows):
    row["relevance_score"] = round(float(scores[i]), 4) if i < len(scores) else 0.0

sorted_rows = sorted(rows, key=lambda r: r.get("relevance_score", 0.0), reverse=True)
top = sorted_rows[:5000]

out_header = list(header)
if "relevance_score" not in out_header:
    out_header.append("relevance_score")

import csv
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=out_header, extrasaction="ignore")
    w.writeheader()
    w.writerows(top)

print("Total:", len(rows), "Kept (top 5000):", len(top))
print("Output:", out)
