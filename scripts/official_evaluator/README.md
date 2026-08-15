# Scoring a submission with the organisers' own evaluator

The GIS Cup organisers publish the scorer: **`https://github.com/alowe/gis-cup-2026-evaluator`**,
MIT licensed. It is the thing that decides the competition, so running our artifact through it is
the strongest pre-submission signal available — stronger than `scripts/audit_submission.py`, which
implements our *reading* of the rules rather than the rules themselves.

This directory holds the headless driver. It is two files and no dependencies of its own; it runs
inside a clone of the evaluator.

| file | what it is |
|---|---|
| `score.test.ts` | the driver — copy to `benchmarks/score.test.ts` in the clone |
| `vitest.score.config.ts` | copy to the clone root; same shape as the vendored benchmark config but with a 6 h timeout instead of 15 min |

## Why it is a vitest test and not a script

The evaluator is browser-*delivered*, not browser-*bound*. Its scoring core is plain TypeScript over
`@arcgis/core` and `rbush` — no DOM, no `Worker`, no `fetch` — so it runs perfectly well under Node.
The vendored `benchmarks/sample-full-evaluation.test.ts` already proves this; it reads geojson from
disk with `node:fs`.

**But it cannot run under bare `node`.** `src/core/constants.ts` opens with

```ts
import packageMetadata from "../../package.json";
```

which is a bare JSON import that needs the Vite transform. Run it through vitest and it works; run
it through `node` or `tsx` and it fails at import time. That is the whole reason for the config file.

## Setup

```bash
git clone https://github.com/alowe/gis-cup-2026-evaluator.git
cd gis-cup-2026-evaluator
pnpm install --frozen-lockfile
pnpm test                     # 73 tests, ~1 s -- confirm green before trusting anything it reports

cp <repo>/scripts/official_evaluator/score.test.ts benchmarks/
cp <repo>/scripts/official_evaluator/vitest.score.config.ts .
```

Needs Node and pnpm (measured with Node v22.14.0 / pnpm 11.16.0; `package.json` pins
`packageManager: pnpm@11.16.0`).

## Running it

```bash
SCORE_DATASET=/path/to/buildings.geojson \
SCORE_SOLUTION=/path/to/final.txt \
SCORE_SUMMARY=/path/to/official-score.json \
pnpm exec vitest run --config vitest.score.config.ts --reporter=verbose
```

| variable | meaning |
|---|---|
| `SCORE_DATASET` | required — the buildings geojson |
| `SCORE_SOLUTION` | required — our three-lines-per-subproblem solution file |
| `SCORE_SUMMARY` | optional — compact per-block JSON, **including the failed claim IDs**. This is the one you want. |
| `SCORE_REPORT` | optional — the full official `EvaluationReport`. One entry per claimed building, so it is large. |
| `SCORE_BLOCKS` | optional — 1-based block indices, e.g. `1,4,7`. **Run the `k=50` blocks first.** |
| `SCORE_FULL_DIAGNOSTIC` | optional — `1` forces complete perimeter computation. Much slower, and **does not change the score**. Only for diagnosing a specific building's coverage. |

Output goes to stdout as three tagged JSON blobs: `OFFICIAL_SCORER_DATASET`,
`OFFICIAL_SCORER_BLOCK` (one per block), and `OFFICIAL_SCORER_TOTAL`.

**Vitest buffers `console.log` until the test resolves**, so a long run shows nothing until it
finishes. Watch the worker process rather than the log if you need to confirm progress.

## Reading the result

The score is `sum(verifiedServiceScore)` over blocks — the evaluator has no aggregate field.

- **Their count equals ours** → confirmed. Proceed.
- **Theirs is lower** → we overclaim under the official predicate. `failedClaimIds` in the summary
  names exactly which buildings. This is the failure that silently costs score.
- **Theirs is higher** → impossible for the same claim set; if you see it, the harness is wrong.

## Things that surprised us, all confirmed by reading the source on 2026-08-15

- **Only *claimed* buildings are evaluated** (`evaluation-engine.ts`, `initializeEvaluationState`
  iterates `claims.uniqueKnownIds`). Unclaimed buildings are never checked, so overclaiming is the
  only way to lose points and underclaiming is silently free.
- **Boundary tolerance is `0.001` m** (`SPATIAL_TOLERANCE_METERS`), not the `1e-8`–`1e-7` this repo
  assumed. Within 1 mm an antenna is **snapped onto the boundary and accepted**; beyond it, dropped
  with `ANTENNA_OFF_BOUNDARY` — and it still counts against `k`. Our eps is far tighter, so passing
  our audit implies passing theirs.
- **The loader rejects holes outright** — `HOLES_NOT_ALLOWED`, "must contain exactly one ring and no
  holes". Our March sample fails to load for this reason (building 9448); the organisers' copy of
  the same sample has that hole removed. See the runbook's §2 stop condition.
- **Antennas past `k` are truncated, not rejected** — `antennas.slice(0, k)`, first-`k` wins, with
  no backfilling if an early one is invalid.
- **Unknown claimed IDs are a warning, not an error.** They are excluded and scoring continues, so
  an ID-field mistake looks like a quietly terrible score rather than a crash.
- **The visibility cache key embeds `tau:`** outside full-diagnostic mode, so an early-exit
  lower-bound result is never reused at a higher tau. Sharing one cache across our nine blocks is
  safe but useless — all nine antenna sets differ.

## Validation

Before trusting the driver on our own artifact, it was checked against every documented expected
result the repository ships:

- the six `datasets/ui-smoke/` fixtures — exact-tau pass, just-under fail, 0.0005 m snap accepted,
  0.002 m rejected, duplicate antennas/claims, and first-`k` truncation. These are covered by the
  vendored `src/core/ui-fixtures.test.ts`, which is inside the 73 that `pnpm test` runs;
- `datasets/GIS-cup-sample-submission.txt`, documented expected verified service score **`1`** —
  reproduced by this driver on 2026-08-15.
