"""Official GIS Cup solution formatting and parsing."""

from __future__ import annotations

import re

from giscup.models import Solution

_POINT_RE = re.compile(r"\(([^,]+),\s*([^\)]+)\)")


def format_float(value: float) -> str:
    """Format a coordinate with IEEE-754-double-friendly precision."""
    return format(float(value), ".17g")


def _sorted_ids(ids: list[int | str]) -> list[int | str]:
    """Claim IDs in a stable, canonical order.

    The spec imposes no order, but upstream `claimed` is a set, so today's order is
    incidental. Sorting is free and makes the file reproducible -- the bundle ships
    source, so an evaluator may re-run and diff.

    Numeric IDs sort numerically: lexicographic order would place 1200 before 7, which
    reads as corrupted output. `Building.id` is typed `int | str`, so non-numeric IDs
    fall back to string order rather than raising on a mixed comparison.
    """
    try:
        return sorted(ids, key=lambda v: (0, float(v), ""))
    except (TypeError, ValueError):
        return sorted(ids, key=str)


def format_solution_block(solution: Solution) -> str:
    """Format one three-line GIS Cup subproblem block."""
    if len(solution.antenna_points) != solution.k:
        raise ValueError(
            f"solution for (tau={solution.tau}, k={solution.k}) has "
            f"{len(solution.antenna_points)} antenna points"
        )
    points = ", ".join(f"({format_float(x)}, {format_float(y)})" for x, y in solution.antenna_points)
    claimed = ", ".join(str(v) for v in _sorted_ids(solution.claimed_building_ids))
    return f"({solution.tau}, {solution.k})\n{points}\n{claimed}"


def format_solution_file(solutions: list[Solution]) -> str:
    """Format all solution blocks, three lines each, with no separators.

    Nine subproblems produce exactly 27 lines. Blocks are NOT separated by blank lines,
    despite that reading more nicely: the official spec is "three lines per sub-problem",
    so an evaluator reading three lines at a time misaligns on the first separator and
    every subsequent block shifts.

    The separators are also ambiguous, which is what settles it. The spec allows an empty
    third line ("may be empty but must still exist"). A block claiming nothing, followed
    by a separator, yields two consecutive blank lines that no parser can tell apart.
    The two features cannot coexist.
    """
    return "\n".join(format_solution_block(s) for s in solutions) + "\n"


def parse_points(line: str) -> list[tuple[float, float]]:
    """Parse a GIS Cup coordinate line."""
    return [(float(x), float(y)) for x, y in _POINT_RE.findall(line)]


def nudge_off_interior(
    point: tuple[float, float],
    buildings: list,
    step: float = 1e-9,
    max_steps: int = 8,
) -> tuple[float, float]:
    """Return `point`, moved just outside any footprint whose interior contains it.

    Antenna candidates at edge midpoints are computed as `(p0 + p1) / 2`, which at
    projected-CRS magnitudes lands ~1e-10 m off the true edge -- inside the polygon
    about 37% of the time. Such a point is legal (far within the official eps of
    1e-8..1e-7) but an evaluator computing visibility against the raw polygon would
    see nothing from it, exactly as this solver did before task #14.

    The nudge is ~1e-9 m: geometrically irrelevant, still inside the legality
    tolerance, and it removes any dependence on how the official evaluator handles
    points that sit an ULP inside a footprint.

    Points already outside every footprint are returned unchanged, so this is a no-op
    for the vertex candidates that make up half the pool.
    """
    from shapely.geometry import Point

    x, y = float(point[0]), float(point[1])
    probe = Point(x, y)
    containing = [b for b in buildings if b.polygon.contains(probe)]
    if not containing:
        return point

    # Move away from the offending footprint's nearest boundary point. That direction
    # is outward by construction, and repeating it escapes a shared edge where two
    # footprints meet.
    for _ in range(max_steps):
        polygon = containing[0].polygon
        nearest = polygon.boundary.interpolate(polygon.boundary.project(Point(x, y)))
        dx, dy = x - nearest.x, y - nearest.y
        norm = (dx * dx + dy * dy) ** 0.5
        if norm == 0.0:
            # Exactly on the boundary numerically; push along the outward normal of
            # the nearest edge instead, approximated by the centroid direction.
            cx, cy = polygon.centroid.x, polygon.centroid.y
            dx, dy = x - cx, y - cy
            norm = (dx * dx + dy * dy) ** 0.5
            if norm == 0.0:
                return (x, y)
        x += step * dx / norm
        y += step * dy / norm
        probe = Point(x, y)
        containing = [b for b in buildings if b.polygon.contains(probe)]
        if not containing:
            break
    return (x, y)
