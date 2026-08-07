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

## Live repository state

Working tree:

!`git status --short`

Recent commits:

!`git log --oneline -8`

## Your task

Using only what is above (drill into `docs/reference/` or source files only if something is
genuinely ambiguous), produce:

1. **Current state** — 3-5 sentences. Where the solver actually is, not where the docs aspire for
   it to be. Distinguish committed work from uncommitted working-tree changes.
2. **Open decisions** — anything the last session left unresolved, and anything the docs and the
   working tree disagree about.
3. **Session todo list** — concrete next actions in priority order, drawn from the recorded next
   steps but re-ranked against what is actually blocking progress now.
4. **Missing context** — absent datasets, credentials, environment assumptions, or unverifiable
   claims. Call out explicitly if `data/` still lacks the official sample dataset, since most
   meaningful work is blocked on it.

Flag any place where `docs/session-state.md` appears stale relative to the working tree.
