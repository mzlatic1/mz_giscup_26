#!/usr/bin/env python
"""Size two untried objective levers BEFORE building either (task board #6).

Rule 2 of the competition posture: state a lever's best-case range and compare it to
the distance you need to cover. ROGII was lost partly to three sessions spent tuning a
knob whose entire range was 1/16 of the gap.

The first #6 attempt (mask out serviced buildings) was built, measured, and rejected:
+6.4% at tau=0.25/k=500, -1.1% at tau=0.75/k=500. Two ideas remain:

  A. Weight buildings NEAR tau -- spend marginal coverage where it can flip a building,
     rather than spreading it over buildings that will never reach tau anyway.
  B. Cap WITHIN a building -- stop paying for coverage above tau*perimeter on a building
     that is already serviced, i.e. the exact capped objective
     sum_b min(visible_weight_b, tau * perimeter_b).

Both reallocate the same scarce resource: covered boundary weight. So both are bounded
by the same quantity -- how much weight is currently spent where it cannot buy a
building -- and by how cheaply near-miss buildings can be flipped with it.

This measures both, exactly, from the real matrix. It does not implement either lever.

One greedy run answers everything: the baseline objective ignores tau, and greedy is a
prefix order, so the first 50 and 500 picks of a k=1000 run ARE the k=50 and k=500
solutions.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.candidates import generate_boundary_candidates  # noqa: E402
from giscup.io import load_buildings  # noqa: E402
from giscup.matrix import build_visibility_matrix  # noqa: E402
from giscup.sampling import get_profile, sample_boundaries  # noqa: E402

TAUS = (0.25, 0.5, 0.75)
KS = (50, 500, 1000)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/GIS-cup-sample-dataset.geojson")
    ap.add_argument("--radius", type=float, default=400.0)
    ap.add_argument("--cache-dir", default="outputs/cache")
    ap.add_argument("--max-k", type=int, default=1000)
    args = ap.parse_args(argv)

    buildings, _ = load_buildings(args.input)
    profile = get_profile("balanced")
    samples = sample_boundaries(buildings, profile)
    candidates = generate_boundary_candidates(buildings, mode="basic", candidate_spacing=25.0)
    matrix = build_visibility_matrix(
        buildings, candidates, samples, radius=args.radius, cache_dir=args.cache_dir
    )
    print(f"buildings={len(buildings):,}  candidates={len(candidates):,}  "
          f"samples={len(samples):,}  pairs={matrix.nonzeros():,}\n", flush=True)

    index = {b.id: i for i, b in enumerate(buildings)}
    owner = np.fromiter((index[s.building_id] for s in samples), dtype=np.int64, count=len(samples))
    weight = np.fromiter((s.weight for s in samples), dtype=np.float64, count=len(samples))
    perim = np.array([b.perimeter for b in buildings], dtype=np.float64)

    covered = matrix.empty_covered()
    taken = np.zeros(matrix.n_candidates, dtype=bool)
    snapshots: dict[int, np.ndarray] = {}

    t0 = time.perf_counter()
    for i in range(args.max_k):
        gains = matrix.marginal_gains(covered)
        gains[taken] = -1
        best = int(np.argmax(gains))
        taken[best] = True
        matrix.add_to_covered(covered, best)
        if (i + 1) in KS:
            ids = matrix.covered_sample_ids(covered)
            got = np.bincount(owner[ids], weights=weight[ids], minlength=len(buildings))
            snapshots[i + 1] = got
            print(f"  k={i+1:<5} captured  [{(time.perf_counter()-t0)/60:.1f} min]", flush=True)
        elif (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{args.max_k}  [{(time.perf_counter()-t0)/60:.1f} min]", flush=True)

    print("\n" + "=" * 92)
    print("LEVER SIZING -- covered boundary weight that cannot buy a building")
    print("=" * 92)
    print(f"{'tau':>5} {'k':>5} {'serviced':>9} {'B: overshoot':>13} {'A: hopeless':>12} "
          f"{'reclaimable':>12} {'best-case +':>12} {'ceiling':>9}")
    print("-" * 92)

    results = []
    for tau in TAUS:
        need = perim * tau
        for k in KS:
            got = snapshots[k]
            serviced = got >= need
            n_serviced = int(serviced.sum())

            # B: weight spent above tau on already-serviced buildings.
            overshoot = float(np.clip(got - need, 0, None)[serviced].sum())

            # A: weight spent on buildings so far from tau that no plausible
            # reallocation reaches them. "Deficit" = weight still needed to hit tau.
            deficit = np.clip(need - got, 0, None)
            unserviced = ~serviced
            # Treat a building as reachable-by-reallocation if its deficit is under the
            # median deficit of unserviced buildings; the rest are the long tail.
            med = float(np.median(deficit[unserviced])) if unserviced.any() else 0.0
            hopeless = float(got[unserviced & (deficit > med)].sum())

            reclaimable = overshoot + hopeless
            # Best case: reallocate every reclaimable metre to the CHEAPEST near-misses.
            cheap = np.sort(deficit[unserviced & (deficit > 0)])
            flips = int(np.searchsorted(np.cumsum(cheap), reclaimable))
            flips = min(flips, len(cheap))
            results.append((tau, k, n_serviced, flips))
            print(f"{tau:>5g} {k:>5} {n_serviced:>9,} {overshoot:>12,.0f}m "
                  f"{hopeless:>11,.0f}m {reclaimable:>11,.0f}m "
                  f"{flips:>+11,} {n_serviced + flips:>9,}")

    print("-" * 92)
    print("\nThis is a HARD UPPER BOUND and is not achievable:")
    print("  * it assumes every reclaimed metre can be moved to a chosen building, but")
    print("    coverage is produced by antennas that illuminate many buildings at once;")
    print("  * it assumes perfect knowledge of which buildings to target;")
    print("  * it ignores that removing an antenna's overshoot usually removes its")
    print("    useful coverage too, since they come from the same sight lines.")
    print("\nA realistic lever captures a fraction of this. Compare against the measured")
    print("first attempt: +6.4% / +0.3% / -1.1% at k=500.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
