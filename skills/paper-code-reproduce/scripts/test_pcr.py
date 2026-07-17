#!/usr/bin/env python3
"""Self-tests for the paper-code-reproduce toolchain.

Usage:  python test_pcr.py            (from anywhere; uses a temp workspace)

The skill tells you not to trust an instrument until it recovers a planted answer (R5). That applies
to the skill's OWN tools first. Every test here exists because the real bug it guards was found by
running it:

  * planted-shift  -> pcr_compare reported every offset with the SIGN FLIPPED
  * citation       -> pcr_extract quoted the start of a two-column line, so the citation pointed at
                      text that did not contain the number (fake provenance)
  * linter         -> must catch untagged constants and must NOT flag tagged/benign ones
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpi

HERE = Path(__file__).resolve().parent
PY = sys.executable
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILED.append(name)


def scene(x, z, dx, dz):
    img = np.zeros((len(z), len(x)))
    for zc in np.arange(20, 91, 10):                 # 10 mm rows
        for xc in np.arange(-24, 25, 4):             # 4 mm columns
            img += np.exp(-(((x[None, :] - xc - dx) / 0.6) ** 2 +
                            ((z[:, None] - zc - dz) / 0.6) ** 2))
    return np.clip(img, 0, 1)


def test_compare_recovers_planted_shift(tmp: Path) -> None:
    """R5: plant a known offset; the tool must recover it in SIGN and magnitude."""
    x = np.linspace(-30, 30, 401)
    z = np.linspace(10, 100, 601)
    TRUE_DX, TRUE_DZ = 1.2, -0.7
    mpi.imsave(tmp / "paper.png", scene(x, z, 0, 0), cmap="gray", vmin=0, vmax=1)
    np.savez(tmp / "ours.npz", img=20 * np.log10(np.maximum(scene(x, z, TRUE_DX, TRUE_DZ), 1e-4)))

    subprocess.run([PY, str(HERE / "pcr_compare.py"), "--paper", str(tmp / "paper.png"),
                    "--ours", str(tmp / "ours.npz"), "--ours-key", "img",
                    "--extent-x", "-30", "30", "--extent-z", "10", "100",
                    "--lattice-x", "4.0", "--lattice-z", "10.0",
                    "--label", "t", "--out", str(tmp / "cmp")],
                   capture_output=True, check=True)
    r = json.loads((tmp / "cmp" / "compare_t.json").read_text())
    dx, dz = r["our_minus_paper_dx_mm"], r["our_minus_paper_dz_mm"]
    # tolerance = the search step (bx/12, bz/12) plus a little
    check("compare: recovers planted dx (sign+magnitude)", abs(dx - TRUE_DX) < 0.25,
          f"planted {TRUE_DX:+.2f}, got {dx:+.2f}")
    check("compare: recovers planted dz (sign+magnitude)", abs(dz - TRUE_DZ) < 0.55,
          f"planted {TRUE_DZ:+.2f}, got {dz:+.2f}")
    check("compare: aligned beats unaligned", r["corr_at_best"] > r["corr_no_shift"],
          f"{r['corr_at_best']:.3f} > {r['corr_no_shift']:.3f}")


def test_compare_flags_boundary(tmp: Path) -> None:
    """An optimum on the search edge is a FAILED search, and must be reported as one."""
    x = np.linspace(-30, 30, 201)
    z = np.linspace(10, 100, 301)
    mpi.imsave(tmp / "p2.png", scene(x, z, 0, 0), cmap="gray", vmin=0, vmax=1)
    np.savez(tmp / "o2.npz", img=20 * np.log10(np.maximum(scene(x, z, 6.0, 0), 1e-4)))
    subprocess.run([PY, str(HERE / "pcr_compare.py"), "--paper", str(tmp / "p2.png"),
                    "--ours", str(tmp / "o2.npz"), "--ours-key", "img",
                    "--extent-x", "-30", "30", "--extent-z", "10", "100",
                    "--lattice-x", "1.0", "--lattice-z", "1.0",     # deliberately too tight
                    "--label", "t2", "--out", str(tmp / "cmp")],
                   capture_output=True, check=True)
    r = json.loads((tmp / "cmp" / "compare_t2.json").read_text())
    check("compare: boundary hit is flagged, offset not a measurement",
          r["search_hit_boundary"] and not r["offset_is_measurement"])


def test_lint(tmp: Path) -> None:
    root = tmp / "ws"
    (root / "code" / "src").mkdir(parents=True)
    (root / ".pcr").mkdir(parents=True)
    (root / ".pcr" / "missing.md").write_text("### M001 — thing\n- **Status**: UNRESOLVED\n")
    (root / "code" / "src" / "m.py").write_text(
        'A = 2800.0   # @src{paper:p.3}\n'
        'B = 15.98    # @missing{M001}\n'
        'C = 1.0      # benign\n'
        'D = 64       # untagged -> must be caught\n'
        'E = 7.5      # @missing{M999}  -> undeclared id, must be caught\n')
    r = subprocess.run([PY, str(HERE / "pcr_lint.py"), str(root)], capture_output=True, text=True)
    out = r.stdout
    check("lint: catches untagged constant", "D:" in out and r.returncode == 1)
    check("lint: catches undeclared @missing id", "M999" in out)
    check("lint: does not flag @src / @missing / benign",
          "A:" not in out and "B:" not in out and "C:" not in out)


def test_extract_citation_contains_value(tmp: Path) -> None:
    """A citation that does not contain its own number is fake provenance."""
    sys.path.insert(0, str(HERE))
    from pcr_extract import draft_targets
    # two-column layout: the number sits far past the start of the line
    page = ("left column text continues here and wraps oddly" + " " * 40 +
            "the CR improved by 37.1 dB in the corrected image")
    d = draft_targets([page])
    ok = bool(d) and all(v["raw"] in v["src"] for v in d.values())
    check("extract: every citation contains its own raw token", ok,
          f"{len(d)} candidate(s)")
    # and the guard against the rounded-value trap: `raw` is the verbatim token, not str(value)
    if d:
        v = next(iter(d.values()))
        check("extract: keeps verbatim `raw` for verification (not str(value))",
              "raw" in v and isinstance(v["raw"], str))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_compare_recovers_planted_shift(tmp)
        test_compare_flags_boundary(tmp)
        test_lint(tmp)
        test_extract_citation_contains_value(tmp)
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED: {', '.join(FAILED)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
