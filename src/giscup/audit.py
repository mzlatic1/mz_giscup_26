"""Two-stage overclaim confirmation.

Auditing v2 at 400 m reported 25 overclaims in one block. All 25 held at 800 m, the
radius the solver's own verification uses; worst case, building 8787 measured 0.1853 at
400 m and 0.5000 at 800 m. Twenty-five false failures, zero true ones.

The reasoning behind the tight audit was correct as far as it went: culling only ever
removes visible pairs, so a tighter radius under-reports coverage and can flag a good
claim but never clear a bad one. That makes it a sound *screen* and a useless *verdict*.
Auditing at 800 m outright is accurate but projects to ~8 hours.

So: screen everything cheaply, then re-measure only what the screen flagged. On the real
block that was 12 s to screen 1,660 claims and 2 s to confirm 25.
"""

from __future__ import annotations

from giscup.exact_coverage import exact_coverage_by_building
from giscup.models import Building, PointLike
from giscup.visibility import BlockerIndex


def confirm_overclaims(
    claimed: list[int | str],
    antenna_points: list[PointLike],
    buildings: list[Building],
    blocker_index: BlockerIndex,
    tau: float,
    screen_radius: float | None = 400.0,
    confirm_radius: float | None = 800.0,
    claim_margin: float = 0.0,
) -> list[tuple[int | str, float]]:
    """Claims that fail at *both* radii, with the confirmed coverage fraction.

    `confirm_radius=None` means unbounded — exact, but slow enough that it is rarely
    the right choice; anything at or beyond the solver's verification radius is enough.

    Returns `(building_id, confirmed_fraction)` pairs. The fraction is the one measured
    at `confirm_radius`, never the screen's: a failure report has to quote the number
    that justifies it.
    """
    if confirm_radius is not None and screen_radius is not None and confirm_radius < screen_radius:
        raise ValueError(
            f"confirm_radius ({confirm_radius}) must not be tighter than screen_radius "
            f"({screen_radius}); confirming tighter can only re-flag what the screen "
            "flagged, which rubber-stamps false failures instead of catching them."
        )
    if not claimed:
        return []

    threshold = tau + claim_margin
    screened = exact_coverage_by_building(
        list(claimed), antenna_points, buildings, blocker_index, radius=screen_radius
    )
    flagged = [bid for bid in claimed if screened.get(bid, 0.0) < threshold]
    if not flagged:
        return []

    confirmed = exact_coverage_by_building(
        flagged, antenna_points, buildings, blocker_index, radius=confirm_radius
    )
    return [
        (bid, confirmed.get(bid, 0.0))
        for bid in flagged
        if confirmed.get(bid, 0.0) < threshold
    ]
