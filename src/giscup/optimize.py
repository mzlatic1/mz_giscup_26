"""Baseline optimization routines for selecting antenna candidates."""

from __future__ import annotations

from typing import Callable

import numpy as np

from giscup.coverage import coverage_by_building, serviced_buildings, visible_sample_ids
from giscup.matrix import VisibilityMatrix
from giscup.models import BoundarySample, Building, Candidate
from giscup.progress import greedy_report_interval
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
    progress: Callable[[int, int], None] | None = None,
    report_every: int | None = None,
) -> tuple[list[Candidate], set[int]]:
    """Greedy selection over a precomputed visibility matrix.

    Identical selections to :func:`greedy_select`, without recomputing visibility.
    Each iteration is one popcount pass over the matrix instead of
    `candidates x samples` geometric predicates, which is what removes the `k`
    factor that made the solver infeasible.

    The objective is still raw newly-visible-sample count, so `tau` and `buildings`
    are accepted but unused -- replacing that with a threshold-aware objective is
    task #6, kept separate so this change stays provably behaviour-preserving.

    `progress`, when given, is called as `progress(picked, k)` every `report_every`
    picks. This is the longest phase in a subproblem -- ~17 min at k=1000 -- so without
    it the run looks stalled for that entire stretch.
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
    # Only consulted when a reporter is attached, so the silent path never depends on it.
    every = 0
    if progress is not None:
        every = report_every if report_every is not None else greedy_report_interval(k)

    for i in range(k):
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
        if progress is not None and every > 0 and ((i + 1) % every == 0 or i + 1 == k):
            progress(i + 1, k)

    return selected, set(matrix.covered_sample_ids(covered).tolist())


def greedy_select_threshold(
    matrix: VisibilityMatrix,
    candidates: list[Candidate],
    samples: list[BoundarySample],
    buildings: list[Building],
    tau: float,
    k: int,
    max_candidates: int | None = None,
) -> tuple[list[Candidate], set[int]]:
    """Greedy selection that stops paying for buildings already over `tau`.

    The scored quantity is serviced *buildings*, not covered samples. Once a building
    clears `tau`, further coverage of it is worth nothing, but the baseline objective
    keeps buying it -- which spreads antennas thinly instead of concentrating them
    where they can flip a building.

    The exact form of this is `sum_b min(visible_weight_b, tau * perimeter_b)`, which
    is submodular. Evaluating it per candidate per iteration needs a segmented sum
    over every candidate and is far too slow at 157k candidates. This implements its
    dominant term: samples of serviced buildings are cleared from an `active` mask, so
    gain becomes `popcount(row & ~covered & active)` -- the same cost as the baseline.

    When every building in reach is serviced the mask empties; selection then falls
    back to raw newly-covered count so that exactly `k` legal antennas are still
    returned.
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

    # Sample -> building, and the weight each sample contributes to its building.
    building_index = {b.id: i for i, b in enumerate(buildings)}
    owner = np.fromiter((building_index[s.building_id] for s in samples), dtype=np.int64, count=len(samples))
    weight = np.fromiter((s.weight for s in samples), dtype=np.float64, count=len(samples))
    need = np.array([b.perimeter * tau for b in buildings], dtype=np.float64)

    covered = matrix.empty_covered()
    taken = np.zeros(matrix.n_candidates, dtype=bool)
    selected: list[Candidate] = []

    # Every sample starts active; samples of serviced buildings are switched off.
    all_active = np.frombuffer(
        np.packbits(np.ones(matrix.words * 64, dtype=np.uint8), bitorder="little").tobytes(),
        dtype=np.uint64,
    ).copy()
    active = all_active.copy()

    for _ in range(k):
        gains = matrix.marginal_gains_masked(covered, active)
        if pool_size < matrix.n_candidates:
            gains[pool_size:] = -1
        gains[taken] = -1
        if gains.max() <= 0:
            # Nothing left to gain under the mask; fall back to raw coverage so we
            # still emit exactly k legal antennas.
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

        # Recompute which buildings are serviced, and deactivate their samples.
        covered_ids = matrix.covered_sample_ids(covered)
        got = np.bincount(owner[covered_ids], weights=weight[covered_ids], minlength=len(buildings))
        serviced = got >= need
        if serviced.any():
            still = ~serviced[owner]
            packed = np.packbits(
                np.concatenate([still, np.zeros(matrix.words * 64 - len(still), dtype=bool)]),
                bitorder="little",
            )
            active = np.frombuffer(packed.tobytes(), dtype=np.uint64).copy()

    return selected, set(matrix.covered_sample_ids(covered).tolist())


def near_tau_target(got: np.ndarray, need: np.ndarray, quantile: float = 50.0) -> np.ndarray:
    """Buildings worth spending the next antenna on.

    A building is targeted when it is unserviced (`got < need`) and its remaining
    deficit is within `quantile` of the live deficit distribution -- i.e. it is among
    the cheapest still-flippable buildings.

    The cutoff must be a quantile, not a constant. At iteration zero every building is
    unserviced with deficit exactly `need`, so any fixed threshold selects all of them
    or none. A quantile tightens by itself as coverage accumulates and the distribution
    compresses onto buildings that are actually about to flip.

    Serviced buildings drop out automatically, which makes this a strict generalisation
    of the threshold objective (lever B) -- that is `quantile=100`.
    """
    deficit = need - got
    unserviced = deficit > 0
    if not unserviced.any():
        return np.zeros_like(unserviced)
    cutoff = float(np.percentile(deficit[unserviced], quantile))
    return unserviced & (deficit <= cutoff)


def greedy_select_near_tau(
    matrix: VisibilityMatrix,
    candidates: list[Candidate],
    samples: list[BoundarySample],
    buildings: list[Building],
    tau: float,
    k: int,
    max_candidates: int | None = None,
    quantile: float = 50.0,
    progress: Callable[[int, int], None] | None = None,
    report_every: int | None = None,
) -> tuple[list[Candidate], set[int]]:
    """Greedy selection that spends coverage where it can still flip a building.

    Lever A from the 2026-08-08 sizing. The baseline objective counts every newly
    visible sample equally, so it keeps buying coverage on buildings far below `tau`
    that will never reach it, and on buildings already above it. At tau=0.75/k=500 the
    long tail alone held 109,622 m of such coverage -- 10.1x the overshoot that lever B
    targets, in the subproblem where relative scoring actually pays.

    Implemented as a mask, so per-iteration cost matches the baseline:
    `popcount(row & ~covered & active)`.
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

    building_index = {b.id: i for i, b in enumerate(buildings)}
    owner = np.fromiter((building_index[s.building_id] for s in samples), dtype=np.int64, count=len(samples))
    weight = np.fromiter((s.weight for s in samples), dtype=np.float64, count=len(samples))
    need = np.array([b.perimeter * tau for b in buildings], dtype=np.float64)

    covered = matrix.empty_covered()
    taken = np.zeros(matrix.n_candidates, dtype=bool)
    selected: list[Candidate] = []
    pad = matrix.words * 64 - len(samples)
    every = 0
    if progress is not None:
        every = report_every if report_every is not None else greedy_report_interval(k)

    def _pack(sample_flags: np.ndarray) -> np.ndarray:
        packed = np.packbits(
            np.concatenate([sample_flags, np.zeros(pad, dtype=bool)]), bitorder="little"
        )
        return np.frombuffer(packed.tobytes(), dtype=np.uint64).copy()

    for i in range(k):
        ids = matrix.covered_sample_ids(covered)
        got = np.bincount(owner[ids], weights=weight[ids], minlength=len(buildings))
        target = near_tau_target(got, need, quantile)

        gains = None
        if target.any():
            gains = matrix.marginal_gains_masked(covered, _pack(target[owner]))
            if pool_size < matrix.n_candidates:
                gains[pool_size:] = -1
            gains[taken] = -1
            if gains.max() <= 0:
                gains = None
        if gains is None:
            # Nothing flippable in reach; fall back so exactly k legal antennas ship.
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
        if progress is not None and every > 0 and ((i + 1) % every == 0 or i + 1 == k):
            progress(i + 1, k)

    return selected, set(matrix.covered_sample_ids(covered).tolist())


def score_visible_set(
    visible: set[int], samples: list[BoundarySample], buildings: list[Building], tau: float) -> int:
    coverage = coverage_by_building(visible, samples, buildings)
    return len(serviced_buildings(coverage, tau))
