#!/usr/bin/env python
"""Measure lever A (near-tau targeting) against the baseline greedy at full scale.

Sized first (scripts/size_objective_levers.py): lever A's resource is 109,622 m at
tau=0.75/k=500, 10.1x lever B's overshoot in the same subproblem, and tau=0.75 is where
relative scoring pays.

Built-in control: `quantile=100` targets every unserviced building, which IS the
already-measured threshold objective (lever B). It was measured at +6.4% / +0.3% /
-1.1% at k=500. If this run does not reproduce roughly that, the implementation is
wrong and no other number here can be trusted.

The baseline objective ignores tau, so one baseline run serves every tau.
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
from giscup.optimize import greedy_select_matrix, greedy_select_near_tau  # noqa: E402
from giscup.sampling import get_profile, sample_boundaries  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/GIS-cup-sample-dataset.geojson")
    ap.add_argument("--radius", type=float, default=400.0)
    ap.add_argument("--cache-dir", default="outputs/cache")
    ap.add_argument("--k", type=int, default=500)
    ap.add_argument("--taus", type=float, nargs="+", default=[0.75, 0.5, 0.25])
    ap.add_argument("--quantiles", type=float, nargs="+", default=[25.0, 50.0, 100.0])
    args = ap.parse_args(argv)

    buildings, _ = load_buildings(args.input)
    samples = sample_boundaries(buildings, get_profile("balanced"))
    candidates = generate_boundary_candidates(buildings, mode="basic", candidate_spacing=25.0)
    matrix = build_visibility_matrix(
        buildings, candidates, samples, radius=args.radius, cache_dir=args.cache_dir
    )
    print(f"pairs={matrix.nonzeros():,}  candidates={len(candidates):,}  "
          f"samples={len(samples):,}  k={args.k}\n", flush=True)

    index = {b.id: i for i, b in enumerate(buildings)}
    owner = np.fromiter((index[s.building_id] for s in samples), dtype=np.int64, count=len(samples))
    weight = np.fromiter((s.weight for s in samples), dtype=np.float64, count=len(samples))
    perim = np.array([b.perimeter for b in buildings], dtype=np.float64)

    def serviced(visible: set[int], tau: float) -> int:
        ids = np.fromiter(visible, dtype=np.int64, count=len(visible))
        got = np.bincount(owner[ids], weights=weight[ids], minlength=len(buildings))
        return int((got >= perim * tau).sum())

    t0 = time.perf_counter()
    _, base_visible = greedy_select_matrix(
        matrix, candidates, samples, buildings, tau=0.5, k=args.k
    )
    print(f"baseline greedy done [{(time.perf_counter()-t0)/60:.1f} min]\n", flush=True)
    baseline = {tau: serviced(base_visible, tau) for tau in args.taus}

    print(f"{'tau':>5} {'quantile':>9} {'baseline':>9} {'near-tau':>9} "
          f"{'delta':>8} {'change':>9} {'note':<22}")
    print("-" * 78)
    for tau in args.taus:
        for q in args.quantiles:
            t1 = time.perf_counter()
            _, vis = greedy_select_near_tau(
                matrix, candidates, samples, buildings, tau=tau, k=args.k, quantile=q
            )
            got = serviced(vis, tau)
            base = baseline[tau]
            delta = got - base
            note = "control == lever B" if q == 100.0 else ""
            print(f"{tau:>5g} {q:>9g} {base:>9,} {got:>9,} {delta:>+8,} "
                  f"{100*delta/max(base,1):>+8.1f}% {note:<22} "
                  f"[{(time.perf_counter()-t1)/60:.1f} min]", flush=True)

    print("\n" + "!" * 78)
    print("THESE ARE UPPER ESTIMATES, NOT SCORE PREDICTIONS.")
    print("!" * 78)
    print("`serviced()` above counts from `samples` -- the same grid the optimizer")
    print("optimized on. That is the #12 defect, which the solver fixed and this")
    print("script reproduces. The bias is NOT symmetric between the two arms:")
    print()
    print("  * baseline greedy takes coverage where it is cheapest, so most of its")
    print("    serviced buildings sit clear of tau and in-sample error rarely flips them;")
    print("  * near-tau concentrates on buildings AT the threshold by construction, so")
    print("    its incremental wins are exactly the ones in-sample error decides.")
    print()
    print("So every number above inflates near-tau more than baseline. Use this table")
    print("to RANK quantiles. For a score, compare post-verification claim counts from")
    print("a full `giscup solve-all` run, which decides claims off an independent grid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
