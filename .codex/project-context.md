# Project Context — ACM SIGSPATIAL 2026 GIS Cup

## Repository Identity

- Repository name: `mz_giscup_26`
- Local root: `/home/markolinux/projects/sigspatial_26`
- GitHub remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Primary language: Python 3.11+
- Project type: geospatial computational geometry / optimization solver
- Compact startup document: `docs/codex-startup-brief.md`

## Scratch and External Context

- `/mnt/c/Users/marko/OneDrive/Documents/SIGSPATIAL_2026` is the project scratch folder.
- Refer to that path as the **OneDrive Parent Folder**.
- Treat OneDrive Parent Folder contents as competition notes, scratch outputs, datasets, packaging workspace, or transfer material.
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

1. Correct geometry and official-format output.
2. Robust line-of-sight visibility with boundary degeneracy tests.
3. Scalable approximate coverage using weighted boundary samples.
4. Candidate generation and pruning.
5. Greedy/lazy-greedy optimization.
6. Diagnostics and reproducibility.
7. Local search, adaptive refinement, and multi-start tuning.
