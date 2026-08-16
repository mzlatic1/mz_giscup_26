#!/usr/bin/env bash
#
# Detached liveness watchdog for a long solve.
#
#   setsid nohup env WATCH_PID=<pid> bash scripts/solve_watchdog.sh >/dev/null 2>&1 &
#
# WHY THIS EXISTS -- IT IS NOT A BACKGROUND TASK, AND THAT IS THE POINT
#
# On 2026-08-15 at 20:10:55 a session rotation killed every harness-owned
# background job within 4 ms of each other: the solve.log monitor, the
# solve-exit watcher, and a block-3 evaluator measurement that was ~16 min into
# a ~17 min run. All three output files end in "[killed]". The work was done
# and discarded, and nothing reported the loss.
#
# The solve itself (pid 86862, running 11 h at the time) was untouched, because
# it had been launched `nohup env ... giscup solve-all ... &` -- detached and
# reparented to init. Same machine, same night, opposite survival properties,
# and the only difference was ownership: harness-owned jobs die with their
# session, init-owned jobs do not.
#
#   Rule: anything that must outlive a session gets nohup'd to a file, not run
#   as a harness background task. A background job is fine for a 15-minute
#   measurement you are actively watching. It is the wrong tool for an
#   overnight watchdog.
#
# WHY IT EMITS A HEARTBEAT
#
# A bare `kill -0` loop is silent while the solve runs and silent if the
# watchdog itself dies -- the two are indistinguishable, which is the same
# ambiguity that makes `tail -F` a poor health check. A timestamped heartbeat
# resolves it, and carrying the last solve.log line in that heartbeat collapses
# two questions into one file:
#
#   stale timestamp                      -> the WATCHDOG died
#   fresh timestamp, unchanged progress  -> the SOLVE stalled
#   fresh timestamp, advancing progress  -> healthy
#
# Verify detachment after launching:  ps -o pid=,ppid=,sid= -p <watchdog pid>
# PPID should be init and SID should be the watchdog's own pid.

set -u

REPO="${REPO:-/home/markolinux/projects/sigspatial_26}"
PID="${WATCH_PID:?set WATCH_PID to the pid to watch}"
LOG="${WATCH_LOG:-$REPO/outputs/solve-watchdog.log}"
SOLVELOG="${WATCH_SOLVELOG:-$REPO/outputs/solve.log}"
INTERVAL="${WATCH_INTERVAL:-300}"

stamp() { date '+%F %T'; }

{
  echo "=================================================================="
  echo "[$(stamp)] watchdog armed on pid $PID  (detached; watchdog pid $$)"
  echo "[$(stamp)] heartbeat every ${INTERVAL}s -> this file"
} >> "$LOG"

while kill -0 "$PID" 2>/dev/null; do
    last=$(tail -n 1 "$SOLVELOG" 2>/dev/null | tr -s ' ' | sed 's/^ *//')
    echo "[$(stamp)] alive | $last" >> "$LOG"
    sleep "$INTERVAL"
done

{
  echo "=================================================================="
  echo "[$(stamp)] *** WATCHED PID $PID HAS EXITED ***"
  echo "final.txt   : $([ -f "$REPO/outputs/final.txt" ] && echo "PRESENT ($(wc -l < "$REPO/outputs/final.txt") lines)" || echo "ABSENT")"
  echo "final.json  : $([ -f "$REPO/outputs/final.json" ] && echo PRESENT || echo ABSENT)"
  echo "partial     : $(wc -l < "$REPO/outputs/final.txt.partial" 2>/dev/null || echo "gone (normal on success)")"
  echo "--- last 30 lines of the solve log ---"
  tail -n 30 "$SOLVELOG"
  echo "=================================================================="
} >> "$LOG"
