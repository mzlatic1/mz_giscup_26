"""Correctness and caching tests for the radius-culled visibility matrix.

Task board #2. The matrix is the project blocker: it is computed once and reused
across all nine subproblems, so a wrong bit is a wrong answer nine times over.

The load-bearing test is `test_matrix_matches_direct_predicate` -- every stored bit
must equal what `is_visible` says for that pair. Everything else guards the cache
and the parallel build against silently diverging from that ground truth.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from giscup.candidates import generate_boundary_candidates
from giscup.geometry import make_building
from giscup.matrix import VisibilityMatrix, build_visibility_matrix, load_matrix
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.visibility import BlockerIndex, is_visible

PROFILE = SamplingProfile("test", 6.0, 4)


def _scene():
    """A small deterministic street-like scene: two rows of squares with a gap."""
    polys = []
    for row_y in (0.0, 40.0):
        for i in range(3):
            x = i * 30.0
            polys.append(Polygon([(x, row_y), (x + 12, row_y), (x + 12, row_y + 12), (x, row_y + 12)]))
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    samples = sample_boundaries(buildings, PROFILE)
    candidates = generate_boundary_candidates(buildings, mode="basic")
    return buildings, candidates, samples


@pytest.fixture(scope="module")
def scene():
    return _scene()


def _naive_bits(buildings, candidates, samples, radius, strategy="relate"):
    """Ground truth: direct predicate over every pair inside the radius."""
    index = BlockerIndex.from_buildings(buildings)
    truth = np.zeros((len(candidates), len(samples)), dtype=bool)
    for c in candidates:
        for s in samples:
            if math.dist(c.point, s.point) <= radius and is_visible(c.point, s.point, index, strategy=strategy):
                truth[c.id, s.id] = True
    return truth


def _dense(matrix: VisibilityMatrix) -> np.ndarray:
    out = np.zeros((matrix.n_candidates, matrix.n_samples), dtype=bool)
    for ci in range(matrix.n_candidates):
        out[ci, matrix.visible_sample_ids(ci)] = True
    return out


# --- ground truth -----------------------------------------------------------


def test_matrix_matches_direct_predicate(scene, tmp_path):
    buildings, candidates, samples = scene
    radius = 45.0
    matrix = build_visibility_matrix(
        buildings, candidates, samples, radius=radius, cache_dir=tmp_path
    )
    truth = _naive_bits(buildings, candidates, samples, radius)
    np.testing.assert_array_equal(_dense(matrix), truth)
    assert truth.sum() > 0, "degenerate scene: no visible pairs to verify against"


def test_pairs_beyond_the_radius_are_excluded(scene, tmp_path):
    """A visible pair further apart than the cull radius must not be recorded."""
    buildings, candidates, samples = scene
    index = BlockerIndex.from_buildings(buildings)
    far = [
        (c, s)
        for c in candidates
        for s in samples
        if math.dist(c.point, s.point) > 30.0 and is_visible(c.point, s.point, index)
    ]
    assert far, "scene has no long visible pair to cull"

    matrix = build_visibility_matrix(buildings, candidates, samples, radius=30.0, cache_dir=tmp_path)
    for c, s in far:
        assert s.id not in set(matrix.visible_sample_ids(c.id))


def test_a_candidate_sees_its_own_building_boundary(scene, tmp_path):
    """Sanity: every candidate sits on a boundary and must see something."""
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    seen = [len(matrix.visible_sample_ids(ci)) for ci in range(matrix.n_candidates)]
    assert min(seen) > 0


# --- parallel build must not diverge ----------------------------------------


def test_parallel_build_matches_serial(scene, tmp_path):
    buildings, candidates, samples = scene
    serial = build_visibility_matrix(
        buildings, candidates, samples, radius=45.0, workers=1, cache_dir=tmp_path / "a"
    )
    parallel = build_visibility_matrix(
        buildings, candidates, samples, radius=45.0, workers=3, cache_dir=tmp_path / "b"
    )
    np.testing.assert_array_equal(serial.bits, parallel.bits)


# --- greedy support ---------------------------------------------------------


def test_marginal_gains_match_naive_count(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    covered = matrix.empty_covered()
    matrix.add_to_covered(covered, 0)
    matrix.add_to_covered(covered, 7)

    covered_ids = set(matrix.visible_sample_ids(0)) | set(matrix.visible_sample_ids(7))
    gains = matrix.marginal_gains(covered)
    for ci in range(matrix.n_candidates):
        expected = len(set(matrix.visible_sample_ids(ci)) - covered_ids)
        assert gains[ci] == expected, f"candidate {ci}"


def test_covered_set_accumulates(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    covered = matrix.empty_covered()
    assert matrix.covered_count(covered) == 0
    matrix.add_to_covered(covered, 3)
    assert matrix.covered_count(covered) == len(matrix.visible_sample_ids(3))
    matrix.add_to_covered(covered, 3)
    assert matrix.covered_count(covered) == len(matrix.visible_sample_ids(3)), "union must be idempotent"
    assert set(matrix.covered_sample_ids(covered)) == set(matrix.visible_sample_ids(3))


def test_gain_of_a_selected_candidate_drops_to_zero(scene, tmp_path):
    buildings, candidates, samples = scene
    matrix = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    covered = matrix.empty_covered()
    matrix.add_to_covered(covered, 5)
    assert matrix.marginal_gains(covered)[5] == 0


# --- caching ----------------------------------------------------------------


def test_cache_is_reused_for_identical_inputs(scene, tmp_path):
    buildings, candidates, samples = scene
    first = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    second = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    assert second.loaded_from_cache is True
    assert first.loaded_from_cache is False
    np.testing.assert_array_equal(first.bits, second.bits)


@pytest.mark.parametrize(
    ("kwargs_a", "kwargs_b"),
    [
        ({"radius": 45.0}, {"radius": 30.0}),
        ({"radius": 45.0, "strategy": "relate"}, {"radius": 45.0, "strategy": "hybrid"}),
    ],
)
def test_cache_key_separates_incompatible_configurations(scene, tmp_path, kwargs_a, kwargs_b):
    buildings, candidates, samples = scene
    a = build_visibility_matrix(buildings, candidates, samples, cache_dir=tmp_path, **kwargs_a)
    b = build_visibility_matrix(buildings, candidates, samples, cache_dir=tmp_path, **kwargs_b)
    assert a.spec.key != b.spec.key
    assert b.loaded_from_cache is False


def test_cache_key_separates_different_sample_sets(scene, tmp_path):
    """A denser sampling profile must not silently reuse a coarser matrix."""
    buildings, candidates, samples = scene
    dense_samples = sample_boundaries(buildings, SamplingProfile("denser", 3.0, 4))
    a = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    b = build_visibility_matrix(buildings, candidates, dense_samples, radius=45.0, cache_dir=tmp_path)
    assert a.spec.key != b.spec.key
    assert b.n_samples == len(dense_samples)


def test_saved_matrix_loads_identically(scene, tmp_path):
    buildings, candidates, samples = scene
    built = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    reloaded = load_matrix(tmp_path, built.spec.key)
    np.testing.assert_array_equal(built.bits, reloaded.bits)
    assert reloaded.spec == built.spec


def test_partial_build_is_not_reused(scene, tmp_path):
    """A crashed build leaves no completion marker and must be rebuilt, not trusted."""
    buildings, candidates, samples = scene
    built = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    built.meta_path(tmp_path).unlink()
    again = build_visibility_matrix(buildings, candidates, samples, radius=45.0, cache_dir=tmp_path)
    assert again.loaded_from_cache is False
    np.testing.assert_array_equal(built.bits, again.bits)
