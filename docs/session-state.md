# Current Session State

Operational state so the next session starts without rereading history.
Task list lives in `docs/task-board.md`. Say **"start session"** and `/startup` handles the rest.

Last session: **2026-08-08**. Working tree clean; **everything pushed**.

## The one thing that matters

**2026-08-08 was a bug-fixing day, not a tuning day.** Six defects were found and fixed, four of
them the same class (relative or sub-resolution tolerances at projected magnitudes). **Every
solution-quality figure recorded before 2026-08-08 ~10:30 is void.** Feasibility timings are
unaffected; correctness figures are not. See task board #13–#17.

The largest, #14, made **32% of all boundary samples permanently unseeable** and alone delivered
**101x at tau=0.75** (13 → 1,312 serviced). No amount of objective tuning came close.

**Current status: the pipeline is proven end-to-end on correct data.** A full nine-block run on the
official dataset completed in 164 min, 27 content lines, 40,118 claims. The audit passed every
structural check — nine blocks, exactly-k counted, boundary legality, IDs — but found overclaims,
which #17 fixed. A re-run with the fix was in flight when this was written.

## Decisions settled

- **Cull radius: 400 m.** 800 m was attempted and abandoned — killed at 12/48 chunks tracking to
  ~15 h, leaving only 1.1x headroom on the day. Not robust: on unseen data a denser extract
  evaporates the window and all nine subproblems score zero. 600 m (~5.4 h, 2.5x headroom) remains
  the upgrade candidate if measured results justify it. Full cost model in task board #3b.
- **Threshold-aware objective (#6): built, measured, NOT adopted.** +6.4% at tau=0.25/k=500,
  neutral elsewhere, **−1.1% at tau=0.75/k=500**. The mask pushes greedy outward toward unserviced
  buildings, but high tau needs concentration. `greedy_select_threshold` is kept and tested but not
  wired into `solve_one`.
- **Feasibility gate: PASS at 4.01 h / 5.0x headroom** (re-run 2026-08-08 on official data,
  15 cores). Supersedes the earlier 3.74 h / 5.3x figure, which predated #17. The gate's
  verification model was itself stale -- it costed the old band-capped pass at 7.9 min while
  #17 re-checks every claim. Now split into claim re-check (bounded by building count,
  50.8 min) and band recovery (7.9 min). Bounding claims by 12,860 is pessimistic at high
  tau and near-tight at low tau, which is the right direction for a gate.
- **Claims are verified exhaustively (#17)**, recovery stays banded. An overclaim is a correctness
  failure; a missed recovery is only lost score.
- **Audit at 400 m, not 800 m.** At 800 m it projected to 8 hours. A tighter radius under-reports
  coverage so it flags more, never fewer — conservative and ~4x faster.

## Resume here

```bash
conda activate mz-giscup-26

# Was running at hand-off: re-solve with exhaustive claim verification (~3 h)
ls -la outputs/nine_real_400_v2.txt outputs/nine_real_400_v2.json

# Then audit it -- at 400 m, NOT 800 m
python scripts/audit_submission.py --input data/GIS-cup-sample-dataset.geojson \
    --solution outputs/nine_real_400_v2.txt --exact-radius 400
```

Matrices in `outputs/cache` are keyed on `interior_tolerance`, so pre-#14 ones can never be reused.
The official 400 m matrix (key `7a385189…`, 8,194,226 pairs) is current and valid.

Local head: `be0a2bf Verify every claim exactly instead of by band (#17)`. Everything pushed.

## Known gaps, ranked

1. **Submission packaging has never been done.** No artifact, no packaging dry run, no run
   instructions. `docs/agent-roles-brief.md` names a `submission-packager` role but nothing has
   produced or tested a bundle. It is the **only completely unrehearsed step** in the pipeline —
   everything else has run end to end at full scale at least once. On a one-shot, no-feedback
   submission this is the largest remaining risk.
2. **Solution quality is baseline greedy.** The one lever sized and built did not earn its place.
   Remaining ideas: weight buildings *near* tau (opposite of what was built), and cap *within* a
   building rather than at building level.
3. **Every figure comes from the March sample; August is a different extract.** Config tuned here
   may not transfer — an argument for keeping the generous headroom.
4. **`solve-all` silence — FIXED 2026-08-08.** `src/giscup/progress.py` reports per-subproblem
   with an ETA weighted by *antennas placed*, not subproblems finished. The measured fit over the
   nine-block run is 2.16 s per antenna with a -24 s intercept, so cost is proportional to `k`;
   count weighting is off by 14x after the first (k=50) block. Progress is on by default,
   `--quiet` disables. The ETA is pessimistic early (131 min predicted vs 163 actual after one
   block) and converges to <1% by block 7 — the safe direction.
5. **My timing estimates ran optimistic five times today** (800 m build 2.6x, audit 16x, nine-block
   26%). Treat any projection of mine that is not calibrated against a measured run with suspicion.

## Repository

- Local root: `/home/markolinux/projects/sigspatial_26`
- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`, branch `main`
- Pushed through `d7b9f6d`. **6 later commits are LOCAL AND UNPUSHED** — Marko's standing rule is
  that pushes need explicit approval each time, and he was asleep.
- Local head: `3166d19 Add the mechanical submission audit (#8)`
- Unpushed: `047159e` (gate PASS), `89945ab` (#13 exact coverage), `3bc49f3` (#10 deletions),
  `26aeedb` (#5 dataset + #3b calibration), `3166d19` (#8 audit), plus this docs commit.

## Environment

```bash
conda activate mz-giscup-26      # Python 3.11; required for all work
```

Host: **16 cores, 24 GB RAM** (the gate's 8-core assumption is conservative — 16 are available).
NumPy 2.4.6 (`np.bitwise_count` available), Shapely 2.1.2, SciPy 1.17.1.
**`ruff` and `mypy` are NOT installed** — `pip install -e .[dev]` if lint is needed.

## Data situation — read before trusting any number

**The official sample dataset is now present**: `data/GIS-cup-sample-dataset.geojson` (6.3 MB,
git-ignored), downloaded 2026-08-08 from
`https://sigspatial2026.sigspatial.org/img/GIS-cup-sample-dataset.geojson` (public, no
registration). Every documented statistic matches exactly: 12,860 buildings, 78,727 exterior
vertices, 858,973.22 m total perimeter, 1 hole-bearing polygon, EPSG:32611.

Test data still does not exist until 2026-08-15.

The synthetic stand-in (`outputs/synthetic_full.geojson`, regenerable via
`scripts/make_synthetic_dataset.py`) is still around and is what every pre-2026-08-08 figure was
measured on. **It understated reality in two ways that mattered:** it omitted the large-building
tail (real max perimeter 1,066 m, max area 17,957 m²) and it understated visibility reach, which
is why the 400 m cull costs ~9% on real data rather than the ~2% it implied. Prefer the official
dataset for everything from now on.

**Matrix cache keys are per-dataset.** The synthetic matrix cannot be reused for real-data solves.

`.gitignore` was tightened this session: `/outputs/*` matched only one level, so the 2.77 GB
matrix showed up as untracked. Now `/outputs/**` plus `*.bits`.

## What was built 2026-08-07

### #1 — `relate` default + erosion hoist (done)

`relate_pattern(poly, "T********")` is exactly the official predicate. Default flipped from
`hybrid` at all six entry points plus the CLI and `configs/defaults.yaml`. `buffer(-eps)` is
memoized per-eps on `BlockerIndex`; strategy dispatch was also hoisted out of the per-blocker loop
(it ran ~1,180 redundant string comparisons per unbounded pair).

**Correction to the board:** the claimed "~2.5x faster" was measured before the hoist. Re-measured
at full scale it is **1.16–1.40x** — hoisting sped `hybrid` up too. Still a win; the figure was
wrong.

### #7 — validation scales (done)

- `geometry.BoundaryIndex`: STRtree over boundaries. **1,877x** faster than the linear scan,
  identical results on 300 full-scale probes. 8.6 min → 0.3 s for k=1000 × 9 blocks.
- `validate.visible_sample_ids_from_points`: point-major with an early-out plus an optional
  `--validation-radius`. Nine blocks in ~95 min measured *under full CPU contention* (real number
  will be well under), against a naive 2.39e8 checks per block.
- Validation deliberately does **not** reuse the solver's matrix: a solution file's points need
  not be in the candidate set, and sharing the matrix would make validation blind to matrix bugs.
  Independence is the point.

### #11 — hole-perimeter question (done)

Official page re-checked verbatim: **"the polygons will not self-intersect and will not have
holes."** Moot on official data — with no interior rings, `polygon.length` equals exterior
perimeter. Defensive behaviour kept because the sample contradicts the page; the assumption and
its bounded cost are recorded in `docs/competition-reference.md`.

### #2 — visibility matrix (code complete, build unproven)

`src/giscup/matrix.py`. Dense candidate-major bit matrix, `uint64` words, memmap-backed.
Marko chose dense bitsets over sparse CSR after seeing the density measurement.

- cKDTree enumerates only pairs inside the radius; parallel workers write disjoint candidate
  ranges through the memmap, so 2.76 GB never crosses a pickle boundary. `fork` inherits
  buildings/candidates/samples copy-on-write; STRtree and KDTree are rebuilt per worker.
- Cache key: blake2b over building WKB + candidate coords + sample coords + radius + strategy +
  eps. The metadata JSON is the completion marker, so a crashed partial build is rebuilt, never
  trusted.
- `optimize.greedy_select_matrix` is tested to select **exactly** what the predicate-based greedy
  selects. `solver.solve_one` gained `--visibility-radius` / `--cache-dir` / `--matrix-workers`.
  The radius is opt-in and never implied.

## Bug found and fixed: `negative_buffer` reported everything visible

At EPSG:32611 magnitudes (~5e5, 3.7e6) `buffer(-1e-9)` is below float64 relative precision
(~2.7e-16 vs eps 2.2e-16) and collapses whole footprints to **empty**. Empty geometry blocks
nothing, so `negative_buffer` reported every pair visible — 56/400 disagreements with `relate` at
≤200 m on real-magnitude data.

`hybrid` survived only because it ORs with `relate`. The compounding danger: `validate-output`
accepts the same `--visibility-strategy`, so solving *and* validating on `negative_buffer` would
have produced a garbage solution that validated clean — the exact ROGII "blind local validation"
failure mode. It now raises with a message naming the cause. `hybrid` passes `strict=False`
because it stays correct.

**Recommendation carried to #10: delete both alternative strategies.** `relate` is the official
predicate; `hybrid` is identical to it but slower; `negative_buffer` is a footgun.

## Measured constants — 2026-08-07, full-scale synthetic

12,860 buildings, 138,077 samples (`balanced`), 160,198 candidates, domain 4,975 × 4,263 m.

Throughput with `relate` (400 pairs per row, 1 core; run-to-run variance ±10–25%):

| segment length | blockers/query | checks/s |
|---|---|---|
| unbounded | 1,180 | 537–580 |
| ≤ 400 m | 21 | 12,172–16,213 |
| ≤ 200 m | 7 | 23,169–25,775 |

Matrix density (150 probe candidates):

| radius | neighbours/candidate | visible/candidate | nonzeros | density |
|---|---|---|---|---|
| 200 m | 798 | 48.3 | 7.74M | 0.035% |
| 400 m | 3,048 | 60.5 | 9.70M | 0.044% |

**200 m → 400 m costs 6.2x the build time for +25% visible pairs.** A quarter of all visibility
lives in that band, so culling at 200 m forfeits real buildings. Radius **400 m** chosen.

**Build time reality check:** the 150-candidate probe projected 58 min on 8 cores; the actual
build tracked to **~117 min**. Contiguous chunks hit denser regions than random probes do, and
8 workers contend for memory bandwidth. Probe-based projections of this build run ~2x optimistic.

## Validation status — 2026-08-07

```bash
python -m pytest -q                        # 119 passed, 4 failed  (was 18 passed)
python -m compileall -q src tests scripts  # OK
```

The 4 failures are **expected and deliberate**: the `select_buildings_to_reverify` tests in
`tests/test_verify.py` fail on `NotImplementedError` because the selection policy is an open
decision for Marko (task #3). Everything else is green. Once that function lands the suite should
read 123 passed.

## Known limitations carried forward

- Greedy objective is still raw newly-visible-sample count, not serviced-building count (#6).
- Candidate "pruning" modes only add candidates; they prune nothing (#9). **Do not enable pruning
  without rebuilding the matrix** — it changes the candidate digest and invalidates the cache.
- `configs/defaults.yaml` is still not wired into the CLI.
- `scripts/compare_configs.py` and `scripts/profile_visibility.py` are placeholders.
- `negative_buffer` / `hybrid` visibility strategies should be deleted (#10).
- The cull radius is a heuristic with no feedback; the un-culled verification pass (#3) is
  scaffolded but its selection policy is unimplemented.
- Only `greedy` exists as an optimizer. `lazy-greedy` / `stochastic-greedy` / `hybrid` raise.

## Session log

**2026-08-07 — critical path: #1, #7, #11 done; #2 built; #3 scaffolded.** See sections above.
Two board corrections recorded (relate speedup 2.5x → 1.16–1.40x; build-time projection 2x
optimistic). One silent-overclaim bug found and guarded. `.gitignore` tightened to keep the
2.77 GB matrix out of git.

**2026-08-06 — Codex to Claude Code migration, security hardening, feasibility gate.**
`AGENTS.md` → `CLAUDE.md`; `.agents/` + `.codex/` → `.claude/agents/` and `docs/reference/`.
Added `/startup`, `/wrapup`, `/solve`, `/rehearsal`, the `giscup-output-format` skill,
`scripts/make_synthetic_dataset.py`, and `scripts/rehearse.py`. `.claude/settings.json` hardened
after a security review found 3 issues; the `data/**` deny is a backstop, not a guarantee — it
does not cover shell writes. Encoded the ROGII lessons as rules and gates.
