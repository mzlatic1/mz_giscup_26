"""Approximate coverage accounting over weighted boundary samples."""

from __future__ import annotations

from collections import defaultdict

from giscup.models import BoundarySample, Building, Candidate
from giscup.visibility import BlockerIndex, is_visible


def visible_sample_ids(
    candidate: Candidate,
    samples: list[BoundarySample],
    blocker_index: BlockerIndex,
    strategy: str = "relate",
) -> set[int]:
    """Compute visible sample IDs for one candidate with direct predicates."""
    return {s.id for s in samples if is_visible(candidate.point, s.point, blocker_index, strategy=strategy)}


def coverage_by_building(
    visible_ids: set[int], samples: list[BoundarySample], buildings: list[Building]
) -> dict[int | str, float]:
    """Convert visible sample IDs to building coverage ratios."""
    visible_weight: dict[int | str, float] = defaultdict(float)
    for sample in samples:
        if sample.id in visible_ids:
            visible_weight[sample.building_id] += sample.weight
    perimeter = {b.id: b.perimeter for b in buildings}
    return {bid: visible_weight.get(bid, 0.0) / perim for bid, perim in perimeter.items() if perim > 0}


def serviced_buildings(coverage: dict[int | str, float], tau: float, margin: float = 0.0) -> list[int | str]:
    """Return building IDs whose approximate coverage meets `tau + margin`."""
    return [bid for bid, ratio in coverage.items() if ratio >= tau + margin]
