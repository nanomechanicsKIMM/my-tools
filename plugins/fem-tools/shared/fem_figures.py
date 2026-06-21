"""FEM 문제 설명 그림용 matplotlib 헬퍼.

규약:
- Geometry edge:  '#1f3a5f', lw=1.6
- Geometry fill:  '#eaf0f6'
- Supports:       '#333',    lw≈1.0
- Force loads:    '#c0392b', '-|>' 화살표
- Disp loads:     '#1f77b4'
- Dimensions:     '#666',    bbox 처리된 텍스트

모든 함수는 Axes에 patch/text를 추가만 한다. set_aspect('equal')은 setup_axes()가 처리.
"""

from __future__ import annotations
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle

# macOS 한글 폰트 — AppleGothic 또는 Apple SD Gothic Neo
matplotlib.rcParams["font.family"] = ["AppleGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 폰트 크기 (기본 10 대비 2.25x = 첫 ×1.5 + 2026-05-26 추가 ×1.5). 헬퍼 함수와 다이어그램 스크립트가 공유.
FS_LABEL = 23  # 일반 라벨·재료 정보·하중 라벨 (was 15)
FS_DIM = 21    # 치수선·키포인트 콜아웃 (was 14)
FS_TITLE = 23  # subplot 타이틀 (was 15)

matplotlib.rcParams["font.size"] = FS_LABEL
matplotlib.rcParams["axes.titlesize"] = FS_TITLE

GEOM_EDGE = "#1f3a5f"
GEOM_FILL = "#eaf0f6"
SUPPORT = "#333333"
LOAD = "#c0392b"
LOAD_DISP = "#1f77b4"
DIM = "#666666"


def make_fig(figsize=(7, 5)):
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    return fig, ax


def setup_axes(ax, xlim, ylim):
    ax.set_aspect("equal")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.axis("off")


def save_dual(fig, stem, dpi_png=200):
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    fig.savefig(f"{stem}.svg", bbox_inches="tight")
    fig.savefig(f"{stem}.png", bbox_inches="tight", dpi=dpi_png)


def fixed_wall(ax, p0, p1, hatch_side="left", n_hatch=12, hatch_len=None, lw=1.4):
    """p0→p1 을 따라 hatched wall. hatch_side ∈ {'left','right'} (진행방향 기준)."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    v = p1 - p0
    L = float(np.linalg.norm(v))
    if L == 0:
        return
    t = v / L
    if hatch_side == "left":
        n = np.array([-t[1], t[0]])
    else:
        n = np.array([t[1], -t[0]])
    if hatch_len is None:
        hatch_len = 0.05 * L
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=SUPPORT, lw=lw)
    for s in np.linspace(0.0, 1.0, n_hatch):
        a = p0 + s * v
        b = a + n * hatch_len + (-t) * hatch_len * 0.6
        ax.plot([a[0], b[0]], [a[1], b[1]], color=SUPPORT, lw=0.7)


def roller_strip(ax, p0, p1, n_out, size=None, n=10, lw=0.7):
    """p0→p1 변에 따라 roller(symmetry) BC. n_out: 도메인 바깥쪽 단위법선(자동 정규화)."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    v = p1 - p0
    L = float(np.linalg.norm(v))
    if L == 0:
        return
    t = v / L
    n_hat = np.asarray(n_out, float)
    n_hat = n_hat / np.linalg.norm(n_hat)
    if size is None:
        size = 0.025 * L
    # ground line outboard
    g0 = p0 + n_hat * size * 1.9
    g1 = p1 + n_hat * size * 1.9
    ax.plot([g0[0], g1[0]], [g0[1], g1[1]], color=SUPPORT, lw=0.9)
    # short hatches on ground
    n_hatch_total = max(n * 2, 8)
    for s in np.linspace(0, 1, n_hatch_total):
        a = p0 + s * v + n_hat * size * 1.9
        b = a + n_hat * size * 0.55 - t * size * 0.4
        ax.plot([a[0], b[0]], [a[1], b[1]], color=SUPPORT, lw=0.5)
    # triangles + small rollers along edge
    for i in range(1, n):
        pi = p0 + (i / n) * v
        apex = pi
        base1 = pi + n_hat * size - t * size * 0.45
        base2 = pi + n_hat * size + t * size * 0.45
        ax.add_patch(
            Polygon([apex, base1, base2], closed=True, fill=False, ec=SUPPORT, lw=lw)
        )
        cc = pi + n_hat * (size + size * 0.22)
        ax.add_patch(Circle(cc, size * 0.18, fill=False, ec=SUPPORT, lw=0.55))


def distributed_load(
    ax,
    p0,
    p1,
    direction,
    n_arrows=8,
    arrow_len=None,
    label=None,
    color=LOAD,
    label_offset=0.6,
    lw=1.1,
):
    """p0→p1 변에 분포 트랙션. 화살표 머리가 변에 닿고, 꼬리는 direction 반대편."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    d = np.asarray(direction, float)
    d_hat = d / np.linalg.norm(d)
    v = p1 - p0
    L = float(np.linalg.norm(v))
    if arrow_len is None:
        arrow_len = 0.10 * max(L, 1e-6)
    for i in range(n_arrows + 1):
        pe = p0 + (i / n_arrows) * v
        ps = pe - d_hat * arrow_len
        ax.annotate(
            "",
            xy=pe,
            xytext=ps,
            arrowprops=dict(
                arrowstyle="-|>", color=color, lw=lw, mutation_scale=10
            ),
        )
    bs0 = p0 - d_hat * arrow_len
    bs1 = p1 - d_hat * arrow_len
    ax.plot([bs0[0], bs1[0]], [bs0[1], bs1[1]], color=color, lw=0.9)
    if label:
        mid = (bs0 + bs1) / 2 - d_hat * arrow_len * label_offset
        ax.text(
            mid[0],
            mid[1],
            label,
            color=color,
            fontsize=FS_LABEL,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9),
        )


def point_load(ax, tip, direction, length=0.12, label=None, color=LOAD, lw=1.8):
    tip = np.asarray(tip, float)
    d = np.asarray(direction, float)
    d_hat = d / np.linalg.norm(d)
    start = tip - d_hat * length
    ax.annotate(
        "",
        xy=tip,
        xytext=start,
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=14),
    )
    if label:
        lp = start - d_hat * 0.02
        ax.text(
            lp[0],
            lp[1],
            label,
            color=color,
            fontsize=FS_LABEL,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9),
        )


def dimension(ax, p1, p2, offset, text, color=DIM, ext_line=True):
    """치수선. offset: p1→p2 진행방향 기준 perpendicular(부호 있음)."""
    p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float)
    v = p2 - p1
    L = float(np.linalg.norm(v))
    if L == 0:
        return
    t = v / L
    n = np.array([-t[1], t[0]])  # left-perp of p1→p2
    if offset < 0:
        n = -n
        off = -offset
    else:
        off = offset
    q1 = p1 + n * off
    q2 = p2 + n * off
    ax.annotate(
        "",
        xy=q2,
        xytext=q1,
        arrowprops=dict(arrowstyle="<|-|>", color=color, lw=0.7, mutation_scale=8),
    )
    if ext_line:
        ax.plot([p1[0], q1[0]], [p1[1], q1[1]], color=color, lw=0.5, ls=(0, (3, 2)))
        ax.plot([p2[0], q2[0]], [p2[1], q2[1]], color=color, lw=0.5, ls=(0, (3, 2)))
    mid = (q1 + q2) / 2
    ax.text(
        mid[0],
        mid[1],
        text,
        color=color,
        fontsize=FS_DIM,
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.95),
    )


def coord_axes(ax, origin=(0, 0), size=0.1, labels=("x", "y"), color="k"):
    ox, oy = origin
    ax.annotate(
        "",
        xy=(ox + size, oy),
        xytext=(ox, oy),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0, mutation_scale=10),
    )
    ax.annotate(
        "",
        xy=(ox, oy + size),
        xytext=(ox, oy),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0, mutation_scale=10),
    )
    ax.text(ox + size * 1.18, oy, labels[0], color=color, fontsize=FS_LABEL, va="center")
    ax.text(ox, oy + size * 1.18, labels[1], color=color, fontsize=FS_LABEL, ha="center")


def label_point(ax, xy, text, dx=0.02, dy=0.02, color="k", fontsize=FS_DIM, **kw):
    ax.plot(xy[0], xy[1], "o", color=color, ms=3.5)
    ax.text(xy[0] + dx, xy[1] + dy, text, fontsize=fontsize, color=color, **kw)


# ─────────────────────────────────────────────────────────────────────────────
# 3D cube cabinet projection (W2 단위 큐브 등에 사용)
# ─────────────────────────────────────────────────────────────────────────────


def cabinet_proj(point3d, alpha_deg=30.0, ratio=0.5):
    """3D → 2D 캐비넷 투영. z축이 +x,+y 사선 방향(angle α)으로 ratio만큼 단축."""
    x, y, z = point3d
    rad = np.radians(alpha_deg)
    return (x + z * ratio * np.cos(rad), y + z * ratio * np.sin(rad))


def cabinet_line(ax, p0_3d, p1_3d, alpha_deg=30.0, ratio=0.5, **plot_kw):
    p0 = cabinet_proj(p0_3d, alpha_deg, ratio)
    p1 = cabinet_proj(p1_3d, alpha_deg, ratio)
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], **plot_kw)


def cabinet_text(ax, p_3d, text, alpha_deg=30.0, ratio=0.5, **text_kw):
    p2d = cabinet_proj(p_3d, alpha_deg, ratio)
    ax.text(p2d[0], p2d[1], text, **text_kw)


def cabinet_arrow(
    ax,
    p0_3d,
    p1_3d,
    alpha_deg=30.0,
    ratio=0.5,
    color=LOAD,
    lw=2.0,
    mutation_scale=16,
    label=None,
    label_offset_2d=(0.0, 0.0),
    fontsize=None,
):
    p0 = cabinet_proj(p0_3d, alpha_deg, ratio)
    p1 = cabinet_proj(p1_3d, alpha_deg, ratio)
    ax.annotate(
        "",
        xy=p1,
        xytext=p0,
        arrowprops=dict(
            arrowstyle="-|>", color=color, lw=lw, mutation_scale=mutation_scale
        ),
    )
    if label:
        fs = fontsize if fontsize is not None else FS_LABEL
        ax.text(
            p1[0] + label_offset_2d[0],
            p1[1] + label_offset_2d[1],
            label,
            color=color,
            fontsize=fs,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9),
        )


def draw_cube(
    ax,
    p0=(0.0, 0.0, 0.0),
    p1=(1.0, 1.0, 1.0),
    alpha_deg=30.0,
    ratio=0.5,
    face_fills=None,
    edge_color=GEOM_EDGE,
    lw=1.6,
    hidden_dash=(0, (5, 3)),
):
    """캐비넷 투영으로 큐브 와이어프레임 그리기 (3개 hidden edge는 점선).

    뷰포인트: 정면(z=0)을 보고 z축이 우상단으로 빠지는 캐비넷 (α=30°, ratio=0.5).
    가시 면: z=0 (front), x=p1[0] (right), y=p1[1] (top).
    Hidden: z=p1[2] (back), x=p0[0] (left), y=p0[1] (bottom).

    face_fills: dict {'z-','z+','x-','x+','y-','y+': dict(...kwargs for Polygon)}
    Returns: V (vertex dict, key='ijk', value=(x_2d, y_2d)), V3 (3D dict)
    """
    proj = lambda p: cabinet_proj(p, alpha_deg, ratio)
    V3, V = {}, {}
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                key = f"{i}{j}{k}"
                v3 = (
                    p1[0] if i else p0[0],
                    p1[1] if j else p0[1],
                    p1[2] if k else p0[2],
                )
                V3[key] = v3
                V[key] = proj(v3)

    faces = {
        "z-": ["000", "100", "110", "010"],
        "z+": ["001", "011", "111", "101"],
        "x-": ["000", "010", "011", "001"],
        "x+": ["100", "101", "111", "110"],
        "y-": ["000", "001", "101", "100"],
        "y+": ["010", "110", "111", "011"],
    }
    if face_fills:
        # 뒤쪽(hidden) 먼저, 그 위에 앞쪽(visible) 채움
        order = ["x-", "y-", "z+", "z-", "x+", "y+"]
        for f in order:
            if f in face_fills:
                pts = [V[v] for v in faces[f]]
                ax.add_patch(Polygon(pts, closed=True, **face_fills[f]))

    edges = [
        ("000", "100"), ("100", "110"), ("110", "010"), ("010", "000"),
        ("001", "101"), ("101", "111"), ("111", "011"), ("011", "001"),
        ("000", "001"), ("100", "101"), ("110", "111"), ("010", "011"),
    ]
    hidden_edges = {
        frozenset({"001", "101"}),
        frozenset({"011", "001"}),
        frozenset({"000", "001"}),
    }
    for u, v in edges:
        if frozenset({u, v}) in hidden_edges:
            ax.plot(
                [V[u][0], V[v][0]],
                [V[u][1], V[v][1]],
                color=edge_color,
                lw=lw * 0.85,
                ls=hidden_dash,
            )
        else:
            ax.plot(
                [V[u][0], V[v][0]],
                [V[u][1], V[v][1]],
                color=edge_color,
                lw=lw,
            )
    return V, V3
