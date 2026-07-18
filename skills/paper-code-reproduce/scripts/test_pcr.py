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
  * status gate    -> pcr_status read `Impact: **HIGH**` as nothing (gate falsely OPEN) and the
                      re-grade `Impact: HIGH -> MED` as HIGH; the gate must FAIL CLOSED and read the
                      final grade. This tool guards the whole ledger gate and had NO test before.
  * test gate      -> guards against "13/13 pass" written from memory while the true state was 11/13:
                      pairing (untested module named), failure (nonzero run is RED), and freshness
                      (any file edited after the recorded run voids the pass claim).
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


def test_status_gate_fails_closed(tmp: Path) -> None:
    """R5 on the gate itself. The gate must FAIL CLOSED: it may never report OPEN on a HIGH unknown
    it could not parse, and it must read the ledger's own re-grade syntax (`HIGH → MED`) and its
    trailing-prose Status lines correctly. Every case below is a real formatting the ledger produces.
    """
    sys.path.insert(0, str(HERE))
    import importlib
    ps = importlib.import_module("pcr_status")

    def gate(entries: str) -> str:
        root = tmp / "gate"
        (root / ".pcr").mkdir(parents=True, exist_ok=True)
        (root / ".pcr" / "missing.md").write_text(entries, encoding="utf-8")
        (root / ".pcr" / "state.md").write_text("- current: X\n- status: Y\n- rounds used: 0/3\n")
        (root / ".pcr" / "targets.json").write_text(
            '{"t": {"value": 1, "tol": 0.1, "load_bearing": true}}')
        r = subprocess.run([PY, str(HERE / "pcr_status.py"), str(root)],
                           capture_output=True, text=True)
        return r.stdout

    # 1. a genuine HIGH + UNRESOLVED blocks
    check("gate: genuine HIGH+UNRESOLVED blocks",
          "BLOCKED" in gate("### M1 — x\n- **Impact**: HIGH\n- **Status**: UNRESOLVED\n"))
    # 2. the ledger's prescribed re-grade `HIGH → MED` reads as MED and does NOT block
    check("gate: `HIGH → MED` re-grade reads final grade, does not block",
          "OPEN" in gate("### M1 — x\n- **Impact**: HIGH → MED (re-graded on evidence)\n"
                         "- **Status**: UNRESOLVED, impact MED (verdict-invariant)\n"))
    # 3. FAIL CLOSED: emphasis makes impact unparseable → must be treated as HIGH and block
    #    (this is exactly source-project self-correction #6: `**HIGH**` → None → falsely OPEN)
    check("gate: unparseable impact fails closed (blocks), never silently OPEN",
          "BLOCKED" in gate("### M1 — x\n- **Impact**: **HIGH**\n- **Status**: UNRESOLVED\n"))
    # 4. a cleared item never blocks, even at HIGH impact
    check("gate: USER-SUPPLIED does not block",
          "OPEN" in gate("### M1 — x\n- **Impact**: HIGH\n- **Status**: USER-SUPPLIED[2026-01-01]\n"))
    check("gate: RESOLVED does not block",
          "OPEN" in gate("### M1 — x\n- **Impact**: HIGH\n- **Status**: RESOLVED[fig, measured]\n"))
    # 5. an unrecognised Status token is NOT cleared → a HIGH item with it still blocks (+ warns)
    out5 = gate("### M1 — x\n- **Impact**: HIGH\n- **Status**: UNRESOVLED (typo)\n")
    check("gate: unrecognised Status is not cleared → HIGH still blocks", "BLOCKED" in out5)
    # 6. dual-scope grade `LOW ... / HIGH (Fig.5)` — the gate is scoped to THIS run's target, so the
    #    FIRST (primary) grade wins; a secondary-scope HIGH on the same line must NOT block. This is
    #    the trap "final grade wins" would fall into — it is an arrow re-grade that means "final",
    #    a slash/scope split that means "primary". Only the arrow signals a re-grade.
    check("gate: dual-scope `LOW ... / HIGH (Fig.5)` reads primary LOW, does not block",
          "OPEN" in gate("### M1 — x\n- **Impact**: LOW for this target / **HIGH** for Fig. 5\n"
                         "- **Status**: UNRESOLVED\n"))
    # 7. a multi-step re-grade takes the newest grade after the last arrow
    check("gate: `HIGH -> MED -> LOW` reads final LOW, does not block",
          "OPEN" in gate("### M1 — x\n- **Impact**: HIGH -> MED -> LOW (twice re-graded)\n"
                         "- **Status**: UNRESOLVED\n"))


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


def test_testgate(tmp: Path) -> None:
    """R5 on the test gate itself: pairing, failure, and freshness must each go RED when planted."""
    import os

    root = tmp / "tg"
    (root / "code" / "src").mkdir(parents=True)
    (root / "code" / "tests").mkdir(parents=True)
    (root / "code" / "src" / "m.py").write_text("def f():\n    return 1\n")
    (root / "code" / "tests" / "test_m.py").write_text("# placeholder\n")
    ok_cmd = f'"{PY}" -c "import sys; sys.exit(0)"'
    bad_cmd = f'"{PY}" -c "import sys; sys.exit(3)"'

    def gate(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([PY, str(HERE / "pcr_testgate.py"), str(root), *extra],
                              capture_output=True, text=True)

    # 1. green run: paired + passing cmd + log recorded
    r = gate("--cmd", ok_cmd)
    check("testgate: paired + passing run is GREEN", r.returncode == 0 and "GREEN" in r.stdout)
    check("testgate: run is recorded", (root / ".pcr" / "test_log.json").exists())
    # 2. --check immediately after: fresh
    r = gate("--check")
    check("testgate: --check right after run is GREEN (fresh)", r.returncode == 0)
    # 3. edit a source file after the run -> the recorded pass is void
    st = (root / "code" / "src" / "m.py").stat()
    os.utime(root / "code" / "src" / "m.py", ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    r = gate("--check")
    check("testgate: edit after run makes --check STALE and RED",
          r.returncode == 1 and "STALE" in r.stdout and "m.py" in r.stdout)
    # 4. failing suite is RED
    r = gate("--cmd", bad_cmd)
    check("testgate: failing run is RED", r.returncode == 1 and "RED" in r.stdout)
    # 5. an unpaired module is named and blocks even with a passing suite
    (root / "code" / "src" / "orphan.py").write_text("X = 1\n")
    r = gate("--cmd", ok_cmd)
    check("testgate: unpaired module is named and blocks",
          r.returncode == 1 and "orphan" in r.stdout)
    # 6. no recorded run at all fails closed
    (root / ".pcr" / "test_log.json").unlink()
    r = gate("--check")
    check("testgate: missing log fails closed", r.returncode == 1)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_compare_recovers_planted_shift(tmp)
        test_compare_flags_boundary(tmp)
        test_lint(tmp)
        test_status_gate_fails_closed(tmp)
        test_extract_citation_contains_value(tmp)
        test_testgate(tmp)
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED: {', '.join(FAILED)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
