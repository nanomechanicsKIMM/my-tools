#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patent Strategy Pro – Full Pipeline Orchestrator

Runs all automated steps of the patent strategy analysis:
  Phase 1: (optional) PDF → MD conversion
  Phase 3: Main CSV → title score → top 10,000 → aggregate stats
  Phase 4: Sub-tech CSVs → title score → top 100 each → fetch abstracts+claims
           → abstract score → top 5 core patents each

User-driven steps (NOT automated here):
  - Step 2: Sub-technology extraction (run extract_sub_technologies.py + user review)
  - Step 3/4: Download CSVs from Google Patents

Usage:
  # Phase 3 only (main stats from main CSV):
  python run_pipeline.py --rfp rfp.md --main-csv main.csv --topic "센서융합디스플레이" -o output/

  # Phase 4 only (sub-tech analysis, after CSVs downloaded):
  python run_pipeline.py --rfp rfp.md --sub-tech-json sub_techs.json
      --sub-tech-csvs sub1.csv,sub2.csv,sub3.csv -o output/

  # Full (Phase 3 + 4):
  python run_pipeline.py --rfp rfp.md --main-csv main.csv
      --sub-tech-json sub_techs.json --sub-tech-csvs sub1.csv,sub2.csv,sub3.csv
      --topic "기술명" -o output/

  # With PDF input:
  python run_pipeline.py --rfp rfp.pdf --main-csv main.csv ... (auto-converts PDF to MD)


Supports two CSV acquisition modes:
  1. Manual: User downloads CSVs from Google Patents (--main-csv, --sub-tech-csvs)
  2. Auto:   EPO OPS API downloads CSVs automatically (--auto-download)
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
LEGACY_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "patent-strategy-report" / "scripts"


def _py() -> Path:
    """Return python executable, prefer venv."""
    venv = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
    return venv if venv.exists() else Path(sys.executable)


def _add_legacy_path():
    """Add existing patent-strategy-report scripts to path for reuse."""
    if LEGACY_SCRIPTS.exists():
        sys.path.insert(0, str(LEGACY_SCRIPTS))
    sys.path.insert(0, str(SCRIPT_DIR))


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    start = 1 if lines and lines[0].strip().lower().startswith("search url") else 0
    if start >= len(lines):
        return [], []
    header = next(csv.reader([lines[start]]))
    rows = list(csv.DictReader(lines[start + 1:], fieldnames=header))
    return rows, header


def write_csv(rows: list[dict], path: Path):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run_step(label: str, cmd: list[str], cwd: Path = None) -> bool:
    print(f"\n[{label}]", " ".join(str(c) for c in cmd))
    # Use explicit cwd if given; otherwise inherit caller's working directory
    # so that relative file paths in args resolve correctly.
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        print(f"  ✗ Failed (exit {r.returncode})", file=sys.stderr)
        return False
    print(f"  ✓ Done")
    return True


# ── Phase 1: PDF conversion ────────────────────────────────────────────────────

def convert_pdf_if_needed(rfp_path: Path, out_dir: Path) -> Path:
    if rfp_path.suffix.lower() != ".pdf":
        return rfp_path
    out_md = out_dir / (rfp_path.stem + ".md")
    if out_md.exists():
        print(f"[PDF→MD] Using existing: {out_md}")
        return out_md
    ok = run_step("PDF→MD", [_py(), SCRIPT_DIR / "pdf_to_md.py", rfp_path, "-o", out_md])
    if not ok:
        print("PDF conversion failed. Please convert manually.", file=sys.stderr)
        sys.exit(1)
    return out_md


# ── Phase 3: Main CSV stats ───────────────────────────────────────────────────

def run_main_stats(rfp_md: Path, main_csv: Path, out_dir: Path,
                   include_terms: list[str], exclude_terms: list[str],
                   topic: str) -> Path:
    """Score main CSV by title, extract top 10k, aggregate for report."""
    _add_legacy_path()
    from score_title_relevance import run as score_title

    top10k = out_dir / "v1_top10000.csv"
    print(f"\n[Main Stats] Scoring main CSV: {main_csv.name}")
    score_title(
        str(main_csv), str(rfp_md), str(top10k),
        top_n=10000, include_terms=include_terms, exclude_terms=exclude_terms,
    )
    print(f"  ✓ Top 10,000 saved: {top10k}")

    # Aggregate
    from aggregate_csv_report import (
        load_csv as agg_load, aggregate_by_priority_year, aggregate_by_publication_year,
        aggregate_applicants, aggregate_countries_for_report,
        table_priority_by_year, table_publication_by_year,
        ascii_bar_years, ascii_bar,
    )
    rows, _ = agg_load(str(top10k))
    total = len(rows)
    by_pri = aggregate_by_priority_year(rows)
    by_pub = aggregate_by_publication_year(rows)
    applicants = aggregate_applicants(rows, 10)
    countries = aggregate_countries_for_report(rows)
    table_pri_str, table_pri_data = table_priority_by_year(by_pri)
    table_pub_str = table_publication_by_year(by_pub)
    ascii_pri = ascii_bar_years(by_pri)
    ascii_app = ascii_bar([(a["name"], a["pct"]) for a in applicants])
    ascii_cnt = ascii_bar([(c.get("name_ko", c["code"]), c["pct"]) for c in countries])
    year_min = min(by_pri.keys()) if by_pri else 0
    year_max = max(by_pri.keys()) if by_pri else 0

    agg_data = {
        "topic": topic,
        "total_count": total,
        "date_range": f"우선일 {year_min}.01.01 ~ {year_max}.12.31",
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "table_priority_by_year": table_pri_str,
        "table_priority_data": table_pri_data,
        "table_publication_by_year": table_pub_str,
        "ascii_chart_priority": ascii_pri,
        "ascii_chart_applicants": ascii_app,
        "ascii_chart_country": ascii_cnt,
        "top_applicants": applicants,
        "countries": countries,
    }
    json_path = out_dir / "aggregate_report_data.json"
    json_path.write_text(json.dumps(agg_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ Aggregate data: {json_path}")
    return json_path


# ── Phase 4: Sub-tech analysis ────────────────────────────────────────────────

def run_sub_tech_analysis(
    rfp_md: Path, sub_tech: dict, csv_path: Path,
    out_subdir: Path, include_terms: list[str], exclude_terms: list[str],
    fetch_delay: float = 1.0, skip_fetch: bool = False, core_n: int = 5,
) -> Path:
    """Process one sub-technology: score → top 100 → abstracts → core 5."""
    _add_legacy_path()
    from score_title_relevance import run as score_title
    from score_abstract_relevance import run as score_abstract

    st_id = sub_tech["id"]
    st_include = list(set(include_terms + sub_tech.get("key_terms", [])))
    st_exclude = list(set(exclude_terms + sub_tech.get("exclude_terms", [])))

    out_subdir.mkdir(parents=True, exist_ok=True)

    # Step 6: Title score → top 100
    top100_path = out_subdir / "top100_title_scored.csv"
    score_title(
        str(csv_path), str(rfp_md), str(top100_path),
        top_n=100, include_terms=st_include, exclude_terms=st_exclude,
    )
    print(f"  [{st_id}] Title scored: top 100 → {top100_path.name}")

    # Step 7: Fetch abstracts + representative claims
    abstracts_path = out_subdir / "top100_with_abstracts.csv"
    resume_path = out_subdir / "abstracts_resume.json"

    if skip_fetch and abstracts_path.exists():
        print(f"  [{st_id}] Skipping fetch (--skip-fetch), using existing {abstracts_path.name}")
    else:
        ok = run_step(
            f"[{st_id}] Fetch abstracts",
            [_py(), SCRIPT_DIR / "fetch_abstracts.py" if (SCRIPT_DIR / "fetch_abstracts.py").exists()
             else LEGACY_SCRIPTS / "fetch_abstracts.py",
             str(top100_path), "-o", str(abstracts_path),
             "--delay", str(fetch_delay), "--resume", str(resume_path)],
        )
        if not ok:
            print(f"  [{st_id}] Fetch failed, continuing without abstracts.", file=sys.stderr)
            abstracts_path = top100_path  # fallback

    # Step 8: Abstract+claim score → core N
    scored_path = out_subdir / "top100_abstract_scored.csv"
    score_abstract(
        str(abstracts_path), str(rfp_md), str(scored_path),
        top_n=None, include_terms=st_include, exclude_terms=st_exclude,
    )

    # Select top core_n
    rows, _ = load_csv(scored_path)
    scored_sorted = sorted(rows, key=lambda r: float(r.get("relevance_score", 0)), reverse=True)
    core = scored_sorted[:core_n]

    core_path = out_subdir / f"core{core_n}_patents.csv"
    write_csv(core, core_path)
    print(f"  [{st_id}] Core {core_n} patents: {core_path.name}")
    return core_path


# ── Main entry point ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Patent Strategy Pro – Full Pipeline")
    ap.add_argument("--rfp", required=True, help="RFP file path (PDF or MD)")
    ap.add_argument("--main-csv", type=str, default=None, help="Main Google Patents CSV")
    ap.add_argument("--sub-tech-json", type=str, default=None, help="sub_techs.json path")
    ap.add_argument("--sub-tech-csvs", type=str, default=None,
                    help="Comma-separated CSV paths for each sub-tech (in order of sub_techs.json)")
    ap.add_argument("-o", "--output-dir", type=str, default="output", help="Output directory")
    ap.add_argument("--topic", type=str, default="특허", help="Report topic name (Korean slug)")
    ap.add_argument("--years", type=int, default=10, help="Search range in years")
    ap.add_argument("--include-terms", type=str, default=None, help="Global include terms (comma)")
    ap.add_argument("--exclude-terms", type=str, default=None, help="Global exclude terms (comma)")
    ap.add_argument("--skip-fetch", action="store_true", help="Skip abstract fetch if CSV exists")
    ap.add_argument("--fetch-delay", type=float, default=1.0, help="Delay between fetches (sec)")
    ap.add_argument("--core-n", type=int, default=5, help="Core patents per sub-tech (default 5)")
    ap.add_argument("--auto-download", action="store_true",
                    help="Auto-download CSVs via EPO OPS API (no manual Google Patents download needed). "
                         "Requires EPO_OPS_KEY and EPO_OPS_SECRET env vars.")
    ap.add_argument("--split-by-year", action="store_true",
                    help="Split EPO searches by year for queries with >2000 results")
    ap.add_argument("--global-required-terms", type=str, default=None,
                    help="Comma-separated required terms for sub-tech queries (AND gate)")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    include_terms = [t.strip() for t in (args.include_terms or "").split(",") if t.strip()]
    exclude_terms = [t.strip() for t in (args.exclude_terms or "").split(",") if t.strip()]
    global_required = [t.strip() for t in (args.global_required_terms or "").split(",") if t.strip()]

    # Phase 1: PDF → MD if needed
    rfp_path = Path(args.rfp)
    rfp_md = convert_pdf_if_needed(rfp_path, out_dir)
    print(f"\nRFP: {rfp_md}")

    # ── Auto-download via EPO OPS API ────────────────────────────────────
    if args.auto_download:
        print("\n" + "=" * 60)
        print("[Auto-Download] EPO OPS API mode")
        print("=" * 60)

        from search_patents_epo import create_client, search_main, search_sub_techs
        client = create_client()
        rfp_text = rfp_md.read_text(encoding="utf-8")

        # Download main CSV
        main_csv_path = out_dir / f"gp-search-{datetime.now().strftime('%Y%m%d')}_main.csv"
        print(f"\n[Main Query] Downloading via EPO OPS ...")
        search_main(
            client, rfp_text, main_csv_path,
            years=args.years,
            required_terms=include_terms or None,
            exclude_terms=exclude_terms or None,
            split_by_year=args.split_by_year,
        )
        args.main_csv = str(main_csv_path)

        # Download sub-tech CSVs
        if args.sub_tech_json:
            print(f"\n[Sub-tech Queries] Downloading via EPO OPS ...")
            csv_map = search_sub_techs(
                client,
                sub_techs_path=Path(args.sub_tech_json),
                rfp_text=rfp_text,
                output_dir=out_dir,
                years=args.years,
                global_required=global_required or include_terms or None,
                global_exclude=exclude_terms or None,
                split_by_year=args.split_by_year,
            )
            # Build comma-separated CSV paths in sub_techs order
            sub_data = json.loads(Path(args.sub_tech_json).read_text(encoding="utf-8"))
            sub_ids = [st["id"] for st in sub_data.get("sub_technologies", [])]
            csv_paths = [csv_map.get(sid, "") for sid in sub_ids]
            args.sub_tech_csvs = ",".join(csv_paths)
            print(f"\n✓ EPO OPS auto-download complete.")

        print("=" * 60)

    # Phase 3: Main CSV stats
    if args.main_csv:
        main_csv = Path(args.main_csv)
        if not main_csv.exists():
            print(f"Main CSV not found: {main_csv}", file=sys.stderr)
            sys.exit(1)
        agg_json = run_main_stats(rfp_md, main_csv, out_dir, include_terms, exclude_terms, args.topic)
        print(f"\n✓ Phase 3 complete. Aggregate data: {agg_json}")
    else:
        print("\n[Phase 3] Skipped (no --main-csv provided)")

    # Phase 4: Sub-tech analysis
    if args.sub_tech_json and args.sub_tech_csvs:
        sub_data = json.loads(Path(args.sub_tech_json).read_text(encoding="utf-8"))
        sub_techs = sub_data.get("sub_technologies", [])
        csv_paths = [Path(p.strip()) for p in args.sub_tech_csvs.split(",")]

        if len(csv_paths) != len(sub_techs):
            print(
                f"Warning: {len(csv_paths)} CSVs for {len(sub_techs)} sub-techs. "
                "Matching by order.", file=sys.stderr,
            )

        core_paths = []
        for i, (st, csv_path) in enumerate(zip(sub_techs, csv_paths)):
            if not csv_path.exists():
                print(f"  [{st['id']}] CSV not found: {csv_path} — skipping", file=sys.stderr)
                continue
            sub_out = out_dir / st["id"]
            core_path = run_sub_tech_analysis(
                rfp_md, st, csv_path, sub_out,
                include_terms, exclude_terms,
                fetch_delay=args.fetch_delay,
                skip_fetch=args.skip_fetch,
                core_n=args.core_n,
            )
            core_paths.append({"sub_tech": st, "core_csv": str(core_path)})

        # Save summary of core patent paths
        summary_path = out_dir / "sub_tech_core_summary.json"
        summary_path.write_text(json.dumps(core_paths, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✓ Phase 4 complete. Summary: {summary_path}")
        print("\nNext: Ask Claude to write §5~§8 of the report using the core patent CSVs.")

    elif args.sub_tech_json and not args.sub_tech_csvs:
        print("\n[Phase 4] sub_techs.json provided but no --sub-tech-csvs.")
        print("  Download CSVs for each sub-tech using the URLs in queries_sub_techs.md")
        print("  Then re-run with: --sub-tech-csvs sub1.csv,sub2.csv,...")

    else:
        print("\n[Phase 4] Skipped (no --sub-tech-json provided)")

    print(f"\nDone. Output directory: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
