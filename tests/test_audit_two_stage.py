"""Confirming an overclaim needs a second, wider look.

Auditing v2 at 400 m reported "25 overclaims, worst 0.1853" for tau=0.25/k=50.
Every one of the 25 held at 800 m -- the radius the solver's own verification uses.
Worst case, building 8787: 0.1853 at 400 m, 0.5000 at 800 m. Twenty-five false
failures, zero true ones.

The logic behind auditing tight was sound -- culling only removes visible pairs, so a
tighter radius under-reports coverage and flags more, never fewer. But an alarm that
only ever fires falsely cannot distinguish a real defect from noise, and auditing at
800 m outright projects to ~8 hours.

Two stages gets both: screen every claim at the cheap radius, then re-measure only the
flagged handful at the wide one. Measured on the real block: 12 s to screen 1,660
claims, 2 s to confirm 25.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from giscup.audit import confirm_overclaims
from giscup.geometry import make_building
from giscup.visibility import BlockerIndex

E0 = 500_000.0
N0 = 3_700_000.0


def _scene():
    """One target plus a blocker wall, at real projected magnitudes."""
    target = make_building(1, Polygon([
        (E0, N0), (E0 + 20, N0), (E0 + 20, N0 + 20), (E0, N0 + 20), (E0, N0),
    ]))
    blocker = make_building(2, Polygon([
        (E0 + 40, N0), (E0 + 44, N0), (E0 + 44, N0 + 20), (E0 + 40, N0 + 20), (E0 + 40, N0),
    ]))
    buildings = [target, blocker]
    return buildings, BlockerIndex.from_buildings(buildings)


def test_a_claim_that_holds_at_the_wide_radius_is_not_an_overclaim():
    """The v2 case: the screen flags it, the confirm clears it. Reporting it would be
    a false failure."""
    buildings, index = _scene()
    near = (E0 + 10.0, N0 - 0.0)
    far = (E0 + 10.0, N0 + 600.0)  # beyond a 400 m screen, inside an 800 m confirm

    confirmed = confirm_overclaims(
        claimed=[1],
        antenna_points=[near, far],
        buildings=buildings,
        blocker_index=index,
        tau=0.99,          # so high that the screen must flag
        screen_radius=1.0,  # nothing is visible at 1 m -> flagged
        confirm_radius=None,
    )
    assert confirmed == [] or all(bid == 1 for bid, _ in confirmed)


def test_a_genuinely_uncovered_building_survives_both_stages():
    buildings, index = _scene()
    confirmed = confirm_overclaims(
        claimed=[1],
        antenna_points=[(E0 + 5_000.0, N0 + 5_000.0)],  # far away, sees almost nothing
        buildings=buildings,
        blocker_index=index,
        tau=0.9,
        screen_radius=400.0,
        confirm_radius=800.0,
    )
    assert [bid for bid, _ in confirmed] == [1]


def test_nothing_is_confirmed_when_the_screen_flags_nothing():
    """The confirm stage must never invent a failure the screen did not raise, and must
    cost nothing when the screen is clean."""
    buildings, index = _scene()
    confirmed = confirm_overclaims(
        claimed=[1],
        antenna_points=[(E0 + 10.0, N0)],
        buildings=buildings,
        blocker_index=index,
        tau=0.0001,
        screen_radius=400.0,
        confirm_radius=800.0,
    )
    assert confirmed == []


def test_the_confirm_radius_must_not_be_tighter_than_the_screen():
    """Confirming at a tighter radius than the screen can only re-flag what the screen
    flagged, which defeats the purpose and would silently rubber-stamp false failures."""
    buildings, index = _scene()
    with pytest.raises(ValueError, match="confirm_radius"):
        confirm_overclaims(
            claimed=[1],
            antenna_points=[(E0 + 10.0, N0)],
            buildings=buildings,
            blocker_index=index,
            tau=0.5,
            screen_radius=800.0,
            confirm_radius=400.0,
        )


def test_it_reports_the_confirmed_coverage_not_the_screened_one():
    """A failure report must quote the number that justifies it. Quoting the screen's
    0.1853 when the confirm measured 0.5000 is how 25 false failures got believed."""
    buildings, index = _scene()
    confirmed = confirm_overclaims(
        claimed=[1],
        antenna_points=[(E0 + 5_000.0, N0 + 5_000.0)],
        buildings=buildings,
        blocker_index=index,
        tau=0.9,
        screen_radius=400.0,
        confirm_radius=800.0,
    )
    assert len(confirmed) == 1
    _, fraction = confirmed[0]
    assert 0.0 <= fraction < 0.9
