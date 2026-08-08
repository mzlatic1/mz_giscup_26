"""Matrix-backed greedy selection (task board #2).

The point of the matrix is that greedy stops recomputing visibility. These tests pin
that the fast path picks *exactly* what the existing predicate-based greedy picks, so
the speedup cannot quietly become a different algorithm. The objective itself is still
raw newly-visible-sample count -- replacing it is task #6, deliberately separate.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.candidates import generate_boundary_candidates
from giscup.geometry import make_building
from giscup.matrix import build_visibility_matrix
from giscup.optimize import greedy_select, greedy_select_matrix
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.visibility import BlockerIndex

PROFILE = SamplingProfile("test", 6.0, 4)
# Larger than any pair distance in the scene, so the matrix is effectively un-culled
# and must reproduce the unbounded predicate-based greedy exactly.
WIDE = 10_000.0


def _scene():
    polys = []
    for row_y in (0.0, 40.0):
        for i in range(3):
            x = i * 30.0
            polys.append(Polygon([(x, row_y), (x + 12, row_y), (x + 12, row_y + 12), (x, row_y + 12)]))
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return buildings, generate_boundary_candidates(buildings, mode="basic"), sample_boundaries(buildings, PROFILE)


@pytest.fixture(scope="module")
def scene():
    return _scene()


@pytest.mark.parametrize("k", [1, 3, 8])
def test_matrix_greedy_matches_predicate_greedy(scene, tmp_path, k):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)

    reference, reference_visible = greedy_select(
        candidates, samples, buildings, BlockerIndex.from_buildings(buildings), tau=0.5, k=k
    )
    fast, fast_visible = greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=k)

    assert [c.id for c in fast] == [c.id for c in reference]
    assert fast_visible == reference_visible


def test_matrix_greedy_returns_exactly_k(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    for k in (1, 5, 12):
        selected, _ = greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=k)
        assert len(selected) == k
        assert len({c.id for c in selected}) == k, "must not select the same candidate twice"


def test_matrix_greedy_coverage_is_monotone(scene, tmp_path):
    """Greedy coverage can never shrink as k grows."""
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    sizes = []
    for k in (1, 2, 4, 8):
        _, visible = greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=k)
        sizes.append(len(visible))
    assert sizes == sorted(sizes)


def test_matrix_greedy_rejects_impossible_k(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="k must be positive"):
        greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=0)
    with pytest.raises(ValueError, match="fewer than required"):
        greedy_select_matrix(
            matrix, candidates, samples, buildings, tau=0.5, k=len(candidates) + 1
        )


def test_matrix_greedy_respects_max_candidates(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=WIDE, cache_dir=tmp_path)
    selected, _ = greedy_select_matrix(
        matrix, candidates, samples, buildings, tau=0.5, k=3, max_candidates=20
    )
    assert all(c.id < 20 for c in selected)
    with pytest.raises(ValueError, match="at least k"):
        greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=5, max_candidates=3)


def test_matrix_must_match_the_candidate_and_sample_sets(scene, tmp_path):
    """A matrix built for a different pool must be rejected, not silently misindexed."""
    buildings, candidates, samples = scene
    smaller = candidates[: len(candidates) // 2]
    assert len(smaller) < len(candidates)
    matrix = build_visibility_matrix(buildings, smaller, samples, radius=WIDE, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="does not match"):
        greedy_select_matrix(matrix, candidates, samples, buildings, tau=0.5, k=3)

    fewer_samples = samples[: len(samples) // 2]
    matrix2 = build_visibility_matrix(
        buildings, candidates, fewer_samples, radius=WIDE, cache_dir=tmp_path
    )
    with pytest.raises(ValueError, match="does not match"):
        greedy_select_matrix(matrix2, candidates, samples, buildings, tau=0.5, k=3)
