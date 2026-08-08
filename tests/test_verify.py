"""Un-culled verification pass (task board #3).

These pin only the invariants that hold for *any* sane selection policy. The band
width, the below-tau cutoff, and the ordering under a cap are deliberate design
choices; tests for those follow once the policy is decided.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.geometry import make_building
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.verify import exact_coverage_for, select_buildings_to_reverify
from giscup.visibility import BlockerIndex

PROFILE = SamplingProfile("test", 6.0, 4)


def _scene():
    polys = [
        Polygon([(x, y), (x + 12, y), (x + 12, y + 12), (x, y + 12)])
        for x, y in [(0, 0), (30, 0), (60, 0)]
    ]
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return buildings, sample_boundaries(buildings, PROFILE)


# --- selection invariants ---------------------------------------------------


def test_buildings_already_at_or_above_tau_are_never_reverified():
    """Coverage only rises without the cull, so these stay claimed regardless."""
    coverage = {"a": 0.80, "b": 0.75, "c": 0.99, "d": 0.74}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert "a" not in chosen and "b" not in chosen and "c" not in chosen


def test_selection_respects_the_cap():
    coverage = {str(i): 0.70 + i * 0.001 for i in range(50)}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10, max_buildings=5)
    assert len(chosen) <= 5


def test_selection_returns_only_known_building_ids():
    coverage = {"a": 0.70, "b": 0.40, "c": 0.74}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert set(chosen) <= set(coverage)
    assert len(set(chosen)) == len(chosen), "no duplicates"


def test_a_building_just_below_tau_is_reverified():
    """The whole point: something 0.01 short under the cull may clear tau without it."""
    coverage = {"near": 0.74, "far": 0.05}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert "near" in chosen


# --- exact re-measurement ---------------------------------------------------


def test_exact_coverage_is_zero_without_antennas():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, checks = exact_coverage_for([0], [], samples, buildings, index)
    assert coverage == {} and checks == 0


def test_exact_coverage_only_touches_requested_buildings():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, checks = exact_coverage_for([1], [(6.0, 0.0)], samples, buildings, index)
    assert set(coverage) == {1}
    assert checks > 0


def test_exact_coverage_is_a_ratio_in_the_unit_interval():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (12.0, 12.0), (36.0, 0.0)]
    coverage, _ = exact_coverage_for([0, 1, 2], points, samples, buildings, index)
    assert coverage
    for ratio in coverage.values():
        assert 0.0 <= ratio <= 1.0


def test_an_antenna_on_a_building_covers_some_of_its_own_boundary():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, _ = exact_coverage_for([0], [(6.0, 0.0)], samples, buildings, index)
    assert coverage[0] > 0.0


@pytest.mark.parametrize("bad_tau", [0.0, 1.5])
def test_exact_coverage_ignores_tau_entirely(bad_tau):
    """exact_coverage_for measures; thresholding is the caller's job."""
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, _ = exact_coverage_for([0], [(6.0, 0.0)], samples, buildings, index)
    assert 0.0 <= coverage[0] <= 1.0
