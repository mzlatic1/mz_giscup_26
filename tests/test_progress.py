"""Progress reporting for long solver runs (ranked gap #1).

A full nine-block run takes ~3 h and printed nothing until it finished, which makes a
healthy run indistinguishable from a hung one. On submission day there is one shot and
no score feedback, so "is it still working?" has to be answerable from the terminal.

The ETA model is measured, not assumed. From the 2026-08-08 nine-block run on the
official dataset, per-subproblem runtime against k:

    k=50    85.4 / 69.4 / 54.3 s
    k=500   1177.7 / 1150.5 / 925.3 s
    k=1000  1705.4 / 2406.5 / 2266.1 s

Least squares gives 2.16 s per antenna with a -24 s intercept: cost is proportional to
`k` with no meaningful fixed term. So remaining work must be weighted by k, not by
subproblem count. Weighting by count is off by 14x after the first block.
"""

from __future__ import annotations

import io

import pytest

from giscup.progress import ProgressReporter, greedy_report_interval, remaining_seconds

# The measured nine-block plan, in the order cmd_solve_all emits it (tau outer, k inner).
PLAN = [(t, k) for t in (0.25, 0.5, 0.75) for k in (50, 500, 1000)]
MEASURED = [85.4, 1177.7, 1705.4, 69.4, 1150.5, 2406.5, 54.3, 925.3, 2266.1]


# --- the ETA model ----------------------------------------------------------


def test_remaining_scales_with_work_not_with_count():
    """One k=50 block done out of nine does NOT mean 1/9 of the work is done."""
    # 50 of 4650 antennas done in 85.4 s -> the other 4600 take ~7857 s.
    assert remaining_seconds(elapsed=85.4, work_done=50, work_total=4650) == pytest.approx(
        7857.0, rel=0.01
    )


def test_remaining_is_zero_when_everything_is_done():
    assert remaining_seconds(elapsed=9840.6, work_done=4650, work_total=4650) == 0.0


def test_remaining_never_goes_negative():
    assert remaining_seconds(elapsed=100.0, work_done=200, work_total=100) == 0.0


def test_remaining_is_unknown_before_any_work_completes():
    """With no completed work there is no rate to extrapolate from; say so rather
    than dividing by zero or inventing a number."""
    assert remaining_seconds(elapsed=0.0, work_done=0, work_total=4650) is None


def test_the_model_tracks_the_measured_run_within_twenty_percent():
    """Replay the real timings and check the ETA converges on the truth.

    This is the property that matters: the number on screen has to be good enough to
    distinguish "on track" from "wedged". Early estimates are allowed to be loose.
    """
    total = sum(MEASURED)
    work_total = sum(k for _, k in PLAN)
    elapsed = 0.0
    work_done = 0
    errors = []
    for (_, k), seconds in zip(PLAN, MEASURED):
        elapsed += seconds
        work_done += k
        eta = remaining_seconds(elapsed, work_done, work_total)
        actual = total - elapsed
        if actual > 0:
            errors.append(abs(eta - actual) / actual)
    # Worst case is the very first block; by the halfway mark it must be close.
    assert max(errors) < 0.20, f"worst ETA error {max(errors):.1%}"
    assert errors[-2] < 0.05, f"late ETA error {errors[-2]:.1%}"


def test_count_weighting_would_have_been_much_worse():
    """Guards the design decision itself, so nobody 'simplifies' it back later."""
    total = sum(MEASURED)
    by_count = remaining_seconds(elapsed=MEASURED[0], work_done=1, work_total=len(PLAN))
    by_work = remaining_seconds(elapsed=MEASURED[0], work_done=PLAN[0][1], work_total=4650)
    actual = total - MEASURED[0]
    # Under-estimates saturate at 100% relative error, so state it as a ratio: after
    # the first (k=50) block, count weighting promises the rest in 11 min. It took 163.
    assert actual / by_count > 10.0, f"count-weighted predicted {by_count:.0f}s of {actual:.0f}s"
    assert abs(by_work - actual) / actual < 0.25


# --- the reporter -----------------------------------------------------------


def test_it_announces_each_subproblem_before_working_on_it():
    """The line must appear at the START. A line printed on completion still leaves
    the 40-minute k=1000 block silent, which is the whole bug."""
    out = io.StringIO()
    reporter = ProgressReporter(PLAN, stream=out)
    reporter.start_subproblem(0.25, 50)
    text = out.getvalue()
    assert "0.25" in text and "50" in text
    assert "1/9" in text


def test_it_reports_an_eta_once_a_subproblem_has_finished():
    out = io.StringIO()
    reporter = ProgressReporter(PLAN, stream=out)
    reporter.start_subproblem(0.25, 50)
    reporter.finish_subproblem(claimed=1652)
    reporter.start_subproblem(0.25, 500)
    assert "eta" in out.getvalue().lower()


def test_it_reports_claimed_counts_so_quality_is_visible_during_the_run():
    """Serviced-building counts are the scored quantity; seeing them accumulate is
    how you notice a config is broken before burning the remaining hours."""
    out = io.StringIO()
    reporter = ProgressReporter(PLAN, stream=out)
    reporter.start_subproblem(0.25, 50)
    reporter.finish_subproblem(claimed=1652)
    assert "1,652" in out.getvalue() or "1652" in out.getvalue()


def test_phases_are_labelled_within_a_subproblem():
    """A k=1000 block runs ~40 min; per-subproblem lines alone leave a 40 min gap."""
    out = io.StringIO()
    reporter = ProgressReporter(PLAN, stream=out)
    reporter.start_subproblem(0.25, 1000)
    reporter.phase("greedy", "picked 250/1000")
    assert "greedy" in out.getvalue()
    assert "250/1000" in out.getvalue()


def test_disabled_reporter_writes_nothing():
    out = io.StringIO()
    reporter = ProgressReporter(PLAN, stream=out, enabled=False)
    reporter.start_subproblem(0.25, 50)
    reporter.phase("greedy", "picked 10/50")
    reporter.finish_subproblem(claimed=1652)
    assert out.getvalue() == ""


def test_it_flushes_so_output_is_visible_in_a_redirected_log():
    """Background runs are redirected to a file; block buffering would hide every
    line until the process exits, which is exactly the failure being fixed."""

    class CountingStream(io.StringIO):
        flushes = 0

        def flush(self):
            type(self).flushes += 1

    out = CountingStream()
    ProgressReporter(PLAN, stream=out).start_subproblem(0.25, 50)
    assert CountingStream.flushes > 0


def test_it_rejects_an_empty_plan():
    with pytest.raises(ValueError, match="plan"):
        ProgressReporter([], stream=io.StringIO())


# --- greedy reporting cadence -----------------------------------------------
#
# One greedy pick costs ~1 s (measured: k=500 greedy ran 8.3 min). The cadence trades
# log noise against how long a stall can hide. The competition k values are 50/500/1000.


def test_cadence_keeps_every_k_under_a_forty_line_budget():
    """Nine subproblems must not bury the per-subproblem lines in pick spam."""
    for k in (50, 500, 1000):
        lines = k // greedy_report_interval(k)
        assert lines <= 40, f"k={k} would emit {lines} progress lines"


def test_cadence_reports_at_least_a_few_times_even_at_small_k():
    """k=50 finishes in ~1 min, but it must still show signs of life."""
    assert 1 <= greedy_report_interval(50) <= 25


def test_cadence_never_returns_zero_or_negative():
    for k in (1, 2, 7, 50, 500, 1000, 5000):
        assert greedy_report_interval(k) >= 1


def test_cadence_bounds_how_long_a_stall_can_hide():
    """At ~1 s per pick, no gap between lines should exceed ~2 min of silence."""
    for k in (50, 500, 1000):
        assert greedy_report_interval(k) <= 120, f"k={k} could go silent for >2 min"
