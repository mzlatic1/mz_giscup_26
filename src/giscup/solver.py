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
) -> Solution:
    """Solve one GIS Cup subproblem with the current baseline pipeline."""
    start = perf_counter()
    buildings, info = load_buildings(input_path)
    profile = get_profile(sampling_profile)
    samples = sample_boundaries(buildings, profile)
    candidates = generate_boundary_candidates(buildings, mode=candidate_mode)
    blocker_index = BlockerIndex.from_buildings(buildings)
    if optimizer not in {"greedy", "lazy-greedy", "stochastic-greedy", "hybrid"}:
        raise ValueError(f"Unsupported optimizer {optimizer!r}")
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
            "optimizer": optimizer,
            "max_candidates": max_candidates,
            "visibility_strategy": visibility_strategy,
            "claim_margin": claim_margin,
        },
        "runtime_seconds": {"total": perf_counter() - start},
        "warnings": [],
    }
    return Solution(tau=tau, k=k, antenna_points=[c.point for c in selected], claimed_building_ids=claimed, diagnostics=diagnostics)
