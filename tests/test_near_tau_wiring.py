"""Wiring for lever A (near-tau targeting), measured 2026-08-09 at k=500.

Sweep result on the official sample, versus the baseline greedy objective:

    tau    q=25     q=50    q=100
    0.75  +77.7%   +60.1%   -1.1%
    0.5    +3.5%    +8.6%   +0.3%
    0.25   -8.3%    +0.2%   +6.4%

The q=100 column is the control: it degenerates to the already-measured threshold
objective (lever B), and it reproduced that measurement exactly at all three taus,
which is what makes the rest of the table trustworthy.

The winning quantile is tau-dependent and moves monotonically: as tau rises, tighten
the mask. At tau=0.75 few buildings are reachable so concentrating pays enormously; at
tau=0.25 nearly every unserviced building is winnable and discriminating actively hurts.
A single global quantile therefore cannot be right for all nine subproblems, so
solve-all accepts one value per tau.

Default is OFF. This is measured at k=500 on the sample dataset only, and the
competition allows one submission with no score feedback; the default does not change
without Marko's call.
"""

from __future__ import annotations

import json

import pytest

from giscup.solver import solve_one

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
                "properties": {"id": 200 + i},
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


# --- library default vs shipped default -------------------------------------
#
# These differ deliberately as of 2026-08-09 (#15). The CLI -- the submission path --
# defaults to lever A. `solve_one` as a Python API still defaults to `None`, so every
# existing caller and test keeps the objective it was written against, and a solve is
# never silently re-objectived by an import. The resolution lives in one place,
# `cli._resolve_near_tau_schedule`.


def test_the_library_api_default_is_still_explicit_off(dataset_path, tmp_path, monkeypatch):
    """`solve_one(...)` with no quantile runs baseline greedy. The CLI default is
    lever A; this pins that the *library* does not decide an objective for you."""
    from giscup import solver

    called = []
    monkeypatch.setattr(
        solver,
        "greedy_select_near_tau",
        lambda *a, **kw: called.append(True) or (_ for _ in ()).throw(AssertionError),
    )
    solve_one(
        dataset_path, tau=0.5, k=3, visibility_radius=10_000.0, cache_dir=str(tmp_path)
    )
    assert not called, "near-tau objective ran without being requested"


def test_the_flag_selects_the_near_tau_objective(dataset_path, tmp_path, monkeypatch):
    from giscup import solver

    real = solver.greedy_select_near_tau
    seen = {}

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(solver, "greedy_select_near_tau", spy)
    solve_one(
        dataset_path,
        tau=0.5,
        k=3,
        visibility_radius=10_000.0,
        cache_dir=str(tmp_path),
        near_tau_quantile=25.0,
    )
    assert seen.get("quantile") == 25.0


def test_it_still_returns_exactly_k_antennas(dataset_path, tmp_path):
    """The one constraint that invalidates a block if broken."""
    solution = solve_one(
        dataset_path,
        tau=0.75,
        k=4,
        visibility_radius=10_000.0,
        cache_dir=str(tmp_path),
        near_tau_quantile=25.0,
    )
    assert len(solution.antenna_points) == 4


def test_the_quantile_is_recorded_in_diagnostics(dataset_path, tmp_path):
    """A run's configuration must be reconstructable from its diagnostics; otherwise
    a good result cannot be reproduced on submission day."""
    solution = solve_one(
        dataset_path,
        tau=0.5,
        k=2,
        visibility_radius=10_000.0,
        cache_dir=str(tmp_path),
        near_tau_quantile=50.0,
    )
    assert solution.diagnostics["config"]["near_tau_quantile"] == 50.0


# --- refuse configurations that cannot do what they claim -------------------


@pytest.mark.parametrize("bad", [0.0, -1.0, 100.1, 1000.0])
def test_an_out_of_range_quantile_is_rejected(dataset_path, bad):
    with pytest.raises(ValueError, match="near_tau_quantile"):
        solve_one(dataset_path, tau=0.5, k=2, visibility_radius=10_000.0, near_tau_quantile=bad)


def test_the_flag_requires_the_visibility_matrix(dataset_path):
    """The near-tau objective exists only on the matrix path. Silently ignoring the
    flag on the fallback path would report a lever as active when it was not."""
    with pytest.raises(ValueError, match="visibility_radius"):
        solve_one(dataset_path, tau=0.5, k=2, near_tau_quantile=25.0)


# --- solve-all: one quantile per tau ----------------------------------------


def _run_solve_all(dataset_path, tmp_path, extra):
    from giscup.cli import main

    out = tmp_path / "out.txt"
    diag = tmp_path / "diag.json"
    main(
        [
            "solve-all",
            "--input", dataset_path,
            "--taus", "0.25", "0.5", "0.75",
            "--ks", "2",
            "--visibility-radius", "10000",
            "--cache-dir", str(tmp_path / "cache"),
            "--output", str(out),
            "--diagnostics", str(diag),
            "--quiet",
            *extra,
        ]
    )
    return json.loads(diag.read_text(encoding="utf-8"))


def test_one_quantile_broadcasts_to_every_tau(dataset_path, tmp_path):
    diag = _run_solve_all(dataset_path, tmp_path, ["--near-tau-quantile", "50"])
    for tau in (0.25, 0.5, 0.75):
        assert diag[f"tau_{tau}_k_2"]["config"]["near_tau_quantile"] == 50.0


def test_a_per_tau_schedule_is_applied_in_tau_order(dataset_path, tmp_path):
    """The measured schedule. Values align with --taus positionally, so 0.25 gets
    100, 0.5 gets 50, and 0.75 gets 25."""
    diag = _run_solve_all(
        dataset_path, tmp_path, ["--near-tau-quantile", "100", "50", "25"]
    )
    assert diag["tau_0.25_k_2"]["config"]["near_tau_quantile"] == 100.0
    assert diag["tau_0.5_k_2"]["config"]["near_tau_quantile"] == 50.0
    assert diag["tau_0.75_k_2"]["config"]["near_tau_quantile"] == 25.0


def test_a_schedule_that_does_not_line_up_with_taus_is_rejected(dataset_path, tmp_path):
    """Two quantiles for three taus is ambiguous. Guessing which tau goes unmodified
    would silently solve two subproblems under a configuration nobody chose."""
    with pytest.raises(SystemExit):
        _run_solve_all(dataset_path, tmp_path, ["--near-tau-quantile", "100", "50"])


def test_omitting_the_flag_now_applies_the_measured_schedule(dataset_path, tmp_path):
    """CHANGED 2026-08-09 (#15, Marko's call). This test used to assert that omitting
    the flag left every subproblem on the baseline objective. Lever A is now the
    shipped default, so the same omission must produce the measured tau->quantile
    schedule instead. The old assertion is not obsolete noise -- it pinned a real
    decision, and it is replaced rather than deleted so the flip stays visible."""
    diag = _run_solve_all(dataset_path, tmp_path, [])
    assert diag["tau_0.25_k_2"]["config"]["near_tau_quantile"] == 100.0
    assert diag["tau_0.5_k_2"]["config"]["near_tau_quantile"] == 50.0
    assert diag["tau_0.75_k_2"]["config"]["near_tau_quantile"] == 25.0


def test_objective_baseline_turns_lever_a_off(dataset_path, tmp_path):
    """The escape hatch. Lever A loses (0.5, 1000) at every quantile, so the ability
    to get plain greedy back is load-bearing for the shipped artifact, not a
    convenience."""
    diag = _run_solve_all(dataset_path, tmp_path, ["--objective", "baseline"])
    for tau in (0.25, 0.5, 0.75):
        assert diag[f"tau_{tau}_k_2"]["config"]["near_tau_quantile"] is None


def test_baseline_objective_with_an_explicit_quantile_is_refused(dataset_path, tmp_path):
    """Contradictory flags. Silently honouring one would solve every subproblem under
    a configuration nobody chose -- the same class as the schedule-length guard."""
    with pytest.raises(SystemExit):
        _run_solve_all(
            dataset_path, tmp_path, ["--objective", "baseline", "--near-tau-quantile", "50"]
        )


def test_the_default_schedule_is_monotone_and_hits_the_measured_points():
    """The mapping is a function of tau, not a positional list, so it survives an
    August extract whose thresholds are not 0.25/0.5/0.75 -- the official page calls
    those example values. Monotonicity is the part that is mechanistically justified:
    higher tau means fewer winnable buildings, so the mask must tighten."""
    from giscup.optimize import default_near_tau_quantile

    assert default_near_tau_quantile(0.25) == 100.0
    assert default_near_tau_quantile(0.5) == 50.0
    assert default_near_tau_quantile(0.75) == 25.0

    taus = [i / 100 for i in range(1, 101)]
    quantiles = [default_near_tau_quantile(t) for t in taus]
    assert quantiles == sorted(quantiles, reverse=True)
