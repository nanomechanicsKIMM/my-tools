#!/usr/bin/env python3
"""1:1 comparison of a reproduced figure against the published panel.

Usage:
  python pcr_compare.py --paper <panel.png> --ours <ours.npz|ours.png> \\
        --extent-x X0 X1 --extent-z Z0 Z1 [--lattice-x 4.0] [--lattice-z 10.0] \\
        [--out <folder>/output/compare] [--label mid]

This tool encodes four lessons that were each paid for in a real project:

  1. NEVER up-sample the reproduction onto the published display grid. A published panel is an
     ENLARGEMENT of a coarser reconstruction; up-sampling manufactures block artifacts that depress
     the correlation and make a decent match look like a failure. We resample the PUBLISHED panel
     DOWN to our native grid.
  2. Sparse point targets make fixed-alignment correlation all-or-nothing: an offset of one target
     width -> ~0; half a lattice period -> NEGATIVE. So we search the offset and report the
     correlation AT BEST ALIGNMENT, together with the offset.
  3. The shift search must be BOUNDED inside one lattice period, or it locks onto aliases (a real
     search once returned exactly half the row pitch as "optimal").
  4. If the optimum lands ON the search boundary, the search FAILED. We say so and refuse to quote
     the offset as a measurement.

Absolute level is meaningless (panels are self-normalised) -> a global offset is removed before
residuals, and that is stated.

Axis calibration is an INPUT here, not a guess: establish it from evidence first (see
references/compare.md) and pass it via --extent-*. A calibration that flips the conclusion cannot
carry the conclusion.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import font_manager


def korean_font():
    # name the installed family exactly; a wrong name silently falls back and renders tofu.
    # DejaVu trails it because Korean faces often lack U+2212 (minus) used by mathtext.
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Apple SD Gothic Neo", "AppleGothic", "Nanum Gothic", "Malgun Gothic"):
        if name in avail:
            plt.rcParams["font.family"] = [name, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_gray(p: Path) -> np.ndarray:
    g = mpimg.imread(str(p))
    if g.ndim == 3:
        g = g[..., :3].mean(axis=2)
    return g.astype(float)


def load_ours(p: Path, key: str | None):
    if p.suffix == ".npz":
        d = np.load(p)
        k = key or next(k for k in d.files if d[k].ndim == 2)
        return d[k].astype(float)
    return load_gray(p)


def to_db(img: np.ndarray, dr: float) -> np.ndarray:
    """Map a self-normalised 8-bit render to a dB scale. Gamma is UNKNOWN -> linear assumed."""
    v = img / img.max() if img.max() > 0 else img
    return (v - 1.0) * dr


def resample(src, x_src, z_src, x_q, z_q):
    from scipy.ndimage import map_coordinates
    zi = np.interp(z_q, z_src, np.arange(len(z_src)))
    xi = np.interp(x_q, x_src, np.arange(len(x_src)))
    ZI, XI = np.meshgrid(zi, xi, indexing="ij")
    out = map_coordinates(src, [ZI, XI], order=1, mode="constant", cval=np.nan)
    valid = ((z_q >= z_src.min()) & (z_q <= z_src.max()))[:, None] & \
            ((x_q >= x_src.min()) & (x_q <= x_src.max()))[None, :]
    return out, valid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--ours", required=True)
    ap.add_argument("--ours-key", default=None)
    ap.add_argument("--extent-x", nargs=2, type=float, required=True, metavar=("X0", "X1"))
    ap.add_argument("--extent-z", nargs=2, type=float, required=True, metavar=("Z0", "Z1"))
    ap.add_argument("--lattice-x", type=float, default=None,
                    help="lateral target period [mm]; bounds the shift search to +/- period/2")
    ap.add_argument("--lattice-z", type=float, default=None)
    ap.add_argument("--dr-db", type=float, default=40.0)
    ap.add_argument("--label", default="panel")
    ap.add_argument("--out", default="./compare")
    a = ap.parse_args()

    korean_font()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    pub = to_db(load_gray(Path(a.paper)), a.dr_db)
    ours = load_ours(Path(a.ours), a.ours_key)
    if ours.max() > 0.01:                 # already dB if <=0 everywhere
        ours = to_db(ours, a.dr_db) if ours.min() >= 0 else ours

    x_pub = np.linspace(a.extent_x[0], a.extent_x[1], pub.shape[1])
    z_pub = np.linspace(a.extent_z[0], a.extent_z[1], pub.shape[0])
    # OUR grid is the comparison grid (lesson 1: never invent resolution)
    x_q = np.linspace(a.extent_x[0], a.extent_x[1], ours.shape[1])
    z_q = np.linspace(a.extent_z[0], a.extent_z[1], ours.shape[0])

    def at(dx, dz):
        pb, vv = resample(pub, x_pub + dx, z_pub + dz, x_q, z_q)
        m = vv & np.isfinite(pb) & np.isfinite(ours)
        return pb, m

    p0, m0 = at(0.0, 0.0)
    corr0 = float(np.corrcoef(p0[m0], ours[m0])[0, 1])

    # lesson 3: bound the search inside one lattice period, else aliases win
    bx = (a.lattice_x / 2.0) if a.lattice_x else 2.0
    bz = (a.lattice_z / 2.0) if a.lattice_z else 2.0
    sx = np.arange(-bx, bx + 1e-9, max(bx / 12, 0.05))
    sz = np.arange(-bz, bz + 1e-9, max(bz / 12, 0.05))
    best = (-2.0, 0.0, 0.0)
    for dz in sz:
        for dx in sx:
            pb, m = at(dx, dz)
            if m.sum() < 0.5 * m0.sum():
                continue
            c = float(np.corrcoef(pb[m], ours[m])[0, 1])
            if c > best[0]:
                best = (c, dx, dz)
    corr, bdx, bdz = best
    on_edge = (abs(abs(bdx) - bx) < 1e-6) or (abs(abs(bdz) - bz) < 1e-6)   # lesson 4

    pb, m = at(bdx, bdz)
    off = float(np.mean(pb[m] - ours[m]))          # panels self-normalised -> absolute dB meaningless
    diff = (ours + off) - pb
    rms = float(np.sqrt(np.mean(diff[m] ** 2)))
    mae = float(np.mean(np.abs(diff[m])))

    # SIGN: at(dx,dz) places the paper's sample i at x_pub[i]+dx, i.e. it MOVES THE PAPER by +dx to
    # meet us. So the shift that aligns them IS (ours - paper). Reporting -bdx flips it.
    # Caught by the planted-shift instrument test (R5): planted +1.20/-0.70 came back -1.17/+0.83.
    # Without a planted answer this tool would have reported every offset backwards.
    res = {"label": a.label, "corr_at_best": corr, "corr_no_shift": corr0,
           "our_minus_paper_dx_mm": float(bdx), "our_minus_paper_dz_mm": float(bdz),
           "rms_db": rms, "mae_db": mae, "offset_db": off,
           "search_hit_boundary": bool(on_edge),
           "offset_is_measurement": (not on_edge),
           "note": ("SEARCH HIT BOUNDARY - the optimum is not resolved; do NOT quote the offset "
                    "as a measurement") if on_edge else "ok"}
    (out / f"compare_{a.label}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    ext = [x_q.min(), x_q.max(), z_q.max(), z_q.min()]
    fig, ax = plt.subplots(1, 3, figsize=(13, 5.2))
    for i, (im, ttl, kw) in enumerate((
            (np.where(m, pb, np.nan), "논문", dict(cmap="gray", vmin=-a.dr_db, vmax=0)),
            (np.where(m, ours + off, np.nan),
             f"재현 (최적정합 우리−논문 dx {bdx:+.2f}, dz {bdz:+.2f} mm)",
             dict(cmap="gray", vmin=-a.dr_db, vmax=0)),
            (np.where(m, diff, np.nan), f"차이  RMS {rms:.1f} dB · corr {corr:.3f}",
             dict(cmap="RdBu_r", vmin=-20, vmax=20)))):
        h = ax[i].imshow(im, extent=ext, aspect="equal", **kw)
        ax[i].set_title(ttl, fontsize=10)
        ax[i].set_xlabel("가로 [mm]"); ax[i].set_ylabel("깊이 [mm]")
        plt.colorbar(h, ax=ax[i], fraction=0.046, label="dB")
    fig.suptitle(f"1:1 대조 — {a.label}" + ("   ⚠ 탐색 경계 도달(정합 미해결)" if on_edge else ""),
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out / f"compare_{a.label}.png", dpi=130)
    plt.close(fig)

    print(f"{a.label}: corr@best {corr:.3f} (no-shift {corr0:+.3f})  "
          f"ours-paper dx {bdx:+.2f} dz {bdz:+.2f} mm  RMS {rms:.2f} dB")
    if on_edge:
        print("  ⚠ search hit the boundary — offset NOT a measurement (widen only within one period)")
    print(f"  -> {out}/compare_{a.label}.png")
    print("  ★ LOOK AT THE DIFFERENCE MAP. A summary number alone misleads in both directions (R6).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
