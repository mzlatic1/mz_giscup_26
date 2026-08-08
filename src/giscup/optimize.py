"""Baseline optimization routines for selecting antenna candidates."""

from __future__ import annotations

import numpy as np

from giscup.coverage import coverage_by_building, serviced_buildings, visible_sample_ids
from giscup.matrix import VisibilityMatrix
from giscup.models import BoundarySample, Building, Candidate
from giscup.visibility import BlockerIndex


def greedy_select(
    candidates: list[Candidate],
    samples: list[BoundarySample],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    tau: float,
    k: int,
    strategy: str = "relate",
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


def greedy_select_matrix(
    matrix: VisibilityMatrix,
    candidates: list[Candidate],
    samples: list[BoundarySample],
    buildings: list[Building],
    tau: float,
    k: int,
    max_candidates: int | None = None,
) -> tuple[list[Candidate], set[int]]:
    """Greedy selection over a precomputed visibility matrix.

    Identical selections to :func:`greedy_select`, without recomputing visibility.
    Each iteration is one popcount pass over the matrix instead of
    `candidates x samples` geometric predicates, which is what removes the `k`
    factor that made the solver infeasible.

    The objective is still raw newly-visible-sample count, so `tau` and `buildings`
    are accepted but unused -- replacing that with a threshold-aware objective is
    task #6, kept separate so this change stays provably behaviour-preserving.
    """
    if k <= 0:
        raise ValueError(f"k must be positive; got {k}")
    if max_candidates is not None and max_candidates < k:
        raise ValueError(f"max_candidates ({max_candidates}) must be at least k ({k})")
    if matrix.n_candidates != len(candidates) or matrix.n_samples != len(samples):
        raise ValueError(
            f"visibility matrix does not match the pool: matrix is "
            f"{matrix.n_candidates} candidates x {matrix.n_samples} samples, "
            f"got {len(candidates)} x {len(samples)}"
        )

    pool_size = min(max_candidates, len(candidates)) if max_candidates else len(candidates)
    if pool_size < k:
        raise ValueError(f"candidate pool contains {pool_size} candidates, fewer than required k={k}")

    covered = matrix.empty_covered()
    selected: list[Candidate] = []
    taken = np.zeros(matrix.n_candidates, dtype=bool)

    for _ in range(k):
        gains = matrix.marginal_gains(covered)
        if pool_size < matrix.n_candidates:
            gains[pool_size:] = -1
        gains[taken] = -1
        best = int(np.argmax(gains))
        if gains[best] < 0:
            raise RuntimeError("greedy selection failed to identify a next candidate")
        taken[best] = True
        matrix.add_to_covered(covered, best)
        selected.append(candidates[best])

    return selected, set(matrix.covered_sample_ids(covered).tolist())


def score_visible_set(
    visible: set[int], samples: list[BoundarySample], buildings: list[Building], tau: float) -> int:
    coverage = coverage_by_building(visible, samples, buildings)
    return len(serviced_buildings(coverage, tau))
