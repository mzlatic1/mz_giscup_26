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
from giscup.gate_model import (
    DEFAULT_OBJECTIVE,
    MEASURED_VERIFY_CONSTANTS,
    MEASURED_VERIFY_SPEEDUP,
    default_verify_workers,
)

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


# --- the same invariant, for the OBJECTIVE (found 2026-08-10) ----------------
#
# #15 made lever A the solver's default but left the gate defaulting to 'baseline'.
# That is this file's bug a second time, and it errs in the DANGEROUS direction:
# baseline is the cheapest constant in the module (0.826 vs near-tau's 1.26), so the
# documented gate command costed a lever A day as baseline and hid ~1.77 h on the
# bound. `verify_constant_for` already refuses an *unknown* objective for exactly this
# reason; it cannot catch a known-but-wrong one.


def _solve_all_args(parser, *extra):
    return parser.parse_args(
        ["solve-all", "--input", "x.geojson", "--taus", "0.5", "--ks", "10",
         "--output", "out.txt", *extra]
    )


def test_the_shared_default_objective_is_one_we_have_measured():
    """A default the gate cannot cost would make `verify_constant_for` raise on the
    plainest possible command."""
    assert DEFAULT_OBJECTIVE in MEASURED_VERIFY_CONSTANTS


def test_the_solver_cli_defaults_to_the_shared_objective():
    assert _solve_all_args(build_parser()).objective == DEFAULT_OBJECTIVE


def test_the_gate_defaults_to_the_shared_objective():
    rehearse = _load_rehearse()
    assert rehearse.build_parser().get_default("objective") == DEFAULT_OBJECTIVE


def test_the_gate_and_the_solver_agree_on_the_objective():
    """The invariant. A gate costing baseline while the solver runs lever A is
    predicting the runtime of a configuration that will not be run -- and doing it
    with the cheaper of the two constants."""
    rehearse = _load_rehearse()
    solver_default = _solve_all_args(build_parser()).objective
    assert rehearse.build_parser().get_default("objective") == solver_default


def test_the_gate_does_not_silently_cost_the_cheaper_objective():
    """Pins the direction of the 2026-08-10 bug, not just the equality above. If
    both entry points were flipped to 'baseline' together the equality test would
    still pass while the gate went quietly optimistic."""
    rehearse = _load_rehearse()
    gate_default = rehearse.build_parser().get_default("objective")
    cheapest = min(MEASURED_VERIFY_CONSTANTS, key=MEASURED_VERIFY_CONSTANTS.get)
    assert MEASURED_VERIFY_CONSTANTS[gate_default] >= MEASURED_VERIFY_CONSTANTS[cheapest]
    assert gate_default != "baseline", (
        "the gate is costing the cheapest measured objective by default; that is the "
        "#16 failure mode -- re-read gate_model.DEFAULT_OBJECTIVE before changing this"
    )


def test_the_objective_flag_still_overrides_on_both_sides():
    """The escape hatch is load-bearing: `(0.5, 1000)` ships baseline, and that block
    has to be both solvable and costable."""
    rehearse = _load_rehearse()
    assert _solve_all_args(build_parser(), "--objective", "baseline").objective == "baseline"
    parsed = rehearse.build_parser().parse_args(
        ["--input", "x.geojson", "--objective", "baseline"]
    )
    assert parsed.objective == "baseline"


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
