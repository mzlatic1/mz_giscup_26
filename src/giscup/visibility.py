"""Line-of-sight visibility predicates and spatial blocker index."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

from shapely.geometry import LineString
from shapely.strtree import STRtree

from giscup.models import Building, PointLike


@dataclass(slots=True)
class BlockerIndex:
    """STRtree wrapper for building footprint blocker queries."""

    buildings: list[Building]
    tree: STRtree

    @classmethod
    def from_buildings(cls, buildings: list[Building]) -> "BlockerIndex":
        return cls(buildings=buildings, tree=STRtree([b.polygon for b in buildings]))

    def query(self, line: LineString) -> list[Building]:
        hits = self.tree.query(line)
        out: list[Building] = []
        for hit in hits:
            if isinstance(hit, Integral):
                out.append(self.buildings[hit])
            else:
                # Shapely variants may return geometries. Use identity fallback.
                for building in self.buildings:
                    if building.polygon is hit or building.polygon.equals(hit):
                        out.append(building)
                        break
        return out


def _blocked_relate(line: LineString, building: Building) -> bool:
    poly = building.polygon
    return bool(line.crosses(poly) or line.within(poly) or line.relate_pattern(poly, "T********"))


def _blocked_negative_buffer(line: LineString, building: Building, eps: float) -> bool:
    interior = building.polygon.buffer(-eps)
    return (not interior.is_empty) and bool(line.intersects(interior))


def is_visible(
    a: PointLike,
    b: PointLike,
    blocker_index: BlockerIndex,
    strategy: str = "hybrid",
    eps: float = 1e-9,
) -> bool:
    """Return whether `a` and `b` have line of sight under GIS Cup rules.

    Boundary-only contact is not blocking; intersection with any building interior is blocking.
    """
    if a == b:
        return True
    line = LineString([a, b])
    for building in blocker_index.query(line):
        if strategy == "relate":
            blocked = _blocked_relate(line, building)
        elif strategy == "negative_buffer":
            blocked = _blocked_negative_buffer(line, building, eps)
        elif strategy == "hybrid":
            blocked = _blocked_negative_buffer(line, building, eps) or _blocked_relate(line, building)
        else:
            raise ValueError("strategy must be one of: relate, negative_buffer, hybrid")
        if blocked:
            return False
    return True
