"""Antenna candidate generation from building boundaries."""

from __future__ import annotations

from dataclasses import replace
from math import ceil

from giscup.geometry import segment_length
from giscup.models import Building, Candidate


def _add_candidate(
    candidates: list[Candidate],
    seen: set[tuple[float, float]],
    x: float,
    y: float,
    building_id: int | str,
    edge_index: int | None,
    kind: str,
) -> None:
    # Rounding to 12 decimals is a no-op at projected-CRS magnitudes -- float64
    # resolution at an easting of 5e5 is already ~6e-11 -- so this merges only
    # genuinely coincident points, such as a corner shared by two footprints. It
    # cannot merge points separated by interpolation jitter, and is not meant to.
    key = (round(float(x), 9), round(float(y), 9))
    if key in seen:
        return
    seen.add(key)
    candidates.append(Candidate(len(candidates), float(x), float(y), building_id, edge_index, kind))


def generate_boundary_candidates(
    buildings: list[Building], mode: str = "basic", candidate_spacing: float = 25.0
) -> list[Candidate]:
    """Generate exterior vertex, midpoint, and optional long-edge sample candidates."""
    candidates: list[Candidate] = []
    seen: set[tuple[float, float]] = set()
    for building in buildings:
        for edge_index, (p0, p1) in enumerate(building.exterior_edges):
            _add_candidate(candidates, seen, p0[0], p0[1], building.id, edge_index, "vertex")
            midpoint = (p0 + p1) / 2.0
            _add_candidate(candidates, seen, midpoint[0], midpoint[1], building.id, edge_index, "midpoint")
            if mode in {"edge_sample", "density", "visibility_probe", "hybrid"}:
                length = segment_length(p0, p1)
                n = max(0, int(ceil(length / candidate_spacing)) - 1)
                for i in range(1, n + 1):
                    t = i / (n + 1)
                    xy = p0 + t * (p1 - p0)
                    _add_candidate(candidates, seen, xy[0], xy[1], building.id, edge_index, "edge_sample")
    return candidates


def prune_candidates(candidates: list[Candidate], stride: int = 1) -> list[Candidate]:
    """Keep every `stride`-th candidate within each building's own ordered list.

    **This is the rule `scripts/size_candidate_prune.py` measured**, reproduced
    deliberately rather than improved on. That script pruned *after* generation, by
    per-building rank, and measured a 2x prune at one serviced building lost of
    14,708 -- free within measurement error -- for ~1.69 h saved. A prune that kept a
    different set, however defensible, would not inherit that measurement.

    Per-building rank is what makes it safe. A global stride would delete whole
    neighbourhoods, because generation walks building by building -- that is exactly
    why `--max-candidates` is documented as a footgun rather than a prune. Here every
    building keeps its own first candidate, so no footprint is ever left without a
    legal antenna position. The consequence is that the prune saturates near 12.2x on
    the official dataset (157,454 candidates over 12,860 buildings); beyond that a
    stride cannot remove anything more without deleting buildings outright.

    `stride=1` is the exact identity, and is load-bearing: it was the sizing script's
    control, where restricted greedy at stride-1 reproduced `greedy_select_matrix`
    exactly. That control is what makes the rest of the measured table trustworthy.

    Ids are re-assigned to match position because `VisibilityMatrix` indexes rows
    positionally (`bits[candidate_index]`). A pruned list carrying its original ids
    would read the wrong rows while every structural check still passed.

    Note that pruning changes `MatrixSpec.candidate_digest`, hence the cache key, so
    an existing matrix is never silently reused against a different candidate set.
    """
    if stride < 1:
        raise ValueError(
            f"candidate stride must be >= 1, got {stride}. Stride 1 keeps everything; "
            "larger values keep every Nth candidate within each building."
        )
    if stride == 1:
        return list(candidates)

    kept: list[Candidate] = []
    rank: dict[int | str, int] = {}
    for candidate in candidates:
        position = rank.get(candidate.source_building_id, 0)
        rank[candidate.source_building_id] = position + 1
        if position % stride == 0:
            kept.append(replace(candidate, id=len(kept)))
    return kept
