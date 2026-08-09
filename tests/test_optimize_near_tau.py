"""Lever A: concentrate coverage on buildings that can still be flipped (task #6).

Sized 2026-08-08 before building. Both remaining #6 ideas compete for the same
resource -- covered boundary weight that cannot buy a building -- and they target
opposite regimes:

  overshoot (lever B)   177,841 m at tau=0.25/k=500, 10,894 m at tau=0.75
  long tail  (lever A)    5,930 m at tau=0.25/k=500, 109,622 m at tau=0.75

Lever B is `greedy_select_threshold`, already built and measured: +6.4% / +0.3% /
-1.1% at k=500, tracking its resource monotonically. It is a low-tau lever, and
tau=0.75 is where relative scoring pays.

Lever A masks to buildings that are unserviced AND close enough to tau to be worth
chasing, so marginal coverage is spent where it can flip something. It subsumes B:
serviced buildings have non-positive deficit and are excluded automatically.

The cutoff must adapt. At iteration zero every building is unserviced with deficit
exactly `tau * perimeter`, so "near tau" is meaningless -- a fixed threshold would
either select everything or nothing. A quantile of the live deficit distribution
tightens naturally as coverage accumulates.
"""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from giscup.candidates import generate_boundary_candidates
from giscup.coverage import coverage_by_building
from giscup.geometry import make_building
from giscup.matrix import build_visibility_matrix
from giscup.optimize import greedy_select_matrix, greedy_select_near_tau, near_tau_target
from giscup.sampling import SamplingProfile, sample_boundaries

PROFILE = SamplingProfile("test", 4.0, 6)
WIDE = 10_000.0


# --- the targeting rule, unit-tested directly -------------------------------


def test_serviced_buildings_are_never_targeted():
    """Zero or negative deficit means the building already clears tau. Chasing it
    further is exactly the waste lever B removes."""
    got = np.array([10.0, 5.0, 8.0])
    need = np.array([8.0, 10.0, 8.0])  # building 0 over, 1 under, 2 exactly at tau
    target = near_tau_target(got, need, quantile=100.0)
    assert target.tolist() == [False, True, False]


def test_only_the_closest_unserviced_buildings_are_targeted():
    """Deficits 1, 2, 3, 4 -> the median cutoff keeps the two cheapest."""
    got = np.array([9.0, 8.0, 7.0, 6.0])
    need = np.array([10.0, 10.0, 10.0, 10.0])
    target = near_tau_target(got, need, quantile=50.0)
    assert target.tolist() == [True, True, False, False]


def test_a_full_quantile_degenerates_to_lever_b():
    """At quantile=100 every unserviced building is in play, which is precisely the
    already-measured threshold objective. Useful as a control arm."""
    got = np.array([9.0, 1.0, 11.0])
    need = np.array([10.0, 10.0, 10.0])
    assert near_tau_target(got, need, quantile=100.0).tolist() == [True, True, False]


def test_nothing_is_targeted_once_everything_is_serviced():
    got = np.array([10.0, 12.0])
    need = np.array([10.0, 10.0])
    assert not near_tau_target(got, need, quantile=50.0).any()


def test_the_cutoff_tightens_as_coverage_accumulates():
    """The defining behaviour. Early on, deficits are wide and similar, so the mask is
    broad. As buildings approach tau the distribution compresses and the mask narrows
    onto the ones actually about to flip."""
    need = np.array([10.0, 10.0, 10.0, 10.0])
    early = near_tau_target(np.array([0.0, 0.0, 0.0, 0.0]), need, quantile=50.0)
    late = near_tau_target(np.array([9.0, 8.0, 2.0, 1.0]), need, quantile=50.0)
    assert early.sum() >= late.sum()
    assert late.tolist() == [True, True, False, False]


# --- greedy contract --------------------------------------------------------


def _scene():
    polys = []
    for row_y in (0.0, 30.0):
        for i in range(4):
            x = i * 22.0
            polys.append(Polygon([(x, row_y), (x + 14, row_y), (x + 14, row_y + 12), (x, row_y + 12)]))
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return buildings, generate_boundary_candidates(buildings, mode="basic"), sample_boundaries(buildings, PROFILE)


@pytest.fixture(scope="module")
def scene():
    return _scene()


@pytest.mark.parametrize("k", [1, 4, 10])
def test_selects_exactly_k_distinct_candidates(scene, tmp_path, k):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    selected, _ = greedy_select_near_tau(matrix, candidates, samples, buildings, tau=0.5, k=k)
    assert len(selected) == k
    assert len({c.id for c in selected}) == k


def test_rejects_impossible_k(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="k must be positive"):
        greedy_select_near_tau(matrix, candidates, samples, buildings, tau=0.5, k=0)
    with pytest.raises(ValueError, match="fewer than required"):
        greedy_select_near_tau(
            matrix, candidates, samples, buildings, tau=0.5, k=len(candidates) + 1
        )


def test_rejects_a_mismatched_matrix(scene, tmp_path):
    buildings, candidates, samples = scene
    smaller = candidates[: len(candidates) // 2]
    matrix = build_visibility_matrix(buildings, smaller, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="does not match"):
        greedy_select_near_tau(matrix, candidates, samples, buildings, tau=0.5, k=3)


def test_still_returns_k_when_the_mask_empties(scene, tmp_path):
    """tau this low services everything almost immediately, emptying the target mask.
    Selection must fall back to raw coverage rather than stalling."""
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    selected, _ = greedy_select_near_tau(matrix, candidates, samples, buildings, tau=0.01, k=12)
    assert len(selected) == 12
    assert len({c.id for c in selected}) == 12


def test_it_does_not_service_fewer_buildings_than_baseline_on_this_scene(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    for tau in (0.25, 0.5, 0.75):
        for k in (4, 8):
            _, base_v = greedy_select_matrix(matrix, candidates, samples, buildings, tau=tau, k=k)
            _, near_v = greedy_select_near_tau(matrix, candidates, samples, buildings, tau=tau, k=k)
            base = sum(1 for r in coverage_by_building(base_v, samples, buildings).values() if r >= tau)
            near = sum(1 for r in coverage_by_building(near_v, samples, buildings).values() if r >= tau)
            assert near >= base, f"tau={tau} k={k}: near-tau {near} < baseline {base}"
