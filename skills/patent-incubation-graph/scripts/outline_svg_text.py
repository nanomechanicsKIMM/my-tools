"""SVG <text> → <path> outliner using fontTools.

For PowerPoint "Convert to Shape" workflow: PowerPoint strips Korean text
during SVG → DrawingML conversion regardless of font-family specification.
This script pre-converts every <text> element into Bezier path outlines
extracted from Malgun Gothic (or Bold/Arial Unicode MS for missing glyphs),
making the SVG fully self-contained — no font lookup needed at conversion time.

Trade-off: text becomes shape geometry (no longer typeable / font-changeable).

Usage:
    python outline_svg_text.py --src FIGURES_DIR --dst FIGURES_PPTX_DIR

Requires:
    pip install fonttools
"""
import argparse, glob, io, os, re, sys, xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

def _first_existing(*candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


FONT_REG = _first_existing(
    r"C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    os.path.expanduser("~/Library/Fonts/NanumGothic.ttf"),
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
)
FONT_BOLD = _first_existing(
    r"C:/Windows/Fonts/malgunbd.ttf",
    os.path.expanduser("~/Library/Fonts/NanumGothicBold.ttf"),
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
)
FONT_FALLBACK = _first_existing(
    r"C:/Windows/Fonts/ARIALUNI.TTF",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)

if FONT_REG is None:
    sys.exit("ERROR: 한글 폰트를 찾지 못했습니다 (malgun.ttf / AppleGothic.ttf / NanumGothic.ttf)")

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


class FontShop:
    def __init__(self, regular_path, bold_path=None, fallback_path=None):
        self.regular = self._load(regular_path)
        self.bold = self._load(bold_path) if bold_path and os.path.exists(bold_path) else None
        self.fallback = self._load(fallback_path) if fallback_path and os.path.exists(fallback_path) else None

    @staticmethod
    def _load(path):
        font = TTFont(path)
        return {
            "font": font,
            "cmap": font.getBestCmap(),
            "glyph_set": font.getGlyphSet(),
            "upem": font['head'].unitsPerEm,
            "hmtx": font['hmtx'].metrics,
        }

    def font_for(self, codepoint, weight="normal"):
        primary = (self.bold
                   if (weight in ("bold", "700", "800", "900") and self.bold)
                   else self.regular)
        if codepoint in primary["cmap"]:
            return primary
        if primary is self.bold and codepoint in self.regular["cmap"]:
            return self.regular
        if self.fallback and codepoint in self.fallback["cmap"]:
            return self.fallback
        return primary


def text_to_path_group(shop, text, x, y, font_size, fill, anchor, weight):
    if not text:
        return [], 0.0
    glyph_data = []
    total_width = 0.0
    for ch in text:
        font_info = shop.font_for(ord(ch), weight)
        gname = font_info["cmap"].get(ord(ch))
        if not gname:
            continue
        scale = font_size / font_info["upem"]
        glyph = font_info["glyph_set"][gname]
        pen = SVGPathPen(font_info["glyph_set"])
        glyph.draw(pen)
        d = pen.getCommands()
        adv_units = font_info["hmtx"].get(gname, (0, 0))[0]
        adv_user = adv_units * scale
        glyph_data.append((d, total_width, scale))
        total_width += adv_user

    if anchor == "middle":
        x -= total_width / 2.0
    elif anchor == "end":
        x -= total_width

    paths = []
    for d, offset_x, scale in glyph_data:
        tx = x + offset_x
        ty = y
        # Glyph outlines are bottom-up; SVG is top-down → scale(s, -s) flips Y.
        transform = f"translate({tx:.3f},{ty:.3f}) scale({scale:.6f},{-scale:.6f})"
        paths.append({"d": d, "transform": transform, "fill": fill})
    return paths, total_width


def get_attr_with_inheritance(elem, name, parent_map, default=None):
    cur = elem
    while cur is not None:
        v = cur.get(name)
        if v is not None:
            return v
        cur = parent_map.get(cur)
    return default


def parse_pixel(v, default=12.0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    m = re.match(r"^(-?\d+\.?\d*)", s)
    return float(m.group(1)) if m else default


def parse_style(style_str):
    if not style_str:
        return {}
    out = {}
    for chunk in style_str.split(";"):
        if ":" in chunk:
            k, v = chunk.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def process_svg(shop, src_path, dst_path):
    tree = ET.parse(src_path)
    root = tree.getroot()
    parent_map = {child: parent for parent in root.iter() for child in parent}

    text_tag = f"{{{SVG_NS}}}text"
    tspan_tag = f"{{{SVG_NS}}}tspan"
    converted = 0

    for t in list(root.iter(text_tag)):
        content = (t.text or "")
        for child in t:
            if child.tag == tspan_tag and child.text:
                content += child.text
            if child.tail:
                content += child.tail
        content = content.strip()
        if not content:
            parent = parent_map.get(t)
            if parent is not None:
                parent.remove(t)
            continue

        style_dict = parse_style(t.get("style"))

        def attr(name, default=None):
            return (style_dict.get(name)
                    or t.get(name)
                    or get_attr_with_inheritance(t, name, parent_map, default))

        x = parse_pixel(attr("x", "0"))
        y = parse_pixel(attr("y", "0"))
        font_size = parse_pixel(attr("font-size", "12"))
        font_weight = (attr("font-weight", "normal") or "normal").lower()
        fill = attr("fill", "#000")
        text_anchor = attr("text-anchor", "start")

        paths, _ = text_to_path_group(
            shop, content, x, y, font_size, fill, text_anchor, font_weight
        )
        if not paths:
            parent = parent_map.get(t)
            if parent is not None:
                parent.remove(t)
            continue

        new_g = ET.Element(f"{{{SVG_NS}}}g")
        for p in paths:
            path_elem = ET.SubElement(new_g, f"{{{SVG_NS}}}path")
            path_elem.set("d", p["d"])
            path_elem.set("transform", p["transform"])
            path_elem.set("fill", p["fill"])

        parent = parent_map.get(t)
        if parent is None:
            continue
        idx = list(parent).index(t)
        parent.remove(t)
        parent.insert(idx, new_g)
        converted += 1

    # Drop any stale <defs><style>@font-face declarations from prior runs
    for defs in root.findall(f".//{{{SVG_NS}}}defs"):
        for style_el in defs.findall(f"{{{SVG_NS}}}style"):
            txt = style_el.text or ""
            if "@font-face" in txt or "font-family" in txt:
                defs.remove(style_el)

    tree.write(dst_path, encoding="utf-8", xml_declaration=True)
    return converted


def main():
    ap = argparse.ArgumentParser(description="Outline SVG <text> into <path> glyphs")
    ap.add_argument("--src", required=True, help="Source SVG directory")
    ap.add_argument("--dst", required=True, help="Output directory for outlined SVG")
    ap.add_argument("--pattern", default="fig*.svg", help="Glob pattern")
    args = ap.parse_args()

    print("Loading fonts...")
    shop = FontShop(FONT_REG, FONT_BOLD, FONT_FALLBACK)
    print(f"  regular  : {FONT_REG} ({len(shop.regular['cmap'])} glyphs)")
    if shop.bold:
        print(f"  bold     : {FONT_BOLD} ({len(shop.bold['cmap'])} glyphs)")
    if shop.fallback:
        print(f"  fallback : {FONT_FALLBACK} ({len(shop.fallback['cmap'])} glyphs)")

    os.makedirs(args.dst, exist_ok=True)
    svgs = sorted(glob.glob(os.path.join(args.src, args.pattern)))
    print(f"\nOutlining {len(svgs)} SVG files...")
    for src in svgs:
        name = os.path.basename(src)
        dst = os.path.join(args.dst, name)
        try:
            n = process_svg(shop, src, dst)
            sz = os.path.getsize(dst)
            print(f"  OK   {name}: {n} <text> → <path> groups ({sz//1024} KB)")
        except Exception as e:
            print(f"  ERR  {name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
