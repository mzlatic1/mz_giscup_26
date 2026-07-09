# Session Handoff

## Current Baseline Status

- Repository scaffold created and pushed to GitHub on `main`.
- Current initial commit: `050f95a Initialize mz_giscup_26 GIS Cup solver repository`.
- GitHub remote: `https://github.com/mzlatic1/mz_giscup_26.git`.
- The detailed README includes the preserved implementation brief and project-specific structure/usage documentation.
- Project-local Codex guidance files have been added under `.codex/`.
- Project agent `geospatial-scientist` has been added under `.agents/geospatial-scientist.yaml`.
- Project agent `geosoft-engineer` has been added under `.agents/geosoft-engineer.yaml`.
- Project agent `geospft-critique` has been added under `.agents/geospft-critique.yaml`.
- Project agent `web-searcher` has been added under `.agents/web-searcher.yaml`.
- Project agent `performance-engineer` has been added under `.agents/performance-engineer.yaml`.
- Project agent `submission-packager` has been added under `.agents/submission-packager.yaml`.
- Project agent `geodata-qc` has been added under `.agents/geodata-qc.yaml`.
- Project agent `optimization-experimenter` has been added under `.agents/optimization-experimenter.yaml`.
- Research registry and durable synthesis files:
  - `.codex/research-papers.md`
  - `.codex/research-synthesis.md`
- Compact startup and context-maintenance docs now live in `/docs`:
  - `docs/codex-startup-brief.md`
  - `docs/competition-reference.md`
  - `docs/codebase-map.md`
  - `docs/session-state.md`
  - `docs/context-maintenance.md`
  - task-specific briefs for research and agent routing

## Known Environment Status

- Base WSL Python 3.12 currently lacks project runtime/test dependencies such as Shapely, GeoPandas, NumPy, and pytest.
- A project Conda environment has been created:
  - name: `mz-giscup-26`
  - Python: 3.11
  - installed package: editable `mz-giscup-26==0.1.0`
  - key tested packages: Shapely, GeoPandas, pyogrio, NumPy, SciPy, pytest, bitarray, orjson
- Existing WSL Conda environments are present:
  - `linux_conda_env_v1`
  - `linux_conda_env_v2`
  - `rogii`
- Prefer using a project-specific `mz-giscup-26` Conda environment from `environment.yml` for future work.

## Latest Test Run

Completed in Conda environment `mz-giscup-26`:

```bash
python -m compileall src tests scripts
python -m pytest -q
giscup --help
giscup inspect --input /tmp/giscup_synthetic.geojson
giscup solve-one --input /tmp/giscup_synthetic.geojson --tau 0.25 --k 3 ...
giscup validate-output --input /tmp/giscup_synthetic.geojson --solution /tmp/giscup_solution.txt
giscup solve-all --input /tmp/giscup_synthetic.geojson --taus 0.25 0.5 --ks 1 2 ...
giscup validate-output --input /tmp/giscup_synthetic.geojson --solution /tmp/giscup_solution_all.txt
```

Results:

- Compile: passed.
- Unit tests: originally `12 passed`; after resynthesis and additional regression tests, `18 passed`.
- CLI help: passed.
- CLI inspect on synthetic GeoJSON: passed.
- CLI solve-one on synthetic GeoJSON: passed.
- CLI validate-output for solve-one: passed.
- CLI solve-all on synthetic GeoJSON: passed.
- CLI validate-output for solve-all: passed.

Issue found and fixed during testing:

- `validate-output` previously stripped empty lines, which broke parsing for valid solution blocks with an empty third line when no buildings were claimed.
- `src/giscup/validate.py` now preserves empty claimed-ID lines while skipping optional blank separators.
- Regression coverage added in `tests/test_validate.py`.

Additional resynthesis fixes applied:

- Solver now fails loudly rather than writing fewer than exactly `k` antennas.
- Output formatting rejects solutions whose point count does not match `k`.
- `validate-output` now advances on malformed headers and performs sampled claim validation.
- Boundary sampling now includes hole/interior rings so sample weights match Shapely `polygon.length`.
- The scaffold now rejects unimplemented optimizer modes instead of silently running plain greedy.
- Config examples now use the implemented `greedy` optimizer until lazy/stochastic/hybrid modes exist.
- Research registry now records source type, credibility/access notes, and read/access-limited status for the seed papers.
- Additional candidate references were added for robust predicates, visibility polygons, and foundational submodular maximization.
- New project agents were added for performance engineering, submission packaging, geodata QC, and optimization experiments.

Latest checks completed in `mz-giscup-26` after resynthesis:

```bash
python -m compileall src tests scripts
python -m pytest -q  # 18 passed
giscup inspect --input /tmp/giscup_synthetic.geojson
giscup solve-one ... && giscup validate-output ...
giscup solve-all ... && giscup validate-output ...
```

## Immediate Next Steps

1. Commit/push the Codex-specific files and validator regression fix.
2. Add the official sample dataset under `data/` when available locally.
3. Run `giscup inspect` against the official sample dataset and compare stats to the preserved brief.
4. Begin Phase 2/3 improvements: stronger visibility predicates, better candidate pruning, and scalable visibility caching.
5. Invoke `geospatial-scientist` for targeted literature synthesis before major algorithm-design changes.
6. Use `geosoft-engineer` for implementation and `geospft-critique` for independent QA before major commits.
7. Use `web-searcher` for credibility-aware internet/source discovery when user input calls for external research, including non-geospatial topics.
8. Use `performance-engineer`, `geodata-qc`, `optimization-experimenter`, and `submission-packager` for scalability, data QA, tuning, and final deliverable readiness respectively.

## Required Startup/Shutdown Context Rule

- New sessions should first read `AGENTS.md`, then the compact `/docs` startup set listed in `docs/README.md`.
- End every session by applying `docs/context-maintenance.md`:
  - update `docs/session-state.md`;
  - update any compact doc affected by code, test, research, agent, or rule changes;
  - keep long context in archival files instead of expanding startup docs;
  - repeat QA/QC until the final documentation pass yields no changes.
