"""Validation helpers for official-format outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from giscup.geometry import is_point_on_any_boundary
from giscup.io import load_buildings
from giscup.output import parse_points


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_solution_file(input_path: str, solution_path: str, eps: float = 1e-7) -> ValidationResult:
    """Validate formatting, point counts, boundary legality, and claimed IDs."""
    buildings, _ = load_buildings(input_path)
    valid_ids = {str(b.id) for b in buildings}
    lines = [line.strip() for line in Path(solution_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    errors: list[str] = []
    warnings: list[str] = []
    if len(lines) % 3 != 0:
        errors.append("Solution file must contain exactly three non-empty lines per subproblem.")
    for block_start in range(0, len(lines), 3):
        if block_start + 2 >= len(lines):
            break
        header, points_line, claims_line = lines[block_start : block_start + 3]
        try:
            tau_s, k_s = header.strip("()").split(",")
            tau = float(tau_s)
            k = int(k_s)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid parameter line {block_start + 1}: {header!r} ({exc})")
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
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
