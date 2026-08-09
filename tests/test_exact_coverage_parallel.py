"""Verification is 81.7% of runtime and ran on one core of sixteen (#18).

Decomposing the v2 nine-block run's measured 33,898 s:

    setup x9            30 s   0.1%
    greedy           6,174 s  18.2%
    verification    27,694 s  81.7%

Every building's exact coverage is independent of every other's, so this loop is
embarrassingly parallel. It was not parallel.

The one thing that must not change is the answer. Coverage decides which claims are
kept and which are dropped, and the competition allows one submission with no score
feedback -- a parallel path that differs from the serial one even in the last bits
would silently alter claims. So these tests demand **exact** equality, not
approximate: same buildings, same float64 values.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.exact_coverage import exact_coverage_by_building
from giscup.geometry import make_building
from giscup.visibility import BlockerIndex

E0 = 500_000.0
N0 = 3_700_000.0


def _scene(n: int = 12):
    """Irregular footprints at real projected magnitudes, with blockers between them."""
    buildings = []
    for i in range(n):
        x = E0 + (i % 4) * 37.0
        y = N0 + (i // 4) * 29.0
        w = 15.0 + (i % 3) * 4.0
        h = 11.0 + (i % 2) * 6.0
        buildings.append(
            make_building(i, Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]))
        )
    return buildings, BlockerIndex.from_buildings(buildings)


def _antennas(buildings):
    pts = []
    for b in buildings:
        x0, y0, x1, y1 = b.bounds
        pts.append((x0, (y0 + y1) / 2.0))
        pts.append(((x0 + x1) / 2.0, y1))
    return pts


@pytest.mark.parametrize("workers", [2, 4])
def test_parallel_results_are_bit_identical_to_serial(workers):
    """The whole contract. Not approx -- identical."""
    buildings, index = _scene()
    ids = [b.id for b in buildings]
    points = _antennas(buildings)

    serial = exact_coverage_by_building(ids, points, buildings, index, radius=400.0)
    parallel = exact_coverage_by_building(
        ids, points, buildings, index, radius=400.0, workers=workers
    )

    assert set(parallel) == set(serial)
    for bid in serial:
        assert parallel[bid] == serial[bid], (
            f"building {bid}: parallel {parallel[bid]!r} != serial {serial[bid]!r}"
        )


def test_serial_is_still_the_default():
    """No caller changes behaviour by accident."""
    buildings, index = _scene()
    ids = [b.id for b in buildings]
    got = exact_coverage_by_building(ids, _antennas(buildings), buildings, index, radius=400.0)
    assert len(got) == len(ids)


def test_every_requested_building_comes_back():
    """A dropped building would be read as coverage 0.0 and silently unclaim it."""
    buildings, index = _scene()
    ids = [b.id for b in buildings][:7]
    got = exact_coverage_by_building(
        ids, _antennas(buildings), buildings, index, radius=400.0, workers=3
    )
    assert set(got) == set(ids)


def test_more_workers_than_buildings_is_harmless():
    buildings, index = _scene()
    ids = [buildings[0].id]
    got = exact_coverage_by_building(
        ids, _antennas(buildings), buildings, index, radius=400.0, workers=8
    )
    assert set(got) == set(ids)


def test_an_empty_selection_costs_nothing_and_starts_no_pool():
    buildings, index = _scene()
    assert exact_coverage_by_building([], _antennas(buildings), buildings, index, workers=4) == {}


@pytest.mark.parametrize("bad", [0, -1])
def test_a_nonsensical_worker_count_is_rejected(bad):
    buildings, index = _scene()
    with pytest.raises(ValueError, match="workers"):
        exact_coverage_by_building(
            [buildings[0].id], _antennas(buildings), buildings, index, workers=bad
        )


def test_unbounded_radius_also_matches_serial():
    """The radius is an optimisation over an exact computation; parallelism must not
    interact with it."""
    buildings, index = _scene(6)
    ids = [b.id for b in buildings]
    points = _antennas(buildings)
    serial = exact_coverage_by_building(ids, points, buildings, index, radius=None)
    parallel = exact_coverage_by_building(ids, points, buildings, index, radius=None, workers=2)
    assert parallel == serial
