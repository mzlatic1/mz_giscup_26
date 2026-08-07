# Development Workflow

## Default Local Checks

Run these before committing solver changes:

```bash
python -m compileall src tests scripts
PYTHONPATH=src python -m pytest -q
```

If the active Python environment lacks geospatial dependencies, use an existing suitable Conda environment or create the project environment from `environment.yml`.

## Recommended Environment

```bash
conda env create -f environment.yml
conda activate mz-giscup-26
python -m pip install -e .[dev]
```

Do not commit virtual environments, raw competition datasets, generated outputs, or visibility caches.

## CLI Smoke Tests

After dependencies are available:

```bash
python -m giscup.cli inspect --input data/GIS-cup-sample-dataset.geojson
python -m giscup.cli solve-one \
  --input data/GIS-cup-sample-dataset.geojson \
  --tau 0.25 \
  --k 50 \
  --output outputs/solution_tau_0.25_k_50.txt \
  --diagnostics outputs/diag_tau_0.25_k_50.json \
  --candidate-mode basic \
  --sampling-profile fast \
  --optimizer greedy \
  --max-candidates 1000
```

## Commit and Push Notes

When committing or pushing:

- Use detailed commit messages.
- Summarize what changed, what was validated, and recommended next steps.
- Do not stage unrelated files silently.
- Keep generated data and outputs out of Git unless explicitly requested.

## Required Documentation Maintenance

At the end of every session, before the final response (`/wrapup` performs these steps):

1. Read `docs/context-maintenance.md`.
2. Update `docs/session-state.md` with current validation status, working-tree status, and next recommended actions.
3. Update any affected compact docs:
   - `docs/startup-brief.md` for major project-state or priority changes.
   - `docs/competition-reference.md` for official-rule/date/format changes.
   - `docs/codebase-map.md` for layout, command, test, implementation, or limitation changes.
   - `docs/research-synthesis-brief.md` for research implications.
   - `docs/agent-roles-brief.md` for agent roster or role changes.
4. If durable reference context changed, update the relevant file under `docs/reference/`.
5. Repeat the documentation QA/QC pass until the final pass yields no changes.

## Phase Plan

1. Correctness foundation: IO, models, geometry, output format, validation.
2. Visibility and sampling: weighted samples, STRtree blocker index, official edge-case tests.
3. Baseline solver: candidates, greedy solve-one, validate-output.
4. Performance: bitsets, visibility cache, parallel precompute, pruning.
5. Competitive improvements: stochastic greedy, local search, adaptive refinement, multi-starts.
6. Final packaging: solve-all, official zip helper, diagnostics summaries.
