"""Line-of-sight visibility predicate and spatial blocker index.

The official rule: a segment is blocked when it intersects the interior of a
building. Tangency, vertex contact, and boundary-only contact do not block.

Why the predicate carries a tolerance
-------------------------------------
Antenna candidates and boundary samples are produced by interpolation along edges:
`p0 + t*(p1 - p0)`. In float64 at projected-CRS magnitudes (EPSG:32611 is ~5e5,
3.7e6) the result lands within an ULP or so of the true edge line -- about 1e-10 m --
and lands **inside** the polygon roughly half the time. One ULP is the smallest
displacement that can exist there; it is not avoidable by computing more carefully.

Tested against the raw polygon, such a point makes every segment ending at it report
blocked, because the segment's interior genuinely does dip inside. The point becomes
invisible from everything, including a candidate two metres away on its own edge.
Measured on the official dataset this made **32% of all samples permanently
unseeable** and depressed every coverage figure by roughly a third.

So blocking is tested against the footprint eroded by `INTERIOR_TOLERANCE`: a segment
blocks when it penetrates more than a micrometre into the interior. That is the same
official rule stated in a way float64 can actually evaluate. A micrometre is five
orders of magnitude above the jitter and five orders below the smallest real
footprint, so nothing geometric rides on the exact value.

Note for the record: `negative_buffer` was removed in task #10 as a footgun because
at `eps=1e-9` it collapsed whole footprints to empty at these magnitudes. The
mechanism was right and the epsilon was wrong -- 1e-9 sits below float64 relative
precision at 3.7e6, 1e-6 does not. `_check_erosion` now makes that failure loud
instead of silent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from giscup.models import Building, PointLike

STRATEGIES = ("relate",)

# Depth of interior penetration required to block, in CRS units (metres).
# Far above interpolation jitter (~1e-10 m), far below any real footprint.
INTERIOR_TOLERANCE = 1e-6


@dataclass(slots=True)
class BlockerIndex:
    """STRtree over building footprints, with the eroded blocking geometry."""

    buildings: list[Building]
    tree: STRtree
    tolerance: float = INTERIOR_TOLERANCE
    _eroded: list[BaseGeometry] | None = field(default=None, repr=False)

    @classmethod
    def from_buildings(
        cls, buildings: list[Building], tolerance: float = INTERIOR_TOLERANCE
    ) -> "BlockerIndex":
        return cls(
            buildings=buildings,
            tree=STRtree([b.polygon for b in buildings]),
            tolerance=tolerance,
        )

    @property
    def eroded(self) -> list[BaseGeometry]:
        """Footprints shrunk by `tolerance`, computed once and reused.

        Erosion is a function of (building, tolerance) only, so it must never happen
        inside the visibility loop -- that was the original `buffer(-eps)` mistake.
        """
        if self._eroded is None:
            eroded = [b.polygon.buffer(-self.tolerance) for b in self.buildings]
            _check_erosion(self.buildings, eroded, self.tolerance)
            self._eroded = eroded
        return self._eroded

    def query_indices(self, geometry: BaseGeometry) -> list[int]:
        """Positional indices of buildings whose bbox intersects `geometry`."""
        out: list[int] = []
        for hit in self.tree.query(geometry):
            if isinstance(hit, Integral):
                out.append(int(hit))
            else:
                # Shapely variants may return geometries. Use identity fallback.
                for i, building in enumerate(self.buildings):
                    if building.polygon is hit or building.polygon.equals(hit):
                        out.append(i)
                        break
        return out

    def query(self, geometry: BaseGeometry) -> list[Building]:
        return [self.buildings[i] for i in self.query_indices(geometry)]


def _check_erosion(
    buildings: list[Building], eroded: list[BaseGeometry], tolerance: float
) -> None:
    """Fail loudly if erosion degenerated instead of silently blocking nothing.

    An empty eroded polygon blocks nothing, so a collapsed footprint would report
    every pair through it as visible and over-claim every building behind it.
    """
    floor = (4.0 * tolerance) ** 2
    for building, shrunk in zip(buildings, eroded, strict=True):
        if shrunk.is_empty and building.area > floor:
            raise ValueError(
                f"building {building.id!r} (area {building.area:.6g}) eroded to empty at "
                f"tolerance={tolerance:g}: the buffer lost all precision at these coordinate "
                f"magnitudes, which would report every pair through it as visible. "
                f"Use a larger tolerance."
            )


def is_visible(
    a: PointLike,
    b: PointLike,
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
) -> bool:
    """Return whether `a` and `b` have line of sight under GIS Cup rules.

    Blocking is tested against footprints eroded by the index's `tolerance`, so a
    segment must penetrate meaningfully into the interior rather than merely graze it
    or terminate an ULP inside. See the module docstring.

    `strategy` accepts only `"relate"`. `eps` is accepted and ignored; it is retained
    because `matrix.MatrixSpec` records it in the visibility-matrix cache key.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"strategy must be one of: {', '.join(STRATEGIES)}; got {strategy!r}"
        )
    if a == b:
        return True
    line = LineString([a, b])
    eroded = blocker_index.eroded
    for i in blocker_index.query_indices(line):
        shrunk = eroded[i]
        if not shrunk.is_empty and line.relate_pattern(shrunk, "T********"):
            return False
    return True
