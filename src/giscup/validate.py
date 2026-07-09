"""Validation helpers for official-format outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from giscup.coverage import coverage_by_building
from giscup.geometry import is_point_on_any_boundary
from giscup.io import load_buildings
from giscup.output import parse_points
from giscup.sampling import get_profile, sample_boundaries
from giscup.visibility import BlockerIndex, is_visible


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_solution_file(
    input_path: str,
    solution_path: str,
    eps: float = 1e-7,
    sampling_profile: str = "accurate",
    visibility_strategy: str = "hybrid",
    claim_margin: float = 0.0,
    validate_claim_coverage: bool = True,
) -> ValidationResult:
    """Validate official formatting, boundary legality, IDs, and sampled claims."""
    buildings, _ = load_buildings(input_path)
    valid_ids = {str(b.id) for b in buildings}
    lines = Path(solution_path).read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    warnings: list[str] = []
    samples = []
    blocker_index = None
    if validate_claim_coverage:
        profile = get_profile(sampling_profile)
        samples = sample_boundaries(buildings, profile)
        blocker_index = BlockerIndex.from_buildings(buildings)

    block_start = 0
    while block_start < len(lines):
        while block_start < len(lines) and not lines[block_start].strip():
            block_start += 1
        if block_start >= len(lines):
            break
        if block_start + 2 >= len(lines):
            errors.append(
                f"Incomplete solution block starting line {block_start + 1}; "
                "expected parameter, points, and claimed-ID lines."
            )
            break
        header = lines[block_start].strip()
        points_line = lines[block_start + 1].strip()
        # The official third line may be empty when no buildings are claimed.
        claims_line = lines[block_start + 2].strip()
        try:
            tau_s, k_s = header.strip("()").split(",")
            tau = float(tau_s)
            k = int(k_s)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid parameter line {block_start + 1}: {header!r} ({exc})")
            block_start += 3
            continue
        if not (0 < tau <= 1):
            errors.append(f"tau must be in (0, 1], got {tau}")
        points = parse_points(points_line)
        if len(points) != k:
            errors.append(f"Expected {k} antenna points, found {len(points)} in block starting line {block_start + 1}")
        for point in points:
            if not is_point_on_any_boundary(point, buildings, eps=eps):
                errors.append(f"Point {point} is not on any building boundary within eps={eps}")
                break
        claims = [v.strip() for v in claims_line.split(",") if v.strip()]
        missing = [v for v in claims if v not in valid_ids]
        if missing:
            errors.append(f"Claimed IDs not present in dataset: {missing[:10]}")
        if validate_claim_coverage and claims and blocker_index is not None:
            visible_ids = _visible_sample_ids_from_points(points, samples, blocker_index, visibility_strategy)
            coverage = coverage_by_building(visible_ids, samples, buildings)
            failed_claims = []
            for claimed_id in claims:
                ratio = coverage.get(_coerce_claim_id(claimed_id), coverage.get(claimed_id, 0.0))
                if ratio < tau + claim_margin:
                    failed_claims.append((claimed_id, ratio))
            if failed_claims:
                preview = ", ".join(f"{bid}: {ratio:.6g}" for bid, ratio in failed_claims[:10])
                errors.append(
                    f"Claimed buildings below tau + claim_margin ({tau + claim_margin:.6g}) "
                    f"in block starting line {block_start + 1}: {preview}"
                )
        block_start += 3
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _visible_sample_ids_from_points(points, samples, blocker_index, strategy: str) -> set[int]:
    visible_ids: set[int] = set()
    for sample in samples:
        if any(is_visible(point, sample.point, blocker_index, strategy=strategy) for point in points):
            visible_ids.add(sample.id)
    return visible_ids


def _coerce_claim_id(claimed_id: str):
    try:
        return int(claimed_id)
    except ValueError:
        return claimed_id
