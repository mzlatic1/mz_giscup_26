"""Line-of-sight visibility predicate and spatial blocker index.

There is exactly one predicate, and it is the official one:
`line.relate_pattern(polygon, "T********")` asks whether the interior of the segment
meets the interior of the polygon, which is precisely the GIS Cup blocking rule.
Boundary-only contact, tangency, and vertex touches do not block.

Two alternative strategies (`negative_buffer`, `hybrid`) were removed on 2026-08-08
(task board #10):

- `hybrid` was measured identical to `relate` across 1,200 full-scale pairs and the
  whole degeneracy set, but ran 1.16-1.40x slower. Pure waste.
- `negative_buffer` was actively dangerous. It eroded footprints by `eps` and tested
  intersection with the result, but at EPSG:32611 magnitudes (~5e5, 3.7e6) an `eps`
  of 1e-9 sits below float64 relative precision, so `buffer(-eps)` collapsed whole
  buildings to empty. Empty geometry blocks nothing, so it reported *every* pair as
  visible -- 56/400 disagreements with `relate` on real-magnitude data. Because
  `validate-output` accepted the same strategy flag, solving and validating on it
  would have produced a garbage solution that validated clean.

Keeping one correct predicate removes the choice, and with it the chance of choosing
wrong on the single submission.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from giscup.models import Building, PointLike

STRATEGIES = ("relate",)


@dataclass(slots=True)
class BlockerIndex:
    """STRtree wrapper for building footprint blocker queries."""

    buildings: list[Building]
    tree: STRtree

    @classmethod
    def from_buildings(cls, buildings: list[Building]) -> "BlockerIndex":
        return cls(buildings=buildings, tree=STRtree([b.polygon for b in buildings]))

    def query_indices(self, line: BaseGeometry) -> list[int]:
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

    def query(self, line: BaseGeometry) -> list[Building]:
        return [self.buildings[i] for i in self.query_indices(line)]


def _blocked(line: LineString, polygon: BaseGeometry) -> bool:
    """Official predicate: interior of the segment meets interior of the polygon."""
    return bool(line.relate_pattern(polygon, "T********"))


def is_visible(
    a: PointLike,
    b: PointLike,
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
) -> bool:
    """Return whether `a` and `b` have line of sight under GIS Cup rules.

    Boundary-only contact is not blocking; intersection with any building interior is
    blocking.

    `strategy` accepts only `"relate"`. It is retained as a parameter so that callers
    and the visibility-matrix cache key keep a stable shape.

    `eps` is accepted and **ignored**. It only ever fed the removed erosion strategies.
    It is kept because `matrix.MatrixSpec` records it in the cache key, and dropping it
    would invalidate every matrix already built -- 110 minutes of work at full scale for
    no behavioural gain.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"strategy must be one of: {', '.join(STRATEGIES)}; got {strategy!r}. "
            "negative_buffer and hybrid were removed 2026-08-08 -- see task board #10."
        )
    if a == b:
        return True
    line = LineString([a, b])
    buildings = blocker_index.buildings
    return not any(_blocked(line, buildings[i].polygon) for i in blocker_index.query_indices(line))
