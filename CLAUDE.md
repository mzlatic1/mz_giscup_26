# mz_giscup_26 — ACM SIGSPATIAL 2026 GIS Cup

Antenna-placement solver. Place exactly `k` points on building boundaries to maximize the
number of buildings whose visible perimeter fraction is `>= tau`.

- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Scratch / **OneDrive Parent Folder**: `/mnt/c/Users/marko/OneDrive/Documents/SIGSPATIAL_2026`
  (competition notes, datasets, scratch outputs, packaging workspace)

## Source-of-truth order

When facts conflict, resolve in this order. Never let a lower tier override a higher one.

1. Official page — `https://sigspatial2026.sigspatial.org/giscup.html`
2. Inspection of the official/test dataset
3. Repository docs (`docs/`) and `docs/original_implementation_brief.md`
4. Engineering judgment — always label it as an assumption or heuristic

## Non-negotiable competition constraints

These are scored. Getting one wrong invalidates a submission block.

- Output **exactly** `k` antenna points per subproblem. Not fewer, not more. Extra points are
  **truncated to the first `k`**, not rejected — and an invalid early point is not backfilled.
- Every antenna must lie on a building boundary (`polygon.boundary.distance(pt) <= eps`, eps `1e-8`–`1e-7`).
  **The official bar is looser: `0.001` m** (evaluator `SPATIAL_TOLERANCE_METERS`, read 2026-08-15).
  Within 1 mm an antenna is *snapped onto the boundary and accepted*; beyond it, dropped while still
  counting against `k`. **Keep our eps tight** — passing at `1e-7` implies passing at `1e-3`, and
  relaxing to match buys nothing.
- Visibility is blocked **only** by a segment intersecting a building *interior*. Tangency,
  vertex contact, and boundary-only contact do **not** block.
- Building coverage = visible boundary length / total perimeter. Serviced when `>= tau`.
- Emit coordinates with `format(x, ".17g")`. Never round to six decimals. Never reproject,
  snap, or normalize final output.
- Output is three lines per subproblem: `(tau, k)`, coordinate list, claimed serviced IDs.
  The third line may be empty but must still exist.

- The `(tau, k)` grid is **published data**, not a constant: the dataset ships
  `competition-parameters.txt`. Nothing hardcodes the nine — `giscup.assemble.subproblem_grid` is
  the single source and every entry point takes `--taus`/`--ks`.

**The official evaluator is source-available and runnable here**: `github.com/alowe/gis-cup-2026-evaluator`
(MIT). It runs headless under vitest — `scripts/official_evaluator/README.md`. Where it disagrees
with our reading of the rules, it wins; it is what assigns the score. Its loader **rejects
hole-bearing polygons** (`HOLES_NOT_ALLOWED`), and it evaluates **only the buildings you claim**.

Full detail: `docs/reference/geometry-and-scoring-rules.md`, `docs/competition-reference.md`.

## Geospatial rules

- **Every geometric tolerance must be ABSOLUTE, in CRS units. Never relative, never below
  float64 resolution.** Coordinates here are ~5e5 easting and ~3.7e6 northing, where one ULP is
  ~6e-11 m and ~5e-10 m. Consequences, all of which actually happened on 2026-08-08:
  - `np.allclose`/`np.isclose` default to `rtol=1e-5`, which is **37 metres** at 3.7e6. It
    declared 16 m edges zero-length, and would call a 37 m ring gap "closed".
  - `buffer(-1e-9)` collapsed whole footprints to empty, because 1e-9 is below float64
    relative precision there. `buffer(-1e-6)` is correct.
  - Interpolated points (`p0 + t*(p1-p0)`, `(p0+p1)/2`) land an ULP off the true line and
    fall **inside** the polygon about half the time. Predicates must tolerate that; emitted
    antennas must be nudged out of it.

  Before writing any tolerance, ask what it equals in metres at 3.7e6. Test geometry at real
  projected magnitudes with irregular coordinates — unit-square tests cannot see any of this,
  and 122 of them passed while a third of the boundary was silently unseeable.
- Preserve CRS explicitly. Do **not** assume EPSG:4326 — the sample is EPSG:32611 (UTM 11N),
  but code must inspect the source data rather than hardcode.
- Preserve holes in loaded geometries and include them in obstacle geometry, even though the
  official page says footprints have none. Our copy of the sample contains one hole-bearing polygon
  (9448). **The official loader rejects such a dataset outright** (`HOLES_NOT_ALLOWED`, confirmed
  2026-08-15) and the organisers ship a de-holed copy of that same sample — so on the day,
  `holes_count > 0` is a stop-and-escalate, not a note. Keep the defensive handling: it is stricter
  than the official predicate, so it can only forfeit a claim, never create an overclaim.
- Never overwrite source data. Derived output goes under `outputs/` or a named scratch path.
  `.claude/settings.json` denies `Write`/`Edit` on `data/**`, but that guard covers only those two
  tools — a shell redirect, `cp`, or a `--output data/...` flag can still write there. Treat the
  deny rule as a backstop, not a guarantee; the rule you actually follow is this bullet.

## Competition posture — read before choosing what to work on

**One submission. No score feedback. Ever.** Test data 2026-08-15, deadline
2026-08-16. There is no leaderboard, no daily slots, no partial score, no retry.
Scoring is relative (`team score / best submitted score`, summed over 9 subproblems),
so a subproblem that does not finish scores ~0.

These rules exist because the ROGII Kaggle competition was lost to exactly these
mistakes (top 20%, no medal, gap 3x the range of every lever being tuned):

1. **Prove feasibility before improving quality.** Run `/rehearsal`. Until it reads
   PASS, feasibility work outranks everything else. A better objective on a solver
   that cannot finish scores zero. **Status: the gate read FAIL by ~5e8x on
   2026-08-06 and has read PASS since 2026-08-07.** A real nine-block run measured
   2.85 h at `--verify-workers 12` (2026-08-09), so feasibility is no longer the
   binding constraint — do not cite it to defer quality work. A PASS is only as
   current as its last run; re-run the gate whenever solver code changes.
2. **Size a lever against the gap before investing in it.** State the lever's
   best-case range and compare it to the distance you need to cover. ROGII spent
   three sessions tuning a knob whose entire range was 1/16 of the gap. If the
   best case cannot close the gap, it is the wrong lever — say so and stop.
3. **Treat 2026-08-15 as a rehearsal deadline, not a start date.** Anything not
   proven end-to-end at full scale before then will not work on the day.
4. **Every performance constant must be measured, not assumed.** Extrapolating
   from a small test case is how the sparsity figure in this project was wrong by
   190x and the throughput figure by 11x. Re-measure at full scale; state the
   sample size when the estimate is noisy.
5. **Local validation is a rejection framework, not a score estimator.** It can
   tell you something is broken. It cannot tell you what you will score.

## Honesty about implementation state

Only the `greedy` **search** exists. Do not describe `lazy-greedy`, `stochastic-greedy`, or
`hybrid` as implemented, and do not let a config silently fall back — unimplemented modes must
raise. `docs/codebase-map.md` holds the current limitation list; keep it accurate.

The **objective** is a separate axis from the search, and both are implemented: `--objective
{near-tau,baseline}`, defaulting to **`near-tau` (lever A)** since 2026-08-09. Lever A wins eight
of nine verified blocks and loses `(0.5, 1000)` at every quantile, so the shipped artifact takes
baseline for that one block. `--objective baseline` is the escape hatch and is load-bearing —
do not remove it.

## Session contract

**When Marko says "start session"** — or "start", "begin session", "let's start", or anything
clearly meaning the same — that is a request to run the `/startup` command. Do it immediately,
before anything else, without asking for confirmation. `/startup` loads the compact context set,
reads `docs/task-board.md`, recreates the task list, and reports state plus next actions.

**When Marko says "resume"** — typically right after a `/clear` or `/compact`, so assume context
has been wiped — do this, in order, without asking for confirmation:

1. Read `docs/session-state.md` **first**. Its top section is a dated handoff block naming exactly
   where work stopped, what is running, and what is uncommitted. Then read `docs/task-board.md`,
   `docs/codebase-map.md`, and `docs/competition-reference.md`.
2. Check for live work before assuming the machine is idle: `git status --short`,
   `git log --oneline -5`, `git log origin/main..HEAD`, and `ps -eo pid,etime,cmd | grep giscup`.
   Long solves and audits are routinely left running across a clear; results land in `outputs/`,
   which is durable, while the background-shell IDs are not.
3. Report state in a few sentences, distinguishing committed from uncommitted.
4. **Output an updated list of unblocked todos**, split into work that needs no decision and work
   blocked on Marko. This list is the deliverable — "resume" is a request for it.

Do not start work off a "resume". Stop after the list and wait.

**When Marko says "wrap", "close out", "pause", or "hand off"** — run `/wrapup`. It applies
`docs/context-maintenance.md` and iterates until a documentation pass yields no changes. Work is
not done until that no-change pass is reported. Never commit, push, or delete during wrap-up
without explicit approval.

Manual equivalents, if a command is unavailable: read `docs/startup-brief.md`,
`docs/competition-reference.md`, `docs/codebase-map.md`, `docs/session-state.md`, and
`docs/task-board.md`. `README.md` and `docs/original_implementation_brief.md` are archival — not
startup reads. Run `/rehearsal` if solver code changed since the last gate run.

## Commands

```bash
conda activate mz-giscup-26
python -m pytest -q                 # 375 passing as of 2026-08-15 (368 before `ca55be7`, 365 before `de03785`)
python -m compileall src tests scripts
giscup inspect --input <geojson>          # RUN THIS FIRST on the day -- confirms the ID field
giscup solve-one  --input <geojson> --tau <float> --k <int> --output <txt> [--diagnostics <json>]
giscup solve-all  --input <geojson> --taus ... --ks ... --output <txt>
giscup validate-output --input <geojson> --solution <txt>
```

**A full-scale solve needs `--visibility-radius 400 --cache-dir outputs/cache` and
`--verify-workers 12`.** Without a radius the solver recomputes visibility every greedy iteration
and will not finish — and the default `near-tau` objective refuses to run at all. Serial
verification costs ~12 h of the window. Full command in `docs/startup-brief.md`.

Do not commit datasets, generated outputs, visibility caches, or environments.

## Subagents

Defined in `.claude/agents/`. Every agent ends with iterative QA/QC until a pass yields no
changes, then reports that no-change pass explicitly. Routing lives in `docs/agent-roles-brief.md`.
