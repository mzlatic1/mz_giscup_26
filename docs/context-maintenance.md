# Context Maintenance Contract

This file defines how project context is compressed, read, and maintained so future sessions
consume less context while retaining the same operational knowledge.

Run `/startup` at session start and `/wrapup` at session end — those commands implement this
contract. The prose below is the specification they follow.

## Beginning of every session

Read the smallest useful context set first:

1. `CLAUDE.md` (auto-loaded)
2. `docs/startup-brief.md`
3. `docs/competition-reference.md`
4. `docs/codebase-map.md`
5. `docs/session-state.md`

Then drill down only if the task requires it:

- Research/math/geography: `docs/research-synthesis-brief.md`, then
  `docs/reference/research-papers.md` and `docs/reference/research-synthesis.md` if needed.
- Agent routing: `docs/agent-roles-brief.md`.
- Full preserved onboarding detail: `docs/original_implementation_brief.md`.
- Implementation/rules detail: `docs/reference/project-context.md`,
  `docs/reference/geometry-and-scoring-rules.md`, `docs/reference/development-workflow.md`.

## End of every session

Before the final response, run a documentation-maintenance pass and update the compact docs
wherever facts changed:

| If this changed | Update |
|---|---|
| Current status, latest tests, next steps, uncommitted state | `docs/session-state.md` |
| Project identity, source-of-truth order, major objective, agent routing, immediate priorities | `docs/startup-brief.md` |
| Official competition rules, dates, format, scoring, or verified official clarifications | `docs/competition-reference.md` |
| File layout, implemented commands, tests, known limitations, validation status | `docs/codebase-map.md` |
| Research findings, source credibility, algorithmic implications | `docs/research-synthesis-brief.md` plus `docs/reference/research-papers.md` / `docs/reference/research-synthesis.md` when detail is needed |
| Agent roster, names, responsibilities, or QA/QC obligations | `docs/agent-roles-brief.md` plus `.claude/agents/*.md` |
| Non-negotiable output-format rules | `.claude/skills/giscup-output-format/SKILL.md` |
| Session rituals, permissions, or hook behavior | `.claude/commands/*.md`, `.claude/settings.json` |
| Documentation index or read-order rules | `docs/README.md` and this file |

## Compression rules

- Keep `docs/` files compact, operational, and durable.
- Prefer bullets, tables, and explicit commands over narrative.
- Do not duplicate the long preserved brief unless a compact fact is needed at startup.
- Record only stable facts, latest verified validation status, and actionable next steps.
- Mark assumptions and heuristics clearly; official competition rules outrank repository notes.
- Keep archival/full-detail context in `README.md`, `docs/original_implementation_brief.md`, and
  `docs/reference/research-synthesis.md`.
- Convert relative dates to absolute.

## QA/QC rule

End-of-session QA/QC is not complete until:

1. Changed code, tests, config, and docs are reflected in the appropriate compact `docs/` file.
2. The startup read order still points to files that exist — including every path referenced by
   `CLAUDE.md`, `.claude/agents/*.md`, and `.claude/commands/*.md`.
3. `docs/session-state.md` names the latest validation status and next recommended actions, with
   the *actual* result of commands run this session rather than a carried-forward figure.
4. The final QA/QC pass yields no documentation changes.
