---
description: Feasibility gate — can the solver finish all nine subproblems inside the submission window?
argument-hint: [budget-hours] [cores]
allowed-tools: Bash(python scripts/rehearse.py:*), Bash(python scripts/make_synthetic_dataset.py:*), Bash(ls:*), Bash(nproc), Read, Glob
---

# Feasibility rehearsal

The GIS Cup gives **one submission and no score feedback**. Test data lands
2026-08-15, deadline 2026-08-16. There is no opportunity to discover on the day
that the pipeline cannot run — so it gets proven now, repeatedly, against a
full-scale stand-in.

Available data:

!`ls -la data/*.geojson outputs/*.geojson 2>/dev/null || echo "  none"`

Cores available:

!`nproc`

## Steps

1. **Ensure a full-scale dataset exists.** Prefer the official one under `data/`
   if present. Otherwise generate the synthetic stand-in:

   ```bash
   python scripts/make_synthetic_dataset.py --output outputs/synthetic_full.geojson
   ```

   Report which one you used. Never present synthetic results as official-data
   results.

2. **Run the gate** (budget defaults to 20 h; `$1` overrides, `$2` sets cores):

   ```bash
   python scripts/rehearse.py --input <dataset> --budget-hours ${1:-20} --cores ${2:-8}
   ```

3. **Report the verdict** and, if FAIL, the cheapest variant that fits and what
   stands between the current code and that variant.

## Reading the result

- **PASS** — the pipeline as written fits. Solution-quality work is now the
  priority.
- **FAIL with a viable route** — that route is the highest-priority work in the
  project. Nothing about objective shaping, candidate modes, or tuning matters
  until the gate reads PASS. A better objective on a solver that cannot finish
  scores zero.
- **FAIL with no viable route** — the architecture is wrong. Escalate; do not
  tune constants.

## Honesty requirements

- The visible-fraction estimate comes from a small probe and is **noisy**. If the
  script warns about hit count, treat the radius figure as indicative and choose
  a cull radius with margin, not the p95 as measured.
- A radius cull is a **heuristic that can discard genuinely visible pairs** —
  long unobstructed sight lines exist in real street grids and the synthetic
  stand-in has no real streets. Budget permitting, choose a generous radius, and
  verify near-threshold buildings without the cull before claiming them.
- The synthetic dataset reproduces documented aggregate statistics only. It has
  no real street topology and omits the large-building tail, so absolute
  visibility numbers will differ from the official data. Use it for feasibility
  and scaling, never for solution-quality claims.
