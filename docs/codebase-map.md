# Codebase Map and Implementation State

## Package layout

```text
src/giscup/
  models.py       # dataclasses for buildings, candidates, samples, solutions, dataset info
  io.py           # GeoJSON/geospatial loading via GeoPandas with fallback
  geometry.py     # boundary extraction, legality checks, bounds, segment lengths
  sampling.py     # weighted boundary samples, including interior rings by default
  candidates.py   # boundary-derived antenna candidates and dedupe
  visibility.py   # STRtree blocker index and LOS predicates
  coverage.py     # sampled coverage and serviced-building checks
  bitsets.py      # integer bitset abstraction (superseded by matrix.py; unused)
  exact_coverage.py # grid-free visible-interval coverage for claims/validation
  verify.py       # two-sided near-threshold re-verification
  matrix.py       # radius-culled cached visibility matrix (dense bitset, memmap, parallel)
  optimize.py     # greedy selection: predicate-based and matrix-backed
  solver.py       # solve-one orchestration
  output.py       # official formatting/parsing; exact-k guard
  validate.py     # solution validation and sampled claim coverage
  diagnostics.py  # dataset summary diagnostics
  cli.py          # inspect / solve-one / solve-all / validate-output
```

## Tests

```text
tests/test_antenna_placement.py  # emitted antennas never inside a footprint (#15)
tests/test_boundary_jitter.py    # THE invariant: a boundary point is visible from its boundary
tests/test_geometry.py
tests/test_projected_tolerances.py  # absolute tolerances at UTM magnitudes (#16)
tests/test_matrix.py             # matrix ground truth, cache keys, parallel==serial
tests/test_optimize_matrix.py    # matrix greedy == predicate greedy
tests/test_output_format.py
tests/test_sampling.py
tests/test_solver.py
tests/test_solver_matrix.py      # solve_one fast path, cross-subproblem reuse
tests/test_validate.py
tests/test_exact_coverage.py     # grid-free coverage vs analytic + brute-force truth
tests/test_validate_scaling.py   # BoundaryIndex + culled scan equivalence
tests/test_verify.py             # two-sided band selection, recover/drop
tests/test_visibility.py
tests/test_visibility_strategy.py  # official predicate, degeneracies, relate default
```

Current latest result: `145 passed` in Conda env `mz-giscup-26` (2026-08-08).

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
scripts/build_matrix.py            # build/reuse the visibility matrix at full scale
```

`data/` has no official dataset yet, so all scaling work runs against the synthetic
stand-in. It reproduces documented aggregate statistics only — no real street
topology, and the large-building tail is absent. Never use it for solution-quality
claims.

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
    --verify-band 0.10 --verify-max-buildings 2000 --output <txt>
giscup validate-output --input <geojson> --solution <txt>
```

`--verify-band` re-measures buildings near `tau` with exact interval coverage, recovering ones the
cull forfeited and dropping ones the sampled grid inflated. `validate-output` checks claims
exactly by default (`exact_claims`), so it needs no profile or radius.

Without `--visibility-radius` the solver recomputes visibility every greedy iteration and will
not finish at full scale. Culling only ever *removes* visible pairs, so it under-reports coverage:
safe for validation (rejects, never wrongly accepts) but a silent score loss for the solver.

Currently implemented solver optimizer: **`greedy` only**. The other optimizer names were
deleted 2026-08-08 (#10) rather than left as roadmap markers, so there is nothing to imply.

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

- Greedy objective is still raw newly visible sample count, not serviced-building count (task #6).
- Candidate pruning modes only add candidates; they prune nothing (task #9).
- The cull radius is a heuristic: it discards genuinely visible pairs beyond the radius and loses
  score with no feedback. The near-threshold verification pass exists (#3a) and now re-measures at
  a **wider** radius than the solver's cull. The 400 m vs 800 m comparison (#3b) is unresolved —
  both matrices must be rebuilt post-#14.
- **Geometry tolerances are load-bearing.** `visibility.INTERIOR_TOLERANCE` (1e-6 m),
  `geometry.COINCIDENT_POINT_TOLERANCE` (1e-9 m) and
  `exact_coverage.DEGENERATE_EDGE_LENGTH` (1e-9 m) are all ABSOLUTE, in CRS units, and each exists
  because a relative or too-fine tolerance produced a real bug. Never loosen or relativise them
  without reading `CLAUDE.md` Geospatial rules first.
- Greedy still optimizes on the sampled matrix. That is deliberate — it is a search heuristic, not
  the scored quantity — but it means the objective and the claim decision measure different things.
- No official dataset: every figure is measured against the synthetic stand-in (#5).

## Resolved since 2026-08-07

- Visibility precomputation/cache: **implemented** (`matrix.py`, task #2).
- Exact interval coverage backs claims and validation (`exact_coverage.py`, task #13).
- Dead names removed (task #10): `negative_buffer`/`hybrid` strategies, the unimplemented
  optimizer names, `scripts/compare_configs.py`, `scripts/profile_visibility.py`,
  `configs/defaults.yaml`. `relate` is now the only visibility strategy.
- Bitset acceleration in the optimizer: **implemented** (`optimize.greedy_select_matrix`).
- Validation scaling: **implemented** (`geometry.BoundaryIndex`, `validate.visible_sample_ids_from_points`).

## Safe development checks

```bash
conda activate mz-giscup-26
python -m compileall src tests scripts
python -m pytest -q
```

For CLI smoke tests, create/use a small synthetic GeoJSON before testing official-size data.
