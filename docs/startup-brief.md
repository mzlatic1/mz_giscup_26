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

**The pipeline is complete and has produced an audited submission artifact.** Implemented:

- IO, dataset inspection, geometry, boundary legality, weighted sampling, candidate generation.
- **Radius-culled cached visibility matrix** (`matrix.py`) — dense memmapped bitsets, parallel build.
- **Two greedy objectives**: baseline sample-count and **lever A near-tau (the default)**.
- **Per-building candidate prune** (`--candidate-stride`, off by default).
- **Grid-free exact interval coverage** backing claims and validation (`exact_coverage.py`).
- **Exhaustive parallel claim verification** plus banded recovery (`verify.py`).
- **Two-stage parallel overclaim audit** (`audit.py`), **partial-run assembly** (`assemble.py`),
  and **submission packaging** (`packaging.py`).
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

Run 2026-08-10 in the `mz-giscup-26` Conda environment. Full detail in `docs/session-state.md`.

```bash
python -m compileall -q src tests scripts   # OK
python -m pytest -q                         # 356 passed
giscup inspect --input data/GIS-cup-sample-dataset.geojson   # OK, EPSG:32611 preserved
python scripts/rehearse.py --input data/GIS-cup-sample-dataset.geojson \
    --cores 16 --measured-radius 400 --verify-workers 12   # PASS, 8.14 h bound / 2.5x
```

**The gate figure moved on 2026-08-10** from 6.87 h / 2.9x to **8.14 h / 2.5x**, because the gate
had been costing `baseline` while the solver ships `near-tau`. Nothing got slower; ~1.77 h of lever
A verification was not being counted. Still a comfortable PASS.

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
python -m pytest -q                 # 356 passed (2026-08-10)
giscup inspect --input data/GIS-cup-sample-dataset.geojson

# feasibility gate -- ALWAYS pass --verify-workers; serial puts the bound at 1.0x
python scripts/rehearse.py --input data/GIS-cup-sample-dataset.geojson \
    --cores 16 --measured-radius 400 --verify-workers 12

# a full nine-block solve (~2.85 h baseline, ~5 h lever A)
giscup solve-all --input data/GIS-cup-sample-dataset.geojson \
    --taus 0.25 0.5 0.75 --ks 50 500 1000 \
    --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 --verify-workers 12 \
    --output outputs/final.txt

# audit -- pass --exact-radius explicitly, and audit what you will ship
python scripts/audit_submission.py --input data/GIS-cup-sample-dataset.geojson \
    --solution outputs/final.txt --exact-radius 400 --confirm-radius 800 --workers 12
```

`--visibility-radius` is required: without it the solver recomputes visibility every greedy
iteration and will not finish at full scale, and the default lever A objective refuses to run.
`/solve <tau> <k>` wraps the single-subproblem case.

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

**Authoritative list: `docs/task-board.md`; current state: `docs/session-state.md`.** Summary only
below — if they disagree, the board and session-state win.

**REWRITTEN 2026-08-09. This section previously said the feasibility gate was the critical path and
listed #1-#5, #7, #10, #11 as open. All of those are DONE, and the gate has read PASS since
2026-08-07.**

The project is **past feasibility and past solution-quality selection**. A complete, audited,
packaged submission artifact exists (`outputs/nine_bestof_400.txt`, 42,728 claims, 0 overclaims) —
**for the March sample.** It proves the pipeline; it is not the deliverable.

**As of 2026-08-10 there is NO open decision and NO preparatory work left. The next session is
submission day.**

1. **Read `docs/submission-day-runbook.md` first**, before touching the extract, and follow it top
   to bottom rather than improvising from memory.
2. **Run `giscup inspect` before solving anything.** The `--id-property` fallback would make every
   claim reference a nonexistent building while passing every structural check, and the official
   page has never named the ID field.
3. **Get the submission link** — still unpublished as of 2026-08-10. Email fallbacks are in
   `docs/session-state.md`.
4. **Regenerate the bundle from the August solution.** The zip on disk is a March-sample bundle
   whose `source/` predates `3f381bb`. Do not ship it.

Settled and not to be re-litigated on the day: radius **400 m**, objective **`near-tau`**,
`--matrix-workers` **8**, `--verify-workers` **12**, `--candidate-stride` **1**.

**Reviewed 2026-08-10 — the "fold in the 7.3x uncontended speedup" item is CLOSED, not open.** It
is already in `gate_model` (`MEASURED_VERIFY_SPEEDUP_UNCONTENDED`, `verify_speedup(...,
contended=False)`, a third reporting row, four tests). Only the verdict deliberately still uses the
4.70x contention floor, and it should stay that way.

Optional, none of it on a critical path: re-measure anything whose constant was fitted under a
different configuration.

**Fixed 2026-08-10 while checking that:** `scripts/rehearse.py --objective` defaulted to `baseline`
while `giscup solve-all` defaulted to `near-tau` (#15), so the documented gate command costed a run
nobody would make — with the cheaper constant, hiding ~1.77 h on the bound. Both now read
`gate_model.DEFAULT_OBJECTIVE`, pinned by `tests/test_verify_workers_default.py`.

## Deadline

Test dataset **2026-08-15**, submission due **2026-08-16** — roughly a 24-hour window. The
nine-subproblem solve pipeline must be automated and performance-proven before Aug 15.

## Session start / closeout

Say **"start session"** — that runs `/startup`, which loads this brief, the competition reference,
the codebase map, session state, and the task board, then recreates the task list.

## Session closeout rule

Run `/wrapup` before ending a session. It applies `docs/context-maintenance.md`, updates the compact docs that changed — especially `docs/session-state.md` — and repeats QA/QC until the final documentation pass yields no changes.
