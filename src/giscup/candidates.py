"""Antenna candidate generation from building boundaries."""

from __future__ import annotations

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
    key = (round(float(x), 12), round(float(y), 12))
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
