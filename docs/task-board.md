# Task Board

Durable task list. `/startup` reads this and recreates the in-session task list from it.
Keep it current: when a task is finished, move it to **Done** with the date and the evidence.

Last updated: 2026-08-07.

## Critical path — CLEARED 2026-08-07

The feasibility gate reads **PASS, measured**: 3.18 h for all nine subproblems against a 20 h
budget, **6.3x headroom**. Observed end to end, not extrapolated. Feasibility no longer outranks
solution quality — but see #13 before trusting any threshold decision.

| # | Task | Blocked by |
|---|---|---|
| 3b | Calibrate the cull radius (verification pass done; radius still a judgment call) | — |

## Unblocked — can start any time

| # | Task |
|---|---|

## Gated on feasibility

| # | Task | Blocked by |
|---|---|---|
| 9 | Prune the candidate pool | 2 |
| 6 | Replace the greedy objective with a threshold-aware one | 4 |
| 8 | Full nine-block end-to-end dry run + submission audit | 4 |

---

## Details

### 2 — Radius-culled cached visibility matrix  ← THE BLOCKER

Replace per-iteration recomputation with a matrix computed **once** and reused across all nine
subproblems. Two compounding effects, measured 2026-08-06:

1. A candidate's visible set never changes during greedy — only the union subtracted from it
   does. Caching removes the `k` factor entirely.
2. Throughput scales inversely with blockers per STRtree query, so restricting to short segments
   gives ~44x more throughput.

Throughput re-measured 2026-08-07 with `relate` after the erosion hoist (400 pairs per row,
single core, synthetic full-scale). Run-to-run variance is ±10–25% — treat as order-of-magnitude,
not precise:

| segment length | blockers/query | checks/s (2026-08-07) | checks/s (2026-08-06) |
|---|---|---|---|
| unbounded | 1,180 | 537–580 | 605 |
| ≤ 400 m | 21 | 12,172–16,213 | 17,951 |
| ≤ 200 m | 7 | 23,169–25,775 | 26,539 |

The 2026-08-07 figures are lower but the PASS verdict survives with margin: 200 m ≈ 11.8 min,
400 m ≈ 1.5 h on 8 cores against a 20 h budget.

Target from the gate: 200 m cull = 1.3e8 checks ≈ 10–12 min on 8 cores; 400 m = 5.2e8 ≈ 1–1.5 h.

**Status 2026-08-07 — implemented, full-scale build in progress.** `src/giscup/matrix.py`:

- Dense candidate-major bit matrix, `uint64` words, memmap-backed under `outputs/cache/`.
  Marko chose dense bitsets over sparse CSR after seeing the density measurement (below).
- cKDTree over samples enumerates only pairs inside the radius; parallel workers write disjoint
  candidate ranges through the memmap, so 2.76 GB never crosses a pickle boundary.
- Cache key is a blake2b digest over building WKB + candidate coords + sample coords + radius +
  strategy + eps, so an incompatible matrix can never be reused. The metadata JSON doubles as the
  completion marker: a crashed partial build is rebuilt, not trusted.
- `optimize.greedy_select_matrix` selects off the matrix and is tested to pick *exactly* what the
  predicate-based greedy picks. `solver.solve_one` takes `--visibility-radius` / `--cache-dir`.
  The radius is opt-in and never implied.

Measured matrix density at full scale (150 probe candidates, `balanced` profile):

| radius | neighbours/candidate | visible/candidate | nonzeros | density | dense bitset |
|---|---|---|---|---|---|
| 200 m | 798 | 48.3 | 7.74M | 0.035% | 2.76 GB |
| 400 m | 3,048 | 60.5 | 9.70M | 0.044% | 2.76 GB |

200 m → 400 m costs **6.2x** the build time for **+25%** visible pairs — sharply diminishing, but
a quarter of all visibility lives in that band. Radius **400 m** chosen (decision recorded in #3).

### 3 — Calibrate the cull radius; add an un-culled verification pass

The cull is a heuristic that can silently discard genuinely visible pairs. Real street grids have
long unobstructed corridors; the synthetic stand-in has no real streets, so the measured
91–274 m visible range is very likely an **underestimate** of the real tail.

Under-culling loses score with no feedback to detect it. The budget has slack — 400 m costs ~1 h
of a 20 h window — so choose the radius **generously**, not at the measured p95.

**Verification pass: DONE 2026-08-07** — see `src/giscup/verify.py`. **Radius calibration: still
open** — measuring how much coverage lives beyond 400 m needs the full-scale matrix, which was
still building. Until that runs, 400 m is a judgment call, not a calibrated number.

### 3b — Cull radius calibration  (MEASURED 2026-08-08 on official data)

Measured on the real sample (40 probe candidates, `balanced` profile):

| radius | neighbours/candidate | visible/candidate | gain vs previous |
|---|---|---|---|
| 200 m | 993 | 21.5 | — |
| 400 m | 3,635 | 27.7 | +29.0% |
| 800 m | 12,559 | 30.0 | +8.3% |
| 1600 m | 41,517 | 30.5 | +1.6% |

**400 m captures ~91% of all visible pairs; 800 m captures ~98%.** The chosen 400 m radius
therefore discards roughly **9% of real visibility** — more than the synthetic stand-in suggested,
exactly as predicted, because real street grids have long unobstructed corridors it could not
reproduce.

**DECIDED 2026-08-08 (Marko): "whatever produced better results."** Being taken as a measurement
rather than an assumption — both radii are being built on the official dataset so the nine-block
solve can be run at each and the **serviced-building counts compared directly**. Visible-pair
capture (91% vs 98%) is a proxy; claimed-building count is the scored quantity.

Cost check before committing to it: 800 m is 3.5x the pairs, so ~6.4 h of matrix build instead of
110 min. The gate still passes — 6.4 h matrix + ~1.3 h greedy = 7.7 h against 20 h, 2.6x headroom.
1600 m is not worth testing: it buys only +1.6% over 800 m for another 3.3x.

Pending result: whichever radius yields more serviced buildings across the nine subproblems wins.
If they tie, 400 m wins on cost.

**Build costs, measured on the official dataset:**

| radius | build time | visible pairs | density | visible/candidate |
|---|---|---|---|---|
| 400 m | 82.5 min (8 workers) | 3,888,638 | 0.01851% | 24.7 |
| 800 m | tracking ~11 h (12 workers) | pending | pending | pending |

The 800 m build is running **far** longer than the 3.5x pair-count ratio implied (~6.4 h
estimated). Same mechanism as every other timing miss in this project: longer segments intersect
more blockers per STRtree query, so throughput falls as radius rises — the pair count and the
per-pair cost both grow.

**The real matrix is 2.5x sparser than the synthetic one** (3.89M pairs vs 9.84M; 24.7 visible
samples per candidate vs 61.5). Real street topology blocks far more sight lines than the
synthetic's layout did. This cuts the opposite way from the visibility-*reach* finding, and is one
more reason no solution-quality number measured on the synthetic can be trusted.

**Mitigation already in place.** The verification pass no longer inherits the solver's cull. It
re-measures at `visibility_radius x verify_radius_factor` (default 2.0), so a 400 m solve verifies
against 800 m. `--verify-radius-factor 0` makes it fully unbounded.

### 5 — Official sample dataset  (DONE 2026-08-08)

Downloaded from `https://sigspatial2026.sigspatial.org/img/GIS-cup-sample-dataset.geojson` —
public, no registration. Now at `data/GIS-cup-sample-dataset.geojson` (6.3 MB, git-ignored).

**Every documented statistic matches exactly:**

| statistic | documented | measured |
|---|---|---|
| buildings | 12,860 | 12,860 |
| exterior vertices | 78,727 | 78,727 |
| total perimeter | 858,973 m | 858,973.22 m |
| hole-bearing polygons | 1 | 1 |
| CRS | EPSG:32611 | EPSG:32611 |

Real vs synthetic at `balanced`: 133,417 samples (vs 138,077) and 157,454 candidates (vs 160,198)
— within 3%. Domain 4,946 x 4,264 m vs 4,975 x 4,263 m.

**Where the synthetic misled:** it omitted the large-building tail. Real max perimeter is
**1,066 m** and max area **17,957 m²**; the synthetic had neither. And real visibility reaches
further, which is what makes the 400 m cull cost ~9% rather than the ~2% the synthetic implied.

All performance figures recorded before 2026-08-08 were measured on the synthetic stand-in. The
matrix in `outputs/cache` is for the SYNTHETIC dataset; a real-data matrix has a different cache
key and must be built before any real-data solve.

### 4 — Gate reads PASS  (DONE 2026-08-07)

**MEASURED VERDICT: PASS.** Observed, not projected — the real 400 m matrix was built and real
greedy iterations were timed.

```
matrix build : 110.8 min   (once, reused by all nine)
greedy       : 1.031 s per iteration
  k=50   x 3 taus :   2.6 min
  k=500  x 3 taus :  25.8 min
  k=1000 x 3 taus :  51.6 min
TOTAL            : 3.18 h        budget 20 h        headroom 6.3x
```

Matrix: 9,844,991 visible pairs, density 0.04451%, 61.5 visible samples per candidate, key
`18912a76b41469a1289b72c3eaf731f6`.

Density extrapolation was excellent (predicted 9.70M vs 9.84M actual, 1.5% off from a
150-candidate probe). **Build-time extrapolation was not**: predicted 58 min vs 110.8 min actual,
~1.9x optimistic, because contiguous chunks hit denser regions than random probes and 8 workers
contend for memory bandwidth. Assume the same ~2x penalty when planning #8.

Formatting and validation are **not** in the 3.18 h. Budget those separately.

`scripts/rehearse.py` now prints the analytic model as a labelled *reference point* for the legacy
path and lets the measured gate set the exit code, so a future session cannot read the stale
`VERDICT: FAIL` line as current.

### 4 — Gate must read PASS (superseded, kept for the original framing)

Currently **FAIL by ~5e8x**. Per `CLAUDE.md`, feasibility work outranks all solution-quality work
until this passes.

```bash
python scripts/rehearse.py --input outputs/synthetic_full.geojson --cores 8
```

The gate currently models cost analytically from measured throughput. Once the cached matrix
exists, extend it to time an **actual** full build rather than a projection, so the PASS is
observed rather than extrapolated. Record the passing configuration in `docs/session-state.md`.

### 5 — Official sample dataset

Released 2026-03-31, still absent locally. Every performance and sparsity figure in this repo is
measured against a synthetic stand-in with no real street topology and no large-building tail.
This is the single input that upgrades the analysis from well-founded to confirmed — and it
directly determines whether the radius chosen in #3 is safe.

On arrival: `giscup inspect` and compare against `docs/original_implementation_brief.md` §4
(12,860 buildings, 78,727 vertices, total perimeter 858,973 m, one hole-bearing polygon id 9448);
full CRS/topology/ID/anomaly report via the `geodata-qc` agent; re-run `/rehearsal` on real data
and correct any figure that moved.

`data/**` is write-denied for `Write`/`Edit` but **not** for shell writes — place the file
deliberately and let nothing overwrite it.

### 6 — Threshold-aware objective  ← NOW THE BIGGEST LEVER

**Sized 2026-08-08 on official data, k=500, before investing** (CLAUDE.md rule 2):

| tau | serviced | within 0.05 below | within 0.10 below | upper-bound upside |
|---|---|---|---|---|
| 0.25 | 5,533 | 1,510 | 2,587 | +47% |
| 0.50 | 859 | 393 | 930 | +108% |
| 0.75 | **13** | 8 | 66 | **+508%** |

Coverage distribution at k=500 is heavily bottom-weighted: 11,071 of 12,860 buildings sit below
0.4, and only 20 reach 0.7 or above.

**At `tau=0.75, k=500` the solver services 13 buildings out of 12,860 while 66 sit within 0.10 of
the line.** The objective maximises newly-visible *samples*, which spreads coverage thinly rather
than concentrating it to push specific buildings over the threshold. At high tau that is close to
pathological. Scoring is relative per subproblem, so three of the nine are currently near-worthless.

This is the opposite of a dead knob: the lever's range dwarfs the gap. **Do this before #9.**

Treat the percentages as upper bounds — they assume every near-threshold building flips at zero
cost to any other, which no real objective achieves.

**Related and larger:** the synthetic stand-in gave 1,581 claims at `tau=0.75, k=500`; real data
gives **13**. A ~100x gap, from 2.5x sparser visibility compounding through the threshold. No
score expectation set on synthetic results survives.

### 6 — Threshold-aware objective  (original framing)

`optimize.greedy_select` scores `len(new_ids)` — raw newly visible sample count — and accepts
`tau` and `buildings` without using either. The scored quantity is serviced **building** count at
threshold `tau`. A building pushed 0.74 → 0.76 at `tau=0.75` is worth everything; one pushed
0.20 → 0.40 is worth nothing.

Reward newly serviced buildings, progress toward `tau`, and complementary near-threshold
coverage. Tune per `(tau, k)` — all nine subproblems are scored independently. See
`docs/reference/research-synthesis.md`: thresholded grouped service is **not** plain submodular
coverage, so lazy-greedy's correctness guarantee does not transfer unchanged.

### 8 — Nine-block dry run  (SYNTHETIC COMPLETE 2026-08-08; real-data run in progress)

Full-scale nine-block solve on the synthetic stand-in, **129.7 min wall clock**, 27 content lines,
43,525 total claims.

| (tau, k) | claims | runtime | recovered | dropped |
|---|---|---|---|---|
| 0.25 / 50 | 1,316 | 0.9 min | 20 | 36 |
| 0.25 / 500 | 9,245 | 9.6 min | 110 | 69 |
| 0.25 / 1000 | 12,171 | 25.9 min | 46 | 30 |
| 0.50 / 50 | 60 | 1.4 min | 11 | 7 |
| 0.50 / 500 | 4,294 | 14.3 min | 321 | 0 |
| 0.50 / 1000 | 9,511 | 28.8 min | 443 | 89 |
| 0.75 / 50 | 13 | 1.4 min | 0 | 2 |
| 0.75 / 500 | 1,581 | 13.0 min | 92 | 119 |
| 0.75 / 1000 | 5,334 | 34.3 min | 219 | 259 |

**The verification pass is earning its keep: 1,262 recovered, 611 dropped.** Every drop is an
overclaim that would otherwise have gone into a submission — 259 in the `0.75 / 1000` block alone.
Every recovery is score the radius cull would have silently forfeited. Drops concentrate at high
`tau`, exactly where coverage sits nearest the threshold.

**Gate correction.** The measured gate projected ~80 min of greedy and reported 3.18 h total. The
actual solve took 129.7 min because **verification is not modelled in the gate at all** — the gate
explicitly excludes formatting and validation, and verification belongs on that list. Still well
inside budget, but any future projection must add it.

### 8 — Nine-block dry run and submission audit  (original framing)

Produce all nine `(tau, k)` blocks end to end on full-scale data inside the wall-clock budget,
then audit with `submission-packager` against every item in
`.claude/skills/giscup-output-format/SKILL.md`: 9 blocks present and unduplicated, exactly three
lines each, exactly `k` coordinates **counted** not trusted from the header, all antennas within
eps of a boundary, 17 significant digits with no six-decimal rounding, every claimed ID present in
the source, all claims passing `validate-output --sampling-profile accurate` with a conservative
margin.

Time the whole run. **This must complete well before 2026-08-15** — that date is a rehearsal
deadline, not a start date.

**Dry run done at small scale 2026-08-07** (60 buildings, UTM 11N, 15.4 s end to end via
`giscup solve-all --visibility-radius 400`). Two findings:

1. **Overclaim** — see #12. `validate-output` rejected our own output.
2. **Blank lines between blocks — confirmed intended, not a defect.** The output carries 27
   content lines plus 8 blank separators. `.claude/skills/giscup-output-format/SKILL.md` line 17
   specifies exactly this ("each **exactly three lines**, blocks separated by a blank line"), and
   `format_solution_file` implements it. Noted here only because the residual risk is unverified:
   the official page states three lines per subproblem without stating whether separators are
   tolerated. If an official clarification ever addresses separators, this is the place to check.

Verified good in the same run: `.17g` round-trips exactly (including
`500000.1 → "500000.09999999998"`), exactly `k` points per block, every claimed ID present in the
source, and every antenna on a boundary.

### 12 — Claim decision must not use the optimizer's own samples

Found 2026-08-07 running the nine-block CLI pipeline end to end at small scale (60 buildings at
UTM 11N magnitudes). **`validate-output` rejected our own solution.**

| tau | k | claimed | overclaims | worst gap |
|---|---|---|---|---|
| 0.75 | 5 | 28 | 1 | 0.0424 |

1 of 489 claims across all nine blocks (0.20%). Every other block was clean.

**Root cause.** `solve_one` optimizes on the `balanced` grid (10 m spacing) and then decides
claims from those same samples. That is an *in-sample* estimate and is optimistically biased:
greedy chose antennas specifically to light up those samples, so sampled coverage overstates true
coverage for the selected set. Re-measuring on `accurate` (5 m) disagrees. The observed gap of
0.0424 is nearly **10x** the current `claim_margin` of 0.005.

Overclaims concentrate at **high tau and low k** — where coverage sits nearest the threshold and
sampling error decides the outcome.

**Options.**

- (a) Decide claims on a denser, independent sampling than the one optimized on. Principled;
  costs one extra coverage pass.
- (b) Raise `claim_margin` to ~0.05. Crude — forfeits every building whose true coverage lies
  between `tau` and `tau + margin`.
- (c) Fold the claim decision into the un-culled verification pass of **#3**, which already
  re-measures near-threshold buildings exactly. Probably the right home: one mechanism handles
  both the cull's under-report and the sampling grid's over-report.

Re-measure at full scale once the matrix lands — 0.20% on 60 buildings may behave very
differently on 12,860.

### 14 — Boundary-point jitter made 32% of samples unseeable  (FIXED 2026-08-08)

**The most damaging bug found in this project.** Every coverage number produced before
2026-08-08 10:30 is wrong.

Samples and candidates are produced by interpolation, `p0 + t*(p1 - p0)`. In float64 at EPSG:32611
magnitudes (~5e5, 3.7e6) the result lands within an ULP of the true edge line — about 1e-10 m —
and lands **inside** the polygon roughly half the time. Measured on the official dataset: **44.5%
of samples sit microscopically inside their own footprint.** One ULP is the smallest displacement
representable there; no amount of careful computation avoids it.

Tested against the raw polygon, such a point makes every segment ending at it report blocked — the
segment's interior genuinely does dip inside. The point became invisible from *everything*,
including a candidate two metres away on its own edge.

| | before | after |
|---|---|---|
| samples invisible from their own building | ~32% | **0.03%** |
| samples visible from any candidate at all | 67.6% | — |
| buildings "unreachable" at tau=0.75 | 76.1% | — |

**Fix:** block when a segment penetrates more than `INTERIOR_TOLERANCE = 1e-6` m into the
interior, by testing against the footprint eroded by that amount. Same official rule, stated so
float64 can evaluate it. A micrometre is five orders above the jitter and five below the smallest
real footprint, so nothing geometric rides on the value. Verified: 0 of 12,860 footprints collapse,
minimum area retained 99.9998%.

**This is the mechanism deleted in #10.** `negative_buffer` failed at `eps=1e-9`, which sits below
float64 relative precision at 3.7e6. The mechanism was right; the epsilon was wrong. I deleted it
on real evidence but drew too broad a conclusion. `_check_erosion` now makes collapse loud.

**Why nothing caught it:** every geometry test used unit-square coordinates, where an ULP is ~2e-16
and the jitter cannot occur. The regression suite (`tests/test_boundary_jitter.py`) now works at
UTM magnitudes with irregular coordinates, and asserts the cheapest possible invariant — *a point
on a boundary must be visible from that same boundary*.

**Blast radius:** both visibility matrices deleted (7.5 GB); the 800 m build was killed at 26/48
chunks; the real 400 m nine-block solve was killed mid-run; the #6 sizing must be redone. The
"76% unreachable at tau=0.75" figure was mostly this bug, not geometry. `MatrixSpec` now carries
`interior_tolerance` so a pre-fix matrix can never be silently reused, and metadata lacking the
field is rejected rather than defaulted.

### 13 — Exact interval coverage  (DONE 2026-08-08)

**CORRECTION to the 2026-08-07 finding.** That entry claimed sampled coverage "does not
converge". **That was wrong** — it was inferred from only four coarse densities. Sampling *does*
converge; it just needs ~0.5 m spacing, far finer than anything in `PROFILES`:

| spacing | samples | bldg 27 | bldg 6 |
|---|---|---|---|
| 5.00 m (`accurate`) | 26 | 0.7232 | 0.7076 |
| 2.50 m (`final`) | 48 | 0.7693 | 0.7373 |
| 0.50 m | 224 | 0.7528 | 0.7361 |
| 0.02 m | 5,516 | 0.7538 | 0.7368 |
| **exact** | — | **0.7537** | **0.7368** |

The real defect is that the profiles we actually use carry errors up to **0.03**, moving
non-monotonically, which misclassifies any building within ~0.03 of `tau`. That is smaller than
the 0.07 originally claimed, but still larger than any usable `claim_margin`.

**Exact coverage is both correct and cheaper** than the sampling density needed to match it:
6.2 ms for two buildings versus 5,516 samples.

**How it works** (`src/giscup/exact_coverage.py`). Visibility along an edge from a fixed point is
piecewise constant, and its breakpoints are exactly where the sight line grazes a blocker vertex.
So: cast rays from the antenna through every nearby blocker vertex, record where they cross the
edge, and those parameters partition [0,1] into intervals of constant visibility. Test one
interior point per interval with the official predicate, union across antennas, sum lengths. No
grid, no tunable density.

**Bug found and fixed during implementation** — same family as the `negative_buffer` failure.
`np.allclose(p0, p1)` defaults to a **relative** tolerance of 1e-5. At UTM 11N northings (~3.7e6)
a 16 m vertical edge differs by only 4.5e-6 relatively, so the degeneracy check declared real
edges zero-length and returned no intervals. Only *vertical* edges broke, because eastings (~5e5)
are an order of magnitude smaller. Unit-square tests at coordinates near 1 could never expose it;
`tests/test_exact_coverage.py` now carries UTM-magnitude regression and brute-force cross-checks.

**Scope (Marko's call):** exact coverage backs the **claim decision and validation**. Greedy keeps
the fast sampled matrix — it is a search heuristic, not the scored quantity, and putting exact
coverage in its inner loop would risk the 6.3x feasibility headroom.

### 9 — Prune the candidate pool  (blocked on #2)

160,198 candidates to choose at most 1,000 from is heavy overkill, and matrix cost is linear in
candidate count — an 8x prune is an 8x saving on the dominant cost.

Implement genuine pruning behind the existing mode names (`density`, `visibility_probe`,
`hybrid`). Today those modes only add **more** candidates via `edge_sample` and prune nothing,
which makes the names misleading. Prefer spatial diversity and high-visibility positions. Measure
the quality cost of each prune level against runtime saved; stop before quality degrades measurably.

### 12 — Claim decision must not use the optimizer's own samples

Found 2026-08-07 running the nine-block CLI pipeline end to end at small scale (60 buildings at
UTM 11N magnitudes). **`validate-output` rejected our own solution.**

| tau | k | claimed | overclaims | worst gap |
|---|---|---|---|---|
| 0.75 | 5 | 28 | 1 | 0.0424 |

1 of 489 claims across all nine blocks (0.20%). Every other block was clean.

**Root cause.** `solve_one` optimizes on the `balanced` grid (10 m spacing) and then decides
claims from those same samples. That is an *in-sample* estimate and is optimistically biased:
greedy chose antennas specifically to light up those samples, so sampled coverage overstates true
coverage for the selected set. Re-measuring on `accurate` (5 m) disagrees. The observed gap of
0.0424 is nearly **10x** the current `claim_margin` of 0.005.

Overclaims concentrate at **high tau and low k** — where coverage sits nearest the threshold and
sampling error decides the outcome.

**Options.**

- (a) Decide claims on a denser, independent sampling than the one optimized on. Principled;
  costs one extra coverage pass.
- (b) Raise `claim_margin` to ~0.05. Crude — forfeits every building whose true coverage lies
  between `tau` and `tau + margin`.
- (c) Fold the claim decision into the un-culled verification pass of **#3**, which already
  re-measures near-threshold buildings exactly. Probably the right home: one mechanism handles
  both the cull's under-report and the sampling grid's over-report.

Re-measure at full scale once the matrix lands — 0.20% on 60 buildings may behave very
differently on 12,860.

### 14 — Boundary-point jitter made 32% of samples unseeable  (FIXED 2026-08-08)

**The most damaging bug found in this project.** Every coverage number produced before
2026-08-08 10:30 is wrong.

Samples and candidates are produced by interpolation, `p0 + t*(p1 - p0)`. In float64 at EPSG:32611
magnitudes (~5e5, 3.7e6) the result lands within an ULP of the true edge line — about 1e-10 m —
and lands **inside** the polygon roughly half the time. Measured on the official dataset: **44.5%
of samples sit microscopically inside their own footprint.** One ULP is the smallest displacement
representable there; no amount of careful computation avoids it.

Tested against the raw polygon, such a point makes every segment ending at it report blocked — the
segment's interior genuinely does dip inside. The point became invisible from *everything*,
including a candidate two metres away on its own edge.

| | before | after |
|---|---|---|
| samples invisible from their own building | ~32% | **0.03%** |
| samples visible from any candidate at all | 67.6% | — |
| buildings "unreachable" at tau=0.75 | 76.1% | — |

**Fix:** block when a segment penetrates more than `INTERIOR_TOLERANCE = 1e-6` m into the
interior, by testing against the footprint eroded by that amount. Same official rule, stated so
float64 can evaluate it. A micrometre is five orders above the jitter and five below the smallest
real footprint, so nothing geometric rides on the value. Verified: 0 of 12,860 footprints collapse,
minimum area retained 99.9998%.

**This is the mechanism deleted in #10.** `negative_buffer` failed at `eps=1e-9`, which sits below
float64 relative precision at 3.7e6. The mechanism was right; the epsilon was wrong. I deleted it
on real evidence but drew too broad a conclusion. `_check_erosion` now makes collapse loud.

**Why nothing caught it:** every geometry test used unit-square coordinates, where an ULP is ~2e-16
and the jitter cannot occur. The regression suite (`tests/test_boundary_jitter.py`) now works at
UTM magnitudes with irregular coordinates, and asserts the cheapest possible invariant — *a point
on a boundary must be visible from that same boundary*.

**Blast radius:** both visibility matrices deleted (7.5 GB); the 800 m build was killed at 26/48
chunks; the real 400 m nine-block solve was killed mid-run; the #6 sizing must be redone. The
"76% unreachable at tau=0.75" figure was mostly this bug, not geometry. `MatrixSpec` now carries
`interior_tolerance` so a pre-fix matrix can never be silently reused, and metadata lacking the
field is rejected rather than defaulted.

### 13 — Exact interval coverage  (DONE 2026-08-08)

**CORRECTION to the 2026-08-07 finding.** That entry claimed sampled coverage "does not
converge". **That was wrong** — it was inferred from only four coarse densities. Sampling *does*
converge; it just needs ~0.5 m spacing, far finer than anything in `PROFILES`:

| spacing | samples | bldg 27 | bldg 6 |
|---|---|---|---|
| 5.00 m (`accurate`) | 26 | 0.7232 | 0.7076 |
| 2.50 m (`final`) | 48 | 0.7693 | 0.7373 |
| 0.50 m | 224 | 0.7528 | 0.7361 |
| 0.02 m | 5,516 | 0.7538 | 0.7368 |
| **exact** | — | **0.7537** | **0.7368** |

The real defect is that the profiles we actually use carry errors up to **0.03**, moving
non-monotonically, which misclassifies any building within ~0.03 of `tau`. That is smaller than
the 0.07 originally claimed, but still larger than any usable `claim_margin`.

**Exact coverage is both correct and cheaper** than the sampling density needed to match it:
6.2 ms for two buildings versus 5,516 samples.

**How it works** (`src/giscup/exact_coverage.py`). Visibility along an edge from a fixed point is
piecewise constant, and its breakpoints are exactly where the sight line grazes a blocker vertex.
So: cast rays from the antenna through every nearby blocker vertex, record where they cross the
edge, and those parameters partition [0,1] into intervals of constant visibility. Test one
interior point per interval with the official predicate, union across antennas, sum lengths. No
grid, no tunable density.

**Bug found and fixed during implementation** — same family as the `negative_buffer` failure.
`np.allclose(p0, p1)` defaults to a **relative** tolerance of 1e-5. At UTM 11N northings (~3.7e6)
a 16 m vertical edge differs by only 4.5e-6 relatively, so the degeneracy check declared real
edges zero-length and returned no intervals. Only *vertical* edges broke, because eastings (~5e5)
are an order of magnitude smaller. Unit-square tests at coordinates near 1 could never expose it;
`tests/test_exact_coverage.py` now carries UTM-magnitude regression and brute-force cross-checks.

**Scope (Marko's call):** exact coverage backs the **claim decision and validation**. Greedy keeps
the fast sampled matrix — it is a search heuristic, not the scored quantity, and putting exact
coverage in its inner loop would risk the 6.3x feasibility headroom.

### 9 — Prune the candidate pool  (blocked on #2)

160,198 candidates to choose at most 1,000 from is heavy overkill, and matrix cost is linear in
candidate count — an 8x prune is an 8x saving on the dominant cost.

Implement genuine pruning behind the existing mode names (`density`, `visibility_probe`,
`hybrid`). Today those modes only add **more** candidates via `edge_sample` and prune nothing,
which makes the names misleading. Prefer spatial diversity and high-visibility positions. Measure
the quality cost of each prune level against runtime saved; stop before quality degrades measurably.

### 10 — Unimplemented names and placeholders

Prevents a false capability claim at submission time.

- `lazy-greedy`, `stochastic-greedy`, `hybrid` appear in configs and CLI help but only `greedy`
  exists (`solver.solve_one` correctly raises). Implement or remove the names.
- **Recommend deleting the `negative_buffer` and `hybrid` *visibility* strategies.** Measured
  2026-08-07: `relate` is the exact official predicate; `hybrid` is semantically identical to it
  (0 disagreements over 1,200 full-scale pairs) but 1.16–1.40x slower, so it is pure waste.
  `negative_buffer` is worse than waste — at EPSG:32611 magnitudes `buffer(-1e-9)` falls below
  float64 relative precision and collapses footprints to empty, so it reported **every** pair
  visible (56/400 disagreements at ≤200 m before the guard landed). It now raises rather than
  over-claiming, but the option should not exist at all: `validate-output` accepts the same
  `--visibility-strategy`, so solving and validating both on it would have produced a garbage
  solution that validated clean — the exact ROGII "blind local validation" failure mode.
- `scripts/compare_configs.py` and `scripts/profile_visibility.py` are placeholders — implement or
  delete. `optimization-experimenter` is currently told to flag rather than run them.
- `configs/defaults.yaml` is not wired into the CLI at all.

---

## Done

| Date | Task | Evidence |
|---|---|---|
| 2026-08-08 | #5 — official sample dataset obtained and verified | `data/GIS-cup-sample-dataset.geojson`. Every documented statistic matches exactly (12,860 / 78,727 / 858,973.22 m / 1 hole / EPSG:32611). Revealed the synthetic omitted the large-building tail (real max perimeter 1,066 m). |
| 2026-08-08 | #3a — verification pass no longer inherits the solver's cull | `--verify-radius-factor` (default 2.0). A 400 m solve now verifies at 800 m, so the pass corrects the blind spot instead of sharing it. |
| 2026-08-08 | #10 — dead names removed | Deleted the `negative_buffer` and `hybrid` visibility strategies (one predicate remains, the official one), the unimplemented optimizer names, `scripts/compare_configs.py`, `scripts/profile_visibility.py`, and `configs/defaults.yaml`. 122 tests pass. `MatrixSpec.eps` deliberately retained — dropping it would have changed the cache key and thrown away the 110-minute matrix build. |
| 2026-08-08 | #13 — exact interval coverage | `src/giscup/exact_coverage.py` + 15 tests. Agrees with converged brute force to 4 dp (0.7537 vs 0.7538) at 6.2 ms for two buildings. Corrected the 2026-08-07 "does not converge" claim — it does converge, at ~0.5 m. Fixed a relative-tolerance bug that silently voided vertical edges at UTM magnitudes. |
| 2026-08-07 | #2 — radius-culled cached visibility matrix | `d7b9f6d` + build. 2.77 GB, 9,844,991 visible pairs, 110.8 min on 8 cores, key `18912a76…`. Reused across all nine subproblems. |
| 2026-08-07 | #4 — feasibility gate reads PASS | **MEASURED**, not projected: 3.18 h for nine subproblems vs a 20 h budget, 6.3x headroom. Was FAIL by ~5e8x at session start. |
| 2026-08-07 | #3 — un-culled verification pass | Uncommitted. `src/giscup/verify.py` + 19 tests. Policy (Marko): band **relative** to tau, **two-sided**, closest-to-tau first under a cap. Recovers what the cull forfeited, drops what the grid inflated. Wired into `solve_one` via `--verify-band` / `--verify-max-buildings`, opt-in. **Radius calibration half still outstanding** — needs the full-scale matrix. |
| 2026-08-07 | #12 — claim decision decoupled from the optimizer's grid | Uncommitted. `verify.dense_samples_for` re-samples targeted buildings independently rather than reusing the grid greedy optimized on. On the mini nine-block run this dropped the original overclaim (building 6) plus 7, and recovered 8 and 27; `validate-output` went from FAIL to `ok: true`. **Superseded in principle by #13** — the underlying instability is unfixed. |
| 2026-08-07 | #11 — hole-perimeter question resolved against official rules | Official page re-checked: "the polygons will not self-intersect and will not have holes." Moot on official data (no interior rings ⇒ `polygon.length` == exterior perimeter). Defensive behaviour kept; assumption + bounded cost recorded in `docs/competition-reference.md`. |
| 2026-08-07 | #7 — validation path scales | Uncommitted. `geometry.BoundaryIndex` replaces the linear boundary scan: **1,877x** faster, identical results on 300 full-scale probes (8.6 min → 0.3 s for k=1000 × 9). `validate.visible_sample_ids_from_points` is point-major with an early-out plus an optional `--validation-radius`: nine blocks in ~95 min measured *under full CPU contention*, against a naive 2.39e8 checks per block. 13 tests in `tests/test_validate_scaling.py` pin equivalence, subset-safety of the cull, and eps handling. |
| 2026-08-06 | Migrate Codex layer to Claude Code | `be6d66b` — 18 tests pass, all paths resolve |
| 2026-08-06 | Harden `.claude/settings.json` after security review | `6403ab6` — 3 findings fixed |
| 2026-08-06 | Full-scale synthetic dataset generator | `ee51eef` — `scripts/make_synthetic_dataset.py`, within a few % of every documented statistic |
| 2026-08-06 | Feasibility gate | `ee51eef` — `scripts/rehearse.py` + `/rehearsal`; found the viable route on day 1 of 9 |
| 2026-08-06 | Encode ROGII lessons as rules and gates | `ee51eef` — `CLAUDE.md` posture section, agent rules, session memory |
| 2026-08-07 | #1 — default visibility strategy → `relate`; hoist `buffer(-eps)` out of the hot loop | Uncommitted. 77 tests pass (was 18). `tests/test_visibility_strategy.py` pins the `relate` default at all 6 entry points + CLI, and 11 degeneracies × 3 strategies agree. Erosion memoized per-eps on `BlockerIndex`; strategy dispatch also hoisted out of the per-blocker loop. Measured speedup 1.16–1.40x, **not** the ~2.5x the board assumed. Found and guarded a silent over-claim bug in `negative_buffer` (see #10). |
