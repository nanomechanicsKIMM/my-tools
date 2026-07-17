"""SVG → PNG with full Korean glyph coverage.

For HWPX embedding (convert_hwpx.py consumes these PNGs).

Architecture — 4 defensive layers:
  1. Block cairocffi import → rlPyCairo falls back to pycairo (Windows libcairo-2.dll
     is not present; pycairo statically bundles Cairo and works).
  2. Register Malgun Gothic (primary, Korean+Latin 99%) and Arial Unicode MS
     (fallback, 100% BMP) with reportlab.
  3. Pre-substitute SVG file content for the small set of glyphs Malgun lacks
     (cosmetic preference). Three glyphs identified in real patent SVGs:
        '↳' → '→',   '−' (math minus) → '-' (hyphen).   '≈' is preserved.
  4. Walk svg2rlg() output Drawing tree; for each String, choose the font that
     covers all its codepoints (Malgun primary, ArialUnicode fallback).

Usage:
    python svg2png.py --src FIGURES_DIR --dst OUTPUT_DIR [--dpi 200]

Requires:
    pip install svglib reportlab pycairo rlPyCairo Pillow fonttools
"""
import argparse, glob, io, os, re, sys, tempfile

# ── 1) Block cairocffi BEFORE importing reportlab/svglib ────────────
sys.modules['cairocffi'] = None

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import String
from svglib.svglib import svg2rlg
from fontTools.ttLib import TTFont as FontInspector

# ── 2) Font registration (Windows/macOS/Linux 후보 중 첫 존재 경로) ──
def _first_existing(*candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


FONTS = [
    ("MalgunGothic", _first_existing(
        r"C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        os.path.expanduser("~/Library/Fonts/NanumGothic.ttf"),
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    )),
    ("MalgunGothic-Bold", _first_existing(
        r"C:/Windows/Fonts/malgunbd.ttf",
        os.path.expanduser("~/Library/Fonts/NanumGothicBold.ttf"),
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    )),
    ("ArialUnicode", _first_existing(
        r"C:/Windows/Fonts/ARIALUNI.TTF",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    )),
]


def _load_cmap(path):
    try:
        return set(FontInspector(path).getBestCmap().keys())
    except Exception:
        return set()


REGISTERED = {}
CMAPS = {}
for name, path in FONTS:
    if path and os.path.exists(path):
        pdfmetrics.registerFont(TTFont(name, path))
        REGISTERED[name] = path
        CMAPS[name] = _load_cmap(path)

if "MalgunGothic" not in REGISTERED:
    sys.exit("ERROR: 한글 폰트를 찾지 못했습니다 (malgun.ttf / AppleGothic.ttf / NanumGothic.ttf)")


# ── 3) Pre-substitution map (Malgun-friendly cosmetic substitutes) ──
GLYPH_REPLACE = {
    '↳': '→',     # right-hooked arrow → plain right arrow
    '−': '-',     # U+2212 math minus → ASCII hyphen-minus
    # '≈' (U+2248) preserved — handled by ArialUnicode fallback
}


def patch_svg_text(svg_text):
    """Force font-family to MalgunGothic + cosmetic glyph substitutions."""
    svg_text = re.sub(r'font-family\s*=\s*"[^"]*"', 'font-family="MalgunGothic"', svg_text)
    svg_text = re.sub(r"font-family\s*:\s*[^;\"']+", "font-family:MalgunGothic", svg_text)
    if '<svg' in svg_text and 'font-family' not in svg_text.split('>', 1)[0]:
        svg_text = re.sub(
            r'<svg\b([^>]*?)>',
            lambda m: '<svg' + m.group(1) + ' font-family="MalgunGothic">',
            svg_text, count=1
        )
    for old, new in GLYPH_REPLACE.items():
        svg_text = svg_text.replace(old, new)
    return svg_text


# ── 4) Drawing tree walker — String fontName override ───────────────
def _select_font(text, weight=False):
    if not text:
        return "MalgunGothic"
    primary = ("MalgunGothic-Bold"
               if (weight and "MalgunGothic-Bold" in REGISTERED)
               else "MalgunGothic")
    primary_cmap = CMAPS.get(primary, set())
    if all(ord(c) in primary_cmap for c in text if c.strip()):
        return primary
    if "ArialUnicode" in REGISTERED and all(
        ord(c) in CMAPS["ArialUnicode"] for c in text if c.strip()
    ):
        return "ArialUnicode"
    return primary


def _force_font(node):
    if isinstance(node, String):
        orig = (node.fontName or "").lower()
        is_bold = ("bold" in orig) or any(w in orig for w in ("700", "800", "900"))
        node.fontName = _select_font(node.text or "", weight=is_bold)
    if hasattr(node, "contents"):
        for child in node.contents:
            _force_font(child)


def convert_one(src, dst, dpi=200):
    with open(src, encoding="utf-8") as f:
        svg_text = f.read()
    svg_text = patch_svg_text(svg_text)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False, encoding="utf-8") as tf:
        tf.write(svg_text)
        tmp = tf.name
    try:
        drawing = svg2rlg(tmp)
        _force_font(drawing)
        renderPM.drawToFile(drawing, dst, fmt="PNG", dpi=dpi)
        return os.path.getsize(dst)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Korean-safe SVG → PNG converter")
    ap.add_argument("--src", required=True, help="Source directory containing fig*.svg")
    ap.add_argument("--dst", required=True, help="Output directory for PNG files")
    ap.add_argument("--pattern", default="fig*.svg", help="Glob pattern (default: fig*.svg)")
    ap.add_argument("--dpi", type=int, default=200, help="Output DPI (default: 200)")
    args = ap.parse_args()

    print(f"Registered fonts: {list(REGISTERED.keys())}")
    print(f"renderPM backend: {renderPM._pmBackend.__name__ if renderPM._pmBackend else 'NONE'}")
    os.makedirs(args.dst, exist_ok=True)

    svgs = sorted(glob.glob(os.path.join(args.src, args.pattern)))
    print(f"\nConverting {len(svgs)} SVG files...")
    for src in svgs:
        name = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(args.dst, name + ".png")
        try:
            sz = convert_one(src, dst, args.dpi)
            print(f"  OK   {name}.png  ({sz//1024} KB)")
        except Exception as e:
            print(f"  ERR  {name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
