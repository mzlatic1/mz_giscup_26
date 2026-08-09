"""The gate and the solver must default to the configuration we will actually run.

#18 parallelised claim verification and moved the feasibility gate from 19.34 h /
1.0x headroom to 6.87 h / 2.9x. But it left `--verify-workers` defaulting to 1 in
both `giscup` and `scripts/rehearse.py`, and `/rehearsal`'s documented command did
not pass the flag. So a session that follows the project's own instructions reads
the *serial* number -- a near-FAIL -- and the fix is invisible unless you already
know it exists.

Two ways that costs the competition:

1. A future session reads 1.0x headroom, concludes feasibility is unsolved, and
   spends the remaining days re-solving a solved problem.
2. Somebody runs `solve-all` on 2026-08-15 without the flag and spends ~12 extra
   hours of a ~24 h window on single-core verification.

The rule this file pins: **the gate's default must equal the solver's default.**
A gate that models a configuration the solver will not use is not a gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from giscup.cli import build_parser
from giscup.gate_model import MEASURED_VERIFY_SPEEDUP, default_verify_workers

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_rehearse():
    """`scripts/` is not a package, so import the gate script by path."""
    spec = importlib.util.spec_from_file_location(
        "rehearse", REPO_ROOT / "scripts" / "rehearse.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the default itself ------------------------------------------------------


def test_a_sixteen_core_host_does_not_verify_on_one_core():
    """This host has 16 cores and verification was using exactly one of them."""
    assert default_verify_workers(16) > 1


def test_the_default_never_exceeds_what_was_measured():
    """Speedup had already decayed to 39% efficiency at 12 workers. Defaulting
    above the top of the measured table would be the same extrapolation that made
    this gate optimistic by 2.35x in the first place."""
    ceiling = max(MEASURED_VERIFY_SPEEDUP)
    assert default_verify_workers(64) == ceiling
    assert default_verify_workers(16) <= ceiling


def test_the_default_never_exceeds_the_cores_available():
    """Oversubscribing memory-bandwidth-bound work makes it slower, not faster."""
    assert default_verify_workers(4) == 4
    assert default_verify_workers(2) == 2


def test_a_single_core_host_gets_serial_verification():
    assert default_verify_workers(1) == 1


def test_a_host_that_will_not_report_its_core_count_gets_serial(monkeypatch):
    """`os.cpu_count()` may return None. Guessing high on an unknown host risks
    thrashing it; serial is the safe direction when you genuinely do not know."""
    monkeypatch.setattr("os.cpu_count", lambda: None)
    assert default_verify_workers() == 1


def test_a_nonsense_core_count_does_not_produce_zero_workers():
    """Zero workers would mean no verification at all -- every claim unchecked,
    which is a correctness failure, not a slow run."""
    assert default_verify_workers(0) == 1
    assert default_verify_workers(-4) == 1


# --- the two entry points that have to agree ---------------------------------


def test_the_solver_cli_does_not_default_to_serial_verification():
    parser = build_parser()
    args = parser.parse_args(
        ["solve-all", "--input", "x.geojson", "--taus", "0.5", "--ks", "10",
         "--output", "out.txt"]
    )
    assert args.verify_workers == default_verify_workers()


def test_the_gate_does_not_default_to_serial_verification():
    rehearse = _load_rehearse()
    parser_default = rehearse.build_parser().get_default("verify_workers")
    assert parser_default == default_verify_workers()


def test_the_gate_and_the_solver_agree_on_the_default():
    """The invariant behind this whole file. If these ever drift, the gate is
    predicting the runtime of a configuration that will not be run."""
    rehearse = _load_rehearse()
    parser = build_parser()
    solver_default = parser.parse_args(
        ["solve-all", "--input", "x.geojson", "--taus", "0.5", "--ks", "10",
         "--output", "out.txt"]
    ).verify_workers
    assert rehearse.build_parser().get_default("verify_workers") == solver_default


def test_the_flag_still_overrides_the_default():
    """Auto-selection must not take the knob away -- the A/B in #18 needed to pin
    workers to 1, 2, 4, 8 and 12 to measure the speedup at all."""
    parser = build_parser()
    args = parser.parse_args(
        ["solve-all", "--input", "x.geojson", "--taus", "0.5", "--ks", "10",
         "--output", "out.txt", "--verify-workers", "1"]
    )
    assert args.verify_workers == 1


# --- the documented command --------------------------------------------------


def test_the_rehearsal_command_documents_the_flag_it_depends_on():
    """`/rehearsal` prints a command for the operator to run. When it omitted
    `--verify-workers`, the verdict it produced was 2.8x worse than the truth."""
    text = (REPO_ROOT / ".claude" / "commands" / "rehearsal.md").read_text()
    assert "--verify-workers" in text


def test_the_rehearsal_command_explains_that_the_gate_reports_two_numbers():
    """The gate prints an upper bound AND a likely estimate (#16). Reading only
    the bound looks like a near-failure on a run with real headroom; reading only
    the likely figure is how it came to claim 5.0x."""
    text = (REPO_ROOT / ".claude" / "commands" / "rehearsal.md").read_text()
    lowered = text.lower()
    assert "upper bound" in lowered and "likely" in lowered
