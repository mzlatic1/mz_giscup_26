"""Geometry helpers for CRS-safe building-boundary work."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from giscup.models import Building


def ring_edges(coords: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return consecutive edges from a closed or open ring coordinate array."""
    if len(coords) < 2:
        return []
    if not np.allclose(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[0]])
    return [(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]


def make_building(building_id: int | str, polygon: Polygon) -> Building:
    """Build a :class:`Building` model from a Shapely polygon."""
    exterior = np.asarray(polygon.exterior.coords, dtype=np.float64)
    interiors = [np.asarray(ring.coords, dtype=np.float64) for ring in polygon.interiors]
    return Building(
        id=building_id,
        polygon=polygon,
        exterior_coords=exterior,
        exterior_edges=ring_edges(exterior),
        interiors=interiors,
        perimeter=float(polygon.length),
        area=float(polygon.area),
        bounds=tuple(float(v) for v in polygon.bounds),
    )


def is_point_on_any_boundary(
    point_xy: tuple[float, float], buildings: Iterable[Building], eps: float = 1e-8
) -> bool:
    """Return whether a point lies on any building boundary within `eps`.

    Linear scan. Use :class:`BoundaryIndex` when checking many points against the
    same building set -- at `k=1000` this costs 1.3e7 distance operations per block.
    """
    point = Point(point_xy)
    return any(b.polygon.boundary.distance(point) <= eps for b in buildings)


@dataclass(slots=True)
class BoundaryIndex:
    """STRtree over building boundaries for repeated legality checks.

    Antenna legality is checked once per antenna per validated block. A linear scan
    is O(buildings) per point; this narrows to the handful whose bounding box comes
    within `eps` of the point before doing any exact distance work.
    """

    buildings: list[Building]
    boundaries: list[BaseGeometry]
    tree: STRtree

    @classmethod
    def from_buildings(cls, buildings: list[Building]) -> "BoundaryIndex":
        boundaries = [b.polygon.boundary for b in buildings]
        return cls(buildings=buildings, boundaries=boundaries, tree=STRtree(boundaries))

    def is_on_any_boundary(self, point_xy: tuple[float, float], eps: float = 1e-8) -> bool:
        x, y = float(point_xy[0]), float(point_xy[1])
        # Expand the probe by eps so a point sitting just outside a boundary's
        # bounding box is still considered; the exact test below decides.
        probe = box(x - eps, y - eps, x + eps, y + eps)
        point = Point(x, y)
        for hit in self.tree.query(probe):
            boundary = self.boundaries[int(hit)] if isinstance(hit, Integral) else hit
            if boundary.distance(point) <= eps:
                return True
        return False


def total_bounds(buildings: Iterable[Building]) -> tuple[float, float, float, float]:
    """Compute aggregate bounds for a building collection."""
    bounds = np.asarray([b.bounds for b in buildings], dtype=np.float64)
    if bounds.size == 0:
        return (float("nan"), float("nan"), float("nan"), float("nan"))
    return (
        float(bounds[:, 0].min()),
        float(bounds[:, 1].min()),
        float(bounds[:, 2].max()),
        float(bounds[:, 3].max()),
    )


def segment_length(p0: np.ndarray, p1: np.ndarray) -> float:
    """Euclidean length of a two-point segment in projected coordinates."""
    return float(np.linalg.norm(p1 - p0))
