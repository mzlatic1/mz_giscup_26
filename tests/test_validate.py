import json

from giscup.validate import validate_solution_file


def test_validate_allows_empty_claim_line(tmp_path):
    dataset = _single_square_dataset()
    dataset_path = tmp_path / "buildings.geojson"
    solution_path = tmp_path / "solution.txt"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    solution_path.write_text("(0.5, 1)\n(0, 0)\n\n", encoding="utf-8")

    result = validate_solution_file(str(dataset_path), str(solution_path))

    assert result.ok
    assert result.errors == []


def test_validate_malformed_header_does_not_hang(tmp_path):
    dataset_path = tmp_path / "buildings.geojson"
    solution_path = tmp_path / "solution.txt"
    dataset_path.write_text(json.dumps(_single_square_dataset()), encoding="utf-8")
    solution_path.write_text("bad header\n(0, 0)\n\n", encoding="utf-8")

    result = validate_solution_file(str(dataset_path), str(solution_path))

    assert not result.ok
    assert "Invalid parameter line" in result.errors[0]


def test_validate_rejects_claim_below_sampled_threshold(tmp_path):
    dataset_path = tmp_path / "buildings.geojson"
    solution_path = tmp_path / "solution.txt"
    dataset_path.write_text(json.dumps(_single_square_dataset()), encoding="utf-8")
    solution_path.write_text("(1.0, 1)\n(0, 0)\n1\n", encoding="utf-8")

    result = validate_solution_file(str(dataset_path), str(solution_path), sampling_profile="fast")

    assert not result.ok
    assert any("Claimed buildings below" in err for err in result.errors)


def _single_square_dataset():
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
            }
        ],
    }
