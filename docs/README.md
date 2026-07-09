# Documentation Index for Fast Codex Startup

This folder is organized so future Codex sessions can consume a small, high-signal context set first, then drill down only when needed.

## Default startup read order

1. `docs/codex-startup-brief.md` — compressed project state and rules.
2. `docs/competition-reference.md` — official GIS Cup constraints and scoring.
3. `docs/codebase-map.md` — repository structure, implemented features, commands, and known gaps.
4. `docs/session-state.md` — current environment, validation status, and next steps.
5. `docs/context-maintenance.md` — required read/update contract when ending a session or editing docs.

## Task-specific drill-down

- Research/math/geography: `docs/research-synthesis-brief.md`
- Agent selection: `docs/agent-roles-brief.md`
- Full original onboarding source: `docs/original_implementation_brief.md`

## Required end-of-session update

At the end of every Codex session, update `docs/session-state.md` and any affected compact docs using `docs/context-maintenance.md`. Do not let code, test, research, agent, or rule changes remain only in chat history.

## Why this exists

`README.md` and `docs/original_implementation_brief.md` intentionally preserve extensive context. For routine sessions, read the compact docs above instead. They retain the same operational knowledge in a smaller form and point to the larger sources only when needed.
