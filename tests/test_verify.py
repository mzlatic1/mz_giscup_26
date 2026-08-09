"""Un-culled verification pass (task board #3).

These pin only the invariants that hold for *any* sane selection policy. The band
width, the below-tau cutoff, and the ordering under a cap are deliberate design
choices; tests for those follow once the policy is decided.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.geometry import make_building
from giscup.sampling import SamplingProfile, sample_boundaries
from giscup.verify import exact_coverage_for, select_buildings_to_reverify, verify_and_recover
from giscup.visibility import BlockerIndex

PROFILE = SamplingProfile("test", 6.0, 4)


def _scene():
    polys = [
        Polygon([(x, y), (x + 12, y), (x + 12, y + 12), (x, y + 12)])
        for x, y in [(0, 0), (30, 0), (60, 0)]
    ]
    buildings = [make_building(i, p) for i, p in enumerate(polys)]
    return buildings, sample_boundaries(buildings, PROFILE)


# --- selection policy -------------------------------------------------------
#
# Decided 2026-08-07 (Marko): band is RELATIVE to tau, the window is TWO-SIDED, and
# selection is closest-to-tau first under a cap.
#
#   window = [tau * (1 - band), tau * (1 + band))
#
# Below tau  -> recover buildings the radius cull under-reported (task #3).
# Above tau  -> drop overclaims the in-sample grid over-reported (task #12).


def test_a_building_just_below_tau_is_reverified():
    """The cull under-reports, so something just short may actually clear tau."""
    coverage = {"near": 0.74, "far": 0.05}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert "near" in chosen
    assert "far" not in chosen


def test_a_building_just_above_tau_is_reverified():
    """Two-sided: the in-sample grid over-reports, so claims near tau are suspect."""
    coverage = {"just_above": 0.7551, "far_above": 0.99}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert "just_above" in chosen, "task #12's overclaim must be caught"
    assert "far_above" not in chosen, "comfortably above tau is not worth the re-check"


@pytest.mark.parametrize(
    ("tau", "inside", "outside"),
    [
        # half_width = max(tau * band, BAND_FLOOR=0.05)
        (0.25, 0.24, 0.15),  # floor binds:    window [0.200, 0.300)
        (0.50, 0.46, 0.40),  # floor ties:     window [0.450, 0.550)
        (0.75, 0.68, 0.60),  # relative binds: window [0.675, 0.825)
    ],
)
def test_band_scales_with_tau(tau, inside, outside):
    coverage = {"in": inside, "out": outside}
    chosen = select_buildings_to_reverify(coverage, tau=tau, band=0.10)
    assert "in" in chosen
    assert "out" not in chosen


def test_selection_is_ordered_closest_to_tau_first():
    """Under a cap, the likeliest flips must come first. Distance is two-sided."""
    coverage = {"far_below": 0.69, "near_below": 0.745, "near_above": 0.752, "far_above": 0.81}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    distances = [abs(coverage[bid] - 0.75) for bid in chosen]
    assert distances == sorted(distances)


def test_selection_respects_the_cap():
    coverage = {str(i): 0.70 + i * 0.001 for i in range(50)}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10, max_buildings=5)
    assert len(chosen) == 5
    # The cap must keep the closest five, not an arbitrary five.
    kept = sorted(abs(coverage[bid] - 0.75) for bid in chosen)
    everything = sorted(abs(v - 0.75) for v in coverage.values())
    assert kept == pytest.approx(everything[:5])


def test_selection_returns_only_known_building_ids():
    coverage = {"a": 0.70, "b": 0.40, "c": 0.74}
    chosen = select_buildings_to_reverify(coverage, tau=0.75, band=0.10)
    assert set(chosen) <= set(coverage)
    assert len(set(chosen)) == len(chosen), "no duplicates"


def test_empty_coverage_selects_nothing():
    assert select_buildings_to_reverify({}, tau=0.5, band=0.10) == []


# --- exact re-measurement ---------------------------------------------------


def test_exact_coverage_is_zero_without_antennas():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, checks = exact_coverage_for([0], [], samples, buildings, index)
    assert coverage == {} and checks == 0


def test_exact_coverage_only_touches_requested_buildings():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, checks = exact_coverage_for([1], [(6.0, 0.0)], samples, buildings, index)
    assert set(coverage) == {1}
    assert checks > 0


def test_exact_coverage_is_a_ratio_in_the_unit_interval():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (12.0, 12.0), (36.0, 0.0)]
    coverage, _ = exact_coverage_for([0, 1, 2], points, samples, buildings, index)
    assert coverage
    for ratio in coverage.values():
        assert 0.0 <= ratio <= 1.0


def test_an_antenna_on_a_building_covers_some_of_its_own_boundary():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, _ = exact_coverage_for([0], [(6.0, 0.0)], samples, buildings, index)
    assert coverage[0] > 0.0


@pytest.mark.parametrize("bad_tau", [0.0, 1.5])
def test_exact_coverage_ignores_tau_entirely(bad_tau):
    """exact_coverage_for measures; thresholding is the caller's job."""
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    coverage, _ = exact_coverage_for([0], [(6.0, 0.0)], samples, buildings, index)
    assert 0.0 <= coverage[0] <= 1.0


# --- two-sided recover and drop ---------------------------------------------


def test_overclaim_above_tau_is_dropped():
    """Task #12: a claim whose exact coverage misses tau must not survive."""
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    # One antenna cannot cover 75% of building 1's perimeter; the sampled estimate
    # claimed it anyway, so the exact pass must drop it.
    reported = {1: 0.7551}
    final, report = verify_and_recover(
        coverage=reported,
        claimed=[1],
        tau=0.75,
        antenna_points=[(30.0, 0.0)],
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert 1 not in final, "overclaim should have been dropped"
    assert 1 in report.dropped_ids


def test_a_genuinely_covered_building_survives_verification():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    # Antennas on all four corners of building 0 see essentially its whole boundary.
    points = [(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (0.0, 12.0)]
    exact, _ = exact_coverage_for([0], points, samples, buildings, index)
    reported = {0: exact[0] * 0.99}  # slight under-report, inside the band
    final, report = verify_and_recover(
        coverage=reported,
        claimed=[0],
        tau=exact[0] * 0.98,
        antenna_points=points,
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert 0 in final
    assert 0 not in report.dropped_ids


def test_unclaimed_buildings_far_below_tau_are_left_untouched():
    """Recovery is banded: something at 0.02 against tau=0.50 cannot plausibly flip.

    Note claims are NOT subject to this -- every claim is verified regardless of how
    far its reported coverage sits from tau (#17). Only recovery is banded.
    """
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    _, report = verify_and_recover(
        coverage={1: 0.02},
        claimed=[],
        tau=0.50,
        antenna_points=[(6.0, 0.0)],
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert report.reverified_count == 0
    assert 1 not in report.coverage_after


def test_report_bounds_what_the_cull_was_hiding():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    points = [(0.0, 0.0), (12.0, 12.0)]
    exact, _ = exact_coverage_for([0], points, samples, buildings, index)
    reported = {0: exact[0] - 0.02}
    _, report = verify_and_recover(
        coverage=reported,
        claimed=[],
        tau=exact[0] - 0.01,
        antenna_points=points,
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert report.max_coverage_delta == pytest.approx(0.02, abs=1e-9)


# --- the relative band collapses at low tau ---------------------------------


def test_band_never_narrows_below_the_sampling_error():
    """At tau=0.25 a 10% relative band is +/-0.025, but sampled coverage carries
    +/-0.03 error. Without an absolute floor the window is narrower than the error it
    exists to catch, and low-tau overclaims escape re-verification entirely."""
    coverage = {"just_over": 0.28, "just_under": 0.22}
    chosen = select_buildings_to_reverify(coverage, tau=0.25, band=0.10)
    assert "just_over" in chosen, "0.28 is within sampling error of tau=0.25"
    assert "just_under" in chosen, "0.22 is within sampling error of tau=0.25"


def test_the_floor_does_not_shrink_a_wide_relative_band():
    """At tau=0.75 the relative band is already +/-0.075; the floor must not reduce it."""
    coverage = {"far": 0.69}
    assert "far" in select_buildings_to_reverify(coverage, tau=0.75, band=0.10)


def test_the_floor_can_be_disabled():
    coverage = {"just_over": 0.28}
    assert select_buildings_to_reverify(coverage, tau=0.25, band=0.10, band_floor=0.0) == []


# --- claims are verified exhaustively, not by band (#17) ---------------------
#
# A band indexed on the SAMPLED value cannot catch the claims whose sampled value is
# most wrong: a large error is precisely what carries a building past the window's
# edge. Measured on the official dataset, a building with true coverage 0.1499 was
# claimed at tau=0.25 and never re-checked.
#
# The asymmetry that matters: an overclaim is a CORRECTNESS failure, a missed
# recovery is only lost score. So every claim is verified exactly; recovery below
# tau stays banded and capped, where being approximate costs opportunity only.


def test_every_claim_is_reverified_however_far_above_tau():
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    # Reported far above tau and far outside any band -- must still be checked.
    reported = {0: 0.99, 1: 0.85}
    _, report = verify_and_recover(
        coverage=reported,
        claimed=[0, 1],
        tau=0.25,
        antenna_points=[(6.0, 0.0)],
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert set(report.coverage_after) >= {0, 1}, "claims outside the band were skipped"


def test_an_overclaim_far_above_tau_is_still_dropped():
    """The exact failure found in the audit: sampled says 0.99, truth is far below.

    An antenna on building 0 sees exactly one of building 2's four edges, so its true
    coverage is 0.25 -- fine at tau=0.25, an overclaim at tau=0.5. The reported 0.99
    sits far outside any band around tau, which is precisely the case the old
    band-only verification could not catch.
    """
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    final, report = verify_and_recover(
        coverage={2: 0.99},
        claimed=[2],
        tau=0.5,
        antenna_points=[(6.0, 0.0)],
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
    )
    assert 2 not in final
    assert 2 in report.dropped_ids


def test_the_cap_limits_recovery_but_never_claim_verification():
    """max_buildings bounds the optional work, not the correctness work."""
    buildings, samples = _scene()
    index = BlockerIndex.from_buildings(buildings)
    claimed = [0, 1, 2]
    reported = {0: 0.99, 1: 0.98, 2: 0.97}
    _, report = verify_and_recover(
        coverage=reported,
        claimed=claimed,
        tau=0.25,
        antenna_points=[(6.0, 0.0)],
        samples=samples,
        buildings=buildings,
        blocker_index=index,
        band=0.10,
        max_buildings=1,
    )
    assert set(report.coverage_after) >= set(claimed), "a cap must not skip claim verification"
