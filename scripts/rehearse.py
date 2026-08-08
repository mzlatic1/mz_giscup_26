"""Feasibility gate: can this solver finish all nine subproblems inside the submission window?

The GIS Cup gives one submission and no score feedback. The test dataset lands
2026-08-15 and the deadline is 2026-08-16, so there is no chance to discover on
the day that the pipeline cannot run. This script answers that question *now*.

It does not run the full problem — that would take longer than the competition.
Instead it measures visibility throughput and the greedy cost model on a scaled
subsample, then extrapolates to full size and reports PASS or FAIL against a
wall-clock budget.

The cost model, from ``optimize.greedy_select``:

    checks = k * |candidates| * |samples|        (no caching, current code)
    checks =     |candidates| * |samples|        (with per-candidate caching)

Usage::

    python scripts/rehearse.py --input outputs/synthetic_full.geojson
    python scripts/rehearse.py --input outputs/synthetic_full.geojson --budget-hours 20
"""

from __future__ import annotations

import argparse
import math
import random
import time

import numpy as np
from shapely.geometry import LineString

from giscup.candidates import generate_boundary_candidates
from giscup.io import load_buildings
from giscup.sampling import get_profile, sample_boundaries
from giscup.visibility import BlockerIndex, is_visible

# The nine subproblems. Sample-page values; the final ones are not published.
TAUS = (0.25, 0.5, 0.75)
KS = (50, 500, 1000)

# Aug 15 release to Aug 16 deadline, minus room for validation and packaging.
DEFAULT_BUDGET_HOURS = 20.0


def _domain_area(buildings) -> float:
    """Bounding-box area of the whole dataset, used to size radius-cull pair counts."""
    xs0 = min(b.bounds[0] for b in buildings)
    ys0 = min(b.bounds[1] for b in buildings)
    xs1 = max(b.bounds[2] for b in buildings)
    ys1 = max(b.bounds[3] for b in buildings)
    return (xs1 - xs0) * (ys1 - ys0)


def _sample_pairs(candidates, samples, radius, rng, n, max_tries=400_000):
    """Draw candidate/sample pairs, optionally restricted to a maximum separation."""
    pairs = []
    tries = 0
    while len(pairs) < n and tries < max_tries:
        tries += 1
        a = rng.choice(candidates).point
        b = rng.choice(samples).point
        if radius is None or math.dist(a, b) <= radius:
            pairs.append((a, b))
    return pairs


def measure_throughput(index, pairs, strategy: str) -> tuple[float, float]:
    """Return (checks/sec, mean blockers per query) for the given pairs."""
    if not pairs:
        return float("nan"), float("nan")
    blockers = sum(len(index.query(LineString([a, b]))) for a, b in pairs[:200]) / min(len(pairs), 200)
    start = time.perf_counter()
    for a, b in pairs:
        is_visible(a, b, index, strategy=strategy)
    elapsed = time.perf_counter() - start
    return (len(pairs) / elapsed if elapsed > 0 else float("inf")), blockers


def measure_visible_fraction(index, candidates, samples, rng, n_cand, n_samp):
    """Estimate what fraction of all samples a candidate can see, and how far."""
    hits, dists = 0, []
    probes = [rng.choice(candidates) for _ in range(n_cand)]
    subset = [rng.choice(samples) for _ in range(n_samp)]
    for c in probes:
        for s in subset:
            if is_visible(c.point, s.point, index, strategy="relate"):
                hits += 1
                dists.append(math.dist(c.point, s.point))
    dists.sort()
    return hits / (len(probes) * len(subset)), dists


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True)
    parser.add_argument("--sampling-profile", default="balanced")
    parser.add_argument("--candidate-mode", default="basic")
    parser.add_argument("--budget-hours", type=float, default=DEFAULT_BUDGET_HOURS)
    parser.add_argument("--probe-pairs", type=int, default=600)
    parser.add_argument("--probe-candidates", type=int, default=8)
    parser.add_argument("--probe-samples", type=int, default=2500)
    parser.add_argument("--cores", type=int, default=1, help="Assumed parallel cores for the projection")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument(
        "--measured-radius",
        type=float,
        default=None,
        help=(
            "Build (or load) the real visibility matrix at this cull radius and time actual "
            "greedy iterations, so the verdict is observed rather than projected."
        ),
    )
    parser.add_argument("--cache-dir", default="outputs/cache")
    parser.add_argument("--greedy-probe-iterations", type=int, default=5)
    args = parser.parse_args(argv)

    print("=" * 78)
    print("GIS CUP FEASIBILITY REHEARSAL")
    print("=" * 78)

    t0 = time.perf_counter()
    buildings, info = load_buildings(args.input)
    profile = get_profile(args.sampling_profile)
    samples = sample_boundaries(buildings, profile)
    candidates = generate_boundary_candidates(buildings, mode=args.candidate_mode)
    setup = time.perf_counter() - t0

    n_s, n_c = len(samples), len(candidates)
    print(f"\ndataset      : {info.path}")
    print(f"CRS          : {info.crs}")
    print(f"buildings    : {len(buildings):,}")
    print(f"samples      : {n_s:,}   (profile {args.sampling_profile}, spacing {profile.spacing} m)")
    print(f"candidates   : {n_c:,}   (mode {args.candidate_mode})")
    print(f"setup time   : {setup:.1f} s")

    rng = random.Random(args.seed)
    index = BlockerIndex.from_buildings(buildings)
    budget_s = args.budget_hours * 3600.0
    domain = _domain_area(buildings)

    # --- how far can a candidate actually see, and how sparse is the matrix? ---
    print(f"\nvisibility reach ({args.probe_candidates} candidates x {args.probe_samples} samples)")
    frac, dists = measure_visible_fraction(
        index, candidates, samples, rng, args.probe_candidates, args.probe_samples
    )
    if not dists:
        print("  no visible pairs sampled — increase --probe-samples; cannot size a radius cull")
        return 1
    p95 = dists[int(len(dists) * 0.95)]
    print(f"  visible fraction of all samples : {frac * 100:.4f}%  ({len(dists)} hits)")
    print(f"  visible distance median/p95/max : {dists[len(dists)//2]:.0f} / {p95:.0f} / {dists[-1]:.0f} m")
    if len(dists) < 20:
        print(f"  NOTE: only {len(dists)} hits — this estimate is noisy; treat p95 as indicative")

    # --- throughput depends strongly on segment length, via blocker count ---
    print("\nthroughput vs segment length (1 core, 'relate')")
    print(f"  {'max length':>12s} {'blockers/query':>16s} {'checks/s':>12s}")
    radii = [r for r in (100.0, 200.0, 400.0, 800.0) if r <= max(dists[-1] * 2, 200.0)]
    radii.append(None)
    rate_by_radius: dict[float | None, float] = {}
    for radius in radii:
        pairs = _sample_pairs(candidates, samples, radius, rng, args.probe_pairs)
        rate, blockers = measure_throughput(index, pairs, "relate")
        rate_by_radius[radius] = rate
        label = f"<= {radius:.0f} m" if radius else "unbounded"
        print(f"  {label:>12s} {blockers:16.1f} {rate:12,.0f}")

    hybrid_pairs = _sample_pairs(candidates, samples, None, rng, min(args.probe_pairs, 600))
    hybrid_rate, _ = measure_throughput(index, hybrid_pairs, "hybrid")

    print(f"\nbudget       : {args.budget_hours:.1f} h across {args.cores} core(s)")

    # --- cost model ---------------------------------------------------------
    # The visibility matrix is computed ONCE and reused by all 9 subproblems:
    # a candidate's visible set never changes, only the union subtracted from it.
    print("\n" + "-" * 78)
    print(f"{'variant':40s} {'checks':>14s} {'time':>14s} {'':>5s}")
    print("-" * 78)

    variants: list[tuple[str, float, float]] = [
        (
            "current: hybrid, no cache, no cull",
            sum(k * n_c * n_s for k in KS) * len(TAUS),
            hybrid_rate * args.cores,
        ),
        (
            "relate, cached, no cull",
            float(n_c) * n_s,
            rate_by_radius[None] * args.cores,
        ),
    ]
    for radius in [r for r in radii if r is not None]:
        frac_pairs = min(math.pi * radius * radius / domain, 1.0)
        variants.append(
            (
                f"relate, cached, radius cull {radius:.0f} m",
                float(n_c) * n_s * frac_pairs,
                rate_by_radius[radius] * args.cores,
            )
        )

    verdicts = []
    for name, checks, rate in variants:
        seconds = checks / rate if rate > 0 else float("inf")
        ok = seconds <= budget_s
        verdicts.append((name, ok, seconds))
        if seconds < 3600:
            pretty = f"{seconds/60:,.1f} min"
        elif seconds < 86400:
            pretty = f"{seconds/3600:,.1f} h"
        else:
            pretty = f"{seconds/86400:,.0f} days"
        print(f"{name:40s} {checks:14.2e} {pretty:>14s} {'PASS' if ok else 'FAIL':>5s}")
    print("-" * 78)

    current_ok = verdicts[0][1]
    fitting = [(n, s) for n, ok, s in verdicts if ok]
    print()
    if current_ok:
        print("VERDICT: PASS — the pipeline as written fits the budget.")
        rc = 0
    elif fitting:
        name, seconds = min(fitting, key=lambda t: t[1])
        print("VERDICT: FAIL — the pipeline AS WRITTEN cannot finish inside the budget.")
        print(f"         Shortfall: {verdicts[0][2] / seconds:,.0f}x.")
        print(f"         A viable route EXISTS: {name!r} ({seconds/3600:.2f} h).")
        print("         Build it now. Feasibility work outranks solution-quality work")
        print("         until this gate reads PASS.")
        rc = 1
    else:
        print("VERDICT: FAIL — no modelled variant fits the budget.")
        print("         Reconsider the approach, not the constants.")
        rc = 1

    if args.measured_radius is not None:
        rc = measured_gate(
            buildings,
            candidates,
            samples,
            radius=args.measured_radius,
            workers=args.cores,
            cache_dir=args.cache_dir,
            budget_s=budget_s,
            greedy_probe_iterations=args.greedy_probe_iterations,
        )

    print("\nReminder (see memory: rogii-lessons-that-transfer): measure a lever's best-case")
    print("range against the gap before investing in it. A better objective on a solver that")
    print("cannot finish scores zero.")
    return rc


def measured_gate(
    buildings,
    candidates,
    samples,
    *,
    radius: float,
    workers: int,
    cache_dir: str,
    budget_s: float,
    greedy_probe_iterations: int,
) -> int:
    """Observe the real pipeline cost instead of projecting it.

    The analytic model above estimates visibility checks from probe throughput. This
    builds (or loads) the actual matrix and times actual greedy iterations, so the
    verdict rests on measurement. Only the k-scaling is extrapolated, and that
    extrapolation is exact by construction: every greedy iteration is one identical
    full pass over the matrix, independent of k.
    """
    from giscup.matrix import build_visibility_matrix

    print("\n" + "=" * 78)
    print(f"MEASURED GATE — radius {radius:g} m, {workers} workers")
    print("=" * 78)

    t0 = time.perf_counter()
    matrix = build_visibility_matrix(
        buildings, candidates, samples, radius=radius, workers=workers,
        cache_dir=cache_dir, progress=True,
    )
    build_s = matrix.build_seconds if matrix.loaded_from_cache else time.perf_counter() - t0
    source = "loaded from cache (build time from metadata)" if matrix.loaded_from_cache else "built now"
    print(f"\nmatrix build : {build_s / 60:,.1f} min   ({source})")

    nonzeros = matrix.nonzeros()
    total_cells = matrix.n_candidates * matrix.n_samples
    print(f"visible pairs: {nonzeros:,}  (density {nonzeros / total_cells * 100:.5f}%)")
    print(f"mean visible samples per candidate : {nonzeros / matrix.n_candidates:.1f}")

    # One greedy iteration = one marginal_gains pass + one covered-set union.
    covered = matrix.empty_covered()
    t0 = time.perf_counter()
    for _ in range(greedy_probe_iterations):
        gains = matrix.marginal_gains(covered)
        matrix.add_to_covered(covered, int(np.argmax(gains)))
    per_iter = (time.perf_counter() - t0) / greedy_probe_iterations
    print(f"greedy       : {per_iter:.3f} s per iteration ({greedy_probe_iterations} timed)")

    solve_s = sum(k * per_iter for k in KS) * len(TAUS)
    total_s = build_s + solve_s
    print("\n" + "-" * 78)
    print(f"{'stage':40s} {'time':>16s}")
    print("-" * 78)
    print(f"{'visibility matrix (once, all 9)':40s} {build_s / 60:>13,.1f} min")
    for k in KS:
        print(f"{f'greedy x3 taus at k={k}':40s} {k * per_iter * len(TAUS) / 60:>13,.1f} min")
    print(f"{'TOTAL for all nine subproblems':40s} {total_s / 3600:>13,.2f} h")
    print("-" * 78)

    ok = total_s <= budget_s
    print(f"\nbudget       : {budget_s / 3600:.1f} h")
    print(f"headroom     : {budget_s / total_s:,.1f}x" if total_s > 0 else "")
    if ok:
        print("\nMEASURED VERDICT: PASS — observed, not extrapolated.")
        print("  Solve cost is measured end to end. Output formatting and validation are")
        print("  NOT included here; budget for them separately before calling the window safe.")
        return 0
    print("\nMEASURED VERDICT: FAIL — the built pipeline does not fit the budget.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
