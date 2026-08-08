"""Boundary-point jitter at projected-CRS magnitudes (task board #14).

Sample and candidate points are computed by interpolation: `p0 + t*(p1 - p0)`. In
float64 at UTM 11N magnitudes (~5e5, 3.7e6) that lands a few times 1e-11 m off the
true edge line -- randomly INSIDE or OUTSIDE the polygon.

When such a point lands inside, every segment ending there has its interior dipping
into the polygon interior, so the official predicate reports it blocked. The point
becomes invisible from everything, including a candidate two metres away on its own
edge. Measured on the official dataset, that made **32% of all samples permanently
unseeable** and depressed every coverage figure by roughly a third.

The invariant below is the one that was violated, and it is the cheapest possible
statement of correctness: a point on a building's boundary must be visible from
somewhere on that same boundary. If that fails, nothing downstream can be trusted.
"""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from giscup.candidates import generate_boundary_candidates
from giscup.geometry import make_building
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.visibility import BlockerIndex, is_visible

# Real EPSG:32611 magnitudes. The bug is invisible at unit-square coordinates.
X0, Y0 = 500_000.0, 3_700_000.0
PROFILE = SamplingProfile("jitter", 3.0, 4)


def _utm_block(n: int = 6) -> list:
    """A small grid of buildings at UTM magnitudes, sized like real footprints."""
    polys = []
    for i in range(n):
        x = X0 + (i % 3) * 40.0
        y = Y0 + (i // 3) * 40.0
        polys.append(
            Polygon([
                (x + 0.246350914647337, y + 0.4007992023),
                (x + 13.418273645102, y + 0.1839274650),
                (x + 13.093827461029, y + 16.6273940182),
                (x + 0.019283746501, y + 16.8203847100),
            ])
        )
    return [make_building(i, p) for i, p in enumerate(polys)]


def test_interpolated_boundary_points_do_land_inside():
    """Establishes the premise: this is a real numerical effect, not a hypothetical."""
    buildings = _utm_block()
    samples = sample_boundaries(buildings, PROFILE)
    polygons = {b.id: b.polygon for b in buildings}
    inside = [s for s in samples if polygons[s.building_id].contains(Point(s.x, s.y))]
    assert inside, "expected some interpolated samples to land microscopically inside"
    # They are inside by a numerically trivial amount -- this is jitter, not geometry.
    worst = max(polygons[s.building_id].boundary.distance(Point(s.x, s.y)) for s in inside)
    assert worst < 1e-6, f"displacement {worst:g} is too large to be float jitter"


def test_every_sample_is_visible_from_its_own_building():
    """THE invariant. A point on a boundary must be seeable from that same boundary."""
    buildings = _utm_block()
    samples = sample_boundaries(buildings, PROFILE)
    candidates = generate_boundary_candidates(buildings, mode="basic")
    index = BlockerIndex.from_buildings(buildings)

    own = {}
    for c in candidates:
        own.setdefault(c.source_building_id, []).append(c)

    unseen = [
        s
        for s in samples
        if not any(is_visible(c.point, s.point, index) for c in own[s.building_id])
    ]
    assert not unseen, (
        f"{len(unseen)} of {len(samples)} samples are invisible from their own building; "
        "boundary-point jitter is being treated as interior penetration"
    )


def test_a_point_a_hair_inside_is_still_visible_along_its_edge():
    """Minimal reproduction, with the displacement constructed explicitly."""
    poly = Polygon([(X0, Y0), (X0 + 13.4, Y0), (X0 + 13.4, Y0 + 16.6), (X0, Y0 + 16.6)])
    index = BlockerIndex.from_buildings([make_building(0, poly)])

    # ONE floating-point step inside the left edge -- the smallest displacement that
    # can exist at these magnitudes. 1e-11 would round away entirely: the ULP at
    # x=5e5 is about 5.8e-11.
    hair_inside = (np.nextafter(X0, X0 + 1), Y0 + 8.0)
    assert poly.contains(Point(*hair_inside)), "expected one ULP inward to be inside"
    assert poly.boundary.distance(Point(*hair_inside)) < 1e-9
    assert is_visible((X0, Y0), hair_inside, index) is True
    assert is_visible((X0, Y0 + 16.6), hair_inside, index) is True


def test_genuine_interior_crossings_still_block():
    """The tolerance must not make the predicate permissive where it matters."""
    poly = Polygon([(X0, Y0), (X0 + 13.4, Y0), (X0 + 13.4, Y0 + 16.6), (X0, Y0 + 16.6)])
    index = BlockerIndex.from_buildings([make_building(0, poly)])
    # Straight through the middle, and corner to opposite corner.
    assert is_visible((X0 - 5, Y0 + 8.0), (X0 + 18.4, Y0 + 8.0), index) is False
    assert is_visible((X0, Y0), (X0 + 13.4, Y0 + 16.6), index) is False


def test_a_blocker_between_two_buildings_still_blocks():
    buildings = _utm_block()
    index = BlockerIndex.from_buildings(buildings)
    # Building 0 spans x in [X0, X0+13.4]; look through it from outside to outside.
    assert is_visible((X0 - 10, Y0 + 8.0), (X0 + 25, Y0 + 8.0), index) is False


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ((X0, Y0), (X0 + 13.4, Y0), True),          # along an edge
        ((X0 - 5, Y0 - 5), (X0, Y0), True),         # vertex touch
        ((X0 - 5, Y0), (X0 + 18.4, Y0), True),      # collinear with an edge
        ((X0, Y0), (X0 - 5, Y0 - 5), True),         # ray outward from a vertex
    ],
)
def test_official_degeneracies_hold_at_utm_magnitudes(a, b, expected):
    poly = Polygon([(X0, Y0), (X0 + 13.4, Y0), (X0 + 13.4, Y0 + 16.6), (X0, Y0 + 16.6)])
    index = BlockerIndex.from_buildings([make_building(0, poly)])
    assert is_visible(a, b, index) is expected
