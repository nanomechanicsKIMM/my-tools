# -*- coding: utf-8 -*-
"""patent_svg 특허 primitive — drawsvg 요소 생성. class 속성으로 QA 대상을 표식한다.

class 규약: 'primitive'(구조 선), 'beam'(광선 다발), 'leader'(지시선), 'labeltext'.
"""
import drawsvg as dw
from . import geometry as G


def _pts(frame, world_pts):
    out = []
    for (x, y) in world_pts:
        out.extend(frame.pt(x, y))
    return out


def polyline(frame, world_pts, style, width=None, dashed=False, cls="primitive",
             close=False, fill="none"):
    kw = dict(stroke=style["stroke"], fill=fill,
              stroke_width=width or style["stroke_primary"], class_=cls)
    if dashed:
        kw["stroke_dasharray"] = style["stroke_dashed"]
    return dw.Lines(*_pts(frame, world_pts), close=close, **kw)


def arc(frame, r_mm, th0, th1, style, width=None, cls="primitive", n=96,
        cx=0.0, cy=0.0, dashed=False):
    return polyline(frame, G.arc_points(r_mm, th0, th1, n, cx, cy), style,
                    width=width, dashed=dashed, cls=cls)


def circle(frame, cxy_mm, r_mm, style, width=None, cls="primitive", fill="none"):
    x, y = frame.pt(*cxy_mm)
    return dw.Circle(x, y, frame.d(r_mm), stroke=style["stroke"], fill=fill,
                     stroke_width=width or style["stroke_primary"], class_=cls)


def beam(frame, src_xy, aim_xy, src_w_mm, waist_w_mm, style, frac=1.0):
    pts = G.beam_polygon(src_xy, aim_xy, src_w_mm, waist_w_mm, frac)
    return dw.Lines(*_pts(frame, pts), close=True, fill=style["beam_fill"],
                    fill_opacity=style["beam_opacity"], stroke=style["stroke"],
                    stroke_width=style["stroke_secondary"] * 0.7, class_="beam")


def cell_ticks(frame, cells, size_mm, style, highlight_idx=(), cls="primitive"):
    """패널 호 위 셀 표식(법선 방향 정렬 사각 틱). highlight는 굵은 선."""
    import math
    out = []
    for i, ((x, y), th) in enumerate(cells):
        t = math.radians(th)
        nx, ny = math.cos(t), math.sin(t)           # 법선(중심 방향)
        ux, uy = -ny, nx
        h = size_mm / 2
        p = [(x + ux * h, y + uy * h), (x - ux * h, y - uy * h)]
        w = style["stroke_primary"] * (2.4 if i in highlight_idx else 1.0)
        out.append(polyline(frame, p, style, width=w, cls=cls))
    return out


def eye_schematic(frame, eye, style):
    """축소 모형안 개요: 안구 원(동공부 개방) + 망막 호 강조 + 수정체 타원."""
    import math
    cx, cy = eye["center"]
    r, td, ph = eye["r"], eye["toward_deg"], eye["pupil_half_deg"]
    els = [arc(frame, r, td + ph, td + 360 - ph, style, n=120, cx=cx, cy=cy),
           arc(frame, r * 0.985, eye["retina"][0], eye["retina"][1], style,
               width=style["stroke_primary"] * 1.8, n=96, cx=cx, cy=cy)]
    # 수정체(동공 뒤 타원)
    lx, ly = G.polar(r * 0.72, td, cx, cy)
    px_, py_ = frame.pt(lx, ly)
    e = dw.Ellipse(px_, py_, frame.d(r * 0.16), frame.d(r * 0.34),
                   stroke=style["stroke"], fill="none",
                   stroke_width=style["stroke_secondary"], class_="primitive")
    e.args["transform"] = f"rotate({-td},{px_},{py_})"
    els.append(e)
    return els


def focal_plane_mark(frame, x_mm, y0_mm, y1_mm, style):
    """가상 초점면 표시(파선 세로선)."""
    return polyline(frame, [(x_mm, y0_mm), (x_mm, y1_mm)], style,
                    width=style["stroke_secondary"], dashed=True, cls="primitive")


def rect(frame, x_mm, y_mm, w_mm, h_mm, style, width=None, cls="primitive",
         fill="none", hatch=False, dashed=False):
    """세계 좌표 (x, y) 좌하단 기준 사각형. hatch=True면 사선 해칭(특허 단면 관례)."""
    import drawsvg as dw
    px, py = frame.pt(x_mm, y_mm + h_mm)
    w, h = frame.d(w_mm), frame.d(h_mm)
    kw = dict(stroke=style["stroke"], fill=fill,
              stroke_width=width or style["stroke_secondary"], class_=cls)
    if dashed:
        kw["stroke_dasharray"] = style["stroke_dashed"]
    els = [dw.Rectangle(px, py, w, h, **kw)]
    if hatch:
        step = max(6.0, h / 4)
        x0 = px - h
        while x0 < px + w:
            xa, ya, xb, yb = x0, py + h, x0 + h, py
            xa2, xb2 = max(xa, px), min(xb, px + w)
            if xa2 < xb2:
                ya2 = py + h - (xa2 - xa)
                yb2 = py + h - (xb2 - xa)
                els.append(dw.Line(xa2, ya2, xb2, yb2, stroke=style["stroke"],
                                   stroke_width=0.6, class_=cls))
            x0 += step
    return els


def arrow(frame, p0_mm, p1_mm, style, width=None, cls="primitive", double=False):
    """화살표(머리는 path 삼각형 — marker 미사용으로 변환기 호환성 확보)."""
    import drawsvg as dw
    import math
    x0, y0 = frame.pt(*p0_mm)
    x1, y1 = frame.pt(*p1_mm)
    w = width or style["stroke_secondary"]
    th = math.atan2(y1 - y0, x1 - x0)
    hl, hw = 9.0 + 2 * w, 4.0 + w

    def head(x, y, t):
        return dw.Lines(x, y, x - hl * math.cos(t) + hw * math.sin(t),
                        y - hl * math.sin(t) - hw * math.cos(t),
                        x - hl * math.cos(t) - hw * math.sin(t),
                        y - hl * math.sin(t) + hw * math.cos(t),
                        close=True, fill=style["stroke"], class_=cls)
    els = [dw.Line(x0, y0, x1, y1, stroke=style["stroke"], stroke_width=w,
                   class_=cls), head(x1, y1, th)]
    if double:
        els.append(head(x0, y0, th + math.pi))
    return els


def wavefront_arcs(frame, center_mm, radii_mm, half_deg, toward_deg, style, n=48):
    """파면(등위상면) 호 다발 — 곡률 중심에서 반경들, toward 방향 ±half_deg."""
    return [arc(frame, r, toward_deg - half_deg, toward_deg + half_deg, style,
                width=style["stroke_secondary"], cls="primitive", n=n,
                cx=center_mm[0], cy=center_mm[1], dashed=True)
            for r in radii_mm]
