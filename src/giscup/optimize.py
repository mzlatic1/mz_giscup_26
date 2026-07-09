"""Baseline optimization routines for selecting antenna candidates."""

from __future__ import annotations

from giscup.coverage import coverage_by_building, serviced_buildings, visible_sample_ids
from giscup.models import BoundarySample, Building, Candidate
from giscup.visibility import BlockerIndex


def greedy_select(
    candidates: list[Candidate],
    samples: list[BoundarySample],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    tau: float,
    k: int,
    strategy: str = "hybrid",
    max_candidates: int | None = None,
) -> tuple[list[Candidate], set[int]]:
    """Simple correctness-oriented greedy baseline.

    This is not intended to be the final competitive optimizer; it provides an
    end-to-end reference implementation that can be replaced by cached/lazy
    greedy variants.
    """
    if k <= 0:
        raise ValueError(f"k must be positive; got {k}")
    if max_candidates is not None and max_candidates < k:
        raise ValueError(f"max_candidates ({max_candidates}) must be at least k ({k})")

    pool = candidates[:max_candidates] if max_candidates else candidates
    if len(pool) < k:
        raise ValueError(f"candidate pool contains {len(pool)} candidates, fewer than required k={k}")

    selected: list[Candidate] = []
    visible: set[int] = set()
    remaining = list(pool)
    for _ in range(k):
        best_idx = -1
        best_new: set[int] = set()
        best_score = -1
        for idx, candidate in enumerate(remaining):
            cand_visible = visible_sample_ids(candidate, samples, blocker_index, strategy=strategy)
            new_ids = cand_visible - visible
            score = len(new_ids)
            if score > best_score:
                best_idx = idx
                best_new = new_ids
                best_score = score
        if best_idx < 0:
            raise RuntimeError("greedy selection failed to identify a next candidate")
        selected.append(remaining.pop(best_idx))
        visible |= best_new
    return selected, visible


def score_visible_set(
    visible: set[int], samples: list[BoundarySample], buildings: list[Building], tau: float) -> int:
    coverage = coverage_by_building(visible, samples, buildings)
    return len(serviced_buildings(coverage, tau))
