# -*- coding: utf-8 -*-
"""patent_svg 출력 계층 — FigureSpec 동반 저장, PNG 미리보기, use-평탄화 유틸.

기존 변환기(svg2png.py, svg2emf.py, outline_svg_text.py)는 용도별 후단으로 그대로 사용.
"""
import json
import os
import re
import xml.etree.ElementTree as ET


def save(drawing, name, spec, outdir, ledger=None, png=True, png_scale=2.0):
    """SVG + FigureSpec(JSON, 재현성) + (선택) PNG 미리보기 저장."""
    os.makedirs(outdir, exist_ok=True)
    svg_path = os.path.join(outdir, f"{name}.svg")
    drawing.save_svg(svg_path)
    meta = dict(spec=spec, ledger=(ledger.export() if ledger else None))
    with open(os.path.join(outdir, f"{name}_spec.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    if png:
        try:
            import cairosvg
            cairosvg.svg2png(url=svg_path,
                             write_to=os.path.join(outdir, f"{name}.png"),
                             scale=png_scale)
        except Exception as ex:
            print(f"[exporters] PNG 미리보기 생략: {ex}")
    return svg_path


_USE = "{http://www.w3.org/2000/svg}use"
_DEFS = "{http://www.w3.org/2000/svg}defs"
_XLINK = "{http://www.w3.org/1999/xlink}href"


def flatten_use(svg_in, svg_out=None):
    """matplotlib SVG의 <defs>+<use> 글리프 참조를 인라인 path로 평탄화.

    PowerPoint 도형 변환의 use 미지원(텍스트 소실) 대응 — Gotcha 2026-07-31.
    반환: 평탄화한 use 개수."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(svg_in)
    root = tree.getroot()
    defs_map = {}
    for d in root.iter(_DEFS):
        for el in list(d):
            i = el.get("id")
            if i:
                defs_map[i] = el
    parents = {c: p for p in root.iter() for c in p}
    n = 0
    for use in list(root.iter(_USE)):
        ref = (use.get(_XLINK) or use.get("href") or "").lstrip("#")
        tgt = defs_map.get(ref)
        if tgt is None:
            continue
        import copy
        clone = copy.deepcopy(tgt)
        clone.attrib.pop("id", None)
        tx = [use.get("x"), use.get("y")]
        tr = use.get("transform", "")
        if tx[0] or tx[1]:
            tr = f"{tr} translate({tx[0] or 0},{tx[1] or 0})".strip()
        if tr:
            old = clone.get("transform", "")
            clone.set("transform", f"{tr} {old}".strip())
        for k, v in use.attrib.items():
            if k not in ("x", "y", "href", _XLINK, "transform") and k not in clone.attrib:
                clone.set(k, v)
        p = parents.get(use)
        if p is not None:
            p.insert(list(p).index(use), clone)
            p.remove(use)
            n += 1
    tree.write(svg_out or svg_in, encoding="unicode", xml_declaration=True)
    return n


def check_no_use(svg_path):
    return len(re.findall(r"<use[\s>]", open(svg_path, encoding="utf-8").read()))
