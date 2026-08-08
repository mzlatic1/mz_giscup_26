"""Emitted antennas must not sit inside a footprint (task board #15).

Antenna candidates at edge midpoints are computed as `(p0 + p1) / 2`. At EPSG:32611
magnitudes that lands ~1e-10 m off the true edge, and **37.4% of midpoints land
inside** their own polygon (measured on the official dataset; vertices are exact
because they are copied from the source data).

Such a point is perfectly *legal* -- 1e-10 m is far inside the official eps of
1e-8..1e-7, so `boundary.distance(pt) <= eps` passes. The risk is different: an
evaluator that computes visibility against the raw polygon would see nothing at all
from an antenna a hair inside it, exactly as our own solver did before #14.

We cannot know how the official evaluator computes visibility, and there is one
submission with no feedback. So emitted antennas are nudged to be provably outside
(or exactly on) the boundary. The displacement is ~1e-9 m: geometrically irrelevant,
still well within the legality tolerance, and it removes the dependency on someone
else's numerical choices.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon

from giscup.geometry import make_building
from giscup.output import nudge_off_interior

X0, Y0 = 500_000.0, 3_700_000.0


def _building():
    poly = Polygon(
        [
            (X0 + 0.246350914647337, Y0 + 0.4007992023),
            (X0 + 13.418273645102, Y0 + 0.1839274650),
            (X0 + 13.093827461029, Y0 + 16.6273940182),
            (X0 + 0.019283746501, Y0 + 16.8203847100),
        ]
    )
    return make_building(0, poly), poly


def _midpoints(poly: Polygon):
    coords = list(poly.exterior.coords)
    return [
        ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        for a, b in zip(coords, coords[1:], strict=False)
    ]


def test_the_premise_some_midpoints_land_inside():
    _, poly = _building()
    inside = [m for m in _midpoints(poly) if poly.contains(Point(m))]
    assert inside, "expected at least one edge midpoint to land microscopically inside"


def test_nudged_points_are_never_strictly_inside():
    building, poly = _building()
    for m in _midpoints(poly):
        out = nudge_off_interior(m, [building])
        assert not poly.contains(Point(out)), f"{m} -> {out} is still inside"


def test_nudge_moves_the_point_only_imperceptibly():
    building, poly = _building()
    for m in _midpoints(poly):
        out = nudge_off_interior(m, [building])
        assert Point(m).distance(Point(out)) < 1e-6


def test_nudged_points_remain_legal_antennas():
    """Still within the official boundary tolerance after nudging."""
    building, poly = _building()
    for m in _midpoints(poly):
        out = nudge_off_interior(m, [building])
        assert poly.boundary.distance(Point(out)) <= 1e-8


def test_points_already_outside_are_returned_unchanged():
    building, poly = _building()
    coords = list(poly.exterior.coords)
    for vertex in coords[:-1]:
        assert nudge_off_interior(vertex, [building]) == vertex


def test_nudge_does_not_push_into_a_neighbouring_building():
    """A point between two near-touching footprints must escape both."""
    a = Polygon([(X0, Y0), (X0 + 10, Y0), (X0 + 10, Y0 + 10), (X0, Y0 + 10)])
    b = Polygon([(X0 + 10, Y0), (X0 + 20, Y0), (X0 + 20, Y0 + 10), (X0 + 10, Y0 + 10)])
    buildings = [make_building(0, a), make_building(1, b)]
    shared_edge_mid = (X0 + 10.0, Y0 + 5.0)
    out = nudge_off_interior(shared_edge_mid, buildings)
    assert not a.contains(Point(out))
    assert not b.contains(Point(out))


@pytest.mark.parametrize("point", [(X0 - 50.0, Y0 - 50.0), (X0 + 500.0, Y0)])
def test_points_far_from_any_building_are_untouched(point):
    building, _ = _building()
    assert nudge_off_interior(point, [building]) == point
