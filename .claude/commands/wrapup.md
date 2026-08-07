---
description: Run the end-of-session documentation-maintenance contract, iterating until a pass yields no changes
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(python -m pytest:*), Bash(python -m compileall:*), Read, Edit, Write, Glob, Grep
---

# Session wrap-up — mz_giscup_26

## The contract

@docs/context-maintenance.md

## What changed this session

!`git status --short || true; git status --porcelain | grep -q . || echo '(working tree clean)'`

!`git diff --stat HEAD || true; git diff --quiet HEAD && echo '(no uncommitted changes)'`

Commits this session:

!`git log --oneline -8`

## Your task

Apply the maintenance contract above. This is **iterative** — you are not done after one pass.

### Pass structure

1. **Tidy** — stop session-owned dev servers, note anything still running, remove temporary files
   this session created when safe. Do not delete user-created or ambiguous files.

2. **Update the compact docs** using the contract's mapping table. At minimum
   `docs/session-state.md` must reflect: current environment, latest validation status with the
   actual command output, working-tree state, recent applied fixes, and next recommended actions.
   Convert relative dates to absolute.

3. **Verify the read order still resolves** — every path referenced in `CLAUDE.md`,
   `docs/README.md`, `docs/startup-brief.md`, and `.claude/agents/*.md` must exist. A broken
   pointer silently degrades every future session.

4. **Re-run the pass.** If it produced any edit, run it again. Repeat until a full pass yields
   **no changes**.

### Honesty requirements

- Record the *actual* result of validation commands. If tests were not run this session, say so
  rather than carrying forward a stale "18 passed".
- Do not describe unimplemented optimizers (`lazy-greedy`, `stochastic-greedy`, `hybrid`) as
  working.
- Keep `docs/` compact and operational — bullets, tables, explicit commands. Long-form context
  belongs in `README.md`, `docs/original_implementation_brief.md`, and `docs/reference/`.

### Final output

Produce a closeout summary separating **completed work**, **remaining work**, **blockers**, and
**recommended next actions** — then state explicitly that the final documentation pass yielded no
changes.

Do **not** commit, push, archive, or delete anything without explicit approval from Marko.
