"""Cost model behind the feasibility gate, calibrated against a run that happened.

The gate read PASS at 4.01 h / 5.0x headroom. The v2 nine-block run then took 9.42 h
on the same dataset, radius and flags -- optimistic by 2.35x. The error was entirely
in the verification constant.

Decomposing v2's 33,898 s against measured greedy timings:

    setup x9            30 s   0.1%
    greedy           6,174 s  18.2%
    verification    27,694 s  81.7%

Verification is not a correction term on the greedy model; it *is* the runtime. Each
claimed building is re-measured against every antenna, so cost goes as
`buildings x k`. Fitting that against v2's 33,540 building-k units gives 0.826 s per
building per 1000 antennas, against the 0.051 the gate had been using.

`tests/test_gate_calibration.py` pins this against the observed run.
"""

from __future__ import annotations

#: Seconds to re-verify one building against 1000 antennas, with exact interval
#: coverage at a 400 m cull. Measured from the v2 nine-block run, 2026-08-09.
#: The previous value, 0.051, under-predicted that run by 16.2x.
MEASURED_VERIFY_S_PER_BUILDING_PER_1K = 0.826

#: The nine subproblems, as published on the sample page.
TAUS = (0.25, 0.5, 0.75)
KS = (50, 500, 1000)


def calibrated_verify_seconds(
    reverified_per_block: dict[tuple[float, int], int],
    seconds_per_building_per_1k: float = MEASURED_VERIFY_S_PER_BUILDING_PER_1K,
) -> float:
    """Verification cost given how many buildings each block actually re-verifies.

    Requires knowing the claim counts, so it is an *estimate for a run like one you
    have already seen*, not something you can compute before solving. Use it to sanity
    check the gate, and to project onto a new dataset by scaling the counts.
    """
    return sum(
        count * (k / 1000.0) * seconds_per_building_per_1k
        for (_tau, k), count in reverified_per_block.items()
    )


#: Fraction of all buildings re-verified in each block, measured on the v2 run
#: (12,860 buildings, 400 m). Ratios transfer to a new extract far better than raw
#: counts do: they encode how tau and k govern how much of the stock gets claimed.
V2_CLAIM_RATIOS: dict[tuple[float, int], float] = {
    (0.25, 50): 0.1501, (0.25, 500): 0.7362, (0.25, 1000): 0.9269,
    (0.5, 50): 0.0351, (0.5, 500): 0.3623, (0.5, 1000): 0.6854,
    (0.75, 50): 0.0040, (0.75, 500): 0.1547, (0.75, 1000): 0.3596,
}


def projected_verify_seconds(
    n_buildings: int,
    seconds_per_building_per_1k: float = MEASURED_VERIFY_S_PER_BUILDING_PER_1K,
) -> float:
    """Expected verification cost on a dataset of this size, from observed ratios.

    Assumes the new extract claims a similar *fraction* of its buildings at each
    (tau, k) as the March sample did. That is an assumption, not a measurement, and it
    breaks if August's extract is much denser or sparser -- but it is far closer to
    what happens than bounding every block by the full building count.
    """
    return sum(
        n_buildings * ratio * (k / 1000.0) * seconds_per_building_per_1k
        for (_tau, k), ratio in V2_CLAIM_RATIOS.items()
    )


def pessimistic_verify_seconds(
    n_buildings: int,
    verify_buildings: int | None = 2000,
    seconds_per_building_per_1k: float = MEASURED_VERIFY_S_PER_BUILDING_PER_1K,
) -> float:
    """Upper bound: assume every building is claimed in every block.

    Claim counts are not knowable before solving -- at tau=0.25/k=1000 the real run
    claimed 11,630 of 12,860 -- so the gate bounds them by the building count. That is
    near-tight at low tau and heavily pessimistic at high tau (27 claims at
    tau=0.75/k=50), which is the direction a gate should err.

    `verify_buildings` caps the band-recovery pass only; #17 made claim re-checking
    exhaustive, so the claim term is never capped.
    """
    per_k = sum(k / 1000.0 for k in KS) * len(TAUS)
    exhaustive = n_buildings * per_k * seconds_per_building_per_1k
    recovery = (verify_buildings or 0) * per_k * seconds_per_building_per_1k
    return exhaustive + recovery
