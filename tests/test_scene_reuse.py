"""`solve-all` must prepare the dataset once, and must not lose finished blocks.

Two defects motivate this file, both found while watching the v2 nine-block run:

1. `cmd_solve_all` called `solve_one(input_path=...)` nine times, and every call
   re-read the GeoJSON, re-sampled every boundary, and re-generated all 157,454
   candidates. Only the visibility matrix was shared (via `cache_dir`).

   **The speedup is negligible and was originally overstated.** Setup measures
   3.32 s on the official sample, so eight redundant repeats cost 27 s of a
   33,898 s run -- 0.08%, not the "~40%" first claimed. What makes the change
   worth keeping is the `SceneSpec` guard: sharing setup silently across
   differently-configured solves would answer a question nobody posed.

2. `cmd_solve_all` wrote its output file only after all nine blocks finished. The
   v2 run passed five hours with nothing on disk. In a one-submission competition
   with no score feedback, a crash in block nine must not destroy blocks one
   through eight.

The scene is exactly the part of the work that does not depend on `(tau, k)`:
loading, sampling, and candidate generation. Sharing it is only safe if the
sharing is *checked* -- a scene built with a different sampling profile or
candidate spacing than the solver was asked for would silently produce a
solution for a problem nobody posed. Hence `SceneSpec` and the mismatch guard.
"""

from __future__ import annotations

import json

import pytest

from giscup.scene import SceneSpec, prepare_scene
from giscup.solver import solve_one

# Real projected magnitudes (EPSG:32611). Unit-square fixtures cannot see the
# float64 behaviour that actually bites this project; see CLAUDE.md.
E0 = 500_000.0
N0 = 3_700_000.0


def _dataset() -> dict:
    features = []
    for i in range(6):
        x = E0 + (i % 3) * 40.0
        y = N0 + (i // 3) * 35.0
        features.append(
            {
                "type": "Feature",
                "properties": {"id": 100 + i},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[x, y], [x + 22, y], [x + 22, y + 17], [x, y + 17], [x, y]]
                    ],
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:32611"}},
        "features": features,
    }


@pytest.fixture
def dataset_path(tmp_path):
    path = tmp_path / "buildings.geojson"
    path.write_text(json.dumps(_dataset()), encoding="utf-8")
    return str(path)


# --- the scene itself -------------------------------------------------------


def test_prepare_scene_loads_buildings_samples_and_candidates(dataset_path):
    scene = prepare_scene(dataset_path)
    assert len(scene.buildings) == 6
    assert scene.samples, "boundary sampling produced nothing"
    assert scene.candidates, "candidate generation produced nothing"
    assert scene.info.feature_count == 6


def test_scene_records_the_configuration_it_was_built_with(dataset_path):
    scene = prepare_scene(dataset_path, sampling_profile="balanced", candidate_spacing=25.0)
    assert scene.spec == SceneSpec(
        input_path=dataset_path,
        id_property="id",
        sampling_profile="balanced",
        candidate_mode="basic",
        candidate_spacing=25.0,
    )


# --- reuse must not change the answer ---------------------------------------


def test_a_reused_scene_yields_an_identical_solution(dataset_path):
    """The whole point: sharing setup across subproblems must be invisible in the
    result. Antenna coordinates are compared exactly -- not approximately -- because
    the submission is emitted at full float64 width."""
    fresh = solve_one(dataset_path, tau=0.5, k=3)
    scene = prepare_scene(dataset_path)
    reused = solve_one(dataset_path, tau=0.5, k=3, scene=scene)

    assert reused.antenna_points == fresh.antenna_points
    assert reused.claimed_building_ids == fresh.claimed_building_ids


def test_one_scene_serves_several_subproblems(dataset_path):
    scene = prepare_scene(dataset_path)
    for tau in (0.25, 0.5, 0.75):
        for k in (1, 3):
            solution = solve_one(dataset_path, tau=tau, k=k, scene=scene)
            assert len(solution.antenna_points) == k


# --- the guard against silently solving the wrong problem -------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sampling_profile": "accurate"},
        {"candidate_spacing": 10.0},
        {"id_property": "osm_id"},
    ],
)
def test_a_mismatched_scene_is_rejected(dataset_path, kwargs):
    """A scene built under one configuration must never be used to answer a request
    made under another. Silently accepting it would emit a solution to a different
    problem than the one asked for, and nothing downstream could detect it."""
    scene = prepare_scene(dataset_path)
    with pytest.raises(ValueError, match="scene does not match"):
        solve_one(dataset_path, tau=0.5, k=2, scene=scene, **kwargs)


def test_a_scene_from_a_different_dataset_is_rejected(dataset_path, tmp_path):
    other = tmp_path / "other.geojson"
    other.write_text(json.dumps(_dataset()), encoding="utf-8")
    scene = prepare_scene(str(other))
    with pytest.raises(ValueError, match="scene does not match"):
        solve_one(dataset_path, tau=0.5, k=2, scene=scene)


# --- solve-all: prepare once ------------------------------------------------


def test_solve_all_prepares_the_dataset_exactly_once(dataset_path, tmp_path, monkeypatch):
    """Nine subproblems, one load. This is the defect: before the fix this counted 9."""
    from giscup import scene as scene_mod

    calls = []
    real = scene_mod.load_buildings

    def counting(*args, **kwargs):
        calls.append(args[0] if args else kwargs.get("path"))
        return real(*args, **kwargs)

    monkeypatch.setattr(scene_mod, "load_buildings", counting)

    from giscup.cli import main

    main(
        [
            "solve-all",
            "--objective",
            "baseline",
            "--input", dataset_path,
            "--taus", "0.25", "0.5", "0.75",
            "--ks", "1", "2", "3",
            "--output", str(tmp_path / "out.txt"),
            "--quiet",
        ]
    )
    assert len(calls) == 1, f"dataset loaded {len(calls)} times, expected 1"


def test_solve_all_still_emits_one_block_per_subproblem(dataset_path, tmp_path):
    from giscup.cli import main

    out = tmp_path / "out.txt"
    main(
        [
            "solve-all",
            "--objective",
            "baseline",
            "--input", dataset_path,
            "--taus", "0.25", "0.5",
            "--ks", "1", "2",
            "--output", str(out),
            "--quiet",
        ]
    )
    lines = out.read_text(encoding="utf-8").split("\n")
    assert lines[-1] == ""  # trailing newline, no blank separator lines
    assert len(lines) - 1 == 4 * 3, "expected exactly three lines per subproblem"


# --- solve-all: never lose finished blocks ----------------------------------


def test_finished_blocks_survive_a_crash_mid_run(dataset_path, tmp_path, monkeypatch):
    """Blocks one and two must be on disk when block three dies. Without incremental
    writes a five-hour run loses everything to a failure in its last minute."""
    from giscup import cli

    real_solve = cli.solve_one
    calls = {"n": 0}

    def failing(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated failure in block three")
        return real_solve(*args, **kwargs)

    monkeypatch.setattr(cli, "solve_one", failing)

    out = tmp_path / "out.txt"
    with pytest.raises(RuntimeError, match="simulated failure"):
        cli.main(
            [
                "solve-all",
            "--objective",
            "baseline",
                "--input", dataset_path,
                "--taus", "0.25", "0.5",
                "--ks", "1", "2",
                "--output", str(out),
                "--quiet",
            ]
        )

    partial = out.with_suffix(out.suffix + ".partial")
    assert partial.exists(), "no partial output: two finished blocks were lost"
    lines = [ln for ln in partial.read_text(encoding="utf-8").split("\n") if ln != ""]
    assert len(lines) == 2 * 3, f"expected 2 complete blocks, got {len(lines)} lines"


def test_the_partial_file_is_removed_once_the_real_output_lands(dataset_path, tmp_path):
    from giscup.cli import main

    out = tmp_path / "out.txt"
    main(
        [
            "solve-all",
            "--objective",
            "baseline",
            "--input", dataset_path,
            "--taus", "0.5",
            "--ks", "1", "2",
            "--output", str(out),
            "--quiet",
        ]
    )
    assert out.exists()
    assert not out.with_suffix(out.suffix + ".partial").exists(), (
        "a stale .partial next to a finished run invites submitting the wrong file"
    )
