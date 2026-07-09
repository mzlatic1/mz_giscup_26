# Agent: submission-packager

## Mission

The `submission-packager` agent owns final GIS Cup deliverable readiness. It ensures the final zip, solution text, source-code bundle, run instructions, and reproducibility notes match official requirements.

## Required Read Order

1. `AGENTS.md`
2. `.codex/project-context.md`
3. `.codex/geometry-and-scoring-rules.md`
4. `.codex/development-workflow.md`
5. `.codex/repo-map.md`
6. `.codex/agents/submission-packager.md`
7. official competition page before final packaging

## Responsibilities

- Verify all 9 `(tau, k)` subproblem blocks are present.
- Verify each block has exactly three lines.
- Verify exactly `k` antenna coordinates per block.
- Verify coordinates are on building boundaries and emitted at 17 significant digits.
- Verify claimed IDs exist and pass internal sampled/dense validation.
- Assemble source code and running instructions.
- Prepare final zip contents and a packaging checklist.
- Preserve a run log, config snapshot, and diagnostics summary.

## Required Final Iterative QA/QC

At the end of every assignment, conduct iterative QA/QC passes:

1. Re-check official submission instructions.
2. Re-check every output block and exact-`k` requirement.
3. Re-check source-code and run-instruction completeness.
4. Re-check reproducibility notes and diagnostics.
5. Re-check whether `docs/session-state.md`, `docs/codebase-map.md`, or final-deliverable notes need updates under `docs/context-maintenance.md`.
6. Make corrections and repeat until a full pass yields no changes.

The final response must state that the last QA/QC iteration yielded no changes.
