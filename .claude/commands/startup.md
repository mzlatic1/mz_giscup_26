---
description: Load the compact project context set and summarize state, open decisions, and a session todo list
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Read, Glob, Grep
---

# Session startup — mz_giscup_26

The compact context set is inlined below. Do **not** read `README.md` or
`docs/original_implementation_brief.md` — those are archival, and reading them at startup is the
exact waste this command exists to prevent.

## Compressed project state

@docs/startup-brief.md

## Official competition constraints

@docs/competition-reference.md

## Codebase map and known limitations

@docs/codebase-map.md

## State at end of last session

@docs/session-state.md

## Task board — the durable to-do list

@docs/task-board.md

## Live repository state

Working tree:

!`git status --short`

Recent commits:

!`git log --oneline -8`

## Your task

Using only what is above (drill into `docs/reference/` or source files only if something is
genuinely ambiguous):

1. **Recreate the task list.** Use `TaskCreate` for every open task in the task board above, in
   board order so IDs match, then `TaskUpdate` to restore the `blocked by` dependencies exactly as
   the board records them. Do not invent, merge, or reorder tasks — the board is authoritative.
   Skip anything under **Done**.

2. **Report current state** — 3-5 sentences. Where the solver actually is, not where the docs
   aspire for it to be. Distinguish committed work from uncommitted working-tree changes.

3. **Name the single next action** and say why it is first. If the feasibility gate has not read
   PASS, the answer is on the critical path and nothing else competes — a better objective on a
   solver that cannot finish scores zero. **As of 2026-08-09 the gate reads PASS with a complete,
   audited, packaged submission artifact on disk**, so the critical path is no longer feasibility;
   check `docs/session-state.md` for what actually remains.

4. **Flag missing context** — environment assumptions and unverifiable claims. Confirm
   `data/GIS-cup-sample-dataset.geojson` is present (it has been since 2026-08-08); the **test**
   dataset does not exist until 2026-08-15, and every solution-quality figure in the repo is
   fitted on the March sample.

5. **Report days remaining** until the 2026-08-15 test-data release, and treat that as a rehearsal
   deadline rather than a start date.

Flag any place where `docs/session-state.md` or `docs/task-board.md` appears stale relative to the
working tree. Then stop and wait — do not start work until Marko says what to do.
