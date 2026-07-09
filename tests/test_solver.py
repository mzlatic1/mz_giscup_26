import json

import pytest

from giscup.solver import solve_one


def test_solver_rejects_max_candidates_below_k(tmp_path):
    dataset_path = tmp_path / "buildings.geojson"
    dataset_path.write_text(json.dumps(_two_square_dataset()), encoding="utf-8")

    with pytest.raises(ValueError, match="max_candidates .* must be at least k"):
        solve_one(str(dataset_path), tau=0.25, k=3, max_candidates=2)


def test_solver_rejects_unimplemented_optimizer(tmp_path):
    dataset_path = tmp_path / "buildings.geojson"
    dataset_path.write_text(json.dumps(_two_square_dataset()), encoding="utf-8")

    with pytest.raises(ValueError, match="not implemented"):
        solve_one(str(dataset_path), tau=0.25, k=1, optimizer="lazy-greedy")


def _two_square_dataset():
    return {
        "type": "FeatureCollection",
        "name": "synthetic_buildings_projected",
        "crs": {"type": "name", "properties": {"name": "EPSG:32611"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"id": 2},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20, 0], [30, 0], [30, 10], [20, 10], [20, 0]]],
                },
            },
        ],
    }
