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

Known limitations — **rewritten 2026-08-09; the 2026-08-06 list here was badly stale**:

- Only `greedy` is implemented as a *search*; other optimizer names were removed 2026-08-08 (#10).
- **The shipped default objective is lever A (near-tau)** since 2026-08-09 (#15), via
  `--objective {near-tau,baseline}`. It wins eight of nine verified blocks and **loses
  `(0.5, 1000)` at every quantile**, so the shipped artifact is per-block best-of.
- A CLI solve **without `--visibility-radius` now fails**, because lever A exists only on the
  cached-matrix path. That is deliberate: a silent fallback to baseline would emit a structurally
  perfect file solved for a different problem.
- Candidate pruning **is** implemented (`--candidate-stride N`, #9), default 1. It is **not free**
  against lever A — −2.03% at `(0.75, 50)` — so treat it as a day-of contingency, not a win.
- The cull radius remains a heuristic. 400 m is settled (#3b); it discards ~9% of visibility, but
  verification re-measures near-threshold buildings at 800 m, so the buildings that decide the
  score already get the wide view.
- **Every solution-quality figure is fitted on the March sample.** August is a different extract.

**These four claims used to appear here and are all now FALSE:** that the gate reads FAIL by ~5e8x;
that the solver cannot finish a subproblem at full scale; that visibility is recomputed per greedy
iteration with no caching or cull; and that pruning modes prune nothing. The gate passes, a full
nine-block run takes ~2.85 h at `--verify-workers 12`, the cached matrix has existed since
2026-08-07, and the prune landed 2026-08-09.

## Current validation status

Run 2026-08-09 in the `mz-giscup-26` Conda environment. Full detail in `docs/session-state.md`.

```bash
python -m compileall -q src tests scripts   # OK
python -m pytest -q                         # 346 passed
giscup inspect --input data/GIS-cup-sample-dataset.geojson   # OK, EPSG:32611 preserved
python scripts/rehearse.py --input data/GIS-cup-sample-dataset.geojson \
    --cores 16 --measured-radius 400 --verify-workers 12   # PASS
```

Three nine-block artifacts exist and **all three audit clean, 0 overclaims**:
`outputs/nine_verifypar_400.txt` (baseline, 39,120 claims), `outputs/nine_leverA_400_full.txt`
(lever A, 42,556), and **`outputs/nine_bestof_400.txt` (per-block best-of, 42,728 — the submission
candidate)**.

**`data/` holds the official March sample** — `data/GIS-cup-sample-dataset.geojson` (6.3 MB,
git-ignored, obtained 2026-08-08). Every documented statistic matches exactly: 12,860 buildings,
78,727 exterior vertices, 858,973.22 m perimeter, 1 hole-bearing polygon, EPSG:32611. *(This
paragraph previously said `data/` was empty — false since 2026-08-08.)*

The synthetic stand-in from `scripts/make_synthetic_dataset.py` still exists and is still fine for
feasibility rehearsals, but it has no real street topology and omits the large-building tail.
**Never use it for solution-quality claims.** Test data does not exist until 2026-08-15.

## Fast command reference

```bash
conda activate mz-giscup-26
python -m pytest -q
python scripts/make_synthetic_dataset.py --output outputs/synthetic_full.geojson
python scripts/rehearse.py --input outputs/synthetic_full.geojson --cores 8
giscup inspect --input outputs/synthetic_full.geojson
```

Solve/validate commands take the same shape once a dataset exists; `/solve <tau> <k>` wraps them.
Do not run a full-scale solve until the feasibility gate passes — it will not finish.

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

**Authoritative list: `docs/task-board.md`.** Summary only below — if the two disagree, the
board wins.

Nothing below the critical path matters until the feasibility gate reads PASS. A better objective
on a solver that cannot finish scores zero.

1. **Critical path (#1-#4):** default strategy to `relate` -> radius-culled cached visibility
   matrix -> calibrate the cull conservatively -> `/rehearsal` reads PASS.
   The matrix (#2) is the blocker for the whole project.
2. **Unblocked now:** obtain the official sample dataset (#5); make validation scale (#7);
   clean up unimplemented names (#10); resolve the hole-perimeter question (#11).
3. **Gated on feasibility:** candidate pruning (#9), threshold-aware objective (#6), nine-block
   dry run and submission audit (#8).

## Deadline

Test dataset **2026-08-15**, submission due **2026-08-16** — roughly a 24-hour window. The
nine-subproblem solve pipeline must be automated and performance-proven before Aug 15.

## Session start / closeout

Say **"start session"** — that runs `/startup`, which loads this brief, the competition reference,
the codebase map, session state, and the task board, then recreates the task list.

## Session closeout rule

Run `/wrapup` before ending a session. It applies `docs/context-maintenance.md`, updates the compact docs that changed — especially `docs/session-state.md` — and repeats QA/QC until the final documentation pass yields no changes.
