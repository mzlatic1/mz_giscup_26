"""Task #20 -- how much visibility lives BELOW the settled 400 m cull.

The radius axis has only ever been explored upward: 500 m modelled, 600 m built,
800 m attempted and abandoned, 1600 m modelled. Downward is unmeasured, and it is
the direction that buys the thing feasibility actually needs, which is time.

**This is the cheap falsification step, not the answer.** It costs seconds and exists
to confirm or kill the interpolated estimates for 300 m (~2,100 neighbours/candidate,
~84% capture) before anyone spends ~43 min building a matrix on them. If the probe
disagrees with the interpolation, stop there.

Method, and the two traps it avoids
-----------------------------------
1. **Built-in control.** It measures 400 m too, and checks itself against the visible
   density of the 400 m matrix **actually on disk** (52.0 samples per candidate). If
   the probe cannot reproduce a matrix that exists, its 300 m number means nothing.
   Same discipline as the sizing script's `stride-1` arm.

   Note that this control deliberately does *not* use the board's 3b probe table,
   which says 62.0 for the same quantity. Running this script is what exposed that
   disagreement: it reproduces the matrix to +2% and the old probe column to −15%.
   The matrix is every candidate; the old probe was 40 of them.
2. **Warm the erosion index before measuring.** `BlockerIndex.eroded` is computed
   lazily, so the first loop over it absorbs the one-time erosion of 12,860
   footprints. That defect made a previous radius sweep read 1,245 checks/s at 400 m
   against 500 m's 16,717 -- throughput apparently *rising* with radius -- and
   inflated every estimate derived from it.

Capture is reported RELATIVE to 400 m rather than absolutely, because the absolute
figure needs a 1600 m reference that costs ~50 min to probe. The board's 400 m
capture (91.1% of the 1600 m ceiling) is reused to convert.

    python scripts/probe_small_radii.py --input data/GIS-cup-sample-dataset.geojson
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from giscup.candidates import generate_boundary_candidates  # noqa: E402
from giscup.io import load_buildings  # noqa: E402
from giscup.sampling import get_profile, sample_boundaries  # noqa: E402
from giscup.visibility import BlockerIndex, is_visible  # noqa: E402

#: The board's measured capture at 400 m, as a fraction of the 1600 m ceiling. A
#: systematic bias in the probe cancels in this ratio -- both terms come from the same
#: run -- so it survives the correction below.
CAPTURE_AT_400 = 0.911

#: Control value: visible samples per candidate at 400 m, **taken from the BUILT
#: MATRIX, not from the board's 3b probe table**.
#:
#: The board carries two different numbers for this quantity and they disagree by 19%:
#: the 3b probe table says 62.0, while the 400 m matrix actually on disk holds
#: 8,194,226 visible pairs over 157,454 candidates = 52.0. The matrix is ground truth
#: -- it is every candidate, not 40 sampled ones -- so it is the control here.
#:
#: This probe reproduces the matrix (53.0 vs 52.0, +2%) and not the old probe column,
#: which is evidence the 3b probe figures run ~15% high. Neighbour counts agree with
#: the board to within 1.4% at both radii, so the discrepancy is confined to the
#: visibility column, not the geometry.
MATRIX_VISIBLE_PER_CANDIDATE_400 = 52.0
BOARD = {400: MATRIX_VISIBLE_PER_CANDIDATE_400}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--radii", type=float, nargs="+", default=[200, 300, 400])
    ap.add_argument("--probes", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20260809)
    ap.add_argument("--sampling-profile", default="balanced")
    args = ap.parse_args()

    t0 = time.perf_counter()
    buildings, info = load_buildings(args.input)
    samples = sample_boundaries(buildings, get_profile(args.sampling_profile))
    candidates = generate_boundary_candidates(buildings)
    sample_xy = np.array([[s.x, s.y] for s in samples], dtype=np.float64)
    tree = cKDTree(sample_xy)
    index = BlockerIndex.from_buildings(buildings)

    print(f"dataset    : {info.path}")
    print(f"CRS        : {info.crs}")
    print(f"buildings  : {len(buildings):,}   samples: {len(samples):,}   "
          f"candidates: {len(candidates):,}")
    print(f"setup      : {time.perf_counter() - t0:.1f} s")

    # Warm the lazily-eroded geometry BEFORE any measurement. See module docstring.
    warm = time.perf_counter()
    _ = index.eroded
    print(f"erosion warm-up (excluded from all figures below): "
          f"{time.perf_counter() - warm:.1f} s\n")

    rng = random.Random(args.seed)
    probes = rng.sample(range(len(candidates)), k=min(args.probes, len(candidates)))

    print(f"{'radius':>8} {'neigh/cand':>12} {'visible/cand':>13} "
          f"{'vs 400 m':>10} {'capture':>9} {'probe cost':>11}")
    print("-" * 70)

    results: dict[float, tuple[float, float]] = {}
    for radius in sorted(args.radii):
        t = time.perf_counter()
        neighbours = 0
        visible = 0
        for ci in probes:
            c = candidates[ci]
            idx = tree.query_ball_point([c.x, c.y], r=radius)
            neighbours += len(idx)
            for si in idx:
                if is_visible(c.point, (sample_xy[si, 0], sample_xy[si, 1]), index):
                    visible += 1
        n_per = neighbours / len(probes)
        v_per = visible / len(probes)
        results[radius] = (n_per, v_per)
        print(f"{radius:>7,.0f}m {n_per:>12,.0f} {v_per:>13,.1f} "
              f"{'—':>10} {'—':>9} {time.perf_counter() - t:>10,.1f}s")

    print("-" * 70)
    if 400 not in results and 400.0 not in results:
        print("no 400 m arm -- cannot express capture without the control. Stopping.")
        return 1

    v400 = results[400.0][1]
    print("\nAgainst the 400 m control:\n")
    print(f"{'radius':>8} {'neigh/cand':>12} {'visible/cand':>13} "
          f"{'vs 400 m':>10} {'capture':>9} {'matrix':>9}")
    print("-" * 70)
    for radius, (n_per, v_per) in sorted(results.items()):
        ratio = v_per / v400 if v400 else float("nan")
        capture = CAPTURE_AT_400 * ratio
        board = BOARD.get(int(radius))
        shown = f"{board:.1f}" if board else "—"
        print(f"{radius:>7,.0f}m {n_per:>12,.0f} {v_per:>13,.1f} "
              f"{ratio:>9.1%} {capture:>8.1%} {shown:>9}")
    print("-" * 70)

    print("\nCONTROL CHECK -- the probe must reproduce the board before its new")
    print("number means anything:")
    ok = True
    for radius, board in BOARD.items():
        if float(radius) in results:
            got = results[float(radius)][1]
            drift = abs(got - board) / board
            verdict = "OK" if drift <= 0.10 else "DRIFTED"
            ok &= drift <= 0.10
            print(f"  {radius:>4} m: matrix {board:.1f}  probe {got:.1f}  "
                  f"({drift:+.1%})  {verdict}")
    if not ok:
        print("\n  A control drifted more than 10%. Treat the new radius as UNMEASURED")
        print("  and find out why before building anything on it.")
        return 1
    print("\n  Controls hold. The new radius figure is usable for a build decision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
