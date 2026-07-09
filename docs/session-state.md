# Current Session State

This document captures the current operational state so future sessions can avoid rereading long history.

## Repository

- Local root: `/home/markolinux/projects/sigspatial_26`
- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Main branch has initial scaffold pushed.
- Current working tree has uncommitted changes from agent/docs creation, resynthesis, and code fixes.

## Environment

Project Conda env exists:

```bash
conda activate mz-giscup-26
```

Known installed/tested stack:

- Python 3.11
- Shapely
- GeoPandas
- pyogrio
- NumPy
- SciPy
- pytest
- bitarray
- orjson
- editable `mz-giscup-26`

## Latest validation

Passed after docs/context-maintenance updates:

```bash
python -m compileall src tests scripts
python -m pytest -q  # 18 passed
```

Additional context QA passed: required compact docs exist, are non-empty, and all `.agents/*.yaml` prompts reference `docs/codex-startup-brief.md`, `docs/session-state.md`, and `docs/context-maintenance.md`.

Synthetic CLI smoke tests passed:

- `giscup inspect`
- `giscup solve-one` + `validate-output`
- `giscup solve-all` + `validate-output`

## Recent applied fixes

- Created compact `/docs` startup set.
- Added `docs/context-maintenance.md` and updated Codex rules so sessions read compact docs at startup and update `/docs` at closeout.
- Updated `AGENTS.md`, `.codex/*.md`, `.codex/agents/*.md`, `.agents/*.yaml`, root `README.md`, and compact docs to enforce `/docs` maintenance.
- Created/updated project agents.
- Added research registry/source credibility metadata.
- Fixed validator empty-line and malformed-header behavior.
- Added sampled claim validation.
- Enforced exact `k` in solver/output paths.
- Made unimplemented optimizers explicit errors.
- Made sampling include interior rings to match Shapely perimeter.
- Added tests for solver, validation, output formatting, and hole sampling.

## Next recommended actions

1. Review current uncommitted diff.
2. Commit and push with a detailed message when approved.
3. Add official sample dataset under `data/` when available locally.
4. Run `giscup inspect` and compare stats against the preserved brief.
5. Start Phase 2/3: visibility cache, bitsets, candidate pruning, threshold-aware greedy.
