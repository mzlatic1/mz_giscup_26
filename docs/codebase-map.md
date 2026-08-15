# Codebase Map and Implementation State

## Package layout

```text
src/giscup/
  models.py       # dataclasses for buildings, candidates, samples, solutions, dataset info
  io.py           # GeoJSON/geospatial loading via GeoPandas with fallback
  geometry.py     # boundary extraction, legality checks, bounds, segment lengths
  sampling.py     # weighted boundary samples, including interior rings by default
  candidates.py   # boundary-derived antenna candidates, dedupe, per-building prune (#9)
  visibility.py   # STRtree blocker index and LOS predicates
  coverage.py     # sampled coverage and serviced-building checks
  bitsets.py      # integer bitset abstraction (superseded by matrix.py; unused)
  exact_coverage.py # grid-free visible-interval coverage for claims/validation (parallel)
  verify.py       # two-sided near-threshold re-verification (parallel, #18)
  audit.py        # two-stage overclaim confirmation: cheap screen, wide confirm (parallel)
  assemble.py     # build one nine-block submission from separately-solved block files
  matrix.py       # radius-culled cached visibility matrix (dense bitset, memmap, parallel)
  optimize.py     # greedy selection: predicate-based, matrix-backed, threshold, near-tau
  scene.py        # SceneSpec: prepare buildings/candidates/samples once per solve-all
  solver.py       # solve-one orchestration
  output.py       # official formatting/parsing; exact-k guard; sorted claim IDs
  validate.py     # solution validation and sampled claim coverage
  diagnostics.py  # dataset summary diagnostics
  gate_model.py   # calibrated cost model behind the feasibility gate
  packaging.py    # submission bundle assembly and manifest
  progress.py     # per-block progress and ETA reporting
  cli.py          # inspect / solve-one / solve-all / validate-output
```

## Tests

```text
tests/test_antenna_placement.py  # emitted antennas never inside a footprint (#15)
tests/test_assemble_blocks.py    # nine-block recovery from partials; exact-k, duplicate, gap
tests/test_audit_coarse_source.py  # the six-decimal heuristic degrades to a NOTE on coarse data (#26)
tests/test_audit_two_stage.py    # screen/confirm radii, parallel==serial, empty final claims
tests/test_boundary_jitter.py    # THE invariant: a boundary point is visible from its boundary
tests/test_candidate_prune.py    # #9 per-building stride: identity control, row re-indexing
tests/test_dependencies.py       # imports declared in packaging metadata
tests/test_exact_coverage.py     # grid-free coverage vs analytic + brute-force truth
tests/test_exact_coverage_parallel.py  # parallel coverage is bit-identical to serial
tests/test_gate_calibration.py   # gate reproduces the v2 run; radius AND objective pinning
tests/test_geometry.py
tests/test_id_property.py        # the silent ID-fallback defect
tests/test_matrix.py             # matrix ground truth, cache keys, parallel==serial
tests/test_near_tau_wiring.py    # lever A plumbing, --objective, the default tau schedule
tests/test_optimize_matrix.py    # matrix greedy == predicate greedy
tests/test_optimize_near_tau.py  # lever A objective
tests/test_optimize_threshold.py # lever B objective
tests/test_output_format.py
tests/test_packaging.py
tests/test_progress.py
tests/test_projected_tolerances.py  # absolute tolerances at UTM magnitudes (#16)
tests/test_sampling.py
tests/test_scene_reuse.py        # SceneSpec guard (#14)
tests/test_solver.py
tests/test_solver_matrix.py      # solve_one fast path, cross-subproblem reuse
tests/test_validate.py
tests/test_validate_scaling.py   # BoundaryIndex + culled scan equivalence
tests/test_verify.py             # two-sided band selection, recover/drop
tests/test_verify_workers_default.py  # gate and solver agree on the worker default
tests/test_parameter_grid.py      # the (tau, k) grid is an argument, not a hardcode
tests/test_visibility.py
tests/test_visibility_strategy.py  # official predicate, degeneracies, relate default
```

Current latest result: **`368 passed`** in Conda env `mz-giscup-26` (2026-08-15, 20.9 s), 32 files.
*(365 -> 368 on 2026-08-15: three cases in `test_audit_coarse_source.py` covering the coarse-precision
`[NOTE]` path from #26. The `365 passed` / `31 files` figures stood in five documents after that
commit landed and were corrected on 2026-08-15 by actually running the suite — including in two
**live** runbooks, where an operator following step 0 would have read 368 against an expected 365 and
had to decide, under time pressure, whether the tree was broken.)*
*(350 -> 356 on 2026-08-10: six cases in `test_verify_workers_default.py` pinning the gate and the
solver to a shared `gate_model.DEFAULT_OBJECTIVE`, after they were found to disagree — the gate
costed `baseline` while the solver ran `near-tau`.)*
*(Grew from 333 over 2026-08-09: ten `test_candidate_prune.py` cases (#9) -> 343, three
`--objective` cases in `test_near_tau_wiring.py` (#15) -> 346, four quiet-machine speedup cases in
`test_gate_calibration.py` -> 350. An earlier `326` recorded here was simply stale.)*

## Compact documentation layer

```text
docs/startup-brief.md      # first-start compressed project memory
docs/competition-reference.md    # official constraints, format, dates, scoring
docs/codebase-map.md             # this file: package/commands/tests/limits
docs/session-state.md            # latest validation, environment, next steps
docs/context-maintenance.md      # mandatory startup/closeout docs-maintenance contract
docs/research-synthesis-brief.md # compact research digest
docs/agent-roles-brief.md        # compact agent routing
docs/task-board.md               # durable task list with dependencies
docs/reference/                  # deep-detail drill-down (project context, geometry
                                 #   and scoring rules, dev workflow, research registry)
```

## Claude Code layer

**None of this ships in the submission bundle.** `.claude/` was never in `SOURCE_TREES`, and
`CLAUDE.md` was removed from `SOURCE_FILES` on 2026-08-15 (#21). It is the operating contract for
this working copy, not source; it stays in the repository because it is the live workflow and holds
the `data/**` write guard.

```text
CLAUDE.md                                    # auto-loaded project rules
.claude/settings.json                        # permissions, data/ write-deny, SessionStart hook
.claude/agents/*.md                          # 8 self-contained subagents
.claude/commands/{startup,wrapup,solve}.md   # session rituals and subproblem runner
.claude/skills/giscup-output-format/         # non-negotiable submission-format rules
.claude/commands/rehearsal.md                # feasibility gate
```

## Feasibility tooling

```text
scripts/make_synthetic_dataset.py  # full-scale stand-in matching documented sample stats
scripts/rehearse.py                # gate: analytic projection, plus --measured-radius for an
                                   #   observed end-to-end verdict off the real matrix
scripts/build_matrix.py            # build/reuse the visibility matrix at full scale (--candidate-stride)
scripts/matrix_progress.py         # read progress of an IN-FLIGHT matrix build (size/du/log are all
                                   #   dead signals; probes the zero/nonzero frontier instead)
scripts/audit_submission.py        # mechanical audit of a nine-block file (two-stage, parallel)
scripts/assemble_blocks.py         # recover a nine-block file from partials / separate runs
scripts/package_submission.py      # build and verify the submission bundle
scripts/official_evaluator/        # headless driver for the ORGANISERS' scorer (see its README)
scripts/size_candidate_prune.py    # #9 sizing: quality cost of pruning the candidate pool
scripts/sweep_near_tau.py          # lever A quantile sweep (IN-SAMPLE — see task board)
```

**`data/` now holds the official March sample dataset** (`GIS-cup-sample-dataset.geojson`,
12,860 buildings, EPSG:32611). Task #5 is closed, and every figure quoted in the task
board since 2026-08-08 is measured against it rather than the stand-in.

`outputs/synthetic_full.geojson` is still generated and still useful for feasibility and
scaling rehearsals when the official file must not be touched. It reproduces documented
aggregate statistics only — no real street topology, and the large-building tail is
absent. Never use it for solution-quality claims.

## Implemented CLI

```bash
giscup inspect --input <geojson>
giscup solve-one --input <geojson> --tau <float> --k <int> --output <txt> [options]
giscup solve-all --input <geojson> --taus ... --ks ... --output <txt> [options]
giscup validate-output --input <geojson> --solution <txt> [options]
```

Full-scale runs need the matrix, which is opt-in and never implied:

```bash
giscup solve-all --input <geojson> --taus 0.25 0.5 0.75 --ks 50 500 1000 \
    --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 --verify-workers 12 --output <txt>
giscup validate-output --input <geojson> --solution <txt>
```

`--verify-band` re-measures buildings near `tau` with exact interval coverage, recovering ones the
cull forfeited and dropping ones the sampled grid inflated. `validate-output` checks claims
exactly by default (`exact_claims`), so it needs no profile or radius.

Without `--visibility-radius` the solver recomputes visibility every greedy iteration and will
not finish at full scale. Culling only ever *removes* visible pairs, so it under-reports coverage:
safe for validation (rejects, never wrongly accepts) but a silent score loss for the solver.

`--optimizer` accepts **`greedy` only**. The other names were deleted 2026-08-08 (#10) rather
than left as roadmap markers, so there is nothing to imply.

The threshold-aware objectives are **not** selected through `--optimizer` — that flag chooses the
*search*, and only `greedy` exists. The **objective** is `--objective {near-tau,baseline}`, and as
of 2026-08-09 it defaults to **`near-tau`** (lever A, #15). `greedy_select_threshold` (lever B) is
implemented and tested but still unwired. See Known limitations for the two deliberate asymmetries
this default carries, and for the one block where lever A loses.

Visibility strategy: **`relate` only** — the exact official predicate. `negative_buffer` and
`hybrid` were deleted 2026-08-08 (#10).

## Important correctness fixes already applied

- `validate-output` preserves empty claimed-ID lines.
- Malformed validation headers no longer loop indefinitely.
- Formatter rejects solution blocks where number of points differs from `k`.
- Solver rejects `max_candidates < k` and candidate pools smaller than `k`.
- Validator performs sampled claim coverage checks.
- Sampling includes hole/interior rings so represented boundary weight matches Shapely perimeter.

## Known limitations

- **The shipped default objective is lever A (near-tau) as of 2026-08-09** (#15, Marko's call).
  `--objective {near-tau,baseline}`, default `near-tau`. With no explicit `--near-tau-quantile` it
  uses `optimize.default_near_tau_quantile(tau)` — a **function of tau**, not a positional list, so
  it cannot misalign if August's thresholds are not 0.25/0.5/0.75. Measured across nine verified
  blocks: **+8.8% claims**, winning eight and losing `(0.5, 1000)`. `greedy_select_threshold`
  (lever B) remains implemented, tested and unwired. `lazy-greedy`, `stochastic-greedy` and
  `hybrid` remain **unimplemented and raise** — do not describe them as available.
- **Two deliberate asymmetries in that default.** (1) The CLI defaults to lever A but `solve_one`
  as a Python API still defaults to `None`, so no existing caller is re-objectived by an import;
  resolution lives only in `cli._resolve_near_tau_schedule`. (2) A CLI solve **without**
  `--visibility-radius` now fails, because lever A exists only on the cached-matrix path — a silent
  fallback to baseline would emit a structurally perfect file solved for a different problem. The
  error names both remedies.
- **Lever A loses `(0.5, 1000)` at every quantile** (baseline 8,063; q=50 7,891; q=100 7,903), so
  the shipped artifact is **per-block best-of** — lever A in eight blocks, baseline in that one.
  Legitimate because the nine subproblems score independently. The per-`(tau, k)` schedule that was
  once proposed to fix this is **retired**: its whole justification was a sweep prediction of +3.5%
  at that cell, and the cell measured −2.0%.
- **Candidate pruning is implemented as of 2026-08-09 (#9): `--candidate-stride N`**, keeping every
  Nth candidate *within each building*. **Default 1 (off), and it should stay off** — see below.
  Reproduces the board's counts exactly (157,454 → 78,727 → 39,431, all 12,860 buildings retained).
  Pruning changes `MatrixSpec.candidate_digest` and therefore the cache key, so a differently-strided
  matrix is rebuilt rather than reused; `candidate_stride` is also part of `SceneSpec`, so a pruned
  scene cannot be handed to a solver asked for the full pool. Stride-2 matrix is built and cached
  (key `7c422675`, 78,727 candidates, 4,878,593 pairs, 50.9 min at 12 workers).
- **The 2x prune is NOT free against the shipped objective.** The "one building of 14,708" figure
  was measured in-sample, with *baseline* greedy, pooled across taus at k=500. Against lever A with
  full verification: `(0.75, 500)` −0.18%, but **`(0.75, 50)` −2.03%**. Cost scales inversely with
  claim count while relative scoring weights every subproblem equally, so the small-count blocks —
  which the pooled sizing averaged away — are where it bites. ~0.07 subproblems over nine blocks.
  **Treat #9 as a day-of contingency lever** alongside #20 (sub-400 m radii): both buy runtime and
  pay score, and neither is worth it while the day projection sits near 5 h of a ~20 h window.
- **The pruned half is 59.5% of the visibility, not 50%** — the surviving vertex half sees 62.0
  samples per candidate against the full pool's 52.0, because corners have wider viewsheds than
  points flat against a wall. Consequence: greedy's saving is a clean 2x (popcount over halved
  rows), but the matrix-build saving is **not** established, and the two builds on record ran at
  different worker counts so no speedup figure should be quoted from them.
- `--max-candidates` is **not a prune**: it truncates by generation order, and generation walks
  building by building, so it deletes whole neighbourhoods. Documented as a footgun in the CLI
  help and in `greedy_select_matrix`.
- The cull radius is a heuristic: it discards genuinely visible pairs beyond the radius and loses
  score with no feedback. The near-threshold verification pass exists (#3a) and now re-measures at
  a **wider** radius than the solver's cull. #3b is **measured**: a 600 m matrix services +4.1%
  more buildings than 400 m but leaves only ~1.6x runtime headroom against 400 m's ~3x. The
  recommendation on record is that 400 m stands; the decision is Marko's.
- **The gate's verification constant belongs to a radius pair AND an objective.** 0.826 s per
  building per 1000 antennas was measured at (400 m solve, 800 m verify) with baseline greedy;
  lever A measured 1.26. `verify_constant_for` refuses any combination it was not measured at
  rather than returning a number, because an unknown objective defaulting to baseline would
  inherit the cheapest constant in the module.
- **Geometry tolerances are load-bearing.** `visibility.INTERIOR_TOLERANCE` (1e-6 m),
  `geometry.COINCIDENT_POINT_TOLERANCE` (1e-9 m) and
  `exact_coverage.DEGENERATE_EDGE_LENGTH` (1e-9 m) are all ABSOLUTE, in CRS units, and each exists
  because a relative or too-fine tolerance produced a real bug. Never loosen or relativise them
  without reading `CLAUDE.md` Geospatial rules first.
- Greedy still optimizes on the sampled matrix. That is deliberate — it is a search heuristic, not
  the scored quantity — but it means the objective and the claim decision measure different things.
  Analysis *scripts* that score off `samples` are therefore in-sample and optimistic; the
  nine-block run is the honest measurement. Measured 2026-08-09: for lever A the in-sample sweep
  turned out to be a good predictor of verified reality in five of six blocks, and where it erred
  it understated lever A rather than inflating it.

## Resolved since 2026-08-07

- Visibility precomputation/cache: **implemented** (`matrix.py`, task #2).
- Exact interval coverage backs claims and validation (`exact_coverage.py`, task #13).
- Dead names removed (task #10): `negative_buffer`/`hybrid` strategies, the unimplemented
  optimizer names, `scripts/compare_configs.py`, `scripts/profile_visibility.py`,
  `configs/defaults.yaml`. `relate` is now the only visibility strategy.
- Bitset acceleration in the optimizer: **implemented** (`optimize.greedy_select_matrix`).
- Validation scaling: **implemented** (`geometry.BoundaryIndex`, `validate.visible_sample_ids_from_points`).

## Resolved 2026-08-08 / 2026-08-09

- Official dataset obtained and every measured figure re-validated against it (task #5).
- Claim re-checking is exhaustive, not band-limited; claim IDs are emitted sorted (#17-defect).
- Scene prepared once per `solve-all`; **partial output written after every block** (#14).
- Feasibility gate re-fitted, 0.051 → 0.826 s per building per 1000 antennas, 16.2x (#16), and
  since pinned to both its radius pair and its objective.
- **Verification parallelised** (#18) and confirmed at full scale: a nine-block re-run at
  `--verify-workers 12` produced identical antennas and identical claim sets to the audited
  serial baseline, 9.42 h → 2.85 h (3.30x). `--verify-workers` now defaults to `min(cores, 12)`
  in both `solve-all` and the gate.
- **The audit is parallel too** (2026-08-09). It was the last single-core stage, run at the point
  in submission day with the least slack. Measured on five lever A blocks (27,803 claims), both
  runs two-stage at 400/800 m: **28 m 51 s serial vs 5 m 41 s at 12 workers — 5.08x at 96%
  efficiency**, and the two agree line for line. Audit cost scales with **claims x k**, not claim
  count; fitted constant **0.090 s per building per 1000 antennas** at a 400 m screen, projecting
  to ~46 min serial / ~9 min parallel for a nine-block artifact.
- **The 4.70x verification speedup in `gate_model` is a contention floor**, measured while two
  other jobs ran. The audit, a similar workload measured on a quiet machine, reached 5.08x at 96%
  efficiency against verification's 39%. Some of that gap is batch size — the audit screens a
  whole block at once, while verification parallelises a near-threshold band with a fresh pool per
  call — but re-measuring verification uncontended is an open opportunity that would shrink every
  projected day figure. Not acted on: `verify_speedup` deliberately refuses to extrapolate past
  the last measurement.
- **`scripts/audit_submission.py`'s unbounded-screen trap is FIXED** (`3f7db68`). It used to default
  `--exact-radius` to `None` — an unbounded screen, the ~8-hour path rather than the two-stage
  design — which meant selecting an 8-hour run by forgetting a flag. Found 2026-08-09 after two
  audits ran that way, one passing 3 h 25 m without finishing. The default is now **400.0 m**,
  matching `giscup.audit`; `none`/`unbounded` remain available explicitly. Confirmed in practice
  2026-08-09: the nine-block lever A audit ran 10 m 51 s at 12 workers.
- **Partial recovery exists** (`assemble.py`, `scripts/assemble_blocks.py`). `solve-all` had
  written `.partial` since #14, but nothing could consume it, so a run dying at block 7 still
  meant re-solving all nine. Round-trips a real nine-block file byte for byte.
- A parsing defect found while building that: `splitlines()` drops the trailing empty string, so
  a **final block that legitimately claims nothing** parsed as truncated. It would have failed a
  valid submission in `scripts/audit_submission.py`, the last gate before submitting. Fixed in
  both parsers.
- **The `(tau, k)` grid is no longer hardcoded** (2026-08-15). The dataset ships
  `competition-parameters.txt`, so the nine subproblems are published data. `assemble.py` grew
  `subproblem_grid(taus, ks)`; `scripts/assemble_blocks.py` and `scripts/audit_submission.py` grew
  `--taus`/`--ks`. Before this, a differing grid would have blocked crash recovery *and* failed a
  correct submission at the last gate. `packaging.py`'s `EXPECTED_BLOCKS = 9` is left alone: a count
  survives a different grid of the same size.
- **`giscup inspect` does not report the ID fallback in its JSON** — `DatasetInfo.id_fallback_used`
  exists on the dataclass but `diagnostics.dataset_summary` never emits it, and the JSON's
  `id_property` is only an echo of the argument. The warning goes to **stderr** (`io.py:15-23`).
  The runbook said to read the JSON field until 2026-08-15. Not fixed in code — the runbook now
  says to capture stderr — because changing the diagnostics schema the day before submission is a
  worse trade than documenting it.

## Safe development checks

```bash
conda activate mz-giscup-26
python -m compileall src tests scripts
python -m pytest -q
```

For CLI smoke tests, create/use a small synthetic GeoJSON before testing official-size data.
