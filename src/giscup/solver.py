"""End-to-end solver orchestration."""

from __future__ import annotations

from time import perf_counter

from giscup.candidates import generate_boundary_candidates
from giscup.coverage import coverage_by_building, serviced_buildings
from giscup.io import load_buildings
from giscup.models import Solution
from giscup.optimize import greedy_select
from giscup.sampling import get_profile, sample_boundaries
from giscup.visibility import BlockerIndex


def solve_one(
    input_path: str,
    tau: float,
    k: int,
    sampling_profile: str = "balanced",
    candidate_mode: str = "basic",
    optimizer: str = "greedy",
    max_candidates: int | None = None,
    visibility_strategy: str = "hybrid",
    claim_margin: float = 0.005,
    candidate_spacing: float = 25.0,
) -> Solution:
    """Solve one GIS Cup subproblem with the current baseline pipeline."""
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
        },
        "runtime_seconds": {"total": perf_counter() - start},
        "warnings": [],
    }
    if len(selected) != k:
        raise RuntimeError(f"internal solver error: selected {len(selected)} antennas for k={k}")
    return Solution(
        tau=tau,
        k=k,
        antenna_points=[c.point for c in selected],
        claimed_building_ids=claimed,
        diagnostics=diagnostics,
    )
