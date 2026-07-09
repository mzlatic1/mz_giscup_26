"""Weighted boundary sampling for approximate perimeter coverage."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from giscup.geometry import segment_length
from giscup.models import BoundarySample, Building


@dataclass(frozen=True, slots=True)
class SamplingProfile:
    name: str
    spacing: float
    min_samples_per_building: int


PROFILES: dict[str, SamplingProfile] = {
    "fast": SamplingProfile("fast", 20.0, 4),
    "balanced": SamplingProfile("balanced", 10.0, 8),
    "accurate": SamplingProfile("accurate", 5.0, 16),
    "final": SamplingProfile("final", 2.5, 24),
}


def get_profile(name: str) -> SamplingProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown sampling profile {name!r}; expected one of {sorted(PROFILES)}") from exc


def sample_building_boundary(
    building: Building, spacing: float, min_samples_per_building: int, start_id: int = 0
) -> list[BoundarySample]:
    """Generate midpoint-weighted exterior boundary samples for one building."""
    raw: list[tuple[int, float, object, object]] = []
    total_segments = 0
    for edge_index, (p0, p1) in enumerate(building.exterior_edges):
        length = segment_length(p0, p1)
        if length <= 0:
            continue
        n = max(1, int(ceil(length / spacing)))
        raw.append((edge_index, length, p0, p1))
        total_segments += n

    scale = max(1.0, min_samples_per_building / total_segments) if total_segments else 1.0
    samples: list[BoundarySample] = []
    sid = start_id
    for edge_index, length, p0, p1 in raw:
        n = max(1, int(ceil(length / spacing * scale)))
        weight = length / n
        for i in range(n):
            t = (i + 0.5) / n
            xy = p0 + t * (p1 - p0)
            samples.append(BoundarySample(sid, float(xy[0]), float(xy[1]), building.id, edge_index, weight))
            sid += 1
    return samples


def sample_boundaries(buildings: list[Building], profile: SamplingProfile) -> list[BoundarySample]:
    """Generate weighted boundary samples for all buildings."""
    samples: list[BoundarySample] = []
    for building in buildings:
        samples.extend(
            sample_building_boundary(
                building, profile.spacing, profile.min_samples_per_building, start_id=len(samples)
            )
        )
    return samples
