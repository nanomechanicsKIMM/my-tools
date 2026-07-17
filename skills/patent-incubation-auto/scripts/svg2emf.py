"""SVG → EMF via Inkscape CLI for PowerPoint metafile import.

PowerPoint can import EMF as vector graphics; ungrouping gives access to
individual shape objects (paths, rects). NOTE: Inkscape's EMF backend ALWAYS
converts Korean text to Bezier paths for CJK glyph compatibility — text is
visually preserved but NOT editable as text in PowerPoint. For full text
fidelity preservation in PowerPoint Convert-to-Shape, prefer outline_svg_text.py.

Usage:
    python svg2emf.py --src FIGURES_DIR --dst FIGURES_DIR

Requires Inkscape 1.x installed (typically `winget install --id Inkscape.Inkscape`).
"""
import argparse, glob, io, os, re, shutil, subprocess, sys, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INKSCAPE_PATHS = [
    r"C:/Program Files/Inkscape/bin/inkscape.exe",
    r"C:/Program Files/Inkscape/bin/inkscape.com",
    r"C:/Program Files (x86)/Inkscape/bin/inkscape.exe",
    r"C:/Users/JHKIM/AppData/Local/Programs/Inkscape/bin/inkscape.exe",
    "/Applications/Inkscape.app/Contents/MacOS/inkscape",
    "/opt/homebrew/bin/inkscape",
    "/usr/bin/inkscape",
]

# 플랫폼별 한글 지원 기본 폰트 (Inkscape가 이름으로 해석)
DEFAULT_KO_FONT = ("Malgun Gothic" if sys.platform.startswith("win")
                   else "AppleGothic" if sys.platform == "darwin"
                   else "NanumGothic")


def find_inkscape():
    p = shutil.which("inkscape")
    if p:
        return p
    for cand in INKSCAPE_PATHS:
        if os.path.exists(cand):
            return cand
    return None


def patch_svg_fonts(svg_text, font=DEFAULT_KO_FONT):
    """Force font-family so Inkscape resolves to a Korean-capable font."""
    svg_text = re.sub(r'font-family\s*=\s*"[^"]*"', f'font-family="{font}"', svg_text)
    svg_text = re.sub(r"font-family\s*:\s*[^;\"']+", f"font-family:{font}", svg_text)
    if not re.search(r'<svg\b[^>]*font-family', svg_text):
        svg_text = re.sub(
            r'<svg\b([^>]*?)>',
            lambda m: '<svg' + m.group(1) + f' font-family="{font}">',
            svg_text, count=1
        )
    svg_text = re.sub(
        r'<text\b(?![^>]*\bfont-family\b)',
        f'<text font-family="{font}"',
        svg_text
    )
    return svg_text


def convert_one(inkscape_exe, src_svg, dst_emf):
    with open(src_svg, encoding='utf-8') as f:
        svg_text = f.read()
    svg_text = patch_svg_fonts(svg_text)
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.svg', delete=False, encoding='utf-8'
    ) as tf:
        tf.write(svg_text)
        tmp_path = tf.name
    try:
        result = subprocess.run(
            [inkscape_exe, tmp_path,
             "--export-type=emf",
             f"--export-filename={dst_emf}"],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120
        )
        if result.returncode != 0 or not os.path.exists(dst_emf):
            return False, (result.stderr or result.stdout or "unknown")[:300]
        return True, f"{os.path.getsize(dst_emf)//1024} KB"
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="SVG → EMF via Inkscape")
    ap.add_argument("--src", required=True, help="Source SVG directory")
    ap.add_argument("--dst", default=None, help="Output EMF directory (default: same as --src)")
    ap.add_argument("--pattern", default="fig*.svg", help="Glob pattern")
    args = ap.parse_args()

    inkscape = find_inkscape()
    if not inkscape:
        print("ERROR: Inkscape not found.")
        print("Install:  winget install --id Inkscape.Inkscape")
        sys.exit(1)
    print(f"Using Inkscape: {inkscape}")

    dst_dir = args.dst or args.src
    os.makedirs(dst_dir, exist_ok=True)

    svgs = sorted(glob.glob(os.path.join(args.src, args.pattern)))
    print(f"Converting {len(svgs)} files to EMF...")
    for src in svgs:
        name = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(dst_dir, name + ".emf")
        ok, info = convert_one(inkscape, src, dst)
        print(f"  {'OK  ' if ok else 'FAIL'} {name}.emf  ({info})")


if __name__ == "__main__":
    main()
