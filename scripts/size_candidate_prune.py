"""Size task #9: what does pruning the candidate pool cost in serviced buildings?

Why this lever is worth measuring at all. Decomposing the 'likely' day total from
measured constants:

    matrix build   1.66 h   scales with candidate count
    greedy argmax  1.72 h   scales with candidate count
    verification   1.64 h   scales with claims x k -- untouched by pruning
                   -----
                   5.01 h

**67% of the runtime is linear in candidate count.** The board framed #9 as a way
to shrink the matrix build; it is nearly twice that, because greedy's argmax is a
popcount pass over every one of the 157,454 rows on every one of the k iterations.

So the only open question is the quality cost, and that is measurable *without
rebuilding anything*: restrict greedy to a subset of the rows of the matrix we
already have, and compare serviced-building counts against the full pool.

RESULT, measured 2026-08-09 at 400 m / k=500 by this script:

    prune  candidates   tau=0.25  tau=0.50  tau=0.75   likely day
      1x      157,454    control   control   control      5.02 h
      2x       78,727     -0.0%     +0.0%     +0.0%      3.33 h
      4x       39,431     -2.0%     -3.0%     -6.6%      2.48 h
    7.2x       21,813     -4.0%     -7.5%    -14.9%      2.11 h

**Only 2x is free** -- one serviced building lost of 14,708. Degradation is
monotone, accelerating, and always worst at high tau. An earlier claim that an 8x
prune was viable is withdrawn: the honest lever is 1.69 h at zero quality cost.

Per-building stride saturates near 12.2x, because every building keeps its first
candidate. Beyond that a prune deletes whole buildings and their only legal
antenna positions.

CAVEAT ON THE TIMING COLUMN THIS SCRIPT PRINTS: ignore it. `marginal_gains`
computes gains for every row and the mask is applied afterwards, so every arm does
identical work -- the column measures contention, not pruning. The runtime case
rests on the structural argument (a genuinely smaller matrix has fewer rows to
popcount), which this script cannot demonstrate.

**A prune rule is only usable if it is computable before the matrix exists**,
since the whole point is to not build those rows. Both rules here are geometry-only:

* `stride-N` -- keep every Nth candidate within each building's own ordered list,
  so the survivors stay spread over the whole domain. Truncating the global list
  instead (what `max_candidates` does) would delete entire neighbourhoods.
* `vertex-only` -- keep only candidates copied verbatim from source vertices. This
  is a 2x prune with an independent argument behind it: #15 measured that 37.4% of
  midpoint candidates land microscopically *inside* their own footprint and need
  nudging on output, while vertices never do.

**Built-in control.** `stride-1` keeps everything, so it must reproduce
`greedy_select_matrix` exactly. The script asserts that before reporting anything
else -- the same discipline that made the lever A sweep trustworthy.

**Scoring caveat, same as the lever A sweep.** Serviced counts here come from the
`samples` grid the optimizer optimized on, so they are in-sample and optimistic.
Unlike that sweep the bias is *not* asymmetric between arms -- every arm runs the
same objective and differs only in which rows it may pick from -- so the ranking
across prune levels is far more trustworthy than the absolute numbers. Treat the
deltas as real and the levels as upper estimates.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from giscup.candidates import generate_boundary_candidates
from giscup.io import load_buildings
from giscup.matrix import build_visibility_matrix
from giscup.optimize import greedy_select_matrix
from giscup.sampling import get_profile, sample_boundaries


def keep_mask(candidates, rule: str, n_candidates: int) -> np.ndarray:
    """Boolean mask over candidate rows. Geometry only -- no visibility consulted."""
    keep = np.zeros(n_candidates, dtype=bool)
    if rule == "vertex-only":
        for i, c in enumerate(candidates):
            keep[i] = c.kind == "vertex"
        return keep

    stride = int(rule.split("-")[1])
    seen: dict[object, int] = {}
    for i, c in enumerate(candidates):
        rank = seen.get(c.source_building_id, 0)
        seen[c.source_building_id] = rank + 1
        keep[i] = (rank % stride) == 0
    return keep


def greedy_restricted(matrix, candidates, k: int, keep: np.ndarray):
    """`greedy_select_matrix` with rows outside `keep` disqualified.

    Replicates that function's loop exactly -- same `marginal_gains`, same
    `add_to_covered`, same argmax tie-breaking -- with one extra mask line, so a
    difference in the result can only come from the restricted pool.
    """
    covered = matrix.empty_covered()
    taken = np.zeros(matrix.n_candidates, dtype=bool)
    blocked = ~keep
    selected = []
    for _ in range(k):
        gains = matrix.marginal_gains(covered)
        gains[taken] = -1
        gains[blocked] = -1
        best = int(np.argmax(gains))
        if gains[best] < 0:
            raise RuntimeError("restricted greedy ran out of candidates")
        taken[best] = True
        matrix.add_to_covered(covered, best)
        selected.append(candidates[best])
    return selected, set(matrix.covered_sample_ids(covered).tolist())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/GIS-cup-sample-dataset.geojson")
    ap.add_argument("--radius", type=float, default=400.0)
    ap.add_argument("--cache-dir", default="outputs/cache")
    ap.add_argument("--k", type=int, default=500)
    ap.add_argument("--taus", type=float, nargs="+", default=[0.25, 0.5, 0.75])
    ap.add_argument(
        "--rules", nargs="+",
        default=["stride-1", "vertex-only", "stride-2", "stride-4", "stride-8"],
    )
    args = ap.parse_args(argv)

    buildings, _ = load_buildings(args.input)
    samples = sample_boundaries(buildings, get_profile("balanced"))
    candidates = generate_boundary_candidates(buildings, mode="basic", candidate_spacing=25.0)
    matrix = build_visibility_matrix(
        buildings, candidates, samples, radius=args.radius, cache_dir=args.cache_dir
    )
    print(f"candidates={len(candidates):,}  samples={len(samples):,}  "
          f"pairs={matrix.nonzeros():,}  k={args.k}\n", flush=True)

    index = {b.id: i for i, b in enumerate(buildings)}
    owner = np.fromiter((index[s.building_id] for s in samples), dtype=np.int64, count=len(samples))
    weight = np.fromiter((s.weight for s in samples), dtype=np.float64, count=len(samples))
    perim = np.array([b.perimeter for b in buildings], dtype=np.float64)

    def serviced(visible: set[int], tau: float) -> int:
        ids = np.fromiter(visible, dtype=np.int64, count=len(visible))
        got = np.bincount(owner[ids], weights=weight[ids], minlength=len(buildings))
        return int((got >= perim * tau).sum())

    # --- control: the unrestricted production path -------------------------
    t0 = time.perf_counter()
    _, ref_visible = greedy_select_matrix(
        matrix, candidates, samples, buildings, tau=0.5, k=args.k
    )
    ref_seconds = time.perf_counter() - t0
    ref = {tau: serviced(ref_visible, tau) for tau in args.taus}
    print(f"control  greedy_select_matrix  [{ref_seconds/60:.1f} min]  "
          + "  ".join(f"tau={t}: {ref[t]:,}" for t in args.taus) + "\n", flush=True)

    header = (f"{'rule':>12} {'kept':>9} {'prune':>6} {'greedy':>8} {'speedup':>8}  "
              + "  ".join(f"{'tau='+str(t):>16}" for t in args.taus))
    print(header)
    print("-" * len(header))

    for rule in args.rules:
        keep = keep_mask(candidates, rule, matrix.n_candidates)
        n_kept = int(keep.sum())
        if n_kept < args.k:
            print(f"{rule:>12} {n_kept:9,}  SKIPPED -- fewer candidates than k")
            continue
        t0 = time.perf_counter()
        _, vis = greedy_restricted(matrix, candidates, args.k, keep)
        secs = time.perf_counter() - t0

        cells = []
        for tau in args.taus:
            got = serviced(vis, tau)
            delta = got - ref[tau]
            pct = 100.0 * delta / ref[tau] if ref[tau] else float("nan")
            cells.append(f"{got:7,} {pct:+6.1f}%")
        print(f"{rule:>12} {n_kept:9,} {len(candidates)/n_kept:5.1f}x "
              f"{secs/60:7.1f}m {ref_seconds/secs:7.2f}x  " + "  ".join(cells), flush=True)

        if rule == "stride-1":
            same = vis == ref_visible
            print(f"{'':>12} CONTROL: restricted greedy at stride-1 reproduces the "
                  f"production path: {'YES' if same else 'NO -- EVERY NUMBER BELOW IS VOID'}",
                  flush=True)
            if not same:
                return 1

    print()
    print("!" * 78)
    print("Serviced counts are IN-SAMPLE (the grid greedy optimized on), so all")
    print("levels are upper estimates. The comparison BETWEEN levels is sound --")
    print("every arm runs the same objective and differs only in the row subset.")
    print("Before adopting any prune, re-measure the winner with a real nine-block")
    print("solve, which decides claims off an independent grid and verifies exactly.")
    print("!" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
