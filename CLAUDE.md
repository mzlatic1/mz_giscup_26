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

- Output **exactly** `k` antenna points per subproblem. Not fewer, not more.
- Every antenna must lie on a building boundary (`polygon.boundary.distance(pt) <= eps`, eps `1e-8`–`1e-7`).
- Visibility is blocked **only** by a segment intersecting a building *interior*. Tangency,
  vertex contact, and boundary-only contact do **not** block.
- Building coverage = visible boundary length / total perimeter. Serviced when `>= tau`.
- Emit coordinates with `format(x, ".17g")`. Never round to six decimals. Never reproject,
  snap, or normalize final output.
- Output is three lines per subproblem: `(tau, k)`, coordinate list, claimed serviced IDs.
  The third line may be empty but must still exist.

Full detail: `docs/reference/geometry-and-scoring-rules.md`, `docs/competition-reference.md`.

## Geospatial rules

- Preserve CRS explicitly. Do **not** assume EPSG:4326 — the sample is EPSG:32611 (UTM 11N),
  but code must inspect the source data rather than hardcode.
- Preserve holes in loaded geometries and include them in obstacle geometry, even though the
  official page says footprints have none. The sample contains one hole-bearing polygon.
- Never overwrite source data. Derived output goes under `outputs/` or a named scratch path.
  (`data/**` is write-denied in `.claude/settings.json`.)

## Honesty about implementation state

Only the `greedy` optimizer exists. Do not describe `lazy-greedy`, `stochastic-greedy`, or
`hybrid` as implemented, and do not let a config silently fall back to plain greedy — unimplemented
modes must raise. `docs/codebase-map.md` holds the current limitation list; keep it accurate.

## Session contract

- **Start:** run `/startup`, or read `docs/startup-brief.md`, `docs/competition-reference.md`,
  `docs/codebase-map.md`, and `docs/session-state.md` before drilling into long-form sources.
  `README.md` and `docs/original_implementation_brief.md` are archival, not startup reads.
- **End:** run `/wrapup`. It applies `docs/context-maintenance.md` and iterates until a
  documentation pass yields no changes. Work is not done until that no-change pass is reported.

## Commands

```bash
conda activate mz-giscup-26
python -m pytest -q                 # 18 passing as of last run
python -m compileall src tests scripts
giscup inspect --input <geojson>
giscup solve-one  --input <geojson> --tau <float> --k <int> --output <txt> [--diagnostics <json>]
giscup solve-all  --input <geojson> --taus ... --ks ... --output <txt>
giscup validate-output --input <geojson> --solution <txt> --sampling-profile accurate
```

Do not commit datasets, generated outputs, visibility caches, or environments.

## Subagents

Defined in `.claude/agents/`. Every agent ends with iterative QA/QC until a pass yields no
changes, then reports that no-change pass explicitly. Routing lives in `docs/agent-roles-brief.md`.
