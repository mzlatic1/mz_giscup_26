"""The feasibility gate must reproduce a run that actually happened.

The gate read PASS at 4.01 h / 5.0x headroom. The v2 nine-block run then took
9.42 h (33,898 s measured, 9 h 25 m wall) on the same dataset, same 400 m radius,
same flags. A gate wrong by 2.35x in the optimistic direction is not a gate.

Root cause: the verification constant. The model used 0.051 s per building per 1000
antennas, carried from an early measurement. Decomposing v2 against measured greedy
timings gives 0.826 -- **16.2x** larger:

    setup x9            30 s   0.1%   (3.32 s measured, not the 8.5 min once claimed)
    greedy           6,174 s  18.2%   (48 / 510 / 1500 s at k=50 / 500 / 1000, x3 taus)
    verification    27,694 s  81.7%   -> 27,694 / 33,540 building-k units = 0.826

So verification is not a correction term on the greedy model; it *is* the runtime.

This file pins the gate against that observed run. Any future change to the cost
model has to keep predicting it.
"""

from __future__ import annotations

import pytest

from giscup.gate_model import (
    MEASURED_AT_SOLVE_RADIUS_M,
    MEASURED_AT_VERIFY_RADIUS_FACTOR,
    MEASURED_AT_VERIFY_RADIUS_M,
    MEASURED_VERIFY_S_PER_BUILDING_PER_1K,
    calibrated_verify_seconds,
    pessimistic_verify_seconds,
    projected_verify_seconds,
    verify_constant_for,
    verify_speedup,
)

# The v2 run, measured 2026-08-09. (tau, k) -> buildings re-verified in that block.
V2_REVERIFIED = {
    (0.25, 50): 1_931, (0.25, 500): 9_468, (0.25, 1000): 11_920,
    (0.5, 50): 451, (0.5, 500): 4_659, (0.5, 1000): 8_815,
    (0.75, 50): 52, (0.75, 500): 1_990, (0.75, 1000): 4_625,
}
V2_VERIFY_SECONDS = 27_694.0
V2_BUILDINGS = 12_860


def test_the_calibrated_model_reproduces_the_v2_run():
    """The whole point of the file. Within 10% of what was actually observed."""
    predicted = calibrated_verify_seconds(V2_REVERIFIED)
    ratio = predicted / V2_VERIFY_SECONDS
    assert 0.90 <= ratio <= 1.10, (
        f"gate predicts {predicted/3600:.2f} h of verification, v2 measured "
        f"{V2_VERIFY_SECONDS/3600:.2f} h (ratio {ratio:.2f})"
    )


def test_the_old_constant_would_have_failed_this_test():
    """Guards against silently reverting to 0.051. That constant under-predicts the
    observed run by more than 15x, which is how the gate came to read PASS at 4.01 h."""
    old = 0.051
    predicted = calibrated_verify_seconds(V2_REVERIFIED, seconds_per_building_per_1k=old)
    assert predicted / V2_VERIFY_SECONDS < 0.10


def test_the_pessimistic_bound_is_above_the_calibrated_estimate():
    """A gate may be wrong, but only in the safe direction. Bounding claims by the
    building count must never come out below what was actually observed."""
    bound = pessimistic_verify_seconds(V2_BUILDINGS, verify_buildings=2000)
    assert bound > V2_VERIFY_SECONDS


def test_the_pessimistic_bound_is_not_absurdly_loose():
    """Pessimism has to stay useful. More than 4x the observed cost would make the
    gate fail runs that comfortably fit, which is its own way of being useless."""
    bound = pessimistic_verify_seconds(V2_BUILDINGS, verify_buildings=2000)
    assert bound / V2_VERIFY_SECONDS < 4.0


def test_cost_scales_linearly_in_k():
    """Each claimed building is re-measured against every antenna, so doubling k
    doubles the work. If this ever stops holding the constant is meaningless."""
    one = calibrated_verify_seconds({(0.5, 500): 1_000})
    two = calibrated_verify_seconds({(0.5, 1000): 1_000})
    assert two == pytest.approx(2 * one, rel=1e-9)


def test_cost_scales_linearly_in_buildings():
    one = calibrated_verify_seconds({(0.5, 500): 1_000})
    two = calibrated_verify_seconds({(0.5, 500): 2_000})
    assert two == pytest.approx(2 * one, rel=1e-9)


def test_the_constant_is_the_measured_one():
    assert MEASURED_VERIFY_S_PER_BUILDING_PER_1K == pytest.approx(0.826, abs=0.005)


# --- projecting onto a dataset you have not solved yet -----------------------


def test_the_projection_reproduces_v2_at_v2s_size():
    """Claim ratios, not claim counts, are what transfers to a new extract. At the
    size they were measured on, they must give back the observed cost."""
    predicted = projected_verify_seconds(V2_BUILDINGS)
    assert predicted / V2_VERIFY_SECONDS == pytest.approx(1.0, abs=0.05)


def test_the_projection_scales_with_dataset_size():
    small = projected_verify_seconds(V2_BUILDINGS)
    big = projected_verify_seconds(2 * V2_BUILDINGS)
    assert big == pytest.approx(2 * small, rel=1e-9)


def test_the_projection_sits_below_the_pessimistic_bound():
    """Two numbers, and the gate must report both: a bound that cannot be exceeded and
    an estimate of what will actually happen. Reporting only the bound reads as a
    near-failure on a run with 2x headroom; reporting only the estimate is how the
    gate came to say 5.0x."""
    assert projected_verify_seconds(V2_BUILDINGS) < pessimistic_verify_seconds(
        V2_BUILDINGS, verify_buildings=2000
    )


# --- parallel verification (#18) --------------------------------------------


def test_speedup_matches_the_measured_points():
    """Measured on a real block (tau=0.75/k=500, 150 claims x 500 antennas) while two
    other jobs were running, so these are floors, not ceilings."""
    assert verify_speedup(1) == pytest.approx(1.00)
    assert verify_speedup(4) == pytest.approx(3.10)
    assert verify_speedup(12) == pytest.approx(4.70)


def test_speedup_never_extrapolates_above_what_was_measured():
    """Scaling stopped paying at 12 workers (39% efficiency). Assuming it keeps
    improving is how a gate starts lying again."""
    assert verify_speedup(64) == verify_speedup(12)
    assert verify_speedup(1000) == pytest.approx(4.70)


def test_an_unmeasured_worker_count_rounds_down_to_a_measured_one():
    """6 workers gets 4 workers' speedup, not an interpolated guess."""
    assert verify_speedup(6) == verify_speedup(4)
    assert verify_speedup(3) == verify_speedup(2)


def test_speedup_is_monotonic():
    values = [verify_speedup(w) for w in (1, 2, 4, 8, 12)]
    assert values == sorted(values)


# --- the constant is not universal; it belongs to a radius PAIR ---------------
#
# 0.826 was measured on a 400 m solve, and `--verify-radius-factor 2.0` means that
# run verified at 800 m. It is not a property of the solver -- it is the cost of
# exact coverage against however many blockers an 800 m query returns.
#
# #3b is live: the 600 m matrix was built 2026-08-09, and a 600 m solve verifies at
# 1200 m, where the per-building cost is materially higher. Reusing 0.826 there
# would understate verification -- the same failure as #16, same mechanism, same
# direction, and nothing in the code recorded the coupling until now.


def test_the_constant_is_returned_at_the_radius_pair_it_was_measured_on():
    got = verify_constant_for(
        MEASURED_AT_SOLVE_RADIUS_M, MEASURED_AT_VERIFY_RADIUS_FACTOR
    )
    assert got == pytest.approx(MEASURED_VERIFY_S_PER_BUILDING_PER_1K)


def test_the_measured_pair_is_400_solving_and_800_verifying():
    """Pinned because the whole refusal below is meaningless if these drift."""
    assert MEASURED_AT_SOLVE_RADIUS_M == pytest.approx(400.0)
    assert MEASURED_AT_VERIFY_RADIUS_FACTOR == pytest.approx(2.0)
    assert MEASURED_AT_VERIFY_RADIUS_M == pytest.approx(800.0)


def test_a_600_metre_solve_is_refused_rather_than_costed_with_the_wrong_constant():
    """The gate must not silently produce a number for a radius it never measured.
    Refusing is the safe direction: a loud stop costs one session, a quiet 2x error
    costs the submission."""
    with pytest.raises(ValueError) as exc:
        verify_constant_for(600.0, 2.0)
    message = str(exc.value)
    assert "1200" in message, "the error must name the verify radius actually requested"
    assert "800" in message, "and the one the constant was measured at"


def test_changing_only_the_verify_factor_is_also_refused():
    """400 m solving with factor 1.0 verifies at 400 m, not 800 -- a different cost
    even though the solve radius is unchanged. The pair is what matters."""
    with pytest.raises(ValueError):
        verify_constant_for(400.0, 1.0)


def test_unbounded_verification_is_refused():
    """`--verify-radius-factor 0` means no cull at all. The board measured ~1,180
    blockers per unbounded query against 21 at 400 m; costing that with an 800 m
    constant is not an approximation, it is a different problem."""
    with pytest.raises(ValueError):
        verify_constant_for(400.0, 0.0)


def test_an_unbounded_solve_is_refused():
    with pytest.raises(ValueError):
        verify_constant_for(None, 2.0)


def test_an_explicit_override_is_honoured():
    """The escape hatch exists so a future session that MEASURES 600/1200 can cost
    it without editing the module. Passing a number is a claim that you measured
    it -- which is the point, because it cannot happen by accident."""
    assert verify_constant_for(600.0, 2.0, override=2.5) == pytest.approx(2.5)


def test_parallel_verification_moves_the_gate_off_the_margin():
    """The point of #18. Serial verification put the pessimistic bound at 1.0x
    headroom against a 20 h budget -- no margin for a denser August extract."""
    serial = pessimistic_verify_seconds(V2_BUILDINGS, verify_buildings=2000)
    parallel = serial / verify_speedup(12)
    assert serial / 3600 > 15.0
    assert parallel / 3600 < 4.0
