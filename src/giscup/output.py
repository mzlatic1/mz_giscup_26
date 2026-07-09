"""Official GIS Cup solution formatting and parsing."""

from __future__ import annotations

import re

from giscup.models import Solution

_POINT_RE = re.compile(r"\(([^,]+),\s*([^\)]+)\)")


def format_float(value: float) -> str:
    """Format a coordinate with IEEE-754-double-friendly precision."""
    return format(float(value), ".17g")


def format_solution_block(solution: Solution) -> str:
    """Format one three-line GIS Cup subproblem block."""
    points = ", ".join(f"({format_float(x)}, {format_float(y)})" for x, y in solution.antenna_points)
    claimed = ", ".join(str(v) for v in solution.claimed_building_ids)
    return f"({solution.tau}, {solution.k})\n{points}\n{claimed}"


def format_solution_file(solutions: list[Solution]) -> str:
    """Format all solution blocks separated by blank lines."""
    return "\n\n".join(format_solution_block(s) for s in solutions) + "\n"


def parse_points(line: str) -> list[tuple[float, float]]:
    """Parse a GIS Cup coordinate line."""
    return [(float(x), float(y)) for x, y in _POINT_RE.findall(line)]
