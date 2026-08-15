# Project Context — ACM SIGSPATIAL 2026 GIS Cup

## Repository Identity

- Repository name: `mz_giscup_26`
- GitHub remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Primary language: Python 3.11+
- Project type: geospatial computational geometry / optimization solver
- Compact startup document: `docs/startup-brief.md`

## Scratch and External Context

- An out-of-repository scratch folder holds competition notes, scratch outputs, datasets, packaging
  workspace, and transfer material. Its location is environment-specific and is set in the operator's
  local instructions rather than here.
- The original implementation brief is preserved in `docs/original_implementation_brief.md`.
- Routine sessions should prefer the compact docs in `docs/` before reading the large README or original brief.
- The compact `/docs` layer is maintained under the contract in `docs/context-maintenance.md`.
- At session start, read the compact `/docs` startup set before drilling into long-form sources.
- At session end, update `docs/session-state.md` and any affected compact docs so the next session can start without rereading full history.

## Source-of-Truth Order

When facts conflict, resolve them in this order:

1. Official competition page: `https://sigspatial2026.sigspatial.org/giscup.html`
2. Official/test dataset inspection
3. Repository documentation and preserved implementation brief
4. Engineering judgment, explicitly marked as an assumption or heuristic

## Competition Summary

The challenge is to place exactly `k` antenna points on building boundaries to maximize the number of buildings serviced at threshold `tau`. A building is serviced if the visible fraction of its perimeter is at least `tau`.

The final structure is expected to contain 9 independent subproblems from all combinations of 3 threshold values and 3 antenna counts.

## High-Level Engineering Priorities

This was the **original** priority ordering, written at project start and kept for provenance. Items
1–4 and 6 were built as described. Items 5 and 7 were not, and the difference is deliberate — see
`docs/codebase-map.md` for the authoritative implementation state.

1. Correct geometry and official-format output.
2. Robust line-of-sight visibility with boundary degeneracy tests.
3. Scalable approximate coverage using weighted boundary samples.
4. Candidate generation and pruning.
5. Greedy/lazy-greedy optimization. — **Only `greedy` was implemented.** `lazy-greedy`,
   `stochastic-greedy`, and `hybrid` were removed rather than left as dead configuration options;
   unimplemented modes raise instead of silently falling back.
6. Diagnostics and reproducibility.
7. Local search, adaptive refinement, and multi-start tuning. — **Not implemented.** Effort went to
   the objective function (`near-tau` vs `baseline`) and to proving full-scale feasibility instead.
