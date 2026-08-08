"""Exact interval-based coverage (task board #13).

Sampled coverage *does* converge to the exact value, but only at ~0.5 m spacing or
finer. The profiles actually in use -- `accurate` (5 m) and `final` (2.5 m) -- carry
errors up to 0.03 and move non-monotonically, which is enough to misclassify any
building within ~0.03 of `tau`. Exact coverage reaches the converged answer directly
and, measured on the mini dataset, faster than the sampling density needed to match it.

These tests pin coverage values known *analytically*, so they check exactness rather
than agreement with another approximation, plus a brute-force cross-check at real
projected magnitudes.

The reference cases use a unit square, where the answers are provable by inspection:
a segment lying along the boundary never enters the interior, and a segment from one
side to another always does.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.exact_coverage import (
    exact_building_coverage,
    exact_coverage_by_building,
    visible_intervals_on_edge,
)
import numpy as np

from giscup.geometry import make_building
from giscup.visibility import BlockerIndex, is_visible

UNIT = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])


def _square():
    building = make_building(0, UNIT)
    return building, BlockerIndex.from_buildings([building])


# --- analytically known coverages -------------------------------------------


def test_antenna_at_a_corner_sees_exactly_half_the_perimeter():
    """From (0,0): the two adjacent edges lie along the boundary and are fully
    visible; the two far edges are reachable only through the interior."""
    building, index = _square()
    assert exact_building_coverage(building, [(0.0, 0.0)], index) == pytest.approx(0.5)


def test_antenna_mid_edge_sees_exactly_one_quarter():
    """From (0.5,0): only its own edge is visible; every other point needs the interior."""
    building, index = _square()
    assert exact_building_coverage(building, [(0.5, 0.0)], index) == pytest.approx(0.25)


def test_antennas_at_all_four_corners_see_the_whole_perimeter():
    building, index = _square()
    points = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert exact_building_coverage(building, points, index) == pytest.approx(1.0)


def test_two_opposite_corners_see_the_whole_perimeter():
    """Each corner covers its two adjacent edges; opposite corners cover all four."""
    building, index = _square()
    assert exact_building_coverage(building, [(0.0, 0.0), (1.0, 1.0)], index) == pytest.approx(1.0)


def test_no_antennas_is_zero_coverage():
    building, index = _square()
    assert exact_building_coverage(building, [], index) == 0.0


# --- structural properties --------------------------------------------------


def test_coverage_is_monotone_in_the_antenna_set():
    building, index = _square()
    a = exact_building_coverage(building, [(0.0, 0.0)], index)
    b = exact_building_coverage(building, [(0.0, 0.0), (1.0, 1.0)], index)
    assert b >= a


def test_coverage_stays_in_the_unit_interval():
    building, index = _square()
    for points in ([(0.0, 0.0)], [(0.5, 0.0), (0.5, 1.0)], [(1.0, 1.0)] * 5):
        ratio = exact_building_coverage(building, points, index)
        assert 0.0 <= ratio <= 1.0


def test_duplicate_antennas_do_not_inflate_coverage():
    building, index = _square()
    once = exact_building_coverage(building, [(0.0, 0.0)], index)
    thrice = exact_building_coverage(building, [(0.0, 0.0)] * 3, index)
    assert once == pytest.approx(thrice)


# --- interval mechanics -----------------------------------------------------


def test_an_edge_fully_visible_returns_one_whole_interval():
    _, index = _square()
    intervals = visible_intervals_on_edge((0.0, 0.0), (0.0, 0.0), (1.0, 0.0), index)
    assert intervals == [pytest.approx((0.0, 1.0))]


def test_an_edge_fully_hidden_returns_nothing():
    _, index = _square()
    # The top edge is unreachable from the bottom-left corner except at its endpoint.
    intervals = visible_intervals_on_edge((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), index)
    assert sum(hi - lo for lo, hi in intervals) == pytest.approx(0.0)


def test_partial_occlusion_splits_an_edge():
    """A blocker between the antenna and a wall must carve a shadow out of it."""
    wall = make_building(0, Polygon([(0, 10), (10, 10), (10, 11), (0, 11)]))
    blocker = make_building(1, Polygon([(4, 4), (6, 4), (6, 6), (4, 6)]))
    index = BlockerIndex.from_buildings([wall, blocker])
    intervals = visible_intervals_on_edge((5.0, 0.0), (0.0, 10.0), (10.0, 10.0), index)
    covered = sum(hi - lo for lo, hi in intervals)
    assert 0.0 < covered < 1.0, "the blocker must hide part of the wall but not all of it"
    assert len(intervals) == 2, "the shadow should fall in the middle, leaving two lit pieces"


# --- the property that motivated this task ----------------------------------


def test_exact_coverage_has_no_grid_to_be_unstable_against():
    """The whole point of #13: one value, not one value per sampling density.

    `exact_building_coverage` takes no profile and no spacing, so the +/-0.07
    oscillation that made near-tau claims unreliable cannot occur.
    """
    building, index = _square()
    values = {exact_building_coverage(building, [(0.0, 0.0)], index) for _ in range(3)}
    assert len(values) == 1
    assert values.pop() == pytest.approx(0.5)


def test_edges_at_utm_magnitudes_are_not_treated_as_degenerate():
    """Regression: `np.allclose` defaults to a RELATIVE tolerance of 1e-5.

    At UTM 11N northings (~3.7e6) a 16 m vertical edge differs by only 4.5e-6
    relatively, so a relative degeneracy test silently declared real edges
    zero-length and returned no visible intervals. Only vertical edges broke,
    because eastings (~5e5) are an order of magnitude smaller. Unit-square tests at
    coordinates near 1 cannot catch this.
    """
    x, y = 500_240.0, 3_700_000.0
    poly = Polygon([(x - 13.4, y), (x, y), (x, y + 16.6), (x - 13.4, y + 16.6)])
    building = make_building(0, poly)
    index = BlockerIndex.from_buildings([building])

    # A vertical edge, viewed from a point collinear with it: fully visible.
    intervals = visible_intervals_on_edge((x, y + 80.0), (x, y + 16.6), (x, y), index)
    assert sum(hi - lo for lo, hi in intervals) == pytest.approx(1.0)

    # And the whole building from its four corners, as in the unit-square case.
    corners = [(x - 13.4, y), (x, y), (x, y + 16.6), (x - 13.4, y + 16.6)]
    assert exact_building_coverage(building, corners, index) == pytest.approx(1.0)


def test_exact_matches_brute_force_at_utm_magnitudes():
    """Ground truth by dense enumeration, at coordinates where the bug lived."""
    x, y = 500_000.0, 3_700_000.0
    a = make_building(0, Polygon([(x, y), (x + 14, y), (x + 14, y + 17), (x, y + 17)]))
    b = make_building(1, Polygon([(x + 40, y), (x + 54, y), (x + 54, y + 17), (x + 40, y + 17)]))
    index = BlockerIndex.from_buildings([a, b])
    points = [(x + 40.0, y), (x + 7.0, y + 17.0)]

    exact = exact_building_coverage(a, points, index)

    n = 4000
    visible_length = 0.0
    for p0, p1 in a.exterior_edges:
        seg = float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        hits = 0
        for i in range(n):
            t = (i + 0.5) / n
            q = p0 + t * (p1 - p0)
            if any(is_visible(pt, (float(q[0]), float(q[1])), index) for pt in points):
                hits += 1
        visible_length += seg * hits / n
    brute = visible_length / a.perimeter

    assert exact == pytest.approx(brute, abs=2e-3)


def test_coverage_by_building_matches_single_building_calls():
    b0 = make_building(0, UNIT)
    b1 = make_building(1, Polygon([(5, 0), (6, 0), (6, 1), (5, 1)]))
    index = BlockerIndex.from_buildings([b0, b1])
    points = [(0.0, 0.0), (5.0, 0.0)]
    bulk = exact_coverage_by_building([0, 1], points, [b0, b1], index)
    assert bulk[0] == pytest.approx(exact_building_coverage(b0, points, index))
    assert bulk[1] == pytest.approx(exact_building_coverage(b1, points, index))
