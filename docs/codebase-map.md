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
  bitsets.py      # integer bitset abstraction
  optimize.py     # baseline greedy selection; future optimizer home
  solver.py       # solve-one orchestration
  output.py       # official formatting/parsing; exact-k guard
  validate.py     # solution validation and sampled claim coverage
  diagnostics.py  # dataset summary diagnostics
  cli.py          # inspect / solve-one / solve-all / validate-output
```

## Tests

```text
tests/test_geometry.py
tests/test_output_format.py
tests/test_sampling.py
tests/test_solver.py
tests/test_validate.py
tests/test_visibility.py
```

Current latest result: `18 passed` in Conda env `mz-giscup-26`.

## Compact documentation layer

```text
docs/startup-brief.md      # first-start compressed project memory
docs/competition-reference.md    # official constraints, format, dates, scoring
docs/codebase-map.md             # this file: package/commands/tests/limits
docs/session-state.md            # latest validation, environment, next steps
docs/context-maintenance.md      # mandatory startup/closeout docs-maintenance contract
docs/research-synthesis-brief.md # compact research digest
docs/agent-roles-brief.md        # compact agent routing
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
scripts/rehearse.py                # measures throughput/sparsity, PASS/FAIL vs budget
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

Currently implemented solver optimizer:

- `greedy` only.

Do not imply `lazy-greedy`, `stochastic-greedy`, or `hybrid` are implemented until code and tests exist.

## Important correctness fixes already applied

- `validate-output` preserves empty claimed-ID lines.
- Malformed validation headers no longer loop indefinitely.
- Formatter rejects solution blocks where number of points differs from `k`.
- Solver rejects `max_candidates < k` and candidate pools smaller than `k`.
- Validator performs sampled claim coverage checks.
- Sampling includes hole/interior rings so represented boundary weight matches Shapely perimeter.

## Known limitations

- Visibility precomputation/cache not implemented.
- Bitset acceleration not integrated into optimizer.
- Greedy objective is still raw newly visible sample count.
- Candidate pruning modes are preliminary.
- Config loading is not wired into CLI.
- `scripts/profile_visibility.py` and `scripts/compare_configs.py` are placeholders.
- Continuous coverage is approximated by weighted samples; final validation should be denser and conservative.

## Safe development checks

```bash
conda activate mz-giscup-26
python -m compileall src tests scripts
python -m pytest -q
```

For CLI smoke tests, create/use a small synthetic GeoJSON before testing official-size data.
