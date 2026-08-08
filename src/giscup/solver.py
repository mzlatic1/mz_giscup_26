"""End-to-end solver orchestration."""

from __future__ import annotations

from time import perf_counter

from giscup.candidates import generate_boundary_candidates
from giscup.coverage import coverage_by_building, serviced_buildings
from giscup.io import load_buildings
from giscup.matrix import build_visibility_matrix
from giscup.models import Solution
from giscup.optimize import greedy_select, greedy_select_matrix
from giscup.sampling import get_profile, sample_boundaries
from giscup.verify import verify_and_recover
from giscup.visibility import BlockerIndex


def solve_one(
    input_path: str,
    tau: float,
    k: int,
    sampling_profile: str = "balanced",
    candidate_mode: str = "basic",
    optimizer: str = "greedy",
    max_candidates: int | None = None,
    visibility_strategy: str = "relate",
    claim_margin: float = 0.005,
    candidate_spacing: float = 25.0,
    visibility_radius: float | None = None,
    cache_dir: str | None = None,
    matrix_workers: int = 1,
    verify_band: float | None = None,
    verify_max_buildings: int | None = None,
    verify_profile: str = "accurate",
) -> Solution:
    """Solve one GIS Cup subproblem.

    Setting `visibility_radius` enables the cached visibility matrix: visibility is
    computed once for pairs within that radius and reused across every greedy
    iteration and every subproblem sharing the same `cache_dir`. Without it the
    solver falls back to recomputing predicates per iteration, which does not finish
    at full scale.

    The radius is opt-in and never implied, because culling silently discards
    genuinely visible pairs and there is no score feedback to detect the loss.
    """
    if not (0 < tau <= 1):
        raise ValueError(f"tau must be in (0, 1], got {tau}")
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    if max_candidates is not None and max_candidates < k:
        raise ValueError(f"max_candidates ({max_candidates}) must be at least k ({k})")
    if optimizer != "greedy":
        raise ValueError(
            f"optimizer {optimizer!r} is not implemented in the current scaffold; "
            "use 'greedy' until lazy/stochastic/hybrid optimizers are implemented"
        )

    start = perf_counter()
    buildings, info = load_buildings(input_path)
    profile = get_profile(sampling_profile)
    samples = sample_boundaries(buildings, profile)
    candidates = generate_boundary_candidates(
        buildings, mode=candidate_mode, candidate_spacing=candidate_spacing
    )
    matrix_info: dict | None = None
    if visibility_radius is not None:
        matrix = build_visibility_matrix(
            buildings,
            candidates,
            samples,
            radius=visibility_radius,
            strategy=visibility_strategy,
            workers=matrix_workers,
            cache_dir=cache_dir,
        )
        selected, visible = greedy_select_matrix(
            matrix, candidates, samples, buildings, tau=tau, k=k, max_candidates=max_candidates
        )
        matrix_info = {
            "key": matrix.spec.key,
            "radius": visibility_radius,
            "loaded_from_cache": matrix.loaded_from_cache,
            "build_seconds": matrix.build_seconds,
            "nonzeros": matrix.nonzeros(),
        }
    else:
        blocker_index = BlockerIndex.from_buildings(buildings)
        selected, visible = greedy_select(
            candidates,
            samples,
            buildings,
            blocker_index,
            tau=tau,
            k=k,
            strategy=visibility_strategy,
            max_candidates=max_candidates,
        )
    coverage = coverage_by_building(visible, samples, buildings)
    claimed = serviced_buildings(coverage, tau, margin=claim_margin)

    verification_info: dict | None = None
    if verify_band is not None:
        # Coverage near tau is unreliable in both directions: the radius cull
        # under-reports it, and deciding claims from the same grid we optimized on
        # over-reports it. Re-measure that window exactly.
        verify_index = BlockerIndex.from_buildings(buildings)
        claimed, report = verify_and_recover(
            coverage=coverage,
            claimed=claimed,
            tau=tau,
            antenna_points=[c.point for c in selected],
            samples=samples,
            buildings=buildings,
            blocker_index=verify_index,
            band=verify_band,
            max_buildings=verify_max_buildings,
            claim_margin=claim_margin,
            strategy=visibility_strategy,
            verify_profile=get_profile(verify_profile),
        )
        verification_info = {
            "band": verify_band,
            "profile": verify_profile,
            "max_buildings": verify_max_buildings,
            "reverified_count": report.reverified_count,
            "recovered": list(report.recovered_ids),
            "dropped": list(report.dropped_ids),
            "checks_performed": report.checks_performed,
            "max_coverage_delta": report.max_coverage_delta,
        }
    diagnostics = {
        "dataset": {"path": info.path, "feature_count": info.feature_count, "crs": info.crs},
        "parameters": {"tau": tau, "k": k},
        "counts": {
            "candidate_count": len(candidates),
            "sample_count": len(samples),
            "selected_count": len(selected),
            "claimed_serviced_count": len(claimed),
        },
        "config": {
            "sampling_profile": sampling_profile,
            "candidate_mode": candidate_mode,
            "candidate_spacing": candidate_spacing,
            "optimizer": optimizer,
            "max_candidates": max_candidates,
            "visibility_strategy": visibility_strategy,
            "claim_margin": claim_margin,
            "visibility_radius": visibility_radius,
            "verify_band": verify_band,
        },
        "runtime_seconds": {"total": perf_counter() - start},
        "warnings": [],
    }
    if matrix_info is not None:
        diagnostics["visibility_matrix"] = matrix_info
    if verification_info is not None:
        diagnostics["verification"] = verification_info
    if len(selected) != k:
        raise RuntimeError(f"internal solver error: selected {len(selected)} antennas for k={k}")
    return Solution(
        tau=tau,
        k=k,
        antenna_points=[c.point for c in selected],
        claimed_building_ids=claimed,
        diagnostics=diagnostics,
    )
