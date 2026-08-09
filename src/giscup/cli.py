"""Command-line interface for the GIS Cup solver."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from giscup.diagnostics import dataset_summary
from giscup.gate_model import default_verify_workers
from giscup.io import load_buildings
from giscup.output import format_solution_file
from giscup.progress import ProgressReporter
from giscup.scene import prepare_scene
from giscup.solver import solve_one
from giscup.validate import validate_solution_file


_NEAR_TAU_HELP = (
    "Enable the near-tau objective (lever A): each greedy pick is scored only against "
    "buildings that are unserviced AND within this percentile of the live deficit "
    "distribution, so coverage is spent where it can still flip a building. 100 targets "
    "every unserviced building. Requires --visibility-radius. OFF by default: measured "
    "at k=500 on the sample dataset only."
)


def _resolve_near_tau_schedule(
    quantiles: list[float] | None, taus: list[float]
) -> list[float | None]:
    """Map --near-tau-quantile onto --taus positionally."""
    if quantiles is None:
        return [None] * len(taus)
    if len(quantiles) == 1:
        return [quantiles[0]] * len(taus)
    if len(quantiles) != len(taus):
        raise SystemExit(
            f"--near-tau-quantile got {len(quantiles)} values for {len(taus)} taus. "
            "Give exactly one value, or one per tau in --taus order."
        )
    return list(quantiles)


def _write_json(path: str | None, payload: Any) -> None:
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def cmd_inspect(args: argparse.Namespace) -> None:
    buildings, info = load_buildings(args.input, id_property=args.id_property)
    print(json.dumps(dataset_summary(buildings, info), indent=2, sort_keys=True))


def cmd_solve_one(args: argparse.Namespace) -> None:
    reporter = ProgressReporter([(args.tau, args.k)], enabled=not args.quiet)
    reporter.start_subproblem(args.tau, args.k)
    solution = solve_one(
        progress=reporter,
        input_path=args.input,
        id_property=args.id_property,
        tau=args.tau,
        k=args.k,
        sampling_profile=args.sampling_profile,
        candidate_mode=args.candidate_mode,
        optimizer=args.optimizer,
        max_candidates=args.max_candidates,
        visibility_strategy=args.visibility_strategy,
        claim_margin=args.claim_margin,
        candidate_spacing=args.candidate_spacing,
        visibility_radius=args.visibility_radius,
        cache_dir=args.cache_dir,
        matrix_workers=args.matrix_workers,
        verify_band=args.verify_band,
        verify_max_buildings=args.verify_max_buildings,
        verify_radius_factor=args.verify_radius_factor,
        near_tau_quantile=args.near_tau_quantile,
        verify_workers=args.verify_workers,
    )
    reporter.finish_subproblem(claimed=len(solution.claimed_building_ids))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(format_solution_file([solution]), encoding="utf-8")
    _write_json(args.diagnostics, solution.diagnostics)


def cmd_solve_all(args: argparse.Namespace) -> None:
    solutions = []
    diagnostics = {}
    plan = [(tau, k) for tau in args.taus for k in args.ks]
    schedule = _resolve_near_tau_schedule(args.near_tau_quantile, args.taus)
    reporter = ProgressReporter(plan, enabled=not args.quiet)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".partial")
    # Loading, sampling, and candidate generation depend on the dataset, not on
    # (tau, k). Doing them once is worth ~27 s of a 33,898 s run (0.08%) -- the
    # point is the SceneSpec guard, not the speedup. See giscup.scene.
    scene = prepare_scene(
        args.input,
        id_property=args.id_property,
        sampling_profile=args.sampling_profile,
        candidate_mode=args.candidate_mode,
        candidate_spacing=args.candidate_spacing,
    )
    for tau, near_tau_quantile in zip(args.taus, schedule):
        for k in args.ks:
            reporter.start_subproblem(tau, k)
            solution = solve_one(
                progress=reporter,
                scene=scene,
                input_path=args.input,
                id_property=args.id_property,
                tau=tau,
                k=k,
                sampling_profile=args.sampling_profile,
                candidate_mode=args.candidate_mode,
                optimizer=args.optimizer,
                max_candidates=args.max_candidates,
                visibility_strategy=args.visibility_strategy,
                claim_margin=args.claim_margin,
                candidate_spacing=args.candidate_spacing,
                visibility_radius=args.visibility_radius,
                cache_dir=args.cache_dir,
                matrix_workers=args.matrix_workers,
                verify_band=args.verify_band,
                verify_max_buildings=args.verify_max_buildings,
                verify_radius_factor=args.verify_radius_factor,
                near_tau_quantile=near_tau_quantile,
                verify_workers=args.verify_workers,
            )
            reporter.finish_subproblem(claimed=len(solution.claimed_building_ids))
            solutions.append(solution)
            diagnostics[f"tau_{tau}_k_{k}"] = solution.diagnostics
            # A nine-block run takes hours. A failure in the last block must not
            # destroy the eight that already succeeded.
            partial.write_text(format_solution_file(solutions), encoding="utf-8")
    output.write_text(format_solution_file(solutions), encoding="utf-8")
    # Leaving a stale .partial beside a finished run invites submitting the wrong file.
    partial.unlink(missing_ok=True)
    _write_json(args.diagnostics, diagnostics)


def cmd_validate_output(args: argparse.Namespace) -> None:
    result = validate_solution_file(
        args.input,
        args.solution,
        eps=args.eps,
        sampling_profile=args.sampling_profile,
        visibility_strategy=args.visibility_strategy,
        claim_margin=args.claim_margin,
        validation_radius=args.validation_radius,
    )
    print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, indent=2))
    if not result.ok:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giscup", description="ACM SIGSPATIAL 2026 GIS Cup solver")
    sub = parser.add_subparsers(required=True)

    inspect_p = sub.add_parser("inspect", help="Inspect an input building-footprint dataset")
    inspect_p.add_argument("--input", required=True)
    inspect_p.add_argument("--id-property", default="id")
    inspect_p.set_defaults(func=cmd_inspect)

    solve_one_p = sub.add_parser("solve-one", help="Solve one (tau, k) subproblem")
    _add_solver_args(solve_one_p)
    solve_one_p.add_argument("--tau", type=float, required=True)
    solve_one_p.add_argument("--k", type=int, required=True)
    solve_one_p.add_argument("--near-tau-quantile", type=float, default=None, help=_NEAR_TAU_HELP)
    solve_one_p.add_argument("--output", required=True)
    solve_one_p.add_argument("--diagnostics")
    solve_one_p.set_defaults(func=cmd_solve_one)

    solve_all_p = sub.add_parser("solve-all", help="Solve all requested tau/k combinations")
    _add_solver_args(solve_all_p)
    solve_all_p.add_argument("--taus", type=float, nargs="+", required=True)
    solve_all_p.add_argument("--ks", type=int, nargs="+", required=True)
    solve_all_p.add_argument(
        "--near-tau-quantile",
        type=float,
        nargs="+",
        default=None,
        help=(
            _NEAR_TAU_HELP
            + " Give one value to apply everywhere, or one per --taus entry, in that "
            "order. The measured schedule at k=500 is 100 50 25 for taus 0.25 0.5 0.75."
        ),
    )
    solve_all_p.add_argument("--output", required=True)
    solve_all_p.add_argument("--diagnostics")
    solve_all_p.set_defaults(func=cmd_solve_all)

    validate_p = sub.add_parser("validate-output", help="Validate official-format solution output")
    validate_p.add_argument("--input", required=True)
    validate_p.add_argument("--solution", required=True)
    validate_p.add_argument("--eps", type=float, default=1e-7)
    validate_p.add_argument("--sampling-profile", default="accurate")
    validate_p.add_argument("--visibility-strategy", default="relate")
    validate_p.add_argument("--claim-margin", type=float, default=0.0)
    validate_p.add_argument(
        "--validation-radius",
        type=float,
        default=None,
        help=(
            "Cull visibility testing to pairs within this distance (CRS units). Culling only "
            "under-reports coverage, so it can reject a good claim but never accept a bad one. "
            "Omit for an exact but much slower check."
        ),
    )
    validate_p.set_defaults(func=cmd_validate_output)
    return parser


def _add_solver_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--id-property",
        default="id",
        help=(
            "Dataset field holding the building ID. If absent, IDs fall back to the row "
            "index and every claim is wrong -- run `giscup inspect` first to confirm."
        ),
    )
    parser.add_argument("--candidate-mode", default="basic")
    parser.add_argument("--candidate-spacing", type=float, default=25.0)
    parser.add_argument("--sampling-profile", default="balanced")
    parser.add_argument("--optimizer", default="greedy")
    parser.add_argument(
        "--max-candidates", type=int,
        help=(
            "DO NOT USE FOR PRUNING. Truncates the candidate list by generation "
            "order, and generation walks building by building -- so this deletes "
            "whole neighbourhoods of the city rather than thinning uniformly. "
            "Measured 2026-08-09, a uniform 2x prune (keep every other candidate, "
            "which is exactly the vertex half) costs 1 serviced building of 14,708; "
            "4x costs 6.6%% at tau=0.75 and 7.2x costs 14.9%%. See task #9. This flag "
            "exists for bounding test runs, nothing else."
        ),
    )
    parser.add_argument("--visibility-strategy", default="relate")
    parser.add_argument("--claim-margin", type=float, default=0.005)
    parser.add_argument(
        "--visibility-radius",
        type=float,
        default=None,
        help=(
            "Enable the cached visibility matrix, culled to pairs within this distance "
            "(CRS units). Required for full-scale runs; without it the solver recomputes "
            "visibility every greedy iteration and will not finish. Choose generously -- "
            "culling discards genuinely visible pairs and loses score silently."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default="outputs/cache",
        help="Where the visibility matrix is stored and reused across subproblems.",
    )
    parser.add_argument(
        "--matrix-workers", type=int, default=1, help="Parallel workers for the matrix build."
    )
    parser.add_argument(
        "--verify-band",
        type=float,
        default=None,
        help=(
            "Re-measure buildings whose coverage lands in [tau*(1-band), tau*(1+band)) with the "
            "exact un-culled predicate: recovers buildings the radius cull forfeited and drops "
            "overclaims the in-sample grid inflated. Expensive; opt-in."
        ),
    )
    parser.add_argument(
        "--verify-radius-factor",
        type=float,
        default=2.0,
        help=(
            "Verification re-measures using visibility-radius x this factor, so it does not "
            "inherit the solver's blind spot. 0 means unbounded (exact but slow). Measured on "
            "the official sample: 400 m captures ~91%% of visible pairs, 800 m ~98%%."
        ),
    )
    parser.add_argument(
        "--verify-max-buildings",
        type=int,
        default=None,
        help="Cap on buildings re-verified per subproblem, closest to tau first.",
    )
    parser.add_argument(
        "--verify-workers", type=int, default=default_verify_workers(),
        help=(
            "Processes for exact claim verification. Verification is ~82%% of a full "
            "run and every building is independent, so this is the cheapest large "
            "speedup available. Results are bit-identical to serial. Defaults to "
            "min(cores, 12) -- serial verification costs ~12 h of a ~24 h window, "
            "so it must be chosen deliberately rather than fallen into. "
            f"On this host: %(default)s."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Suppress per-subproblem progress. Progress is ON by default: a full run "
            "takes hours, and silence is indistinguishable from a hang."
        ),
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
