"""Line-of-sight visibility predicates and spatial blocker index."""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from giscup.models import Building, PointLike

STRATEGIES = ("relate", "negative_buffer", "hybrid")


@dataclass(slots=True)
class BlockerIndex:
    """STRtree wrapper for building footprint blocker queries.

    Also owns the per-epsilon eroded-geometry cache. Erosion is a function of
    (building, eps) only, so it is computed once per index rather than once per
    predicate call -- `buffer(-eps)` inside the visibility loop was previously
    the dominant cost of the `negative_buffer` and `hybrid` strategies.
    """

    buildings: list[Building]
    tree: STRtree
    _eroded: dict[float, list[BaseGeometry]] = field(default_factory=dict, repr=False)
    _degenerate: dict[float, str | None] = field(default_factory=dict, repr=False)

    @classmethod
    def from_buildings(cls, buildings: list[Building]) -> "BlockerIndex":
        return cls(buildings=buildings, tree=STRtree([b.polygon for b in buildings]))

    def query_indices(self, line: LineString) -> list[int]:
        """Return positional indices of buildings whose bbox intersects `line`."""
        hits = self.tree.query(line)
        out: list[int] = []
        for hit in hits:
            if isinstance(hit, Integral):
                out.append(int(hit))
            else:
                # Shapely variants may return geometries. Use identity fallback.
                for i, building in enumerate(self.buildings):
                    if building.polygon is hit or building.polygon.equals(hit):
                        out.append(i)
                        break
        return out

    def query(self, line: LineString) -> list[Building]:
        return [self.buildings[i] for i in self.query_indices(line)]

    def eroded_polygons(self, eps: float, strict: bool = True) -> list[BaseGeometry]:
        """Return buildings eroded by `eps`, aligned with `self.buildings`.

        Memoized per `eps`; the returned list must not be mutated by callers.

        With `strict` (the default), raises if erosion degenerated. At projected-CRS
        magnitudes (EPSG:32611 is ~5e5, 3.7e6) an `eps` of 1e-9 is below float64
        relative precision, and `buffer(-eps)` collapses whole buildings to empty.
        An empty eroded polygon blocks nothing, so `negative_buffer` would silently
        report every pair as visible and over-claim every building.

        `hybrid` passes `strict=False`: it ORs with `relate`, which stays correct at
        any magnitude, so degenerate erosion costs it work but never an answer.
        """
        cached = self._eroded.get(eps)
        if cached is None:
            cached = [b.polygon.buffer(-eps) for b in self.buildings]
            self._eroded[eps] = cached
            self._degenerate[eps] = self._degeneracy_reason(eps, cached)
        if strict:
            reason = self._degenerate[eps]
            if reason is not None:
                raise ValueError(reason)
        return cached

    def _degeneracy_reason(self, eps: float, eroded: list[BaseGeometry]) -> str | None:
        """Report the first footprint that vanished under erosion but should not have."""
        # A footprint far larger than eps^2 cannot legitimately vanish under
        # erosion by eps; if it did, the buffer lost all precision.
        floor = (4.0 * eps) ** 2
        for building, shrunk in zip(self.buildings, eroded, strict=True):
            if shrunk.is_empty and building.area > floor:
                return (
                    f"building {building.id!r} (area {building.area:.6g}) eroded to empty at "
                    f"eps={eps:g}: buffer(-eps) lost all precision at these coordinate "
                    f"magnitudes, which would report every pair as visible. "
                    f"Use strategy='relate' (the exact official predicate) or a larger eps."
                )
        return None


def _blocked_relate(line: LineString, polygon: BaseGeometry) -> bool:
    """Official predicate: interior of the segment meets interior of the polygon."""
    return bool(line.crosses(polygon) or line.within(polygon) or line.relate_pattern(polygon, "T********"))


def _blocked_eroded(line: LineString, eroded: BaseGeometry) -> bool:
    return (not eroded.is_empty) and bool(line.intersects(eroded))


def is_visible(
    a: PointLike,
    b: PointLike,
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
) -> bool:
    """Return whether `a` and `b` have line of sight under GIS Cup rules.

    Boundary-only contact is not blocking; intersection with any building interior is blocking.

    `relate` is the default: `relate_pattern(poly, "T********")` is exactly the official
    predicate, and it agrees with the other strategies across the full degeneracy set
    (see `tests/test_visibility_strategy.py`) while being materially faster.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of: {', '.join(STRATEGIES)}")
    if a == b:
        return True
    line = LineString([a, b])
    indices = blocker_index.query_indices(line)
    if not indices:
        return True

    if strategy == "relate":
        polygons = blocker_index.buildings
        return not any(_blocked_relate(line, polygons[i].polygon) for i in indices)

    if strategy == "negative_buffer":
        eroded = blocker_index.eroded_polygons(eps)
        return not any(_blocked_eroded(line, eroded[i]) for i in indices)

    eroded = blocker_index.eroded_polygons(eps, strict=False)
    buildings = blocker_index.buildings
    return not any(
        _blocked_eroded(line, eroded[i]) or _blocked_relate(line, buildings[i].polygon) for i in indices
    )
