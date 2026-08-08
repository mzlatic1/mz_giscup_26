"""Scaling fixes for the validation path (task board #7).

Validation is the only correctness signal that exists in a one-shot competition, so
it has to be both fast enough to run on all nine blocks and provably equivalent to
the naive implementation it replaces. Every test here pins equivalence, not just speed.
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import Polygon

from giscup.geometry import BoundaryIndex, is_point_on_any_boundary, make_building
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.validate import visible_sample_ids_from_points
from giscup.visibility import BlockerIndex, is_visible

PROFILE = SamplingProfile("test", 6.0, 4)


def _scene():
    polys = []
    for row_y in (0.0, 40.0):
        for i in range(3):
            x = i * 30.0
            polys.append(Polygon([(x, row_y), (x + 12, row_y), (x + 12, row_y + 12), (x, row_y + 12)]))
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return buildings, sample_boundaries(buildings, PROFILE)


@pytest.fixture(scope="module")
def scene():
    return _scene()


# --- boundary legality ------------------------------------------------------


def test_boundary_index_agrees_with_linear_scan(scene):
    buildings, samples = scene
    index = BoundaryIndex.from_buildings(buildings)
    probes = [(s.x, s.y) for s in samples]
    probes += [(-50.0, -50.0), (6.0, 6.0), (1000.0, 1000.0), (0.0, 0.0), (12.0, 12.0)]
    for point in probes:
        assert index.is_on_any_boundary(point) is is_point_on_any_boundary(point, buildings)


def test_boundary_index_accepts_every_sample_point(scene):
    """Samples are generated on boundaries, so all of them must be legal."""
    buildings, samples = scene
    index = BoundaryIndex.from_buildings(buildings)
    assert all(index.is_on_any_boundary((s.x, s.y)) for s in samples)


def test_boundary_index_rejects_interior_and_exterior_points(scene):
    buildings, _ = scene
    index = BoundaryIndex.from_buildings(buildings)
    assert index.is_on_any_boundary((6.0, 6.0)) is False  # inside building 0
    assert index.is_on_any_boundary((-20.0, -20.0)) is False  # far outside


def test_boundary_index_respects_epsilon(scene):
    buildings, _ = scene
    index = BoundaryIndex.from_buildings(buildings)
    just_outside = (-1e-6, 6.0)
    assert index.is_on_any_boundary(just_outside, eps=1e-8) is False
    assert index.is_on_any_boundary(just_outside, eps=1e-5) is True


# --- visible-sample scan ----------------------------------------------------


def _naive_visible(points, samples, blocker_index, strategy="relate"):
    return {
        s.id
        for s in samples
        if any(is_visible(p, s.point, blocker_index, strategy=strategy) for p in points)
    }


def test_unbounded_scan_matches_naive(scene):
    buildings, samples = scene
    blocker_index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (42.0, 12.0), (60.0, 52.0)]
    assert visible_sample_ids_from_points(points, samples, blocker_index) == _naive_visible(
        points, samples, blocker_index
    )


def test_no_points_sees_nothing(scene):
    buildings, samples = scene
    blocker_index = BlockerIndex.from_buildings(buildings)
    assert visible_sample_ids_from_points([], samples, blocker_index) == set()


def test_radius_cull_only_removes_never_adds(scene):
    """Culling must be conservative: a culled scan is a subset of the full scan."""
    buildings, samples = scene
    blocker_index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (42.0, 12.0), (60.0, 52.0)]
    full = visible_sample_ids_from_points(points, samples, blocker_index)
    culled = visible_sample_ids_from_points(points, samples, blocker_index, radius=25.0)
    assert culled <= full
    assert culled != full, "scene must contain a visible pair beyond 25 m for this to be meaningful"


def test_radius_cull_keeps_every_pair_inside_the_radius(scene):
    buildings, samples = scene
    blocker_index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (42.0, 12.0)]
    radius = 25.0
    culled = visible_sample_ids_from_points(points, samples, blocker_index, radius=radius)
    for s in samples:
        inside_and_visible = any(
            math.dist(p, s.point) <= radius and is_visible(p, s.point, blocker_index) for p in points
        )
        if inside_and_visible:
            assert s.id in culled


def test_a_generous_radius_reproduces_the_unbounded_scan(scene):
    buildings, samples = scene
    blocker_index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (42.0, 12.0), (60.0, 52.0)]
    assert visible_sample_ids_from_points(
        points, samples, blocker_index, radius=10_000.0
    ) == visible_sample_ids_from_points(points, samples, blocker_index)
