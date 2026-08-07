# Startup Brief — mz_giscup_26

Use this as the first project document in future sessions. It compresses the current state, rules, agents, codebase, and next steps.

## Project identity

- Project: `mz_giscup_26`
- Purpose: ACM SIGSPATIAL 2026 GIS Cup antenna-placement solver.
- Local root: `/home/markolinux/projects/sigspatial_26`
- GitHub remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Scratch folder / OneDrive Parent Folder: `/mnt/c/Users/marko/OneDrive/Documents/SIGSPATIAL_2026`
- Preserved full build brief: `docs/original_implementation_brief.md`
- Context maintenance rule: run `/startup` at session start and `/wrapup` at session end, per `docs/context-maintenance.md`.

## Source-of-truth hierarchy

1. Official GIS Cup page: `https://sigspatial2026.sigspatial.org/giscup.html`
2. Official/test dataset inspection
3. Repository docs and preserved original brief
4. Engineering judgment, clearly marked as heuristic or assumption

## Core competition objective

Given building footprints `B`, threshold `tau`, and antenna count `k`, output exactly `k` antenna points on building boundaries to maximize the number of buildings whose visible perimeter fraction is at least `tau`.

Final expected structure: one dataset, three `tau` values, three `k` values, and therefore nine independent subproblems.

## Non-negotiable competition constraints

- Output exactly `k` antenna points per subproblem.
- Every antenna must be on a building boundary.
- Visibility is blocked only by line-segment intersection with a building interior.
- Tangency, vertex contact, and boundary-only contact do not block visibility.
- Building coverage is visible boundary length divided by total perimeter.
- Coordinates must preserve IEEE-754 double precision; use 17 significant digits.
- Output format is three lines per subproblem: `(tau, k)`, coordinate list, claimed serviced IDs.

## Current implementation state

Implemented scaffold:

- IO and dataset inspection.
- Building/candidate/sample/solution dataclasses.
- Geometry helpers and boundary legality checks.
- Weighted boundary sampling.
- Boundary candidate generation.
- STRtree-backed visibility checks.
- Approximate sampled coverage.
- Baseline greedy solver.
- Official solution formatting and parsing.
- Output validation, including exact `k`, boundary legality, ID existence, and sampled claim validation.
- CLI: `inspect`, `solve-one`, `solve-all`, `validate-output`.
- Project Conda env: `mz-giscup-26`.

Known scaffold limitations:

- Only `greedy` optimizer is implemented. Lazy/stochastic/hybrid are roadmap items and should not be accepted silently.
- Current greedy objective is raw newly visible sample count, not the final shaped threshold objective.
- Visibility is recomputed directly and will not scale to final-size runs without caching/bitsets/pruning.
- Candidate modes are early-stage; density/visibility-probe/hybrid names need true pruning behavior later.
- `compare-configs` and profiling scripts are placeholders.

## Current validation status

Latest known checks in `mz-giscup-26` Conda environment:

```bash
python -m compileall src tests scripts
python -m pytest -q  # 18 passed
giscup inspect --input /tmp/giscup_synthetic.geojson
giscup solve-one ... && giscup validate-output ...
giscup solve-all ... && giscup validate-output ...
```

## Fast command reference

```bash
conda activate mz-giscup-26
python -m pytest -q
giscup inspect --input data/GIS-cup-sample-dataset.geojson
giscup solve-one --input data/GIS-cup-sample-dataset.geojson --tau 0.5 --k 500 --output outputs/solution_tau_0.5_k_500.txt --diagnostics outputs/diag_tau_0.5_k_500.json --candidate-mode basic --sampling-profile balanced --optimizer greedy
giscup validate-output --input data/GIS-cup-sample-dataset.geojson --solution outputs/solution_tau_0.5_k_500.txt --sampling-profile accurate
```

## Agent routing

- `geospatial-scientist`: research/math/geography synthesis.
- `geosoft-engineer`: implementation.
- `geospft-critique`: independent competition/code critique.
- `web-searcher`: credibility-aware internet research beyond geospatial topics too.
- `performance-engineer`: profiling, cache, bitsets, parallelism.
- `geodata-qc`: dataset inspection and anomaly reports.
- `optimization-experimenter`: experiments, multi-starts, diagnostics comparison.
- `submission-packager`: final zip/output/run-instruction readiness.

All agents must end with iterative QA/QC until the final pass yields no changes.

## Immediate next priorities

1. Add the official sample dataset under `data/` — released 2026-03-31, still absent locally.
   Most remaining work is blocked on it.
2. Run `giscup inspect` on the sample and compare with documented stats (`geodata-qc`).
3. Improve visibility performance: cache, bitsets, candidate pruning (`performance-engineer`).
4. Replace the raw-sample greedy objective with a threshold-aware weighted objective — the scored
   quantity is serviced-building count, not visible perimeter.
5. Add true lazy/stochastic greedy and local search.
6. Build the final packaging/audit workflow (`submission-packager`).

## Deadline

Test dataset **2026-08-15**, submission due **2026-08-16** — roughly a 24-hour window. The
nine-subproblem solve pipeline must be automated and performance-proven before Aug 15.

## Session closeout rule

Run `/wrapup` before ending a session. It applies `docs/context-maintenance.md`, updates the compact docs that changed — especially `docs/session-state.md` — and repeats QA/QC until the final documentation pass yields no changes.
