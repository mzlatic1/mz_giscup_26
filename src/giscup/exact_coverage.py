"""Exact, grid-free boundary coverage (task board #13).

Why this replaces sampling for claim decisions
----------------------------------------------
`sampling.py` estimates coverage by testing segment midpoints and crediting each
segment's whole weight to that single verdict. Refining the grid moves sample points
across visibility boundaries, so the estimate **oscillates instead of converging** --
measured at up to 0.07 on one building. Any footprint within ~0.05 of `tau` is
therefore unclassifiable by sampling at any density we can afford, which is larger
than any usable claim margin.

The official rules define coverage continuously: "the ratio of the length of visible
segments on the boundary to the total perimeter", a segment being visible when every
point along it is visible from at least one antenna. This module computes that
directly.

How it works
------------
Visibility along an edge, seen from a fixed point `a`, is **piecewise constant**. Its
breakpoints occur exactly where the sight line grazes a blocker vertex: between two
consecutive such events nothing can enter or leave the line of sight. So for each
edge and antenna:

1. Cast a ray from `a` through every vertex of every nearby blocker and record where
   it crosses the edge. Those parameters, plus the edge's own endpoints, partition
   `[0, 1]` into intervals of constant visibility.
2. Test one interior point per interval with the exact official predicate. That
   verdict holds for the whole interval.
3. Union the visible intervals across all antennas, and sum their lengths.

The result has no grid and no tunable density, so the threshold instability that
motivated this task cannot occur. Extra breakpoints are harmless -- they only split
an interval into two pieces carrying the same verdict -- so the ray test is
deliberately permissive rather than trying to identify only true silhouette vertices.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from giscup.models import Building, PointLike
from giscup.visibility import BlockerIndex, is_visible

# Parameters closer than this along an edge are treated as the same breakpoint.
# Edge parameters are normalised to [0, 1], so this is relative to edge length.
PARAM_EPS = 1e-12

# An edge shorter than this (in CRS units) contributes nothing measurable. This is an
# ABSOLUTE length in metres, deliberately not a relative tolerance -- see the note in
# `visible_intervals_on_edge`.
DEGENERATE_EDGE_LENGTH = 1e-9


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _breakpoints(
    a: PointLike, p0: np.ndarray, p1: np.ndarray, vertices: np.ndarray
) -> list[float]:
    """Edge parameters where the sight line from `a` grazes a blocker vertex.

    Solves `p0 + t*(p1 - p0) = a + s*(v - a)` for `t`, keeping any `t` inside [0, 1].
    """
    if vertices.size == 0:
        return []
    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
    wx, wy = float(a[0] - p0[0]), float(a[1] - p0[1])

    ex = vertices[:, 0] - a[0]
    ey = vertices[:, 1] - a[1]
    denom = dx * ey - dy * ex
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (wx * ey - wy * ex) / denom
    ok = np.isfinite(t) & (t > 0.0) & (t < 1.0) & (np.abs(denom) > 0.0)
    return t[ok].tolist()


def _blocker_vertices(index: BlockerIndex, region: Polygon) -> np.ndarray:
    """Vertices of every building whose bounding box meets `region`."""
    chunks: list[np.ndarray] = []
    for i in index.query_indices(region):
        building = index.buildings[i]
        chunks.append(building.exterior_coords)
        chunks.extend(building.interiors)
    if not chunks:
        return np.empty((0, 2), dtype=np.float64)
    return np.vstack(chunks)


def visible_intervals_on_edge(
    a: PointLike,
    p0: PointLike | np.ndarray,
    p1: PointLike | np.ndarray,
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
) -> list[tuple[float, float]]:
    """Sub-intervals of edge `p0->p1`, in parameter space [0, 1], visible from `a`.

    Returned intervals are disjoint, ascending, and merged where adjacent.
    """
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    # Absolute length test, never a relative one. `np.allclose` defaults to
    # rtol=1e-5, which at UTM northings (~3.7e6) declares a 16 m edge degenerate
    # and silently returns no intervals -- the same relative-tolerance trap that
    # made buffer(-1e-9) collapse footprints in visibility.py.
    if float(np.hypot(p1[0] - p0[0], p1[1] - p0[1])) <= DEGENERATE_EDGE_LENGTH:
        return []

    # Only blockers meeting the triangle (a, p0, p1) can affect this edge.
    region = Polygon([(float(a[0]), float(a[1])), tuple(p0), tuple(p1)])
    if not region.is_valid:  # collinear a/p0/p1 gives a degenerate triangle
        region = region.buffer(0)
    vertices = _blocker_vertices(blocker_index, region)

    cuts = [0.0, 1.0]
    cuts.extend(_breakpoints(a, p0, p1, vertices))
    cuts.sort()

    intervals: list[tuple[float, float]] = []
    delta = p1 - p0
    for lo, hi in zip(cuts, cuts[1:], strict=False):
        if hi - lo <= PARAM_EPS:
            continue
        mid = 0.5 * (lo + hi)
        probe = p0 + mid * delta
        if is_visible(a, (float(probe[0]), float(probe[1])), blocker_index, strategy=strategy, eps=eps):
            if intervals and lo - intervals[-1][1] <= PARAM_EPS:
                intervals[-1] = (intervals[-1][0], hi)
            else:
                intervals.append((lo, hi))
    return intervals


def _merge(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for lo, hi in intervals[1:]:
        last_lo, last_hi = merged[-1]
        if lo <= last_hi + PARAM_EPS:
            merged[-1] = (last_lo, max(last_hi, hi))
        else:
            merged.append((lo, hi))
    return merged


def _building_edges(building: Building) -> list[tuple[np.ndarray, np.ndarray]]:
    """Every boundary edge, interior rings included.

    Interior rings are included so the numerator matches `Building.perimeter ==
    polygon.length`, which also includes them. See `docs/competition-reference.md`
    for why holes are handled defensively even though the official page excludes them.
    """
    from giscup.geometry import ring_edges

    edges = list(building.exterior_edges)
    for ring in building.interiors:
        edges.extend(ring_edges(ring))
    return edges


def exact_building_coverage(
    building: Building,
    antenna_points: list[PointLike],
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
    radius: float | None = None,
) -> float:
    """Exact visible-boundary fraction for one building.

    `radius` optionally skips antennas further than that from the edge. Unlike the
    solver's cull this is a pure optimisation over an exact computation, so set it
    generously or leave it `None`.
    """
    if not antenna_points or building.perimeter <= 0:
        return 0.0

    visible_length = 0.0
    for p0, p1 in _building_edges(building):
        edge_length = float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        if edge_length <= 0:
            continue
        pieces: list[tuple[float, float]] = []
        for a in antenna_points:
            if radius is not None:
                # Cheap reject: nearest endpoint further than radius + edge length
                # cannot contribute, since any point on the edge is within that.
                if min(
                    np.hypot(a[0] - p0[0], a[1] - p0[1]),
                    np.hypot(a[0] - p1[0], a[1] - p1[1]),
                ) > radius + edge_length:
                    continue
            pieces.extend(
                visible_intervals_on_edge(a, p0, p1, blocker_index, strategy=strategy, eps=eps)
            )
            if pieces and _merge(pieces) == [(0.0, 1.0)]:
                pieces = [(0.0, 1.0)]
                break  # edge already fully covered; further antennas cannot add
        visible_length += sum(hi - lo for lo, hi in _merge(pieces)) * edge_length

    return visible_length / building.perimeter


def exact_coverage_by_building(
    building_ids: list[int | str],
    antenna_points: list[PointLike],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    strategy: str = "relate",
    eps: float = 1e-9,
    radius: float | None = None,
) -> dict[int | str, float]:
    """Exact coverage for the requested buildings only.

    Cost scales with the selection, not the dataset, so this is affordable for the
    near-threshold band even though it is far too slow to run over every building.
    """
    wanted = set(building_ids)
    return {
        b.id: exact_building_coverage(
            b, antenna_points, blocker_index, strategy=strategy, eps=eps, radius=radius
        )
        for b in buildings
        if b.id in wanted
    }
