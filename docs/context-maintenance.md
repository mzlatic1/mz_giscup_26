# Codex Context Maintenance Contract

This file defines how project context is compressed, read, and maintained so future Codex sessions can consume less context while retaining the same operational knowledge.

## Beginning of every Codex session

Read the smallest useful context set first:

1. `AGENTS.md`
2. `docs/codex-startup-brief.md`
3. `docs/competition-reference.md`
4. `docs/codebase-map.md`
5. `docs/session-state.md`

Then drill down only if the task requires it:

- Research/math/geography: `docs/research-synthesis-brief.md`, then `.codex/research-papers.md` and `.codex/research-synthesis.md` if needed.
- Agent routing: `docs/agent-roles-brief.md`.
- Full preserved onboarding detail: `docs/original_implementation_brief.md`.
- Implementation/rules detail: `.codex/project-context.md`, `.codex/geometry-and-scoring-rules.md`, `.codex/development-workflow.md`, `.codex/repo-map.md`.

## End of every Codex session

Before final response, run a documentation-maintenance pass and update the compact docs when facts changed:

| If this changed | Update |
|---|---|
| Current status, latest tests, next steps, uncommitted state | `docs/session-state.md` |
| Project identity, source-of-truth order, major objective, agent routing, immediate priorities | `docs/codex-startup-brief.md` |
| Official competition rules, dates, format, scoring, or verified official clarifications | `docs/competition-reference.md` |
| File layout, implemented commands, tests, known limitations, validation status | `docs/codebase-map.md` |
| Research findings, source credibility, algorithmic implications | `docs/research-synthesis-brief.md` plus `.codex/research-papers.md` / `.codex/research-synthesis.md` when detail is needed |
| Agent roster, names, responsibilities, or QA/QC obligations | `docs/agent-roles-brief.md` plus `.agents/*.yaml` / `.codex/agents/*.md` |
| Documentation index or read-order rules | `docs/README.md` and this file |
| Persistent Codex-only implementation context | `.codex/session-handoff.md` and the relevant `.codex/*.md` file |

## Compression rules

- Keep `/docs` files compact, operational, and durable.
- Prefer bullets, tables, and explicit commands over narrative.
- Do not duplicate the long preserved brief unless a compact fact is needed for startup.
- Record only stable facts, latest verified validation status, and actionable next steps.
- Mark assumptions and heuristics clearly; official competition rules outrank repository notes.
- Keep archival/full-detail context in `README.md`, `docs/original_implementation_brief.md`, and `.codex/research-synthesis.md`.

## QA/QC rule

End-of-session QA/QC is not complete until:

1. Changed code/tests/config/docs are reflected in the appropriate compact `/docs` file.
2. The startup read order still points to valid files.
3. `docs/session-state.md` names the latest validation status and next recommended actions.
4. The final QA/QC pass yields no documentation changes.
