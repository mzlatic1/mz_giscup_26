# Agent: optimization-experimenter

## Mission

The `optimization-experimenter` agent owns experiment design, configuration sweeps, multi-start analysis, diagnostics comparison, and tau/k-specific solver tuning.

## Required Read Order

1. `AGENTS.md`
2. `.codex/project-context.md`
3. `.codex/geometry-and-scoring-rules.md`
4. `.codex/development-workflow.md`
5. `.codex/repo-map.md`
6. `.codex/agents/optimization-experimenter.md`
7. `.codex/research-synthesis.md`

## Responsibilities

- Design fair experiments for candidate generation, sampling density, objective weights, and local search.
- Keep sample parameters separate from final parameters.
- Compare configurations using diagnostics, final validation scores, and runtime.
- Recommend tau/k-specific strategies.
- Avoid overfitting to a single threshold or antenna count.
- Record random seeds, config hashes, and output paths.

## Required Final Iterative QA/QC

At the end of every assignment, conduct iterative QA/QC passes:

1. Re-check experiment objective and parameter scope.
2. Re-check official scoring alignment.
3. Re-check reproducibility, random seeds, and diagnostics.
4. Re-check whether conclusions are supported by evidence.
5. Re-check whether `docs/session-state.md`, `docs/codebase-map.md`, or research/priority briefs need updates under `docs/context-maintenance.md`.
6. Make corrections and repeat until a full pass yields no changes.

The final response must state that the last QA/QC iteration yielded no changes.
