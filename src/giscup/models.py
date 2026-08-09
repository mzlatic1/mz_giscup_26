"""Typed data models for the GIS Cup solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from shapely.geometry import Polygon

PointLike = tuple[float, float]


@dataclass(slots=True)
class Building:
    """A building footprint and precomputed boundary metadata."""

    id: int | str
    polygon: Polygon
    exterior_coords: np.ndarray
    exterior_edges: list[tuple[np.ndarray, np.ndarray]]
    interiors: list[np.ndarray]
    perimeter: float
    area: float
    bounds: tuple[float, float, float, float]


@dataclass(slots=True)
class Candidate:
    """A legal antenna candidate generated from a building boundary."""

    id: int
    x: float
    y: float
    source_building_id: int | str
    source_edge_index: int | None
    kind: str

    @property
    def point(self) -> PointLike:
        return (self.x, self.y)


@dataclass(slots=True)
class BoundarySample:
    """A weighted sample representing a segment of building boundary."""

    id: int
    x: float
    y: float
    building_id: int | str
    edge_index: int
    weight: float

    @property
    def point(self) -> PointLike:
        return (self.x, self.y)


@dataclass(slots=True)
class Solution:
    """A solution for one `(tau, k)` subproblem."""

    tau: float
    k: int
    antenna_points: list[PointLike]
    claimed_building_ids: list[int | str]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetInfo:
    """Dataset metadata captured during loading/inspection."""

    path: str
    crs: str | None
    feature_count: int
    geometry_types: list[str]
    id_property: str
    #: True when `id_property` was absent and building IDs fell back to the row index.
    #: Legitimate for a dataset with no ID field, catastrophic otherwise -- every
    #: claimed ID would be wrong while the output still passes every structural check.
    id_fallback_used: bool = False
