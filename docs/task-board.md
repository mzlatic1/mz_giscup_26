# Task Board

Durable task list. `/startup` reads this and recreates the in-session task list from it.
Keep it current: when a task is finished, move it to **Done** with the date and the evidence.

Last updated: 2026-08-06.

## Critical path — nothing downstream matters until #4 passes

| # | Task | Blocked by |
|---|---|---|
| 1 | Switch default visibility strategy to `relate`; hoist `buffer(-eps)` out of the hot loop | — |
| 2 | **Build the radius-culled cached visibility matrix** | 1 |
| 3 | Calibrate cull radius conservatively; add an un-culled verification pass | 2 |
| 4 | **Re-run `/rehearsal` until the feasibility gate reads PASS** | 2, 3 |

## Unblocked — can start any time

| # | Task |
|---|---|
| 5 | Obtain the official sample dataset into `data/`; re-validate every measured claim |
| 7 | Make the validation path scale |
| 10 | Implement or remove unimplemented optimizer names and script placeholders |
| 11 | Resolve the hole-perimeter question against official rules |

## Gated on feasibility

| # | Task | Blocked by |
|---|---|---|
| 9 | Prune the candidate pool | 2 |
| 6 | Replace the greedy objective with a threshold-aware one | 4 |
| 8 | Full nine-block end-to-end dry run + submission audit | 4, 7 |

---

## Details

### 1 — Switch default visibility strategy to `relate`

Two free, semantics-preserving speedups in `src/giscup/visibility.py`.

**(a)** Change the default from `"hybrid"` to `"relate"` in `is_visible()`,
`solver.solve_one()`, `validate.validate_solution_file()`, and `cli.py`. Verified 2026-08-06:
`relate` and `hybrid` agree on all 9 official degeneracies (corner graze, collinear-along-edge,
single-vertex touch, interior crossing, self-blocking, adjacent same-edge points, boundary
endpoint rays inward and outward), and `relate` is ~2.5x faster.
`relate_pattern(poly, "T********")` is exactly the official predicate — interior-of-line meets
interior-of-polygon.

**(b)** `_blocked_negative_buffer` calls `polygon.buffer(-eps)` *inside the hot loop*. If the
strategy is kept as an option at all, precompute the eroded geometry once per building.

Add a test asserting relate/hybrid agreement across the degeneracy set so the default cannot
silently regress.

### 2 — Radius-culled cached visibility matrix  ← THE BLOCKER

Replace per-iteration recomputation with a matrix computed **once** and reused across all nine
subproblems. Two compounding effects, measured 2026-08-06:

1. A candidate's visible set never changes during greedy — only the union subtracted from it
   does. Caching removes the `k` factor entirely.
2. Throughput scales inversely with blockers per STRtree query, so restricting to short segments
   gives ~44x more throughput.

| segment length | blockers/query | checks/s |
|---|---|---|
| unbounded | 1,401 | 605 |
| ≤ 400 m | 21 | 17,951 |
| ≤ 200 m | 7 | 26,539 |

Use a spatial index over samples to enumerate only pairs within the cull radius. Store as bitsets
(`src/giscup/bitsets.py` exists but the optimizer never uses it). Key the cache on
dataset / candidate-set / sampling-profile / strategy / radius hashes so it can never be reused
across incompatible configurations.

Target from the gate: 200 m cull = 1.3e8 checks ≈ 10 min on 8 cores; 400 m = 5.2e8 ≈ 1 h.

### 3 — Calibrate the cull radius; add an un-culled verification pass

The cull is a heuristic that can silently discard genuinely visible pairs. Real street grids have
long unobstructed corridors; the synthetic stand-in has no real streets, so the measured
91–274 m visible range is very likely an **underestimate** of the real tail.

Under-culling loses score with no feedback to detect it. The budget has slack — 400 m costs ~1 h
of a 20 h window — so choose the radius **generously**, not at the measured p95.

Then add a verification pass that re-checks buildings near `tau` **without** the cull before they
are claimed, so the heuristic can never cause an overclaim. Report the coverage delta between
culled and un-culled results to bound the loss.

### 4 — Gate must read PASS

Currently **FAIL by ~5e8x**. Per `CLAUDE.md`, feasibility work outranks all solution-quality work
until this passes.

```bash
python scripts/rehearse.py --input outputs/synthetic_full.geojson --cores 8
```

The gate currently models cost analytically from measured throughput. Once the cached matrix
exists, extend it to time an **actual** full build rather than a projection, so the PASS is
observed rather than extrapolated. Record the passing configuration in `docs/session-state.md`.

### 5 — Official sample dataset

Released 2026-03-31, still absent locally. Every performance and sparsity figure in this repo is
measured against a synthetic stand-in with no real street topology and no large-building tail.
This is the single input that upgrades the analysis from well-founded to confirmed — and it
directly determines whether the radius chosen in #3 is safe.

On arrival: `giscup inspect` and compare against `docs/original_implementation_brief.md` §4
(12,860 buildings, 78,727 vertices, total perimeter 858,973 m, one hole-bearing polygon id 9448);
full CRS/topology/ID/anomaly report via the `geodata-qc` agent; re-run `/rehearsal` on real data
and correct any figure that moved.

`data/**` is write-denied for `Write`/`Edit` but **not** for shell writes — place the file
deliberately and let nothing overwrite it.

### 6 — Threshold-aware objective  (blocked on #4)

`optimize.greedy_select` scores `len(new_ids)` — raw newly visible sample count — and accepts
`tau` and `buildings` without using either. The scored quantity is serviced **building** count at
threshold `tau`. A building pushed 0.74 → 0.76 at `tau=0.75` is worth everything; one pushed
0.20 → 0.40 is worth nothing.

Reward newly serviced buildings, progress toward `tau`, and complementary near-threshold
coverage. Tune per `(tau, k)` — all nine subproblems are scored independently. See
`docs/reference/research-synthesis.md`: thresholded grouped service is **not** plain submodular
coverage, so lazy-greedy's correctness guarantee does not transfer unchanged.

### 7 — Make validation scale

Same complexity bug as the solver.

- `validate._visible_sample_ids_from_points` is samples × points: 138k × 1000 = 1.4e8 checks,
  ~11 h at `k=1000` on measured full-scale throughput. Reuse the cached matrix.
- `geometry.is_point_on_any_boundary` is a linear scan over all buildings — 1.3e7
  boundary-distance ops per run at `k=1000`, with an STRtree sitting unused.

With one shot and no feedback, validation is the only correctness signal that exists. It has to be
fast enough to run on all nine blocks inside the window.

### 8 — Nine-block dry run and submission audit  (blocked on #4, #7)

Produce all nine `(tau, k)` blocks end to end on full-scale data inside the wall-clock budget,
then audit with `submission-packager` against every item in
`.claude/skills/giscup-output-format/SKILL.md`: 9 blocks present and unduplicated, exactly three
lines each, exactly `k` coordinates **counted** not trusted from the header, all antennas within
eps of a boundary, 17 significant digits with no six-decimal rounding, every claimed ID present in
the source, all claims passing `validate-output --sampling-profile accurate` with a conservative
margin.

Time the whole run. **This must complete well before 2026-08-15** — that date is a rehearsal
deadline, not a start date.

### 9 — Prune the candidate pool  (blocked on #2)

160,198 candidates to choose at most 1,000 from is heavy overkill, and matrix cost is linear in
candidate count — an 8x prune is an 8x saving on the dominant cost.

Implement genuine pruning behind the existing mode names (`density`, `visibility_probe`,
`hybrid`). Today those modes only add **more** candidates via `edge_sample` and prune nothing,
which makes the names misleading. Prefer spatial diversity and high-visibility positions. Measure
the quality cost of each prune level against runtime saved; stop before quality degrades measurably.

### 10 — Unimplemented names and placeholders

Prevents a false capability claim at submission time.

- `lazy-greedy`, `stochastic-greedy`, `hybrid` appear in configs and CLI help but only `greedy`
  exists (`solver.solve_one` correctly raises). Implement or remove the names.
- `scripts/compare_configs.py` and `scripts/profile_visibility.py` are placeholders — implement or
  delete. `optimization-experimenter` is currently told to flag rather than run them.
- `configs/defaults.yaml` is not wired into the CLI at all.

### 11 — Hole perimeter question

`sampling.py` includes interior rings, so the coverage denominator uses `polygon.length` including
hole perimeter — but `candidates.py` generates candidates only from `exterior_edges`. For the one
hole-bearing polygon (id 9448) coverage is structurally **underestimated**. That is the safe
direction and it is deliberate, but it costs a building if the official evaluator uses
exterior-only perimeter.

The official page says footprints have no holes while the sample contains one — the sources
disagree. Check for an official clarification; absent one, keep the conservative behaviour and
record the assumption explicitly in `docs/competition-reference.md`.

---

## Done

| Date | Task | Evidence |
|---|---|---|
| 2026-08-06 | Migrate Codex layer to Claude Code | `be6d66b` — 18 tests pass, all paths resolve |
| 2026-08-06 | Harden `.claude/settings.json` after security review | `6403ab6` — 3 findings fixed |
| 2026-08-06 | Full-scale synthetic dataset generator | `ee51eef` — `scripts/make_synthetic_dataset.py`, within a few % of every documented statistic |
| 2026-08-06 | Feasibility gate | `ee51eef` — `scripts/rehearse.py` + `/rehearsal`; found the viable route on day 1 of 9 |
| 2026-08-06 | Encode ROGII lessons as rules and gates | `ee51eef` — `CLAUDE.md` posture section, agent rules, session memory |
