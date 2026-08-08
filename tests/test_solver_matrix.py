"""End-to-end solver on the cached visibility matrix (task board #2).

`solve_one` gains an opt-in fast path. These tests pin that turning it on changes the
runtime, not the answer, and that the matrix is genuinely reused rather than rebuilt
per subproblem -- reuse across the nine subproblems is the whole point.
"""

from __future__ import annotations

import json

import pytest

from giscup.solver import solve_one

WIDE = 10_000.0


def _dataset(tmp_path):
    payload = {
        "type": "FeatureCollection",
        "name": "synthetic_buildings_projected",
        "crs": {"type": "name", "properties": {"name": "EPSG:32611"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"id": i},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[x, y], [x + 12, y], [x + 12, y + 12], [x, y + 12], [x, y]]
                    ],
                },
            }
            for i, (x, y) in enumerate(
                [(0, 0), (30, 0), (60, 0), (0, 40), (30, 40), (60, 40)]
            )
        ],
    }
    path = tmp_path / "buildings.geojson"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("k", [1, 4])
def test_matrix_path_gives_the_same_solution(tmp_path, k):
    dataset = _dataset(tmp_path)
    baseline = solve_one(dataset, tau=0.25, k=k)
    fast = solve_one(
        dataset, tau=0.25, k=k, visibility_radius=WIDE, cache_dir=str(tmp_path / "cache")
    )
    assert fast.antenna_points == baseline.antenna_points
    assert sorted(map(str, fast.claimed_building_ids)) == sorted(map(str, baseline.claimed_building_ids))


def test_matrix_is_reused_across_subproblems(tmp_path):
    """The second solve on the same dataset must hit the cache, not rebuild."""
    dataset = _dataset(tmp_path)
    cache = str(tmp_path / "cache")
    first = solve_one(dataset, tau=0.25, k=2, visibility_radius=WIDE, cache_dir=cache)
    second = solve_one(dataset, tau=0.75, k=3, visibility_radius=WIDE, cache_dir=cache)
    assert first.diagnostics["visibility_matrix"]["loaded_from_cache"] is False
    assert second.diagnostics["visibility_matrix"]["loaded_from_cache"] is True
    assert second.diagnostics["visibility_matrix"]["key"] == first.diagnostics["visibility_matrix"]["key"]


def test_matrix_path_still_emits_exactly_k_points(tmp_path):
    dataset = _dataset(tmp_path)
    for k in (1, 3, 7):
        solution = solve_one(
            dataset, tau=0.5, k=k, visibility_radius=WIDE, cache_dir=str(tmp_path / "cache")
        )
        assert len(solution.antenna_points) == k


def test_diagnostics_record_the_radius_and_key(tmp_path):
    dataset = _dataset(tmp_path)
    solution = solve_one(
        dataset, tau=0.5, k=2, visibility_radius=250.0, cache_dir=str(tmp_path / "cache")
    )
    info = solution.diagnostics["visibility_matrix"]
    assert info["radius"] == 250.0
    assert info["key"]
    assert info["nonzeros"] > 0
    assert solution.diagnostics["config"]["visibility_radius"] == 250.0


def test_radius_is_required_for_the_matrix_path(tmp_path):
    """A cache_dir alone must not silently enable culling with an implicit radius."""
    dataset = _dataset(tmp_path)
    solution = solve_one(dataset, tau=0.5, k=2, cache_dir=str(tmp_path / "cache"))
    assert "visibility_matrix" not in solution.diagnostics
