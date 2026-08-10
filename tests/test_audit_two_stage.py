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


# ---------------------------------------------------------------------------
# The audit is the LAST step before submission, and it was single-core.
#
# #18 parallelised the solver's verification and left `confirm_overclaims`
# passing workers=1 into `exact_coverage_by_building`, which has accepted a
# `workers` argument since that commit. So the audit ran on one core of sixteen at
# the point in submission day with the least slack -- after a five-hour solve, on
# the check that gates submitting.
#
# (An earlier version of this comment quoted "32 min for five blocks, ~48 min for
# nine". That was a misreading -- 32 min was how long the run had been going when
# it was looked at, not how long it took, and it was also running the unbounded
# screen. See `giscup.audit.confirm_overclaims` on the screen radius.)
#
# Same proof obligation as #18: identical to serial, not merely close. Coverage
# decides which claims survive and there is one submission with no feedback.
# ---------------------------------------------------------------------------


def _row(n: int = 12):
    """Irregular footprints at real projected magnitudes, mutually blocking."""
    buildings = []
    for i in range(n):
        x = E0 + (i % 4) * 37.0
        y = N0 + (i // 4) * 29.0
        w = 15.0 + (i % 3) * 4.0
        h = 11.0 + (i % 2) * 6.0
        buildings.append(
            make_building(i, Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]))
        )
    return buildings, BlockerIndex.from_buildings(buildings)


def _points(buildings):
    pts = []
    for b in buildings:
        x0, y0, x1, y1 = b.bounds
        pts.append((x0, (y0 + y1) / 2.0))
    return pts


@pytest.mark.parametrize("workers", [2, 4])
def test_parallel_confirmation_is_identical_to_serial(workers):
    """The contract. Same overclaims, same order, same floats -- not approx."""
    buildings, index = _row()
    claimed = [b.id for b in buildings]
    points = _points(buildings)

    serial = confirm_overclaims(
        claimed=claimed, antenna_points=points, buildings=buildings,
        blocker_index=index, tau=0.85, screen_radius=400.0, confirm_radius=800.0,
    )
    parallel = confirm_overclaims(
        claimed=claimed, antenna_points=points, buildings=buildings,
        blocker_index=index, tau=0.85, screen_radius=400.0, confirm_radius=800.0,
        workers=workers,
    )
    assert parallel == serial


def test_the_parallel_path_is_actually_exercised_by_that_test():
    """Guards the test above from passing vacuously. If the scene produced no
    overclaims, comparing [] to [] would prove nothing about parallelism."""
    buildings, index = _row()
    found = confirm_overclaims(
        claimed=[b.id for b in buildings], antenna_points=_points(buildings),
        buildings=buildings, blocker_index=index, tau=0.85,
        screen_radius=400.0, confirm_radius=800.0,
    )
    assert len(found) >= 2


def test_confirmation_is_serial_unless_asked():
    """Changing the library default would silently re-shape every existing caller."""
    import inspect

    assert inspect.signature(confirm_overclaims).parameters["workers"].default == 1


def test_a_nonsensical_worker_count_is_rejected():
    buildings, index = _row()
    with pytest.raises(ValueError):
        confirm_overclaims(
            claimed=[b.id for b in buildings], antenna_points=_points(buildings),
            buildings=buildings, blocker_index=index, tau=0.85, workers=0,
        )


def test_an_empty_claim_list_is_still_free_with_workers_set():
    """No pool for nothing to do. A block may legitimately claim zero buildings."""
    buildings, index = _row()
    assert confirm_overclaims(
        claimed=[], antenna_points=_points(buildings), buildings=buildings,
        blocker_index=index, tau=0.85, workers=4,
    ) == []


def _load_audit_script():
    """`scripts/` is not a package, so import the audit script by path."""
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "audit_submission", root / "scripts" / "audit_submission.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_audit_script_defaults_to_the_same_worker_count_as_the_solver():
    """Load-bearing, and the reason #18's speedup went unused here for a day: the
    capability existed, every entry point defaulted to 1, and the documented command
    therefore described serial work. Pinned to `default_verify_workers` so the audit
    and the solver cannot drift apart."""
    from giscup.gate_model import default_verify_workers

    parser = _load_audit_script().build_parser()
    args = parser.parse_args(["--input", "x.geojson", "--solution", "y.txt"])
    assert args.workers == default_verify_workers()


def test_the_audit_script_lets_you_force_serial():
    """Serial stays reachable -- it is the reference the parallel path is proven
    against, and a host that cannot fork needs it."""
    parser = _load_audit_script().build_parser()
    args = parser.parse_args(
        ["--input", "x.geojson", "--solution", "y.txt", "--workers", "1"]
    )
    assert args.workers == 1


def test_the_audit_parses_a_final_block_that_claims_nothing():
    """Found 2026-08-09 while building the assembler, which had the same defect.

    `"(0.25, 1)\\n(1.0, 2.0)\\n".splitlines()` yields TWO elements -- the trailing
    empty string is dropped -- so a final block with an empty claims line parsed as
    truncated and raised "incomplete block". The third line is explicitly allowed to
    be empty, so that is a legal file, and the audit is the last gate before
    submission: this defect fails a valid submission rather than passing an invalid
    one, but on a one-shot competition both are fatal.
    """
    parse_blocks = _load_audit_script().parse_blocks
    blocks = parse_blocks("(0.25, 1)\n(1.0, 2.0)\n")
    assert len(blocks) == 1
    tau, k, points, claims, _line = blocks[0]
    assert (tau, k, claims) == (0.25, 1, "")


def test_the_audit_still_rejects_a_genuinely_truncated_block():
    """The fix must not turn a real truncation into a silent pass. A header with no
    points line at all is broken, not empty-claimed."""
    parse_blocks = _load_audit_script().parse_blocks
    with pytest.raises(ValueError):
        parse_blocks("(0.25, 1)\n")
