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

This module recovers those forfeited buildings. Every building whose culled coverage
sits just below `tau` is re-measured against the exact, un-culled predicate; those
that actually clear `tau` are claimed after all.

The re-check is expensive -- it is exactly the unbounded visibility work the cull was
introduced to avoid, at roughly 550 checks/s versus 17,500 culled. So it must be
aimed at the buildings where it can change an outcome, not run over the whole set.
That targeting decision is `select_buildings_to_reverify`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from giscup.models import BoundarySample, Building, PointLike
from giscup.visibility import BlockerIndex, is_visible


@dataclass(slots=True)
class VerificationReport:
    """What the un-culled pass changed, so the cull's cost can be bounded."""

    reverified_count: int = 0
    recovered_ids: list[int | str] = field(default_factory=list)
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


def select_buildings_to_reverify(
    coverage: dict[int | str, float],
    tau: float,
    band: float = 0.10,
    max_buildings: int | None = None,
) -> list[int | str]:
    """Choose which buildings get the expensive un-culled re-check.

    TODO(marko): implement the selection policy.

    Inputs:
        coverage      building id -> culled (underestimated) coverage ratio, 0..1
        tau           the threshold for this subproblem
        band          how far below `tau` to consider recoverable
        max_buildings optional cap on how many to re-check, or None for no cap

    Return the building ids to re-verify, best candidates first when capped.

    Trade-offs to weigh:
      - Buildings already at or above `tau` need no re-check: coverage only rises
        without the cull, so they stay claimed. Re-checking them is pure waste.
      - Buildings far below `tau` are unlikely to be rescued by the ~25% of visible
        pairs living in the 200-400 m band, and each re-check is ~30x the cost of a
        culled one. Where you cut off is the real decision.
      - Under a cap, which ones first? Closest to `tau` are the likeliest flips, but
        a building with a large perimeter may be worth more attention than a small
        one, and all buildings score identically (one serviced building = one point).
      - `tau` varies across the nine subproblems (0.25 / 0.5 / 0.75). A fixed
        absolute band behaves very differently at 0.25 than at 0.75; consider whether
        the band should scale.
    """
    raise NotImplementedError(
        "select_buildings_to_reverify is not implemented yet -- see task board #3"
    )


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
) -> tuple[list[int | str], VerificationReport]:
    """Recover buildings the cull forfeited, and report how much it was hiding.

    Returns the final claim list (original claims plus recovered ones) and a report
    bounding the cull's cost.
    """
    already = set(claimed)
    targets = [bid for bid in select_buildings_to_reverify(coverage, tau, band, max_buildings)
               if bid not in already]
    report = VerificationReport(reverified_count=len(targets))
    if not targets:
        return list(claimed), report

    exact, checks = exact_coverage_for(
        targets, antenna_points, samples, buildings, blocker_index, strategy=strategy
    )
    report.checks_performed = checks
    report.coverage_before = {bid: coverage.get(bid, 0.0) for bid in exact}
    report.coverage_after = dict(exact)

    recovered = [bid for bid, ratio in exact.items() if ratio >= tau + claim_margin]
    report.recovered_ids = recovered
    return list(claimed) + recovered, report
