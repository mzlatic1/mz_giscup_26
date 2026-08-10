"""End-to-end solver orchestration."""

from __future__ import annotations

from time import perf_counter

from giscup.coverage import coverage_by_building, serviced_buildings
from giscup.matrix import build_visibility_matrix
from giscup.models import Solution
from giscup.optimize import greedy_select, greedy_select_matrix, greedy_select_near_tau
from giscup.output import nudge_off_interior
from giscup.progress import ProgressReporter
from giscup.sampling import get_profile
from giscup.scene import Scene, SceneSpec, prepare_scene
from giscup.verify import verify_and_recover
from giscup.visibility import BlockerIndex


def solve_one(
    input_path: str,
    tau: float,
    k: int,
    id_property: str = "id",
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
    verify_radius_factor: float = 2.0,
    progress: ProgressReporter | None = None,
    scene: Scene | None = None,
    near_tau_quantile: float | None = None,
    verify_workers: int = 1,
    candidate_stride: int = 1,
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
        raise ValueError(f"optimizer must be 'greedy'; got {optimizer!r}")
    if near_tau_quantile is not None:
        if not (0 < near_tau_quantile <= 100):
            raise ValueError(
                f"near_tau_quantile must be in (0, 100], got {near_tau_quantile}"
            )
        if visibility_radius is None:
            raise ValueError(
                "near_tau_quantile requires visibility_radius: the near-tau objective "
                "exists only on the cached-matrix path."
            )

    def _phase(name: str, detail: str = "") -> None:
        if progress is not None:
            progress.phase(name, detail)

    start = perf_counter()
    requested = SceneSpec(
        input_path=input_path,
        id_property=id_property,
        sampling_profile=sampling_profile,
        candidate_mode=candidate_mode,
        candidate_spacing=candidate_spacing,
        candidate_stride=candidate_stride,
    )
    if scene is None:
        scene = prepare_scene(
            input_path,
            id_property=id_property,
            sampling_profile=sampling_profile,
            candidate_mode=candidate_mode,
            candidate_spacing=candidate_spacing,
            candidate_stride=candidate_stride,
        )
    else:
        differing = scene.mismatches(requested)
        if differing:
            raise ValueError(
                "scene does not match the requested configuration; differs in "
                f"{', '.join(differing)}. Reusing it would solve a different problem "
                "than the one asked for."
            )
    buildings, info = scene.buildings, scene.info
    samples, candidates = scene.samples, scene.candidates
    _phase("setup", f"{len(buildings):,} bldg  {len(candidates):,} cand")
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
        _phase("matrix", f"{matrix.nonzeros():,} pairs  cached={matrix.loaded_from_cache}")
        greedy_progress = (
            None
            if progress is None
            else (lambda i, total: _phase("greedy", f"picked {i:,}/{total:,}"))
        )
        if near_tau_quantile is None:
            selected, visible = greedy_select_matrix(
                matrix,
                candidates,
                samples,
                buildings,
                tau=tau,
                k=k,
                max_candidates=max_candidates,
                progress=greedy_progress,
            )
        else:
            selected, visible = greedy_select_near_tau(
                matrix,
                candidates,
                samples,
                buildings,
                tau=tau,
                k=k,
                max_candidates=max_candidates,
                quantile=near_tau_quantile,
                progress=greedy_progress,
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
    # Emitted antennas must not sit an ULP inside a footprint (#15). Midpoint
    # candidates land inside ~37% of the time at projected-CRS magnitudes; that is
    # legal but an evaluator testing visibility against the raw polygon would see
    # nothing from them. Nudge BEFORE verification, so we verify what we emit.
    nudge_index = BlockerIndex.from_buildings(buildings)
    from shapely.geometry import Point as _Point

    antenna_points = []
    for candidate in selected:
        nearby = [buildings[i] for i in nudge_index.query_indices(_Point(*candidate.point))]
        antenna_points.append(
            nudge_off_interior(candidate.point, nearby) if nearby else candidate.point
        )

    coverage = coverage_by_building(visible, samples, buildings)
    claimed = serviced_buildings(coverage, tau, margin=claim_margin)
    _phase("coverage", f"{len(claimed):,} claimed pre-verify")

    verification_info: dict | None = None
    if verify_band is not None:
        # Coverage near tau is unreliable in both directions: the radius cull
        # under-reports it, and deciding claims from the same grid we optimized on
        # over-reports it. Re-measure that window exactly.
        verify_index = nudge_index
        claimed, report = verify_and_recover(
            coverage=coverage,
            claimed=claimed,
            tau=tau,
            antenna_points=antenna_points,
            samples=samples,
            buildings=buildings,
            blocker_index=verify_index,
            band=verify_band,
            max_buildings=verify_max_buildings,
            claim_margin=claim_margin,
            strategy=visibility_strategy,
            verify_profile=get_profile(verify_profile),
            workers=verify_workers,
            # Deliberately WIDER than the solver's cull. Measured on the official
            # sample: a 400 m cull captures ~91% of visible pairs, 800 m ~98%. If the
            # verification pass reused the solver's radius it would inherit the exact
            # blind spot it exists to correct.
            exact_radius=(
                visibility_radius * verify_radius_factor
                if visibility_radius is not None and verify_radius_factor > 0
                else None
            ),
        )
        _phase(
            "verify",
            f"{report.reverified_count:,} checked  "
            f"+{len(report.recovered_ids):,}/-{len(report.dropped_ids):,}",
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
        "dataset": {
            "path": info.path,
            "feature_count": info.feature_count,
            "crs": info.crs,
            "id_property": info.id_property,
            "id_fallback_used": info.id_fallback_used,
        },
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
            "candidate_stride": candidate_stride,
            "optimizer": optimizer,
            "max_candidates": max_candidates,
            "visibility_strategy": visibility_strategy,
            "claim_margin": claim_margin,
            "visibility_radius": visibility_radius,
            "verify_band": verify_band,
            "verify_radius_factor": verify_radius_factor,
            "near_tau_quantile": near_tau_quantile,
            "verify_workers": verify_workers,
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
        antenna_points=antenna_points,
        claimed_building_ids=claimed,
        diagnostics=diagnostics,
    )
