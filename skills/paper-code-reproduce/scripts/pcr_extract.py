#!/usr/bin/env python3
"""Extract text, high-resolution figures, and a targets.json draft from the paper PDF.

Usage:  python pcr_extract.py <paper-folder> [--dpi 600]

Figures are rendered at >=600 dpi for vector pages, or taken at NATIVE size when the page embeds a
bitmap. Never up-sampled: a comparison must not invent resolution it does not have.

Backends (first available): PyMuPDF (fitz) -> poppler (pdftotext/pdftoppm).
Emits:
  .pcr/paper_text.md        full text with <!--p.N--> anchors (citation targets)
  .pcr/paper_figs/*.png     page renders (crop panels later; record boxes in panels.json)
  .pcr/targets.json         DRAFT — every number found near result-ish language. REVIEW REQUIRED.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Numbers the paper reports as results are the strongest oracle: exact, unrendered, untunable.
# In the source project a logged value matching a reported one to 5 s.f. is what PROVED which run
# produced the figure — an inference no pixel comparison could make.
CLAIM = re.compile(
    r"(?P<val>-?\d+\.\d+|\d+)\s*(?P<unit>%|-fold|fold|dB|mm|um|µm|MHz|kHz|m/s|iterations?)?",
    re.I)
CUE = re.compile(r"\b(reach|reaching|achiev|improv|increas|decreas|was|were|of|to|by|"
                 r"mean|average|FWHM|SSIM|SNR|CNR|error|accuracy|ratio|gain|fold)\b", re.I)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def extract_fitz(pdf: Path, figs: Path, dpi: int):
    import fitz  # PyMuPDF
    doc = fitz.open(pdf)
    pages = []
    for i, page in enumerate(doc, 1):
        pages.append(page.get_text())
        # native bitmap if the page is essentially one image -> take it unresampled
        imgs = page.get_images(full=True)
        if len(imgs) == 1:
            xref = imgs[0][0]
            d = doc.extract_image(xref)
            (figs / f"p{i:03d}_native.{d['ext']}").write_bytes(d["image"])
        else:
            page.get_pixmap(dpi=dpi).save(figs / f"p{i:03d}_r{dpi}.png")
    return pages


def extract_poppler(pdf: Path, figs: Path, dpi: int):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(figs / "p")], check=False)
    return txt.split("\f")


def draft_targets(pages: list[str]) -> dict:
    """Draft candidate targets, each quoted with the text AROUND its own match.

    The quote MUST contain the number. Quoting the start of the line instead produces a citation that
    points at text not containing the value — two-column PDFs put the columns side by side on one
    line, so the number often sits past column 110. A wrong citation is worse than none: this whole
    skill rests on provenance being true.
    """
    out, n = {}, 0
    for pno, text in enumerate(pages, 1):
        for line in text.splitlines():
            for m in CLAIM.finditer(line):
                val, unit = m.group("val"), m.group("unit")
                if "." not in val and not unit:
                    continue                       # bare integers are usually not results
                # context is a window centred on THIS match, and the cue must be near it
                lo, hi = max(0, m.start() - 70), min(len(line), m.end() + 70)
                ctx = line[lo:hi].strip()
                if not CUE.search(ctx):
                    continue
                try:
                    v = float(val)
                except ValueError:
                    continue
                n += 1
                out[f"T{n:03d}"] = {
                    "value": v,
                    # `raw` is the VERBATIM token as printed in the paper. Keep it: verifying a
                    # value by its formatted repr is the rounded-value trap (R7) — float 36.0
                    # renders "36.0" while the paper says "36", and a search then "proves" the
                    # citation is fake when it is not. Verify with `raw`, never with str(value).
                    "raw": val,
                    "unit": unit or "", "tol": None,
                    "src": f'p.{pno} "…{ctx}…"',
                    "load_bearing": None,          # you decide
                    "kind": "unknown",
                }
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 600
    pdfs = sorted(root.glob("*.pdf"))
    if not pdfs:
        print("no PDF; run pcr_init.py first")
        return 2
    pdf = pdfs[0]
    figs = root / ".pcr" / "paper_figs"
    figs.mkdir(parents=True, exist_ok=True)

    try:
        import fitz  # noqa: F401
        pages = extract_fitz(pdf, figs, dpi)
        backend = "PyMuPDF"
    except ImportError:
        if not (have("pdftotext") and have("pdftoppm")):
            print("need PyMuPDF (pip install pymupdf) or poppler (pdftotext/pdftoppm)")
            return 2
        pages = extract_poppler(pdf, figs, dpi)
        backend = "poppler"

    md = [f"<!-- extracted from {pdf.name} via {backend} -->\n"]
    for i, t in enumerate(pages, 1):
        md.append(f"\n<!--p.{i}-->\n{t}")
    (root / ".pcr" / "paper_text.md").write_text("".join(md), encoding="utf-8")

    tgt_path = root / ".pcr" / "targets.json"
    existing = json.loads(tgt_path.read_text()) if tgt_path.exists() and tgt_path.stat().st_size > 2 else {}
    if existing:
        print(f"! targets.json already has {len(existing)} entries — draft written to targets_draft.json")
        tgt_path = root / ".pcr" / "targets_draft.json"
    draft = draft_targets(pages)
    tgt_path.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    n_fig = len(list(figs.iterdir()))
    print(f"backend      : {backend}")
    print(f"pages        : {len(pages)}")
    print(f"figures      : {n_fig} -> .pcr/paper_figs/  ({dpi} dpi or native)")
    print(f"targets draft: {len(draft)} candidates -> {tgt_path.name}")
    print("\n★ NEXT — this draft is not the oracle yet:")
    print("  1. keep only real reported results; delete the noise")
    print("  2. set `tol` from the paper's own precision, and `load_bearing`")
    print("  3. FREEZE. widening a tolerance later to pass is metric fitting (R2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
