# Current Session State

Operational state so the next session starts without rereading history.
Task list lives in `docs/task-board.md`. Say **"start session"** and `/startup` handles the rest.

Last session: **2026-08-08**. Working tree clean; **6 commits local and UNPUSHED**.

## The one thing that matters

**The feasibility blocker is CLEARED.** `scripts/rehearse.py --measured-radius 400` reads
**PASS, measured end to end**: 3.18 h for all nine subproblems against a 20 h budget, **6.3x
headroom**. At the start of 2026-08-07 this gate read FAIL by ~5e8x. Feasibility no longer
outranks solution quality.

What matters now is **solution quality and claim correctness**, plus one open decision:

**The 400 m cull radius discards ~9% of real visibility** (measured on the official dataset).
800 m would cut that to ~2% for a ~6.4 h matrix build instead of 110 min, still passing the gate
at 2.6x headroom. 400 m was Marko's call, made before that data existed. **This is the open
decision.**

**7 days to test-data release (2026-08-15); submission 2026-08-16.** One shot, no score feedback
ever. Treat Aug 15 as a rehearsal deadline, not a start date.

## Resume here

```bash
conda activate mz-giscup-26

# Which matrices exist? One key per (dataset, candidates, samples, radius, strategy, eps).
ls outputs/cache/visibility-*.json

# Full-scale solve on the OFFICIAL dataset (needs a real-data matrix; see below).
giscup solve-all --input data/GIS-cup-sample-dataset.geojson \
    --taus 0.25 0.5 0.75 --ks 50 500 1000 \
    --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 \
    --output outputs/nine_blocks_real.txt --diagnostics outputs/nine_blocks_real.json

# Mechanical audit of the result -- trusts nothing from the solver.
python scripts/audit_submission.py --input data/GIS-cup-sample-dataset.geojson \
    --solution outputs/nine_blocks_real.txt --exact-radius 800
```

**Two jobs were running when this was written** (2026-08-08 ~01:50):
`giscup solve-all` on the synthetic (nine-block timings for #8), and
`scripts/build_matrix.py` on the **official** dataset at 400 m. Check
`outputs/nine_blocks.txt` and `outputs/cache/*.json` for their results.

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
