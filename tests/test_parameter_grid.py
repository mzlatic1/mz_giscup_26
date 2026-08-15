"""The (tau, k) grid must come from the competition, not from a constant in this repo.

Until 2026-08-15 three places hardcoded `0.25/0.5/0.75` x `50/500/1000`. That was
harmless right up until it wasn't: the competition dataset ships a companion
`competition-parameters.txt`, and CLAUDE.md's source-of-truth order puts dataset
inspection *above* repository docs. If that file names a different grid, the hardcodes
fail in two ways that both cost the whole submission:

* `giscup.assemble.REQUIRED_SUBPROBLEMS` -- `scripts/assemble_blocks.py` never exposed
  the `required=` override, so the crash-recovery path would refuse to assemble a
  correct set of blocks. That is the one contingency that exists for a run dying at
  hour 5 of a 24-hour window.
* `scripts/audit_submission.py` -- would report FAIL and exit 1 on a *correct*
  submission, at the last gate before upload, with no time to diagnose it.

There is one submission and no score feedback, so a clerical failure here is
indistinguishable from a solver failure. These tests pin the grid to an argument.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from giscup.assemble import (
    DEFAULT_KS,
    DEFAULT_TAUS,
    REQUIRED_SUBPROBLEMS,
    assemble_blocks,
    parse_blocks,
    subproblem_grid,
)

# Real projected magnitudes -- a unit-square coordinate cannot exercise anything that
# matters here (CLAUDE.md: one ULP is ~5e-10 m at 3.7e6).
E0 = 500_000.0
N0 = 3_700_000.0

# A deliberately different grid: different taus, different ks, and a different *count*,
# so a check that merely counts nine blocks cannot pass by accident.
ALT_TAUS = (0.3, 0.6)
ALT_KS = (10, 100)


def _block(tau: float, k: int, claims: str = "1, 2") -> str:
    pts = ", ".join(f"({E0 + i:.17g}, {N0 + i:.17g})" for i in range(k))
    return f"({tau}, {k})\n{pts}\n{claims}"


def _grid_text(taus, ks) -> str:
    return "\n".join(_block(tau, k) for tau in taus for k in ks)


def _load_script(name: str):
    """`scripts/` is not a package, so import by path -- same trick as
    `tests/test_audit_two_stage.py`."""
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_default_grid_is_still_the_nine_assumed_subproblems():
    """Hardening must not quietly change the shipped default. Everything measured in
    this project is fitted on this grid."""
    assert subproblem_grid() == REQUIRED_SUBPROBLEMS
    assert len(REQUIRED_SUBPROBLEMS) == 9
    assert DEFAULT_TAUS == (0.25, 0.5, 0.75)
    assert DEFAULT_KS == (50, 500, 1000)


def test_the_grid_is_tau_outer_k_inner():
    """Order is how a reader keys a block to a subproblem, and it is the emission
    order of `assemble_blocks`. Transposing it silently mislabels every block."""
    assert subproblem_grid((0.25, 0.5), (50, 500)) == (
        (0.25, 50), (0.25, 500), (0.5, 50), (0.5, 500),
    )


def test_assemble_recovers_a_run_solved_on_a_different_published_grid():
    """The contingency this exists for: the solve dies partway and the published grid
    is not the assumed one. Before 2026-08-15 this raised 'missing 9 of 9'."""
    required = subproblem_grid(ALT_TAUS, ALT_KS)
    out = assemble_blocks([_grid_text(ALT_TAUS, ALT_KS)], required=required)

    blocks = parse_blocks(out)
    assert [(b.tau, b.k) for b in blocks] == list(required)
    assert len(out.splitlines()) == 3 * len(required)


def test_assemble_still_refuses_a_block_missing_from_a_custom_grid():
    """Hardening must not become permissiveness. An absent block scores ~0 on that
    subproblem, so the tool still refuses rather than emitting a short file."""
    required = subproblem_grid(ALT_TAUS, ALT_KS)
    partial = _grid_text(ALT_TAUS, ALT_KS[:1])

    with pytest.raises(ValueError, match="missing"):
        assemble_blocks([partial], required=required)


def test_assemble_blocks_script_exposes_the_grid_and_defaults_to_nine():
    parser = _load_script("assemble_blocks").build_parser()
    args = parser.parse_args(["--input", "a.txt", "--output", "b.txt"])
    assert subproblem_grid(args.taus, args.ks) == REQUIRED_SUBPROBLEMS


def test_assemble_blocks_script_assembles_a_non_default_grid(tmp_path):
    """End to end through `main`, because the defect was that the CLI never reached
    the `required=` argument the library already had."""
    source = tmp_path / "partial.txt"
    source.write_text(_grid_text(ALT_TAUS, ALT_KS), encoding="utf-8")
    out = tmp_path / "assembled.txt"

    rc = _load_script("assemble_blocks").main([
        "--input", str(source), "--output", str(out),
        "--taus", *[str(t) for t in ALT_TAUS],
        "--ks", *[str(k) for k in ALT_KS],
    ])

    assert rc == 0
    assert [(b.tau, b.k) for b in parse_blocks(out.read_text(encoding="utf-8"))] == list(
        subproblem_grid(ALT_TAUS, ALT_KS)
    )


def test_audit_script_exposes_the_grid_and_defaults_to_nine():
    parser = _load_script("audit_submission").build_parser()
    args = parser.parse_args(["--input", "x.geojson", "--solution", "y.txt"])
    assert subproblem_grid(args.taus, args.ks) == REQUIRED_SUBPROBLEMS


def test_audit_passes_structure_on_a_correct_non_default_grid(tmp_path, capsys, monkeypatch):
    """The expensive failure: a *correct* submission failing its own audit at the last
    gate before upload.

    Only the structure section is exercised. It runs before `load_buildings`, so the
    loader is replaced with a sentinel -- the dataset-dependent checks need a real
    geojson and are covered in `tests/test_audit_two_stage.py`.
    """
    module = _load_script("audit_submission")
    solution = tmp_path / "solution.txt"
    solution.write_text(_grid_text(ALT_TAUS, ALT_KS), encoding="utf-8")

    class _Sentinel(Exception):
        pass

    def _stop(*args, **kwargs):
        raise _Sentinel

    monkeypatch.setattr(module, "load_buildings", _stop)

    with pytest.raises(_Sentinel):
        module.main([
            "--input", "unused.geojson", "--solution", str(solution),
            "--taus", *[str(t) for t in ALT_TAUS],
            "--ks", *[str(k) for k in ALT_KS],
        ])

    printed = capsys.readouterr().out
    structure = printed.split("DATASET-DEPENDENT CHECKS")[0]
    assert "[FAIL]" not in structure, structure
    assert f"{len(subproblem_grid(ALT_TAUS, ALT_KS))} blocks present" in structure


def test_audit_still_fails_a_submission_that_does_not_match_the_declared_grid(
    tmp_path, capsys, monkeypatch
):
    """The check must still bite. A file solved for the wrong grid is unsubmittable,
    and this is the last place that can say so."""
    module = _load_script("audit_submission")
    solution = tmp_path / "solution.txt"
    solution.write_text(_grid_text(ALT_TAUS, ALT_KS), encoding="utf-8")

    class _Sentinel(Exception):
        pass

    monkeypatch.setattr(module, "load_buildings", lambda *a, **k: (_ for _ in ()).throw(_Sentinel()))

    # Declares the default nine while the file holds four blocks on another grid.
    with pytest.raises(_Sentinel):
        module.main(["--input", "unused.geojson", "--solution", str(solution)])

    structure = capsys.readouterr().out.split("DATASET-DEPENDENT CHECKS")[0]
    assert "[FAIL]" in structure
