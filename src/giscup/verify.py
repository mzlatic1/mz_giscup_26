"""Un-culled verification pass for near-threshold buildings (task board #3).

Why this exists
---------------
The visibility matrix is culled to pairs within a radius. Culling can only *remove*
visible pairs, so culled coverage is an **underestimate** of true coverage. That has
one good consequence and one bad one:

- Good: it can never cause an overclaim. A building we claim under the cull would
  also clear `tau` without it.
- Bad: it silently *forfeits* buildings. A building whose true coverage is 0.76 may
  measure 0.73 under the cull and go unclaimed at `tau = 0.75`. There is no score
  feedback in this competition, so that loss is invisible.

There is a second, opposite error. `solve_one` decides claims from the same sampled
grid it optimized on, which is an *in-sample* estimate: greedy chose antennas
specifically to light up those samples, so sampled coverage **over**-states true
coverage for the selected set (task #12). Measured at small scale, that produced a
building claimed at `tau = 0.75` whose true coverage was 0.7076.

So coverage near `tau` is unreliable in both directions, and one exact re-measurement
fixes both. This module re-measures every building whose reported coverage lands in a
window around `tau`, then:

- below `tau`: **recovers** buildings the cull forfeited;
- above `tau`: **drops** claims the sampling grid inflated.

Policy decided 2026-08-07 (Marko): the window is **relative** to `tau` and two-sided,

    window = [tau * (1 - band), tau * (1 + band))     band default 0.10

and targets are taken **closest to `tau` first** under a cap, since proximity to the
threshold is the only signal that predicts a flip and every serviced building is worth
exactly one point regardless of size.

The re-check is expensive -- it is exactly the unbounded visibility work the cull was
introduced to avoid, at roughly 550 checks/s versus 17,500 culled -- so it is aimed
only at buildings where it can change an outcome.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from giscup.models import BoundarySample, Building, PointLike
from giscup.exact_coverage import exact_coverage_by_building
from giscup.sampling import SamplingProfile, sample_building_boundary
from giscup.visibility import BlockerIndex, is_visible


def dense_samples_for(
    buildings: list[Building], building_ids: list[int | str], profile: SamplingProfile
) -> list[BoundarySample]:
    """Re-sample just the targeted buildings at `profile`'s density.

    The claim decision must not reuse the grid the optimizer ran on. Greedy chose
    antennas to light up those exact samples, so measuring against them again
    reproduces the same optimistic bias (task #12). Sampling independently, and more
    finely, is what makes the re-measurement informative rather than circular.
    """
    wanted = set(building_ids)
    out: list[BoundarySample] = []
    for building in buildings:
        if building.id in wanted:
            out.extend(
                sample_building_boundary(
                    building,
                    profile.spacing,
                    profile.min_samples_per_building,
                    start_id=len(out),
                )
            )
    return out


@dataclass(slots=True)
class VerificationReport:
    """What the un-culled pass changed, so the cull's cost can be bounded."""

    reverified_count: int = 0
    recovered_ids: list[int | str] = field(default_factory=list)
    dropped_ids: list[int | str] = field(default_factory=list)
    coverage_before: dict[int | str, float] = field(default_factory=dict)
    coverage_after: dict[int | str, float] = field(default_factory=dict)
    checks_performed: int = 0

    @property
    def max_coverage_delta(self) -> float:
        """Largest under-report the cull produced among re-verified buildings.

        This is the empirical bound on how much the cull was hiding. If it is near
        zero the radius is comfortably generous; if it is large the radius is too
        tight and is costing score on buildings that were never even re-checked.
        """
        if not self.coverage_after:
            return 0.0
        return max(
            self.coverage_after[bid] - self.coverage_before.get(bid, 0.0)
            for bid in self.coverage_after
        )


# Sampled coverage carries about +/-0.03 error at the profiles in use (`accurate` 5 m,
# `final` 2.5 m). A purely relative band collapses below that at low tau -- at
# tau=0.25 a 10% band is only +/-0.025 -- so the window would be narrower than the
# error it exists to catch and low-tau overclaims would escape re-verification.
BAND_FLOOR = 0.05


def select_buildings_to_reverify(
    coverage: dict[int | str, float],
    tau: float,
    band: float = 0.10,
    max_buildings: int | None = None,
    band_floor: float = BAND_FLOOR,
) -> list[int | str]:
    """Choose which buildings get the expensive un-culled re-check.

    The window is two-sided and relative to `tau`, but never narrower than
    `band_floor` in absolute terms:

        half_width = max(tau * band, band_floor)
        [tau - half_width, tau + half_width)

    Buildings outside it are left alone: far below `tau` the cull's under-report
    cannot plausibly close the gap, and far above it the grid's over-report cannot
    plausibly have invented the whole margin. Both re-checks would be wasted work.

    Args:
        coverage: building id -> reported coverage ratio in 0..1, from the sampled,
            radius-culled estimate.
        tau: threshold for this subproblem.
        band: half-width of the window as a fraction of `tau`.
        max_buildings: cap on how many to re-check, or None for no cap.

    Returns:
        Building ids ordered by absolute distance from `tau`, closest first, so a cap
        keeps the likeliest flips.
    """
    if not coverage:
        return []
    if band < 0:
        raise ValueError(f"band must be non-negative, got {band}")

    # Widen to at least `band_floor` in absolute coverage terms; see BAND_FLOOR.
    half_width = max(tau * band, band_floor)
    low = tau - half_width
    high = tau + half_width
    targets = [bid for bid, ratio in coverage.items() if low <= ratio < high]
    targets.sort(key=lambda bid: abs(coverage[bid] - tau))
    if max_buildings is not None:
        targets = targets[:max_buildings]
    return targets


def exact_coverage_for(
    building_ids: list[int | str],
    antenna_points: list[PointLike],
    samples: list[BoundarySample],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    strategy: str = "relate",
) -> tuple[dict[int | str, float], int]:
    """Re-measure coverage for `building_ids` with no radius cull at all.

    Returns (coverage ratio by building id, number of visibility checks performed).
    Only samples belonging to the requested buildings are touched, so cost scales
    with the selection, not with the dataset.
    """
    wanted = set(building_ids)
    if not wanted or not antenna_points:
        return {}, 0

    by_building: dict[int | str, list[BoundarySample]] = defaultdict(list)
    for sample in samples:
        if sample.building_id in wanted:
            by_building[sample.building_id].append(sample)

    perimeter = {b.id: b.perimeter for b in buildings}
    coverage: dict[int | str, float] = {}
    checks = 0
    for building_id, building_samples in by_building.items():
        visible_weight = 0.0
        for sample in building_samples:
            for point in antenna_points:
                checks += 1
                if is_visible(point, sample.point, blocker_index, strategy=strategy):
                    visible_weight += sample.weight
                    break
        total = perimeter.get(building_id, 0.0)
        if total > 0:
            coverage[building_id] = visible_weight / total
    return coverage, checks


def verify_and_recover(
    coverage: dict[int | str, float],
    claimed: list[int | str],
    tau: float,
    antenna_points: list[PointLike],
    samples: list[BoundarySample],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    band: float = 0.10,
    max_buildings: int | None = None,
    claim_margin: float = 0.0,
    strategy: str = "relate",
    verify_profile: SamplingProfile | None = None,
    use_exact: bool = True,
    exact_radius: float | None = None,
    workers: int = 1,
) -> tuple[list[int | str], VerificationReport]:
    """Re-measure buildings near `tau` exactly, then recover and drop accordingly.

    Buildings below `tau` that actually clear it are recovered; claims above `tau`
    that actually miss it are dropped. Buildings outside the window are trusted as
    reported and left untouched.

    Returns the final claim list and a report bounding what the cull was hiding.
    """
    # CLAIMS ARE VERIFIED EXHAUSTIVELY. A band indexed on the sampled value cannot
    # catch the claims whose sampled value is most wrong -- a large error is exactly
    # what pushes a building past the window's edge. Measured on the official
    # dataset: a building with true coverage 0.1499 was claimed at tau=0.25 and sat
    # outside the [0.20, 0.30) window, so it was never re-checked.
    #
    # An overclaim is a correctness failure; a missed recovery is only lost score.
    # So claims get an unconditional exact check, and the band + cap govern recovery
    # below tau, where approximation costs opportunity rather than validity.
    recovery = [
        bid
        for bid in select_buildings_to_reverify(coverage, tau, band, max_buildings)
        if coverage.get(bid, 0.0) < tau
    ]
    targets = list(dict.fromkeys(list(claimed) + recovery))
    report = VerificationReport(reverified_count=len(targets))
    if not targets:
        return list(claimed), report

    # Measure EXACTLY (task #13). Sampling only converges at ~0.5 m spacing, far
    # finer than any profile in use, so a sampled re-measurement would just trade one
    # grid's bias for another's. Interval coverage has no grid at all.
    if use_exact:
        # `exact_radius` is a pure optimisation over an exact computation: an antenna
        # further than this from an edge cannot see it in practice, and skipping it
        # avoids building a domain-spanning triangle whose STRtree query would return
        # thousands of blockers and thousands of breakpoints per edge.
        exact = exact_coverage_by_building(
            targets, antenna_points, buildings, blocker_index,
            strategy=strategy, radius=exact_radius, workers=workers,
        )
        checks = 0
    else:
        measure_on = (
            dense_samples_for(buildings, targets, verify_profile) if verify_profile else samples
        )
        exact, checks = exact_coverage_for(
            targets, antenna_points, measure_on, buildings, blocker_index, strategy=strategy
        )
    report.checks_performed = checks
    report.coverage_before = {bid: coverage.get(bid, 0.0) for bid in exact}
    report.coverage_after = dict(exact)

    threshold = tau + claim_margin
    already = set(claimed)

    # Keep claims we did not re-check; re-checked ones must earn their place.
    final = [bid for bid in claimed if bid not in exact or exact[bid] >= threshold]
    report.dropped_ids = [bid for bid in claimed if bid in exact and exact[bid] < threshold]
    report.recovered_ids = [
        bid for bid, ratio in exact.items() if bid not in already and ratio >= threshold
    ]
    return final + report.recovered_ids, report
