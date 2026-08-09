"""Building IDs must come from the dataset, and a fallback must be loud.

The third line of every block is a list of building IDs. If those IDs are wrong, the
block claims buildings that do not exist and scores nothing -- and unlike a crash, it
produces plausible-looking output that passes every structural check.

`load_buildings` silently falls back to the row index when its `id_property` is absent.
The sample dataset uses `id`, but the August test dataset is a different extract and may
use `building_id`, `fid`, `OBJECTID`, or anything else. With one submission and no score
feedback, a silent fallback here is the worst possible failure mode.
"""

from __future__ import annotations

import json

import pytest

from giscup.io import load_buildings

SQUARE = [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]]


def _write(tmp_path, id_field: str | None, values=(101, 202)):
    features = []
    for i, v in enumerate(values):
        props = {} if id_field is None else {id_field: v}
        offset = i * 20.0
        ring = [[x + offset, y] for x, y in SQUARE[0]]
        features.append(
            {"type": "Feature", "properties": props,
             "geometry": {"type": "Polygon", "coordinates": [ring]}}
        )
    path = tmp_path / "d.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return path


def test_ids_come_from_the_named_property(tmp_path):
    buildings, info = load_buildings(_write(tmp_path, "building_id"), id_property="building_id")
    assert [b.id for b in buildings] == [101, 202]
    assert info.id_property == "building_id"


def test_a_missing_id_property_is_reported_not_silently_indexed(tmp_path):
    """The dangerous case: ask for `id`, dataset has `building_id`, get 0..n-1 back
    with no indication anything went wrong."""
    path = _write(tmp_path, "building_id")
    with pytest.warns(UserWarning, match="id_property"):
        buildings, info = load_buildings(path, id_property="id")
    assert info.id_fallback_used is True
    assert [b.id for b in buildings] == [0, 1]


def test_no_warning_when_the_property_is_present(tmp_path):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _, info = load_buildings(_write(tmp_path, "id"), id_property="id")
    assert info.id_fallback_used is False


def test_a_dataset_with_no_properties_at_all_still_loads(tmp_path):
    """Index IDs are legitimate when the dataset genuinely has no ID field -- it just
    has to be visible."""
    with pytest.warns(UserWarning):
        buildings, info = load_buildings(_write(tmp_path, None), id_property="id")
    assert [b.id for b in buildings] == [0, 1]
    assert info.id_fallback_used is True


def test_string_ids_are_preserved_not_coerced(tmp_path):
    path = _write(tmp_path, "id", values=("A-1", "B-2"))
    buildings, _ = load_buildings(path, id_property="id")
    assert [b.id for b in buildings] == ["A-1", "B-2"]


def test_solve_subcommands_expose_id_property():
    """`inspect` had --id-property; the solvers did not, so a dataset with a different
    ID field could not be solved correctly even if you noticed the problem."""
    from giscup.cli import build_parser

    parser = build_parser()
    for cmd in ("solve-one", "solve-all"):
        args = parser.parse_args(
            [cmd, "--input", "x.geojson", "--output", "o.txt", "--id-property", "OBJECTID"]
            + (["--tau", "0.5", "--k", "5"] if cmd == "solve-one" else
               ["--taus", "0.5", "--ks", "5"])
        )
        assert args.id_property == "OBJECTID"
