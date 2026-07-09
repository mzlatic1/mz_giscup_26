"""Diagnostics helpers for inspect and solve runs."""

from __future__ import annotations

import statistics
from typing import Any

from giscup.geometry import total_bounds
from giscup.models import Building, DatasetInfo


def dataset_summary(buildings: list[Building], info: DatasetInfo) -> dict[str, Any]:
    perimeters = [b.perimeter for b in buildings]
    areas = [b.area for b in buildings]
    vertices = [max(0, len(b.exterior_coords) - 1) for b in buildings]
    return {
        "path": info.path,
        "crs": info.crs,
        "feature_count": info.feature_count,
        "geometry_types": info.geometry_types,
        "id_property": info.id_property,
        "bounds": total_bounds(buildings),
        "holes_count": sum(len(b.interiors) for b in buildings),
        "area": _stats(areas),
        "perimeter": _stats(perimeters),
        "exterior_vertices": _stats(vertices),
    }


def _stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None, "sum": 0}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "max": max(values),
        "sum": sum(values),
    }
