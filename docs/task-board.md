# Task Board

Durable task list. `/startup` reads this and recreates the in-session task list from it.
Keep it current: when a task is finished, move it to **Done** with the date and the evidence.

Last updated: **2026-08-09**.

## Feasibility — the 2026-08-07 figure was wrong; this supersedes it

The old header here claimed **PASS at 3.18 h / 6.3x headroom**, and the later re-run claimed
4.01 h / 5.0x. **A real nine-block run then took 9.42 h.** The gate's verification constant was
16.2x too small (#16). Do not quote either old figure.

Current, after #16 (re-fit) and #18 (parallel verification), against a 20 h budget:

| | serial | **--verify-workers 12** |
|---|---|---|
| upper bound (every building claimed) | 19.34 h / 1.0x | **6.87 h / 2.9x** |
| likely (v2 claim fractions) | 11.18 h / 1.8x | **5.14 h / 3.9x** |

**Always pass `--verify-workers` — to `rehearse.py` and to `solve-all` on the day.** Serial puts
the bound back on the margin.

## Unblocked — can start any time

| # | Task | Why now |
|---|---|---|
| 9 | Prune the candidate pool | **Re-ranked up.** Previously waved off as contraindicated by "robust over runtime" — that assumed 5.0x headroom. Runtime is a robustness property at 2.9x. |
| — | Shrink the matrix build | It is now the **largest single line** (99.5 min of 6.87 h) and cannot be served from cache on the day. |
| — | *(#20 CLOSED 2026-08-09 — 300 m measured, costs ~0.79 subproblems for ~0.8 h; ranked below #9, which saves ~2x for ~1/11 the cost. 400 m stands.)* | |

## Blocked on machine time (no decision needed)

| # | Task | Unblocks when |
|---|---|---|
| — | *(empty — 19b closed 2026-08-09 19:24)* | |

**#19b DONE 2026-08-09.** All nine lever A blocks exist, assembled into
`outputs/nine_leverA_400_full.txt` (27 lines, 9 blocks, 4,650 antennas, 42,556 claims) and
**AUDITED CLEAN: 0 overclaims of 42,556 claims**, 0 off-boundary antennas, 0 unknown IDs, exactly-k
counted in every block. Audit took **10 m 51 s** at 12 workers against a ~9.6 min projection — the
fitted 0.090 s/building/1000-antennas constant held. Log: `outputs/audit_leverA_full.log`.

**Verification speedup re-measured uncontended, and the gate is conservative by ~1.6x.** The
k=1000 run had the machine to itself. Block `(0.5, 1000)` verified 8,537 buildings in 20.3 min and
`(0.75, 1000)` verified 5,261 in 15.1 min, i.e. **0.143 and 0.172 s per building per 1000
antennas** against the serial near-tau constant of 1.26 — an effective **8.8x and 7.3x at 12
workers**, versus the 4.70x contention floor `gate_model` assumes. **Plan with 7.3x, not 8.8x**:
the higher figure belongs to the block with more buildings in the band, which is consistent with
the documented batch-size effect, so the smaller number is the one that generalises. Not yet folded
into `gate_model` — `verify_speedup` deliberately refuses to extrapolate past its last measurement,
and changing it is a separate, tested edit.

## Blocked on Marko

| # | Task | Waiting on |
|---|---|---|
| 15 | Does lever A become the submission default? | **Nothing — decide now.** 7 of 9 blocks measured (+9.7%), 0 overclaims of 27,803 audited. 19b only makes the artifact submittable; it will not change the verdict. |
| — | Final packaging | which artifact wins (#15) |

**#17 is answered** (see "Lever A" under #6): **+9.7% verified claims across 7 of 9 blocks**,
winning six of seven, and **0 overclaims of 27,803 claims** on the five audited. Shipping baseline
instead forfeits ~1.89 of 9 subproblems. **#19 is done.** **#3b is answered**: 600 m services
+4.1% but leaves only ~1.6x headroom — recommendation is that 400 m stands, Marko's call.

---

## Closed 2026-08-09 (overnight + morning)

- **#14** scene reuse + per-block partial writes (`4c947d6`). NOTE: the "~40% of a run"
  justification was WRONG -- setup is 3.32 s, the waste was 27 s (0.08%). The `SceneSpec`
  guard and the partial writes are the real value.
- **#16** feasibility gate re-fitted (`06e9d4f`). One constant, 16.2x wrong: 0.051 ->
  **0.826** s per building per 1000 antennas. Gate now prints an upper bound AND a likely
  estimate; the likely one predicts v2 within 1%. Pinned by `tests/test_gate_calibration.py`.
- **#18** exact claim verification parallelised (`2a7ed77`). Was 81.7% of runtime on one
  core of sixteen. Measured floors: 1.77x / 3.10x / 4.20x / **4.70x** at 2/4/8/12 workers,
  **bit-identical to serial**. Gate: 19.34 h / 1.0x -> **6.87 h / 2.9x**.
  **CONFIRMED AT FULL SCALE 2026-08-09** by a nine-block re-run at `--verify-workers 12`
  (`outputs/nine_verifypar_400.txt`, 171.1 min): identical antenna coordinates in all nine
  blocks and **identical claim sets** — 39,120 claims, zero IDs added or dropped in any block.
  End to end **9.42 h -> 2.85 h, 3.30x**. Verification falls from dominating the run to about
  half of it (86.6 min greedy vs 82.5 min verify over the seven logged blocks).
  *The run's own auto-diff printed `DIFFERS`; that was the harness, not the solver.* It compared
  bytes, and `nine_real_400_v2` launched ~22:11 on 2026-08-08 — an hour before the ID-sorting
  commit `1da0db4` landed at 23:25 — so that process froze the pre-fix `list(set)` order at
  import. Compare claim **sets**, never bytes, across runs that straddle a formatting change.
- **#8 (baseline half)** `outputs/nine_real_400_v2_clean.txt` PASSES the full two-stage
  audit: 0 overclaims of 39,120 claims, exactly 4,650 antennas.
- Audit defect fixed (`45c9766`): auditing at 400 m gave 25 false failures and 0 real ones.
  Now screens cheap, confirms at 800 m via `giscup.audit.confirm_overclaims`.

**New item this surfaced:** with verification down to 49% of the projected total, the
**99.5 min matrix build is now the largest single line** -- and unlike the sample run it
cannot be served from cache on submission day.

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

**Re-measured 2026-08-08 on CORRECT visibility** (post-#14; the first curve ran on the broken
predicate). 40 probe candidates, official dataset, `balanced`:

| radius | neighbours/candidate | visible/candidate | gain | captured | probe cost |
|---|---|---|---|---|---|
| 200 m | 993 | 48.3 | — | 70.9% | 2 s |
| 400 m | 3,635 | 62.0 | +28.5% | 91.1% | 8 s |
| 800 m | 12,559 | 67.1 | +8.1% | **98.5%** | 51 s |
| 1600 m | 41,517 | 68.1 | +1.5% | 100.0% | 417 s |

*(broken-predicate values were 21.5 / 27.7 / 30.0 / 30.5 — absolute visibility roughly doubled
after the fix, but the **shape held**: 400 m captured 91% then and 91.1% now. I had flagged this
curve as void; the relative conclusion in fact survived.)*

**400 m discards ~9% of real visibility; 800 m discards ~1.5%.** Cost scales with
neighbours/candidate: 800 m is 3.45x the pairs of 400 m, 1600 m is 11.4x.

**Build-cost model, measured 2026-08-08** (probe throughput + neighbour counts, calibrated
against the measured 400 m build of 99.5 min on 12 workers):

| radius | neigh/cand | checks/s | model | **corrected** | capture | day total | headroom |
|---|---|---|---|---|---|---|---|
| 400 m | 3,217 | 16,481 | 100 min | **1.7 h** *(measured)* | 91.1% | 4.2 h | **4.8x** |
| 500 m | 4,909 | 14,801 | 169 min | ~3.2 h | ~93% | 5.7 h | 3.5x |
| 600 m | 6,825 | 13,486 | 258 min | **~5.4 h** | ~95% | 7.9 h | **2.5x** |
| 700 m | 9,300 | 10,046 | 472 min | ~11 h | ~97% | 13.5 h | 1.5x |
| 800 m | 11,297 | 9,516 | 605 min | ~15 h *(observed)* | 98.5% | 17.6 h | 1.1x |

`corrected` applies the gap between model and reality: the model predicted 6.0x for 800 m over
400 m; the observed ratio was **9.1x**. Single-threaded probes cannot capture 12-way
memory-bandwidth contention, and that penalty grows with radius. Day total adds ~2.5 h for greedy,
verification, validation and packaging.

**800 m was attempted and abandoned.** It was killed at 12/48 chunks after 4.4 h, tracking to
~15.1 h. At 1.1x headroom a config is not robust — on unseen data, if the August extract is larger
or denser, the window evaporates and **all nine subproblems score zero**. Capturing 7% more
visibility is not worth risking the finishing guarantee.

**600 m is the largest radius that keeps a real margin** (2.5x) and is the upgrade candidate if
400 m's measured results justify it.

**Mitigation that weakens the whole radius argument:** the verification pass already re-measures
near-threshold buildings at **2x the solver's radius** (`--verify-radius-factor`, default 2.0). A
400 m solve verifies at 800 m, so the buildings that actually decide score already get the wide
view. The cull's cost falls mainly on buildings far from `tau`, which were not going to flip.

**Method note.** The first attempt at this measurement was wrong: `BlockerIndex.eroded` is computed
lazily, so the first timed loop absorbed the one-time erosion of 12,860 footprints. That made 400 m
read 1,245 checks/s against 500 m's 16,717 — throughput apparently *rising* with radius. Since
400 m was also the calibration base, every derived estimate was inflated. Warm the index before
timing anything.

**DECIDED 2026-08-08 (Marko): "whatever produced better results."**

### 600 m ANSWERED 2026-08-09 — matched-pair measurement, awaiting Marko's call

Both matrices built on the official dataset; identical candidates (157,454), samples (133,417),
script and objective; **only the radius differs**. Serviced-building counts:

| tau | k | 400 m | 600 m | change |
|---|---|---|---|---|
| 0.25 | 50 | 1,652 | 1,875 | **+13.5%** |
| 0.25 | 500 | 8,818 | 9,083 | +3.0% |
| 0.25 | 1000 | 11,622 | 11,742 | +1.0% |
| 0.50 | 50 | 390 | 484 | **+24.1%** |
| 0.50 | 500 | 4,578 | 4,931 | +7.7% |
| 0.50 | 1000 | 8,545 | 8,729 | +2.2% |
| 0.75 | 50 | 28 | 69 | **+146.4%** |
| 0.75 | 500 | 1,312 | 1,439 | +9.7% |
| 0.75 | 1000 | 3,648 | 3,886 | +6.5% |
| | **total** | 40,593 | 42,238 | **+4.1%** |

**The gain is real and concentrates at low k and high tau** — the starved subproblems, where
relative scoring pays most. But the model here predicted ~5.4 h and the build took **7.24 h**
(sixth optimistic projection in this project).

**Unmeasured cost, and it is the deciding one:** `--verify-radius-factor 2.0` means a 600 m solve
verifies at **1200 m**, while the 0.826 s constant was measured at 800 m. `gate_model` now
*refuses* to cost that pair rather than guess. Even ignoring it: 7.24 h matrix + 1.72 h greedy +
1.64 h verify = ~10.6 h likely / ~12.3 h bound, **~1.6x headroom** — below the 2.5x this section
projected and near the 1.1x that got 800 m killed.

**Recommendation: 400 m stands.** Rule 1 — feasibility outranks quality, and 1.6x on an unseen
extract is not robust. The open counter-proposal is a **2x-pruned 600 m build** (~3.6 h instead of
7.24 h, since a 2x prune was *then believed* free — see #9, where that claim is now superseded), which might land back near 2.5x. That is ~3.6 h of
machine time and is **Marko's call**.

Not worth testing: 1600 m buys +1.6% over 800 m for another 3.3x.

**Build costs, measured on the official dataset. CORRECTED 2026-08-09 — the figures that were
here before were measured with the PRE-#14 broken predicate and understate visibility by ~2x.**

| radius | build time | visible pairs | visible/candidate | key | valid? |
|---|---|---|---|---|---|
| 400 m | 82.5 min (8 workers) | 3,888,638 | 24.7 | `171c436e` | **NO — pre-#14** |
| 400 m | **99.6 min** (8 workers) | **8,194,226** | **52.0** | `7a385189` | yes |
| 600 m | **434.5 min** (6 workers, nice 15) | **8,891,506** | **56.5** | `89846a10` | yes |
| 800 m | abandoned at 12/48 chunks, tracking ~15 h | — | — | — | — |

Only the last two rows may be quoted. The `24.7 → 52.0` jump is #14: absolute visibility roughly
doubled once boundary jitter stopped making a third of the samples unseeable.

Longer segments intersect more blockers per STRtree query, so throughput falls as radius rises —
the pair count and the per-pair cost both grow. That is why 600 m cost **4.36x** the build time of
400 m for **+8.5%** visible pairs.

**CORRECTED 2026-08-09.** This paragraph used to read "the real matrix is 2.5x sparser than the
synthetic one (3.89M pairs vs 9.84M)". That compared the **pre-#14** real matrix against the
synthetic and is wrong. Post-fix the real 400 m matrix holds **8,194,226** pairs (52.0 visible
samples per candidate) against the synthetic's 9,844,991 (61.5) — real is **1.2x sparser, not
2.5x**. Real street topology does block more sight lines than the synthetic's layout, but by far
less than the broken predicate made it look. The conclusion that survives unchanged: no
solution-quality number measured on the synthetic can be trusted.

**Mitigation already in place.** The verification pass no longer inherits the solver's cull. It
re-measures at `visibility_radius x verify_radius_factor` (default 2.0), so a 400 m solve verifies
against 800 m. `--verify-radius-factor 0` makes it fully unbounded.

### 20 — Radii BELOW 400 m — contingency sizing  (ADDED 2026-08-09, not started)

**Marko's request. Do not start until he says so.** Every radius measurement in this project runs
*upward* from 400 m (500 m modelled, 600 m built, 800 m abandoned, 1600 m modelled). Downward is
unexplored, and it is the direction that buys the thing feasibility actually needs: **time**.

**The motivating scenario is not "300 m as the default".** It is the submission-day runbook's
"what to give up if the extract is bigger" section, which currently names no measured fallback.
If the August extract is materially denser or larger than the March sample, the 400 m config's
~2.9x bound compresses, and the only lever available *on the day* is a cheaper config. Having a
measured 300 m point turns that from improvisation into a switch.

**Pre-sizing from the measured curve** (200/400/800/1600 m are measured; 300 m is interpolated and
must be confirmed, not quoted):

| radius | neigh/cand | capture | build (8 workers) | status |
|---|---|---|---|---|
| 200 m | 993 | 70.9% | ~25 min *(inferred)* | measured curve point |
| **300 m** | **~2,100** *(est)* | **~84%** *(est)* | **~43 min** *(est)* | **UNMEASURED — this task** |
| 400 m | 3,635 | 91.1% | **99.6 min** *(measured)* | current default |

Neighbours scale as roughly **r^1.87**, not r² — sub-quadratic because building footprints occupy
area that candidates cannot, and the deficit grows with radius. Both the 200→300 and 400→300
extrapolations agree on ~2,100, which is why the estimate is worth stating at all.

**Expected quality cost is real and should not be soft-pedalled.** 400→600 m gained ~4 points of
capture and delivered **+4.1%** serviced buildings. 400→300 m gives up ~7 points, so a **−5% to −8%**
serviced count is the honest expectation. This is a feasibility lever, not a quality lever.

**Two things make it more attractive than that number suggests:**

1. **The gate's refusal is asymmetric in our favour going *down*.** A 300 m solve verifies at 600 m,
   which `verify_constant_for` will refuse as an unmeasured pair — same guard that blocks 500 m and
   600 m. But 600 m verification is strictly *cheaper* than the 800 m the 0.826 / 1.26 constants were
   fitted at, so costing 300 m with the 800 m constant is a **safe upper bound**. Going up, no such
   bound exists. So this task can produce a defensible headroom figure without a new verification
   measurement, which 500 m and 600 m cannot.
2. **It stacks with the free 2x prune (#9).** 300 m + 2x prune projects to a **~22 min** matrix build
   against the current 99.6 min. That is the realistic emergency config.

**Size it against #9 before spending machine time — #9 may dominate it outright.** The 2x prune buys
**1.69 h at zero measured quality cost** (one serviced building of 14,708). A 300 m cull buys ~1 h
at a −5–8% cost. **As a pure time-buying lever the prune strictly dominates**, and if the goal is
only headroom, do #9 first and this may never be needed. The case for measuring 300 m anyway is that
the two stack, and that a *contingency* needs to exist before the day it is needed — not that 300 m
competes with 400 m on merit.

**Suggested order when started:** (a) probe neigh/cand and capture at 300 m to confirm or kill the
~2,100 / ~84% estimates — minutes, not hours, and it is the cheap falsification step; (b) only if
those hold, build the matrix and run a matched-pair serviced-count comparison against 400 m, exactly
as #3b did for 600 m — identical candidates, samples, script and objective, radius the only change.

**Do not let this quietly become a default change.** Same one-shot-submission logic as #15 and #3b:
it is Marko's call, and 300 m is a fallback config unless a measurement says otherwise.

#### PROBED 2026-08-09 — both interpolations confirmed, and a board error found

`scripts/probe_small_radii.py`, 60 probe candidates, official dataset, erosion index warmed first:

| radius | neigh/cand | visible/cand | vs 400 m | capture | predicted |
|---|---|---|---|---|---|
| 200 m | 981 | 41.2 | 77.7% | **70.8%** | board says 70.9% ✓ |
| **300 m** | **2,105** | **49.1** | 92.7% | **84.5%** | **~2,100 / ~84%** ✓ |
| 400 m | 3,586 | 53.0 | 100.0% | 91.1% | control |

**The r^1.87 neighbour scaling was right to 0.2%** (predicted ~2,100, measured 2,105), and the
capture estimate to half a point. The pre-registered estimates survived contact with measurement,
which is the opposite of how the sweep-based predictions went.

**A board error surfaced doing this.** The 3b probe table's *visible/candidate* column reads 62.0 at
400 m, but the 400 m matrix on disk holds 8,194,226 pairs over 157,454 candidates — **52.0**. This
probe reproduces the matrix (+2.0%) and not the old column (−15%). Neighbour counts agree with the
board to within 1.4%, so the error is confined to the visibility column.

**The `capture` column is unaffected and remains trustworthy** — it is a ratio taken within a single
run, so a systematic multiplicative bias cancels. The 200 m arm reproducing the board's 70.9% to
within 0.1 points is direct evidence of that. **So: do not quote the 3b probe table's absolute
visible/candidate figures; the capture percentages are fine.**

**Next: matched-pair quality comparison at 300 m.** Note the experimental design point — a 300 m
solve verifies at 600 m under the default factor 2.0, while the 400 m artifact verified at 800 m.
Comparing them directly would confound the solve cull with the verification radius, so the 300 m arm
must run `--verify-radius-factor 2.6667` to verify at the same 800 m.

#### 300 m MATRIX BUILT 2026-08-09

| | candidates | visible pairs | visible/cand | build | key |
|---|---|---|---|---|---|
| 300 m | 157,454 | 7,529,996 | 47.8 | **48.6 min @ 12 w** | `73e00daa` |
| 400 m | 157,454 | 8,194,226 | 52.0 | 99.6 min @ **8 w** | `7a385189` |

**300 m retains 91.9% of 400 m's visibility.** The probe predicted 92.7% from 60 candidates; the
full builds say 91.9%. The probe's *ratio* was right to 0.8 points even though its absolute
densities ran ~2% high — further evidence that ratios from these probes transfer and absolute
figures do not.

#### The 8-vs-12 worker question, finally answerable

Three builds now exist, and two of them are at 12 workers, which is enough to back out throughput:

| build | checks (cand x neigh) | time | checks/s |
|---|---|---|---|
| stride-2 @ 400 m, 12 w | 78,727 x 3,586 = 282 M | 50.9 min | **92 K/s** |
| full @ 300 m, 12 w | 157,454 x 2,105 = 331 M | 48.6 min | **114 K/s** |

Throughput is **higher at 300 m** despite more total checks — shorter segments intersect fewer
blockers per STRtree query, the same effect that makes cost grow super-linearly with radius.

**Inference (labelled as such): a full 400 m build at 12 workers would cost ~102 min**, from
565 M checks at the stride-2 build's 92 K/s. The measured 8-worker build took **99.6 min**. So
**12 workers buys essentially nothing over 8 for this workload** — it is memory-bandwidth bound,
exactly as the concurrency notes in `session-state` describe.

That closes the gap that made the #9 and #20 build savings unquotable:

- **300 m saves ~50 min** of matrix build against 400 m (48.6 vs ~100).
- **stride-2 saves ~50 min** likewise (50.9 vs ~100).
- They should stack to roughly **~25 min**, since the two reductions are independent.

**This is an inference from one throughput constant applied across candidate mixes, not a matched
measurement.** A real matched 12-worker 400 m build would cost ~100 min to settle it. Not spent —
but do not quote these as measured.

### #20 ANSWERED 2026-08-09 — 300 m is a LAST-RESORT lever, ranked below #9

Matched pair against the shipped artifact, six of nine blocks, lever A on both arms, **both
verifying at 800 m** (the 300 m arm forced to `--verify-radius-factor 2.6667`) so only the solve
cull differs. 50.8 min.

| block | 400 m (shipped) | 300 m | delta | subproblems lost |
|---|---|---|---|---|
| (0.25, 50) | 1,659 | 1,433 | **−13.6%** | 0.136 |
| (0.25, 500) | 9,349 | 9,000 | −3.7% | 0.037 |
| (0.5, 50) | 269 | **193** | **−28.3%** | **0.283** |
| (0.5, 500) | 4,247 | 4,041 | −4.9% | 0.049 |
| (0.75, 50) | 148 | **110** | **−25.7%** | **0.257** |
| (0.75, 500) | 2,222 | 2,156 | −3.0% | 0.030 |
| **total** | **17,894** | **16,933** | **−5.4%** | **0.79** |

**The claim-count view (−5.4%) understates the damage by an order of magnitude.** Under relative
scoring these six blocks lose **0.79 subproblems**, because the loss concentrates in the small-count
blocks that are worth exactly as much as the large ones. This is the *same trap* as #9's pooled
sizing, hit independently. **My −5% to −8% pre-registered estimate was right about claims and
useless as a decision input.**

The mechanism mirrors 600 m going the other way (+146% at `(0.75, 50)`, +6.5% at k=1000): **radius
and antenna budget substitute for each other.** With few antennas each must reach far to be useful,
so the cull binds hardest; at k=1000 there is enough coverage nearby that radius barely matters.

#### The decisive asymmetry: 300 m does not speed up greedy at all

| lever | matrix build | greedy | total saved | score cost |
|---|---|---|---|---|
| **#9 stride-2** | ~50 min | **~0.86 h** (candidates halved) | **~1.7 h** | **~0.07** |
| **#20 300 m** | ~50 min | **nothing** (same 157,454 candidates) | ~0.8 h | **~0.79** |

Greedy's argmax is a popcount over every candidate row, and words-per-row depends on *sample* count,
not on how many bits are set. A 300 m matrix has fewer visible pairs but the **same number of rows
of the same width**, so greedy costs exactly what it did at 400 m.

**So #9 strictly dominates #20: about twice the time saved at about a eleventh of the score cost.**
If runtime must be bought on the day, spend the prune first and only reach for a radius cut if that
is not enough.

**One caveat that makes 300 m look better here than it would in production.** This comparison gave
the 300 m arm the benefit of **800 m verification**, forced deliberately to isolate the cull. Run
normally at `--verify-radius-factor 2.0`, a 300 m solve verifies at **600 m** — tighter, so fewer
band recoveries, so probably *worse* than −5.4%. Treat this table as the optimistic bound for 300 m.

**Verdict: #20 is answered and closed. 400 m stands, with more evidence than before.** 300 m stays
documented as a last-resort contingency for an August extract that genuinely threatens the window,
ranked below #9. Matrix `73e00daa` is cached if it is ever needed.

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

### 4 — Gate reads PASS  (2026-08-07 — **NUMBERS SUPERSEDED, DO NOT QUOTE**)

> **The 3.18 h / 6.3x below is DISPROVEN.** It omitted verification entirely, which turned out to
> be 81.7% of the runtime. A real nine-block run took **9.42 h**. Kept only to show what the gate
> used to say and why. Current figures are in the header of this file; the calibrated model lives
> in `giscup.gate_model`, pinned by `tests/test_gate_calibration.py`. These numbers were also
> measured on the SYNTHETIC stand-in and on the pre-#14 predicate.

```
matrix build : 110.8 min   (once, reused by all nine)
greedy       : 1.031 s per iteration
  k=50   x 3 taus :   2.6 min
  k=500  x 3 taus :  25.8 min
  k=1000 x 3 taus :  51.6 min
TOTAL            : 3.18 h    <-- WRONG: excludes verification, actual run 9.42 h
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

### 6 — Threshold-aware objective  — LEVER A MEASURED AND WIRED (default off), 2026-08-09

**Sized first** (CLAUDE.md rule 2), on official data at k=500, post-#14:

| tau | serviced (k=500) | ceiling | within 0.10 below | upper-bound upside |
|---|---|---|---|---|
| 0.25 | 8,818 | 12,860 | 1,382 | +15.7% |
| 0.50 | 4,578 | 12,860 | 1,881 | +41.1% |
| 0.75 | 1,312 | 12,860 | 999 | +76.1% |

The ceiling is 12,860 at every tau — every building is serviceable in principle, and 100.0% of
samples are visible from at least one candidate. The constraint is purely how the `k` budget is
allocated.

**Then built the safest form and measured it.** `optimize.greedy_select_threshold` clears samples
of already-serviced buildings from an `active` mask, so gain is
`popcount(row & ~covered & active)` — the dominant term of the submodular capped objective
`sum_b min(visible_weight_b, tau * perimeter_b)`, at unchanged iteration cost.

| tau | k | baseline | threshold | delta | gain |
|---|---|---|---|---|---|
| 0.25 | 50 | 1,652 | 1,659 | +7 | +0.4% |
| 0.50 | 50 | 390 | 394 | +4 | +1.0% |
| 0.75 | 50 | 28 | 28 | 0 | +0.0% |
| 0.25 | 500 | 8,818 | **9,384** | **+566** | **+6.4%** |
| 0.50 | 500 | 4,578 | 4,591 | +13 | +0.3% |
| 0.75 | 500 | 1,312 | **1,298** | **−14** | **−1.1%** |

**Verdict: NOT adopted as the default.** One real win, four neutrals, and a regression at
`tau=0.75, k=500` — exactly where the upper bound was largest. Scoring is per-subproblem, so a
gain in one block does not pay for a loss in another.

**Why it fails at high tau.** The mask deactivates serviced buildings, pushing greedy *outward*
toward the many unserviced ones. But at `tau=0.75` a building needs three-quarters of its
perimeter, so winning requires **concentrating** effort. The mask spreads it — the same failure it
was built to cure, relocated. At low tau buildings tip over cheaply, so redirecting away from
satisfied ones genuinely finds new wins; hence +6.4% at 0.25 and −1.1% at 0.75.

**Where the remaining headroom actually is:** weight buildings *near* the threshold and abandon
ones far below it — the opposite move, and the higher-variance option set aside earlier. The
building-level mask also never caps *within* a building, so a footprint at 0.74 still contributes
every sample at full weight; the finer form needs the segmented sum the mask avoids.

`greedy_select_threshold` is kept, tested, and available. It is not wired into `solve_one`.

#### Lever A — measured 2026-08-09, and the prediction above was right

`optimize.greedy_select_near_tau` masks to buildings that are unserviced **and** within a quantile
of the live deficit distribution, so marginal coverage is spent where it can still flip something.
The cutoff must adapt: at iteration zero every building is unserviced with deficit exactly
`tau * perimeter`, so a fixed threshold would select everything or nothing.

**The sweep carried its own control.** `quantile=100` targets every unserviced building, which *is*
lever B. It reproduced lever B's three measured numbers exactly — `−1.1% / +0.3% / +6.4%` — so the
rest of the table is trustworthy. Against baseline greedy, k=500:

| tau | q=25 | q=50 | q=100 (= lever B) | best |
|---|---|---|---|---|
| 0.75 | **+77.7%** (1,312 → 2,331) | +60.1% | −1.1% | q=25 |
| 0.50 | +3.5% | **+8.6%** | +0.3% | q=50 |
| 0.25 | −8.3% | +0.2% | **+6.4%** | q=100 |

**As tau rises, tighten the mask.** At tau=0.75 few buildings are reachable so concentrating pays
enormously; at tau=0.25 nearly every unserviced building is winnable and discriminating hurts.
Lever B is therefore not a failed lever — it is the **tau→0 corner of this one-parameter family**,
and it had only ever been measured at the corner where it happens to be right.

Capture against the pre-registered hard bound: **13.1%** (+1,019 of +7,756), versus a ~14% estimate
made before the measurement existed.

**The optimum also depends on k.** Full k=50 table, controls again exact (+0.0 / +1.0 / +0.4%,
matching lever B on all three — **six-for-six across two k values**):

| tau | q=25 | q=50 | q=100 (= lever B) | best |
|---|---|---|---|---|
| 0.75 | **+460.7%** (28 → 157) | +189.3% | +0.0% | q=25 |
| 0.50 | **+37.7%** | +22.1% | +1.0% | q=25 |
| 0.25 | −13.8% | −5.7% | **+0.4%** | q=100 |

And k=1000, which **inverts** the trend:

| tau | q=25 | q=50 | q=100 (= lever B) | best |
|---|---|---|---|---|
| 0.75 | +28.0% | **+29.7%** | +0.5% | q=50 |
| 0.50 | **−6.4%** | +1.1% | **+3.5%** | q=100 |
| 0.25 | −0.6% | +3.0% | **+6.8%** | q=100 |

**The optimal quantile tracks how many buildings are realistically winnable.** Higher tau → fewer
winnable → tighten. Higher k → more winnable → loosen. The two effects oppose, and the resulting
grid is clean and monotone in both directions:

| optimal q | k=50 | k=500 | k=1000 |
|---|---|---|---|
| tau=0.75 | 25 | 25 | **50** |
| tau=0.50 | 25 | **50** | **100** |
| tau=0.25 | 100 | 100 | 100 |

**The schedule is not a free knob — the wrong value loses**: −13.8% at tau=0.25/k=50/q=25, −6.4% at
tau=0.5/k=1000/q=25.

**The shipped schedule `100 50 25` is safe, and better than it had any right to be.** It is
positive in all nine cells and *optimal in five of them*:

| tau | q used | k=50 | k=500 | k=1000 |
|---|---|---|---|---|
| 0.25 | 100 | **+0.4%** ✓ | **+6.4%** ✓ | **+6.8%** ✓ |
| 0.50 | 50 | +22.1% (best 37.7) | **+8.6%** ✓ | +1.1% (best 3.5) |
| 0.75 | 25 | **+460.7%** ✓ | **+77.7%** ✓ | +28.0% (best 29.7) |

It gives up meaningfully only at **tau=0.5**, and tau=0.25 wants q=100 at every k — i.e. plain
lever B is exactly right there. A per-(tau, k) schedule would recover the tau=0.5 cells; whether
that is worth the CLI surface **and the overfitting risk on a one-shot submission tuned entirely on
the March sample** is task #15, Marko's call.

Wired as `--near-tau-quantile`, **default off**. Every figure here is the March sample; the
quantile is a *tuned* parameter and may not transfer to the August extract, which the baseline
objective's lack of any knob does not risk.

#### READ THIS BEFORE TREATING +77.7% AS A SCORE

`scripts/sweep_near_tau.py` counts serviced buildings from `samples` — **the same grid the
optimizer optimized on**. That is exactly the #12 defect ("claim decision must not use the
optimizer's own samples"), which the solver fixed and this analysis script reproduces.

**The bias is not symmetric between the two arms.** Baseline greedy accumulates coverage where it
is cheapest, so most of its serviced buildings sit comfortably clear of tau and in-sample error
rarely flips them. Lever A *deliberately concentrates on buildings near the threshold*, so its
incremental wins are precisely the ones a small in-sample/out-of-sample discrepancy decides.

So every sweep number above **inflates lever A more than baseline**. Treat them as an upper
estimate and a ranking of quantiles, not as a score prediction. The honest measurement is the
nine-block run, which decides claims off an independent grid and then verifies exhaustively:

#### COMPLETE 2026-08-09 — all nine blocks measured, and one of them LOSES

The two k=1000 blocks landed at 19:09 (70 m 39 s for both). Full table, all post-verification,
schedule `--near-tau-quantile 100 50 25` mapped positionally onto `--taus 0.25 0.5 0.75`:

| block | q | baseline | lever A | verified | sweep predicted |
|---|---|---|---|---|---|
| (0.25, 50) | 100 | 1,660 | 1,659 | −0.1% | +0.4% |
| (0.25, 500) | 100 | 8,854 | 9,349 | +5.6% | +6.4% |
| (0.25, 1000) | 100 | 11,630 | 12,279 | +5.6% | +6.8% |
| (0.5, 50) | 50 | 144 | 269 | +86.8% | +22.1% |
| (0.5, 500) | 50 | 3,903 | 4,247 | +8.8% | +8.6% |
| **(0.5, 1000)** | **50** | **8,063** | **7,891** | **−2.1%** | **+1.1%** |
| (0.75, 50) | 25 | 27 | 148 | +448.1% | +460.7% |
| (0.75, 500) | 25 | 1,295 | 2,222 | +71.6% | +77.7% |
| (0.75, 1000) | 25 | 3,544 | 4,492 | +26.7% | +28.0% |
| **total** | | **39,120** | **42,556** | **+8.8%** | |

Both totals reconcile independently against previously audited figures: baseline sums to the
audited 39,120, and the first five lever A blocks sum to the audited 27,803.

**`(0.5, 1000)` is lever A's first material loss — 172 buildings.** The board predicted the
mechanism before the measurement: the k=1000 sweep says q=50 gives only +1.1% there while **q=100
gives +3.5%**, and the shipped schedule uses q=50 because it was fitted at k=500. The documented
rule — *higher k loosens the optimum* — is exactly what bit. Verification came in 3.2 points below
the sweep at this block; `(0.75, 1000)` tracked its sweep to within 1.3 points.

**Scoring the two artifacts against each other**, each block against the better of our own options:

| artifact | subproblems (of 9) |
|---|---|
| pure baseline | **6.90** |
| pure lever A | **8.98** |
| per-block best of both | **9.00** |

So lever A wins decisively, but **the right answer is not a single default** — subproblems score
independently and both artifacts exist. This is a comparison between two of our own options, not a
score prediction; competition rule 5 still holds.

#### The earlier 7-of-9 measurement (superseded by the table above)

Baseline `outputs/nine_verifypar_400.txt` vs lever A (`outputs/nine_leverA_400_5of9.txt` plus
`outputs/leverA_tau075_small.txt`), all post-verification, schedule `--near-tau-quantile 100 50 25`
mapped positionally onto `--taus 0.25 0.5 0.75`:

| block | q | baseline | lever A | verified | sweep predicted | ratio if we ship baseline |
|---|---|---|---|---|---|---|
| (0.25, 50) | 100 | 1,660 | 1,659 | **−0.1%** | +0.4% | 1.001 |
| (0.25, 500) | 100 | 8,854 | 9,349 | **+5.6%** | +6.4% | 0.947 |
| (0.25, 1000) | 100 | 11,630 | 12,279 | **+5.6%** | — | 0.947 |
| (0.5, 50) | 50 | 144 | 269 | **+86.8%** | +22.1% | 0.535 |
| (0.5, 500) | 50 | 3,903 | 4,247 | **+8.8%** | +8.6% | 0.919 |
| (0.5, 1000) | 50 | 8,063 | *not measured* | | | |
| (0.75, 50) | 25 | 27 | 148 | **+448.1%** | +460.7% | **0.182** |
| (0.75, 500) | 25 | 1,295 | 2,222 | **+71.6%** | +77.7% | **0.583** |
| (0.75, 1000) | 25 | 3,544 | *not measured* | | | |
| **subtotal** | | **27,513** | **30,173** | **+9.7%** | | |

**The lever is real and the gap is large.** It wins six blocks of seven; the single loss is one
building. The last column is the score we would take on each block if a rival submitted
lever-A-equivalent numbers: shipping baseline instead of lever A forfeits **1.89 of 9 subproblems**
across these seven blocks, ~21% of the achievable total. That is a comparison between two of *our
own* options, not a score prediction — competition rule 5 still holds.

**The blocks that matter most are the ones with the fewest claims.** Under relative scoring every
subproblem is worth 1.0 regardless of size, so `(0.75, 50)` — 27 baseline claims — swings more than
`(0.25, 1000)`'s 11,630. Lever A's gains are largest exactly where the counts are smallest. Any
future lever must be sized on this table, never on the total claim count.

**The predicted in-sample asymmetry never materialised, in any block.** The warning above reasoned
that lever A's wins sit near the threshold, so verification should punish lever A harder than
baseline, making sweep numbers an upper estimate for lever A. Measured: in **five of six** blocks
with a sweep prediction, verification landed within a few points of it (+0.4→−0.1, +6.4→+5.6,
+8.6→+8.8, +460.7→+448.1, +77.7→+71.6). The sixth, `(0.5, 50)`, went the *other* way — the sweep
**understated** lever A by 4x, because verification cut the baseline from 390 in-sample to 144
(−63%) against lever A's 476→269 (−43%). So where the bias existed at all it favoured **baseline**,
never lever A. The `sweep_near_tau.py` numbers proved a good predictor of verified reality; keep
the methodological caution, but the empirical claim that it inflates lever A is **withdrawn**.

**`(0.5, 1000)` and `(0.75, 1000)` remain unmeasured** — the original run was killed at 13:55 in
block 6 of 9 after 10.4 h, having been launched with serial verification before the
`--verify-workers` default landed. Both are k=1000 blocks, where the k=1000 sweep *inverts* the
trend (see above), so they are the two blocks least safe to extrapolate. They cost ~2 h together.

#### The schedule is per-tau, but the optimum is per-(tau, k)

`--near-tau-quantile` maps positionally onto `--taus`, so one quantile serves all three k values at
that tau. The sweeps say the optimum moves with k as well — higher tau tightens, higher k loosens,
and the two effects oppose. Checking the shipped `100 50 25` schedule against each block's own best
quantile in the sweep tables above:

| block | schedule q | sweep at that q | best q | sweep at best | leaves |
|---|---|---|---|---|---|
| (0.25, 50) | 100 | +0.4% | 100 | +0.4% | — |
| (0.25, 500) | 100 | +6.4% | 100 | +6.4% | — |
| (0.25, 1000) | 100 | +6.8% | 100 | +6.8% | — |
| (0.5, 50) | 50 | +22.1% | **25** | **+37.7%** | **15.6 pts** |
| (0.5, 500) | 50 | +8.6% | 50 | +8.6% | — |
| (0.5, 1000) | 50 | +1.1% | **100** | **+3.5%** | **2.4 pts** |
| (0.75, 50) | 25 | +460.7% | 25 | +460.7% | — |
| (0.75, 500) | 25 | +77.7% | 25 | +77.7% | — |
| (0.75, 1000) | 25 | +28.0% | 50 | +29.7% | 1.7 pts |

Six of nine blocks already run at their best quantile. The one worth acting on is **`(0.5, 50)`**,
where q=25 beats the scheduled q=50 by 15.6 points in the sweep — and `(0.5, 50)` is a
small-count block, so under relative scoring it carries the same weight as `(0.25, 1000)`.
`(0.5, 1000)` and `(0.75, 1000)` leave little.

**This needs a CLI change**, not just a different argument: the schedule cannot currently express a
per-`(tau, k)` quantile. Sizing before building it — the sweep says the whole realisable gain is
concentrated in one block, so this is a small lever, not a second lever A. Do not start it before
#15 is settled and the two missing blocks are measured.

#### RETIRED 2026-08-09 20:03 — the per-(tau, k) schedule was refuted before it was built

The whole case for the CLI change was the sweep's claim that `(0.5, 1000)` wants **q=100 (+3.5%)**
rather than the scheduled q=50 (+1.1%). That cell was re-solved directly, full verification, same
config as the artifact:

| (0.5, 1000) | claims | vs baseline |
|---|---|---|
| baseline | **8,063** | — |
| lever A, q=50 (shipped schedule) | 7,891 | **−2.1%** |
| lever A, q=100 (the proposed fix) | 7,903 | **−2.0%** |

**Lever A loses at this block regardless of quantile**, and the sweep was optimistic by 5.5 points
on the very cell the mechanism was meant to rescue. Building a per-`(tau, k)` schedule now would be
constructing machinery on the one prediction we have proven unreliable.

**The failure is mechanistic, not noise.** At high `k` and middling tau most winnable buildings are
*already* winnable, so concentrating on near-threshold buildings re-secures footprints baseline
would have taken anyway. The objective is wrong for that regime; the knob is not mistuned. This is
the same monotone rule the board already records — higher `k` loosens the optimum — continued past
the point where even the loosest setting (q=100, i.e. plain lever B) still loses.

**Consequence:** `(0.5, 1000)` ships **baseline**, and the submission artifact is per-block best-of
rather than a single objective. Task #15 is therefore not "which default", it is "lever A
everywhere except the one block where it measurably loses".

**Kept for the record:** `outputs/leverA_tau05_k1000_q100.txt` (37 m 50 s, 7,903 claims).

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

### 17 — Claims must be verified exhaustively, not by band  (FIXED 2026-08-08)

Found by the first full-scale audit of a correct nine-block run. Two blocks checked before it was
stopped:

| block | claims | overclaims | worst exact coverage |
|---|---|---|---|
| 0.25 / 50 | 1,689 | 4 | 0.2366 |
| 0.25 / 500 | 8,942 | 24 | **0.1499** |

**The mechanism.** Verification re-checked buildings whose **sampled** coverage landed near `tau`.
But the error being corrected lives in that same sampled value, so *a large enough error carries a
building past the window's edge and out of scope*. The worst case was claimed at `tau=0.25` with
true coverage 0.1499 — its sampled value had to exceed 0.30 to escape the `[0.20, 0.30)` window,
i.e. an over-report of 0.15+.

**Why sampling errs that much.** Each boundary segment's midpoint decides the verdict for the whole
segment, so per-building error scales with sample count. A large building with 200 samples errs by
~0.5% per sample; a small one at the 8-sample floor errs by **12.5% per sample**. The ±0.03 figure
the band was sized on came from two large buildings and never described the small ones — which are
the majority.

**Why widening the band does not fix it.** Catching a 0.15 error needs `[tau-0.15, tau+0.15)` —
most of the population — and the 2,000 cap already bound in three blocks.

**The fix, and the asymmetry behind it.** An overclaim is a *correctness* failure; a missed
recovery is only lost score. So:

- **every claim gets an unconditional exact check** — no band, no cap. This makes overclaims
  structurally impossible rather than probabilistically unlikely.
- **recovery below `tau` stays banded and capped**, where approximation costs opportunity only.

Affordable: exact coverage runs ~50 ms/building at 400 m, so 1.7k–11.7k claims per block is
1.5–10 min, ~35 min across all nine against a 20 h budget.

**Audit cost note.** The audit was run at `--exact-radius 800` and projected to **8 hours** — 0.49 s
per claim at k=500, worse at k=1000. My 51 ms/building figure was measured at 400 m; 800 m is ~10x
that, not the 3–4x assumed. Audit at 400 m: a tighter radius under-reports coverage, so it flags
*more* claims, never fewer — conservative in the safe direction and ~4x faster.

### 16 — Absolute tolerances at projected magnitudes  (FIXED 2026-08-08)

A sweep for the bug class behind #13, #14 and #15, after three instances in one day made it clear
this was a pattern rather than a coincidence.

**`geometry.ring_edges`** decided whether to close a ring with `np.allclose(coords[0],
coords[-1])`. Default `rtol=1e-5` is **37 metres** at a northing of 3.7e6, so a genuinely open
ring would be treated as closed and its closing edge silently dropped — shortening the perimeter,
which is the denominator of every coverage ratio. Latent in practice because Shapely always
returns closed rings, but live for any other input path. Now an absolute
`COINCIDENT_POINT_TOLERANCE = 1e-9` m, just above float64 resolution there.

**`candidates._add_candidate`** deduped on `round(x, 12)`. Twelve decimals is meaningless at an
easting of 5e5, where float64 resolution is already ~6e-11. It merges genuinely coincident points
(a corner shared by two footprints) and cannot merge jittered near-duplicates. Changed to 9
decimals and documented, so the code no longer implies a precision it does not have.

**The rule is now in `CLAUDE.md`** under Geospatial rules: every geometric tolerance absolute, in
CRS units, never relative and never below float64 resolution — with the three concrete failures
and the instruction to test at real projected magnitudes with irregular coordinates. Unit-square
tests cannot see any of this: 122 of them passed while a third of the boundary was unseeable.

### 15 — Emitted antennas must not sit inside a footprint  (FIXED 2026-08-08)

A sibling of #14, on the output side. Measured on the official dataset:

| candidate kind | count | land inside their own footprint |
|---|---|---|
| vertex | 78,727 | 0 (0.0%) — copied verbatim from source data |
| midpoint | 78,727 | 29,472 (**37.4%**) — computed as `(p0+p1)/2` |

Median depth 7.9e-11 m, max 2.3e-10 m.

Those points are **legal**: the official check is `polygon.boundary.distance(pt) <= eps` with eps
1e-8..1e-7, and 1e-10 passes comfortably. The risk is different — an evaluator computing
*visibility* against the raw polygon would see nothing at all from an antenna a hair inside it,
exactly as this solver did before #14. We cannot know how the official evaluator handles it, and
there is one submission with no feedback.

**Fix:** `output.nudge_off_interior` moves emitted antennas just outside any footprint containing
them, ~1e-9 m. Applied in `solve_one` **before** verification, so we verify exactly what we emit.
Vertices are untouched. Verified end to end: 105 emitted antennas, 0 strictly inside, all still
measuring 0.0 m from a boundary, `validate-output` green.

Deliberately applied at output rather than in candidate generation: changing the candidate set
would change the matrix cache key and discard the rebuild in flight, for no gain — a 1e-9 m shift
cannot alter which candidates greedy would pick.

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
coverage in its inner loop would risk the feasibility headroom. (The "6.3x" that stood here is
the disproven 2026-08-07 figure; current headroom is 2.9x on the bound. The reasoning is
unaffected — if anything a tighter budget strengthens it.)

### 9 — Prune the candidate pool  (IMPLEMENTED 2026-08-09; **the "free" claim did NOT survive
re-measurement against lever A** — see the two subsections at the end of this entry)

**The board used to frame this as a matrix-build saving. It is nearly twice that.** Greedy's
argmax is a popcount pass over all 157,454 rows on every one of the `k` iterations, so **67% of
the likely day total is linear in candidate count**, not 33%:

| | h | scales with |
|---|---|---|
| matrix build | 1.66 | candidates |
| greedy argmax | 1.72 | candidates |
| verification | 1.64 | claims × k — untouched by pruning |

**Measured degradation, official data, k=500** (`scripts/size_candidate_prune.py`). The prune rule
keeps every Nth candidate *within each building*, so survivors stay spread over the domain:

| prune | candidates | tau=0.25 | tau=0.50 | tau=0.75 | likely | headroom (bound) |
|---|---|---|---|---|---|---|
| 1x (control) | 157,454 | 8,818 | 4,578 | 1,312 | 5.02 h | 3.0x |
| **2x** | 78,727 | −0.0% | +0.0% | **+0.0%** | **3.33 h** | **4.0x** |
| 4x | 39,431 | −2.0% | −3.0% | −6.6% | 2.48 h | 4.7x |
| 7.2x | 21,813 | −4.0% | −7.5% | **−14.9%** | 2.11 h | 5.2x |

**Only 2x is free** — one serviced building lost of 14,708. **SUPERSEDED 2026-08-09:** that was measured with *baseline* greedy, pooled at k=500. Against lever A it costs **−2.03% at `(0.75, 50)`**; see the end of this entry. Degradation is monotone, accelerating,
and always worst at high tau. An earlier claim in this session that an 8x prune was viable was
wrong and is withdrawn. **The honest lever is 1.69 h at zero measured quality cost.**

Two structural facts:

- **The free 2x is exactly `vertex-only`.** Candidates alternate vertex/midpoint, so `stride-2`
  and `vertex-only` are the *same set* — they are one measurement, not two agreeing. Pleasant
  coincidence with #15: the discarded half is the midpoint half, 37.4% of which lands
  microscopically inside its own footprint and needs an output nudge.
- **Per-building stride saturates near 12.2x** (157,454 candidates over 12,860 buildings), because
  every building keeps its first candidate. Beyond that a prune must delete whole buildings,
  removing their only legal antenna positions.

**Control passed:** `stride-1` reproduced `greedy_select_matrix` exactly, so the rest of the table
is trustworthy. Counts are in-sample (the grid greedy optimized on) so levels are upper estimates,
but the bias is *not* asymmetric between arms — every arm runs the same objective and differs only
in the row subset — so the comparison between levels is sound.

**Caveats before adopting:** measured at 400 m and k=500 only. Whether 2x stays free at k=50 —
where tau=0.75 services just 28 buildings and one lost candidate shows — is untested.

**`--max-candidates` is NOT this.** It truncates by generation order, which walks building by
building, so it deletes whole neighbourhoods. Documented as such in the CLI help and in
`greedy_select_matrix`. Do not use it for pruning.

**Sequencing:** pruning changes the candidate digest and therefore the matrix cache key. Adopting
it discards both the valid 400 m matrix and the 600 m build. Do not start until #3b is settled.

### #9 IMPLEMENTED AND BUILT 2026-08-09 — with one correction to the sizing

`--candidate-stride N` (`30b8c08`), and the stride-2 400 m matrix is built:

| | candidates | visible pairs | visible/candidate | build | key |
|---|---|---|---|---|---|
| stride 1 | 157,454 | 8,194,226 | 52.0 | 99.6 min @ **8** workers | `7a385189` |
| **stride 2** | **78,727** | **4,878,593** | **62.0** | **50.9 min @ 12** workers | `7c422675` |

**The pruned half is not half the visibility — it is 59.5% of it.** Halving the candidates removed
only 40.5% of the visible pairs, because the surviving set is the *vertex* half and vertices see
substantially more than midpoints (62.0 vs 52.0 samples each). Corners have wider viewsheds than
points flat against a wall. That is a favourable surprise: the prune is materially better than
discarding a random half, and it is a second independent reason the 2x came out free in the sizing.

**Correction to the saving, stated as uncertainty rather than a number.** The two builds ran at
**different worker counts** (8 vs 12), so they are not a matched pair and **no speedup figure should
be quoted from them**. What can be said:

- **Greedy's half of the saving is a clean 2x.** The argmax is a popcount over every candidate row,
  and words-per-row depends on sample count, not candidate count — so halving the rows halves the
  work exactly. That is ~0.86 h of the projected 1.72 h.
- **The matrix-build half is not established.** The 1.69 h figure assumed build cost halves with
  candidate count. Whether it does depends on neighbours-per-candidate and per-check blocker counts
  for vertices versus midpoints, and the 62.0-vs-52.0 gap says those populations are not
  interchangeable. A matched 12-worker stride-1 build would settle it and costs ~70 min; not spent,
  because the decision does not turn on it.

Treat #9's saving as **"at least ~0.86 h, probably more, not confidently 1.69 h."**

### #9 IS NOT FREE UNDER LEVER A — measured 2026-08-09, default stays OFF

The "free" claim came from the sizing script: one serviced building lost of 14,708, measured
**in-sample, with baseline greedy, pooled across three taus at k=500**. Re-measured against the
objective we actually ship, with full verification:

| block | stride 1 (audited) | stride 2 | delta | cost under relative scoring |
|---|---|---|---|---|
| (0.75, 500) | 2,222 | 2,218 | **−0.18%** | 0.0018 |
| (0.75, 50) | 148 | **145** | **−2.03%** | **0.0203** |

**The prune's cost scales inversely with claim count, and relative scoring weights every subproblem
equally.** So the blocks where pruning hurts most are precisely the small-count ones that are worth
exactly as much as `(0.25, 1000)`. Pooling across taus at k=500 — what the sizing did — averages
that signal away. Extrapolating the two measurements over nine blocks puts the total cost near
**0.07 subproblems**.

**Decision: `--candidate-stride` stays default 1.** Feasibility is no longer the binding constraint
— the day projection is ~5 h against a ~20 h window, and verification measured 1.6x faster than
`gate_model` assumes — so paying ~0.07 subproblems for ≥0.86 h of headroom we do not need is the
wrong trade. **This reverses the basis on which #9 was adopted**, which was the free-ness claim;
Marko may want to re-decide with these numbers.

**What #9 is now: a day-of contingency lever, the same shape as [#20](#20).** Both buy runtime and
pay score. Use it if the August extract is materially larger than the March sample and the window
tightens; leave it off otherwise. It is implemented, tested, measured, and one flag away.

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
| 2026-08-07 | #4 — feasibility gate reads PASS | ~~3.18 h, 6.3x headroom~~ **DISPROVEN — the real run took 9.42 h.** The gate excluded verification, which was 81.7% of runtime. Re-fitted in #16; current figures are in this file's header. The PASS verdict itself survived; the number did not. |
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
