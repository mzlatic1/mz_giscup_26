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

import os

#: Seconds to re-verify one building against 1000 antennas, with exact interval
#: coverage at a 400 m cull. Measured from the v2 nine-block run, 2026-08-09.
#: The previous value, 0.051, under-predicted that run by 16.2x.
MEASURED_VERIFY_S_PER_BUILDING_PER_1K = 0.826

#: The same quantity for a **lever A** (`--near-tau-quantile`) run, measured
#: 2026-08-09 at (0.25, 1000): 15,696 s of serial verification over 12,469 checks
#: at k=1000. Lever A verifies the same buildings more expensively than baseline
#: does, because near-tau selection deliberately parks them *at* the threshold --
#: inside the band where exact interval coverage must actually be computed instead
#: of short-circuited.
#:
#: **Weaker provenance than 0.826, and knowingly so.** That figure was fitted across
#: a whole nine-block run; this is one block, timed while the 600 m matrix build was
#: running at `nice 15`. Contention inflates it, and for a feasibility gate an
#: inflated verification cost is the safe direction, so it is used as measured. The
#: ratio against baseline is 1.5x measured this way and 1.8x if compared against
#: baseline's own parallel figure from the same pair of runs (0.150 s x 4.70); the
#: conservative end of that range is what is encoded here.
MEASURED_VERIFY_S_PER_BUILDING_PER_1K_NEAR_TAU = 1.26

#: Every objective whose verification cost has actually been measured. Anything not
#: in here is refused rather than costed -- see `verify_constant_for`.
MEASURED_VERIFY_CONSTANTS: dict[str, float] = {
    "baseline": MEASURED_VERIFY_S_PER_BUILDING_PER_1K,
    "near-tau": MEASURED_VERIFY_S_PER_BUILDING_PER_1K_NEAR_TAU,
}

#: The radius pair `MEASURED_VERIFY_S_PER_BUILDING_PER_1K` belongs to. The v2 run
#: solved at a 400 m cull with `--verify-radius-factor 2.0`, so every exact-coverage
#: query it timed ran against blockers within **800 m**.
MEASURED_AT_SOLVE_RADIUS_M = 400.0
MEASURED_AT_VERIFY_RADIUS_FACTOR = 2.0
MEASURED_AT_VERIFY_RADIUS_M = MEASURED_AT_SOLVE_RADIUS_M * MEASURED_AT_VERIFY_RADIUS_FACTOR


def verify_constant_for(
    solve_radius_m: float | None,
    verify_radius_factor: float = MEASURED_AT_VERIFY_RADIUS_FACTOR,
    *,
    objective: str = "baseline",
    override: float | None = None,
) -> float:
    """Seconds per building per 1000 antennas -- at the radius AND objective measured.

    **0.826 is not a property of the solver.** It is the cost of exact interval
    coverage against however many blockers one query returns, and that count grows
    steeply with radius: the board measured 21 blockers per query at 400 m against
    ~1,180 unbounded, and the audit found 800 m cost ~10x what 400 m did rather than
    the 3-4x assumed.

    So the constant belongs to the *pair* (solve radius, verify factor) = (400 m,
    2.0), i.e. verification at 800 m. This matters right now: #3b built a 600 m
    matrix on 2026-08-09, and a 600 m solve verifies at 1200 m. Reusing 0.826 there
    would understate verification -- the same failure as #16, same mechanism, same
    optimistic direction.

    Refusing is the safe direction. A loud stop costs one session; a quiet 2x error
    costs the submission, which is what happened when the gate read 4.01 h for a
    9.42 h run. `override` is the escape hatch, and passing a number is an assertion
    that you measured it -- which cannot happen by accident.

    **The objective is the second such dimension, and it bites the same way.** 0.826
    was fitted to v2, a *baseline greedy* run. Lever A verifies the same buildings
    more expensively (1.26 measured), because parking them at the threshold is the
    whole mechanism, and the threshold band is where exact coverage cannot
    short-circuit. If #15 adopts lever A and the gate keeps costing it at 0.826,
    every gate number is optimistic -- #16 again, one constant measured under one
    configuration and silently applied to another.

    An unrecognised objective is refused rather than defaulted to baseline. Baseline
    is the *cheapest* constant, so a typo or a newly added optimizer would inherit
    the most optimistic number in the module, which is the worst possible fallback.
    """
    if override is not None:
        return override
    if objective not in MEASURED_VERIFY_CONSTANTS:
        known = ", ".join(sorted(MEASURED_VERIFY_CONSTANTS))
        raise ValueError(
            f"verification cost is uncalibrated for objective {objective!r}. "
            f"Measured objectives are: {known}. Defaulting an unknown objective to "
            f"'baseline' would hand it the cheapest constant in the module (0.826 vs "
            f"near-tau's 1.26), so the gate refuses instead. Measure the objective and "
            f"add it to MEASURED_VERIFY_CONSTANTS, or pass override=<seconds>."
        )
    measured = MEASURED_VERIFY_CONSTANTS[objective]
    if solve_radius_m == MEASURED_AT_SOLVE_RADIUS_M and (
        verify_radius_factor == MEASURED_AT_VERIFY_RADIUS_FACTOR
    ):
        return measured

    if solve_radius_m is None:
        requested = "unbounded"
    elif not verify_radius_factor:
        requested = "unbounded (verify_radius_factor=0)"
    else:
        requested = f"{solve_radius_m * verify_radius_factor:g} m"
    raise ValueError(
        f"verification cost is uncalibrated at this radius: you asked to cost "
        f"verification at {requested}, but {measured} s "
        f"per building per 1000 antennas (objective {objective!r}) was measured at "
        f"{MEASURED_AT_VERIFY_RADIUS_M:g} m (a "
        f"{MEASURED_AT_SOLVE_RADIUS_M:g} m solve at factor "
        f"{MEASURED_AT_VERIFY_RADIUS_FACTOR:g}). Blockers per query grow steeply with "
        f"radius -- 800 m cost ~10x 400 m -- so reusing this constant would understate "
        f"the run, exactly as the gate did before #16. Measure the new pair and pass "
        f"it as override=<seconds>."
    )


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


#: Speedup from parallel verification (#18), measured on a real block --
#: tau=0.75/k=500, 150 claims x 500 antennas -- while the lever A re-solve and the
#: 600 m matrix build were both running. Contended, so these are FLOORS.
#: Efficiency falls off hard: 88% at 2 workers, 78% at 4, 53% at 8, 39% at 12.
MEASURED_VERIFY_SPEEDUP: dict[int, float] = {1: 1.00, 2: 1.77, 4: 3.10, 8: 4.20, 12: 4.70}


def verify_speedup(workers: int) -> float:
    """Speedup for `workers` processes, never extrapolated beyond what was measured.

    An unmeasured count rounds *down* to the nearest measured one, and anything above
    12 gets 12's figure. Scaling had already decayed to 39% efficiency there; assuming
    it keeps improving is exactly how this gate came to be optimistic in the first
    place.
    """
    if workers < 1:
        raise ValueError(f"workers must be at least 1, got {workers}")
    usable = [w for w in sorted(MEASURED_VERIFY_SPEEDUP) if w <= workers]
    return MEASURED_VERIFY_SPEEDUP[usable[-1]] if usable else 1.0


def default_verify_workers(cpu_count: int | None = None) -> int:
    """How many verification processes to use when nobody says otherwise.

    #18 made verification parallel but left every entry point defaulting to 1, so
    the documented commands still described serial verification -- the gate read
    19.34 h / 1.0x headroom instead of 6.87 h / 2.9x, and a run launched without
    the flag would burn ~12 extra hours of a ~24 h submission window.

    Bounded on both sides, and neither bound is arbitrary:

    * never above `max(MEASURED_VERIFY_SPEEDUP)`, because scaling had already
      decayed to 39% efficiency there and this project's whole history of bad
      estimates is extrapolation past the last measurement;
    * never above the core count, because verification is memory-bandwidth bound
      and oversubscribing it makes the run slower;
    * never below 1, because zero workers would mean claims go unverified, and an
      overclaim is a correctness failure rather than merely a slow run.

    A host that will not report its core count gets serial. Guessing high on an
    unknown machine risks thrashing it, and this is the safe direction.
    """
    if cpu_count is None:
        cpu_count = os.cpu_count()
    if cpu_count is None or cpu_count < 1:
        return 1
    return min(cpu_count, max(MEASURED_VERIFY_SPEEDUP))


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
