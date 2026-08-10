"""Task #9 -- the per-building candidate stride, adopted 2026-08-09 (Marko's call).

**Why a prune is worth anything at all.** Greedy's argmax is a popcount pass over
every candidate row on every one of the `k` iterations, and the matrix build is
linear in candidates too, so ~67% of the projected day total scales with candidate
count. A 2x prune was sized at **1.69 h saved for one serviced building lost of
14,708** -- free within measurement error.

**The rule implemented here is the rule that was measured**, and that matters more
than its elegance: `scripts/size_candidate_prune.py` pruned *after* generation, by
per-building rank, so `prune_candidates` does the same. A prune that kept a
different set would not inherit the measurement.

Two structural facts pinned below:

* **`stride-1` must be the exact identity.** It was the sizing script's control --
  restricted greedy at stride-1 reproduced `greedy_select_matrix` exactly, which is
  what made the rest of that table trustworthy. If the identity ever drifts, the
  measurement it validated is void.
* **`stride-2` is *usually* the vertex half, but not by definition.** Candidates are
  emitted vertex-then-midpoint per edge, so ranks 0, 2, 4... are vertices -- unless
  the global dedupe in `_add_candidate` drops a shared corner, which shifts every
  later rank in that building by one. The board records these as "the same set"; they
  are the same set only when no dedupe collision occurs, and both cases are pinned
  here so nobody re-derives the claim as universal.

Coordinates are at EPSG:32611 magnitudes throughout. Per CLAUDE.md, unit-square
fixtures cannot see the float64 behaviour that actually bites this project.
"""

from __future__ import annotations

import pytest

from shapely.geometry import Polygon

from giscup.candidates import generate_boundary_candidates, prune_candidates
from giscup.geometry import make_building
from giscup.models import Building
from giscup.scene import SceneSpec

# Real projected magnitudes (EPSG:32611), deliberately irregular.
E0 = 500_000.0
N0 = 3_700_000.0


def _building(bid: int, dx: float, dy: float, size: float = 17.3) -> Building:
    x, y = E0 + dx, N0 + dy
    poly = Polygon(
        [(x, y), (x + size, y), (x + size, y + size * 0.7), (x, y + size * 0.7)]
    )
    return make_building(bid, poly)


def _disjoint_buildings() -> list[Building]:
    """No shared corners, so the global dedupe never fires."""
    return [_building(i, dx=i * 240.0, dy=i * 137.0) for i in range(4)]


def test_stride_1_is_the_exact_identity_control():
    # The sizing script's control. If this drifts, the #9 measurement is void.
    candidates = generate_boundary_candidates(_disjoint_buildings())
    kept = prune_candidates(candidates, stride=1)

    assert len(kept) == len(candidates)
    assert [(c.x, c.y) for c in kept] == [(c.x, c.y) for c in candidates]
    assert [c.id for c in kept] == [c.id for c in candidates]


def test_ids_are_reindexed_to_match_row_position():
    # VisibilityMatrix indexes rows positionally (`bits[candidate_index]`), so a
    # pruned list whose ids no longer equal their positions would silently read the
    # wrong row. This is the invariant that makes pruning safe at all.
    candidates = generate_boundary_candidates(_disjoint_buildings())
    kept = prune_candidates(candidates, stride=2)

    assert [c.id for c in kept] == list(range(len(kept)))


def test_stride_2_halves_each_building_independently():
    buildings = _disjoint_buildings()
    candidates = generate_boundary_candidates(buildings)
    kept = prune_candidates(candidates, stride=2)

    for building in buildings:
        before = [c for c in candidates if c.source_building_id == building.id]
        after = [c for c in kept if c.source_building_id == building.id]
        # Every building keeps its own first candidate -- that is what stops a prune
        # from deleting a building's only legal antenna positions.
        assert after[0].point == before[0].point
        assert len(after) == (len(before) + 1) // 2


def test_every_building_survives_even_at_a_huge_stride():
    # Per-building stride saturates near 12.2x on the official dataset because each
    # building keeps its first candidate. Beyond that a prune would have to delete
    # whole buildings, removing their only legal antenna positions.
    buildings = _disjoint_buildings()
    kept = prune_candidates(generate_boundary_candidates(buildings), stride=10_000)

    assert {c.source_building_id for c in kept} == {b.id for b in buildings}
    assert len(kept) == len(buildings)


def test_stride_2_equals_vertex_only_when_no_dedupe_collision():
    candidates = generate_boundary_candidates(_disjoint_buildings())
    kept = prune_candidates(candidates, stride=2)

    vertex_only = [c for c in candidates if c.kind == "vertex"]
    assert [(c.x, c.y) for c in kept] == [(c.x, c.y) for c in vertex_only]


def test_stride_2_diverges_from_vertex_only_when_a_corner_is_shared():
    # Two footprints sharing a corner: the second building's duplicate vertex is
    # dropped by the global dedupe, so its ranks shift by one and stride-2 starts
    # keeping midpoints. The board calls stride-2 and vertex-only "the same set";
    # this pins the case where that is false, so the equivalence is not assumed.
    size = 17.3
    a = _building(0, dx=0.0, dy=0.0, size=size)
    shared_x, shared_y = E0 + size, N0
    b = make_building(
        1,
        Polygon(
            [
                (shared_x, shared_y),
                (shared_x + size, shared_y),
                (shared_x + size, shared_y + size),
                (shared_x, shared_y + size),
            ]
        ),
    )
    candidates = generate_boundary_candidates([a, b])
    kept = prune_candidates(candidates, stride=2)

    assert any(c.kind == "midpoint" for c in kept), (
        "expected the dedupe collision to shift ranks so a midpoint survives"
    )


@pytest.mark.parametrize("stride", [0, -1, -7])
def test_invalid_stride_raises(stride):
    candidates = generate_boundary_candidates(_disjoint_buildings())
    with pytest.raises(ValueError, match="stride"):
        prune_candidates(candidates, stride=stride)


def test_scene_spec_treats_stride_as_load_bearing():
    # A scene built at one stride handed to a solver asked for another would answer a
    # question nobody posed, and every downstream check would still pass -- the exact
    # failure SceneSpec exists to stop.
    base = dict(
        input_path="x.geojson",
        id_property="id",
        sampling_profile="balanced",
        candidate_mode="basic",
        candidate_spacing=25.0,
    )
    assert SceneSpec(**base, candidate_stride=1) != SceneSpec(**base, candidate_stride=2)
    assert "candidate_stride" in SceneSpec.__slots__
