# Documentation Index

This folder is organized so future sessions consume a small, high-signal context set first, then
drill down only when needed. Run `/startup` to load the whole default set at once.

## Default startup read order

1. `docs/startup-brief.md` — compressed project state and rules.
2. `docs/competition-reference.md` — official GIS Cup constraints and scoring.
3. `docs/codebase-map.md` — repository structure, implemented features, commands, and known gaps.
4. `docs/session-state.md` — current environment, validation status, and the one thing that matters.
5. `docs/task-board.md` — the durable task list, with dependencies.
6. `docs/context-maintenance.md` — required read/update contract when ending a session or editing docs.

## Task-specific drill-down

- **Submission day (2026-08-15/16): `docs/submission-day-runbook.md`** — the operational sequence.
  Not a startup read; read it *on the day*, before touching the test extract. It carries the
  `--id-property` trap, the sizing sequence, and what to give up if the extract is bigger.
- Research/math/geography: `docs/research-synthesis-brief.md`
- Agent selection: `docs/agent-roles-brief.md`
- Full original onboarding source: `docs/original_implementation_brief.md`

## Required end-of-session update

At the end of every session, run `/wrapup` — it updates `docs/session-state.md` and any affected compact docs using `docs/context-maintenance.md`. Do not let code, test, research, agent, or rule changes remain only in chat history.

## Why this exists

`README.md` and `docs/original_implementation_brief.md` intentionally preserve extensive context. For routine sessions, read the compact docs above instead. They retain the same operational knowledge in a smaller form and point to the larger sources only when needed.
