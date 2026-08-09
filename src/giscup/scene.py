"""The part of solver setup that does not depend on `(tau, k)`.

Loading the dataset, sampling boundaries, and generating candidates are functions of
the *dataset and its configuration only*. `solve-all` runs nine subproblems over one
dataset, so doing this work nine times is pure waste -- on the official sample it is
about 8.5 minutes per repeat, roughly 40% of a nine-block run.

Sharing it is only safe when the sharing is checked. A scene built with one sampling
profile handed to a solver asked for another would answer a question nobody posed, and
no downstream check would catch it: the output would be structurally perfect. So a
scene carries the `SceneSpec` it was built under and the solver refuses any mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass

from giscup.candidates import generate_boundary_candidates
from giscup.io import load_buildings
from giscup.models import Building, BoundarySample, Candidate, DatasetInfo
from giscup.sampling import get_profile, sample_boundaries


@dataclass(frozen=True, slots=True)
class SceneSpec:
    """Everything the prepared scene depends on. Two scenes with equal specs are
    interchangeable; two with unequal specs are not."""

    input_path: str
    id_property: str
    sampling_profile: str
    candidate_mode: str
    candidate_spacing: float


@dataclass(frozen=True, slots=True)
class Scene:
    """Loaded buildings plus the derived sampling and candidate sets."""

    buildings: list[Building]
    info: DatasetInfo
    samples: list[BoundarySample]
    candidates: list[Candidate]
    spec: SceneSpec

    def mismatches(self, other: SceneSpec) -> list[str]:
        """Field names where this scene disagrees with a requested configuration."""
        return [
            name
            for name in SceneSpec.__slots__
            if getattr(self.spec, name) != getattr(other, name)
        ]


def prepare_scene(
    input_path: str,
    *,
    id_property: str = "id",
    sampling_profile: str = "balanced",
    candidate_mode: str = "basic",
    candidate_spacing: float = 25.0,
) -> Scene:
    """Do the `(tau, k)`-independent setup once."""
    spec = SceneSpec(
        input_path=input_path,
        id_property=id_property,
        sampling_profile=sampling_profile,
        candidate_mode=candidate_mode,
        candidate_spacing=candidate_spacing,
    )
    buildings, info = load_buildings(input_path, id_property=id_property)
    samples = sample_boundaries(buildings, get_profile(sampling_profile))
    candidates = generate_boundary_candidates(
        buildings, mode=candidate_mode, candidate_spacing=candidate_spacing
    )
    return Scene(
        buildings=buildings, info=info, samples=samples, candidates=candidates, spec=spec
    )
