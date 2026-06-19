# -*- coding: utf-8 -*-
"""
Shared style tokens for the VR/AR display paper figures.

Centralizes three things that were previously duplicated/hardcoded across the
make_figN_nature.py scripts:
  1. Pretendard font registration (journal-grade Korean+Latin face)
  2. global rcParams (vector-embed safe: pdf.fonttype=42, svg.fonttype=none)
  3. the colour palette (Okabe-Ito colourblind-safe) and a semantic
     font-size scale, bumped ~+2.5 pt over the original Nature sizing for
     better print legibility (still journal-appropriate, not poster-sized).

Usage in each figure script:
    import figstyle as fs
    ...
    ax.text(..., fontsize=fs.FS_BULLET, color=fs.INK)
"""
import os
import glob
import matplotlib as mpl
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_HERE, "fonts")


def register_fonts():
    """Register bundled Pretendard weights with matplotlib's font manager."""
    for p in glob.glob(os.path.join(_FONT_DIR, "Pretendard-*.otf")):
        try:
            fm.fontManager.addfont(p)
        except Exception:
            pass


register_fonts()

# --------------------------------------------------------------- rcParams
mpl.rcParams.update({
    "font.family": "Pretendard",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,          # embed as subsetted TrueType/Type42 (editable, print-safe)
    "svg.fonttype": "none",      # keep SVG text as text (editable in Inkscape/Illustrator)
    "font.size": 9.0,            # base, bumped from 6.5
    "mathtext.fontset": "dejavusans",   # digits/superscripts for $10^5$ etc.
    # data-plot text auto-bumps these (when scripts don't hardcode fontsize)
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.0,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "legend.fontsize": 8.0,
    "legend.title_fontsize": 8.5,
    "figure.titlesize": 11.0,
})

# ------------------------------------------------------------ colour tokens
# Okabe-Ito colourblind-safe palette + project accents
BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#E69F00"
VERMIL = "#D55E00"
GREEN = "#009E73"
GRAY = "#7F7F7F"
INK = "#1A1A1A"
NAVY = "#1F3A5F"
# RGB sub-pixel accents (R/G/B emitters)
R_ = "#E45756"
G_ = "#59A14F"
B_ = "#4E79A7"

# -------------------------------------------------------- font-size scale
# Semantic sizes, ~+2.5 pt over the original Nature sizing.
# (original value -> new value)
FS_TITLE = 10.5     # panel letters a/b/c/d            (8.0  -> 10.5)
FS_HEADING = 9.0    # panel names                      (6.5  -> 9.0)
FS_BANNER = 7.5     # top requirements banner          (6.0  -> 7.5, kept tight to fit one line)
FS_VERDICT = 7.5    # verdict pills                    (5.2  -> 7.5)
FS_CHIP = 7.5       # R/G/B chip text                  (5.0  -> 7.5)
FS_LAYER = 7.3      # layer rectangle labels (default) (4.8  -> 7.3)
FS_BULLET = 7.0     # bullet lists (longest text)      (4.7  -> 7.0)
FS_LAYER_SM = 6.9   # thin layer labels                (4.4  -> 6.9)
FS_NOTE = 6.9       # italic in-figure notes           (4.4  -> 6.9)

MM = 1 / 25.4

# ------------------------------------------------------------ output helper
# Migrated figures are written here as 600 dpi PNG only (no PDF/SVG/preview).
OUT_DIR = os.path.join(_HERE, "figures_v2")
os.makedirs(OUT_DIR, exist_ok=True)


def save_png(fig, name, dpi=600):
    """Save a figure as <name>_600dpi.png into the migration output folder."""
    path = os.path.join(OUT_DIR, name + "_600dpi.png")
    fig.savefig(path, dpi=dpi)
    print("saved:", path)
    return path
