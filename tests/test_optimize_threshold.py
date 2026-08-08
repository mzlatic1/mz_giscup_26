"""Threshold-aware greedy objective (task board #6).

The scored quantity is serviced *buildings* at threshold `tau`, but the baseline
objective maximises newly-visible *samples*. Those differ: once a building is over
`tau`, further coverage of it is worth exactly nothing, yet the sample objective keeps
paying for it. Measured on the official dataset at k=500, 999 buildings sat within
0.10 below `tau=0.75` against 1,312 serviced.

The exact capped objective is `sum_b min(visible_weight_b, tau * perimeter_b)`, which
is submodular. Computing it per candidate per iteration needs a segmented sum over
157k candidates and is far too slow. This implements its dominant term: mask out
samples belonging to buildings already serviced, so gain is
`popcount(row & ~covered & active)` -- three bitwise ops, same cost as the baseline.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.candidates import generate_boundary_candidates
from giscup.coverage import coverage_by_building
from giscup.geometry import make_building
from giscup.matrix import build_visibility_matrix
from giscup.optimize import greedy_select_matrix, greedy_select_threshold
from giscup.sampling import SamplingProfile, sample_boundaries

PROFILE = SamplingProfile("test", 4.0, 6)
WIDE = 10_000.0


def _scene():
    """Two rows of footprints with a street between them."""
    polys = []
    for row_y in (0.0, 30.0):
        for i in range(4):
            x = i * 22.0
            polys.append(Polygon([(x, row_y), (x + 14, row_y), (x + 14, row_y + 12), (x, row_y + 12)]))
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return (
        buildings,
        generate_boundary_candidates(buildings, mode="basic"),
        sample_boundaries(buildings, PROFILE),
    )


@pytest.fixture(scope="module")
def scene():
    return _scene()


def _serviced(matrix, selected_visible, samples, buildings, tau):
    coverage = coverage_by_building(selected_visible, samples, buildings)
    return sum(1 for r in coverage.values() if r >= tau)


# --- contract ---------------------------------------------------------------


@pytest.mark.parametrize("k", [1, 4, 10])
def test_selects_exactly_k_distinct_candidates(scene, tmp_path, k):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    selected, _ = greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.5, k=k)
    assert len(selected) == k
    assert len({c.id for c in selected}) == k


def test_rejects_impossible_k(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="k must be positive"):
        greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.5, k=0)
    with pytest.raises(ValueError, match="fewer than required"):
        greedy_select_threshold(
            matrix, candidates, samples, buildings, tau=0.5, k=len(candidates) + 1
        )


def test_coverage_is_monotone_in_k(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    sizes = []
    for k in (1, 2, 4, 8):
        _, visible = greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.5, k=k)
        sizes.append(len(visible))
    assert sizes == sorted(sizes)


def test_respects_max_candidates(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    selected, _ = greedy_select_threshold(
        matrix, candidates, samples, buildings, tau=0.5, k=3, max_candidates=20
    )
    assert all(c.id < 20 for c in selected)


def test_rejects_a_mismatched_matrix(scene, tmp_path):
    buildings, candidates, samples = scene
    smaller = candidates[: len(candidates) // 2]
    matrix = build_visibility_matrix(buildings, smaller, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="does not match"):
        greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.5, k=3)


# --- the behaviour that distinguishes it from the baseline ------------------


def test_it_stops_paying_for_already_serviced_buildings(scene, tmp_path):
    """The defining property: once a building clears tau, its samples stop counting.

    At tau very low, buildings are serviced almost immediately, so the threshold
    objective's active mask empties fast and it must keep finding *new* buildings
    rather than re-covering satisfied ones.
    """
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)

    _, base_visible = greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.2, k=6)
    _, thr_visible = greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.2, k=6)

    base = _serviced(matrix, base_visible, samples, buildings, 0.2)
    thr = _serviced(matrix, thr_visible, samples, buildings, 0.2)
    assert thr >= base, f"threshold objective serviced {thr} vs baseline {base}"


def test_it_does_not_service_fewer_buildings_across_taus(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    for tau in (0.25, 0.5):
        for k in (4, 8):
            _, base_v = greedy_select_matrix(matrix, candidates, samples, buildings, tau=tau, k=k)
            _, thr_v = greedy_select_threshold(matrix, candidates, samples, buildings, tau=tau, k=k)
            base = _serviced(matrix, base_v, samples, buildings, tau)
            thr = _serviced(matrix, thr_v, samples, buildings, tau)
            assert thr >= base, f"tau={tau} k={k}: threshold {thr} < baseline {base}"


def test_falls_back_to_raw_gain_when_everything_is_serviced(scene, tmp_path):
    """With the active mask empty, selection must still return k legal candidates
    rather than stalling or raising."""
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    # tau this low is met by almost any antenna, emptying the mask early.
    selected, _ = greedy_select_threshold(matrix, candidates, samples, buildings, tau=0.01, k=12)
    assert len(selected) == 12
    assert len({c.id for c in selected}) == 12
