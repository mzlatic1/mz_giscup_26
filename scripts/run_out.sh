#!/usr/bin/env bash
#
# UNATTENDED RUN-OUT — everything between "the solve finished" and "there is a zip to upload".
#
#   setsid nohup env SOLVE_PID=86862 bash scripts/run_out.sh >/dev/null 2>&1 &
#
# WHY THIS EXISTS
#
# The deadline is 2026-08-16 09:00 PDT. The solve finishes ~03:12 and the run-out chain
# costs ~2h45m, so the chain must run while the operator is ASLEEP. Starting it at wake-up
# (08:00) would finish at ~10:45, nearly two hours past the deadline. There is no version of
# this night where the post-solve work is done interactively.
#
# It is `nohup`'d and `setsid`'d for the reason recorded in scripts/solve_watchdog.sh: on
# 2026-08-15 at 20:10:55 a session rotation killed every harness-owned background job within
# 4 ms, including a measurement 16 minutes into a 17-minute run. Anything that must outlive a
# session cannot be owned by one.
#
# THE DESIGN RULE: NEVER LEAVE THE OPERATOR WITH NOTHING
#
# `set -e` is deliberately NOT used. A failure in stage 3 must not prevent stage 7 from
# packaging the artifact stage 1 already proved good. The script therefore packages a SAFETY
# bundle from the best available file BEFORE attempting any improvement, and only replaces it
# once a better file has passed the audit. At every instant after ~03:20 there is a valid,
# uploadable zip on disk.
#
# Quality ladder, best first:
#   1. final_bestof.txt  — nine blocks, k=9 best-of merged in, audited      (the goal)
#   2. final.txt         — nine blocks, all near-tau, as solved             (safe fallback)
#   3. final_filled.txt  — real blocks + structural filler for any missing  (last resort)
#
# READ THIS FILE AT WAKE-UP, NOT THE LOG:  outputs/RUN-OUT-STATUS.txt

set -u

REPO="${REPO:-/home/markolinux/projects/sigspatial_26}"
EVAL="${EVAL:-$HOME/projects/gis-cup-2026-evaluator}"
SOLVE_PID="${SOLVE_PID:?set SOLVE_PID to the running solve pid}"

LOG="$REPO/outputs/run-out.log"
STATUS="$REPO/outputs/RUN-OUT-STATUS.txt"

DS="data/GIS-cup-competition-dataset.geojson"
IDPROP="id"
TAUS="0.32 0.49 0.68"
KS="9 49 484"

# DRY_RUN=1 stubs the three expensive stages (k=9 re-solve, audit, evaluator) so the control
# flow, the status file and the packaging ladder can be exercised without loading the machine.
DRY_RUN="${DRY_RUN:-0}"

cd "$REPO" || exit 1
source "$HOME/miniconda3/etc/profile.d/conda.sh" && conda activate mz-giscup-26

# `pnpm` and `node` come from nvm, which is loaded by ~/.bashrc — and a detached,
# non-interactive shell never sources that. It happens to work by PATH inheritance from
# whatever launched this, but the evaluator stage runs at ~05:00 with nobody watching, so
# the path is pinned rather than inherited.
NVM_BIN="$HOME/.nvm/versions/node/v22.14.0/bin"
[ -d "$NVM_BIN" ] && case ":$PATH:" in *":$NVM_BIN:"*) ;; *) PATH="$NVM_BIN:$PATH" ;; esac
export PATH

stamp() { date '+%F %T'; }
log()   { echo "[$(stamp)] $*" >> "$LOG"; }
rule()  { echo "==================================================================" >> "$LOG"; }

# The single file a tired operator reads. Rewritten after every stage so it is never stale.
SHIP_FILE=""
SHIP_ZIP=""
SHIP_QUALITY="none"
declare -a NOTES=()

write_status() {
    {
        echo "=================================================================="
        echo " GIS CUP RUN-OUT STATUS      (regenerated $(stamp))"
        echo "=================================================================="
        echo ""
        if [ -n "$SHIP_ZIP" ] && [ -f "$SHIP_ZIP" ]; then
            echo "  >>> UPLOAD THIS FILE <<<"
            echo "  $SHIP_ZIP"
            echo "  ($(du -h "$SHIP_ZIP" | cut -f1), built from $(basename "$SHIP_FILE"), quality: $SHIP_QUALITY)"
        else
            echo "  !!! NO BUNDLE YET — see the stage list below !!!"
        fi
        echo ""
        echo "  Upload to: https://easychair.org/conferences/?conf=giscup2026"
        echo "  DEADLINE:  2026-08-16 09:00 PDT / 16:00 UTC"
        echo ""
        echo "------------------------------------------------------------------"
        echo " STAGES"
        echo "------------------------------------------------------------------"
        for n in "${NOTES[@]}"; do echo "  $n"; done
        echo ""
        echo "  Full log: $LOG"
        echo "=================================================================="
    } > "$STATUS"
}

note() { NOTES+=("$*"); write_status; }

# Package $1, and on success promote it to the thing we ship.
# Never demotes: a failed package leaves the previous winner in place.
package_as() {
    local src="$1" quality="$2"
    log "packaging $src  (quality: $quality)"
    if python scripts/package_submission.py --solution "$src" >> "$LOG" 2>&1; then
        local zip
        zip=$(ls -t "$REPO"/outputs/submission/*.zip 2>/dev/null | head -n 1)
        if [ -n "$zip" ]; then
            SHIP_FILE="$src"; SHIP_ZIP="$zip"; SHIP_QUALITY="$quality"
            note "PACKAGED  $(basename "$zip")  <- $(basename "$src")  [$quality]"
            return 0
        fi
    fi
    note "FAILED    packaging $(basename "$src") — previous bundle retained"
    return 1
}

rule
log "run-out armed; waiting on solve pid $SOLVE_PID"
note "WAITING   on solve pid $SOLVE_PID (started $(stamp))"

# HARD CUTOFF — Marko 2026-08-16 00:35, moving the drop-dead from 04:15 to 05:30.
# If the solve is still running then, it is killed and block 9 is filled from the partial.
# Projected finish is ~03:06, so this has ~2h24m of slack and should never fire. It exists so
# that a stalled solve cannot consume the audit and evaluator budget: killing at 05:30 leaves
# ~60 min audit + ~50 min evaluator, landing ~07:20, still ahead of an 08:00 wake-up.
HARD_CUTOFF="${HARD_CUTOFF:-05:30}"
CUTOFF_EPOCH=$(date -d "today $HARD_CUTOFF" +%s)
log "hard cutoff armed for $HARD_CUTOFF (epoch $CUTOFF_EPOCH)"

while kill -0 "$SOLVE_PID" 2>/dev/null; do
    if [ "$(date +%s)" -ge "$CUTOFF_EPOCH" ]; then
        note "CUTOFF    *** $HARD_CUTOFF reached, solve still running — stopping pid $SOLVE_PID ***"
        log "sending TERM to $SOLVE_PID"
        kill "$SOLVE_PID" 2>/dev/null
        sleep 30
        kill -0 "$SOLVE_PID" 2>/dev/null && { log "TERM ignored; sending KILL"; kill -9 "$SOLVE_PID" 2>/dev/null; }
        sleep 5
        break
    fi
    sleep 60
done

log "solve pid $SOLVE_PID is no longer running"
rule
sleep 20   # let the solver flush final.txt / final.json

# ---------------------------------------------------------------- stage 1: establish a base
BASE=""
if [ -f outputs/final.txt ] && [ "$(wc -l < outputs/final.txt)" -eq 27 ]; then
    BASE="outputs/final.txt"
    note "SOLVE     COMPLETE — final.txt has 27 lines (nine blocks)"
elif [ -f outputs/final.txt.partial ]; then
    n=$(wc -l < outputs/final.txt.partial)
    note "SOLVE     INCOMPLETE — partial has $n lines ($((n/3)) blocks); filling"
    log "running emergency_filler_blocks"
    if python scripts/emergency_filler_blocks.py --input "$DS" \
            --partial outputs/final.txt.partial --id-property "$IDPROP" \
            --taus $TAUS --ks $KS --output outputs/final_filled.txt --force >> "$LOG" 2>&1; then
        BASE="outputs/final_filled.txt"
        note "FILLED    final_filled.txt built from the partial"
    else
        note "FAILED    filler failed — MANUAL INTERVENTION REQUIRED"
    fi
else
    note "FAILED    no final.txt and no partial — MANUAL INTERVENTION REQUIRED"
fi

if [ -z "$BASE" ]; then
    log "no base file; nothing further can run"
    write_status
    exit 1
fi

# ------------------------------------------------------- stage 2: SAFETY bundle, immediately
# Before improving anything, make sure a valid zip exists. Everything after this point is
# upside; if the machine died right now the operator would still have something to upload.
package_as "$BASE" "safe fallback (unaudited, as solved)"

# package_submission.py names the zip by DATE, so a later successful package overwrites this
# one in place -- "previous bundle retained" would be a lie without a copy under a distinct
# name. This is the artifact that guarantees the operator wakes up to something uploadable
# even if every stage below fails.
if [ -n "$SHIP_ZIP" ] && [ -f "$SHIP_ZIP" ]; then
    cp -f "$SHIP_ZIP" "$REPO/outputs/submission/SAFETY_FALLBACK.zip" 2>>"$LOG" \
        && note "SAFETY    preserved as outputs/submission/SAFETY_FALLBACK.zip"
fi

# ------------------------------------------- stage 3: k=9 best-of (only from a complete solve)
BESTOF=""
if [ "$DRY_RUN" = "1" ]; then
    note "DRYRUN    skipped k=9 best-of"
elif [ "$BASE" = "outputs/final.txt" ]; then
    log "k=9 best-of re-solve, --objective baseline, against the cached matrix"
    if giscup solve-all --input "$DS" --id-property "$IDPROP" \
            --taus $TAUS --ks 9 --objective baseline \
            --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 8 \
            --verify-workers 12 --output outputs/k9_baseline.txt >> "$LOG" 2>&1; then
        note "BESTOF    k9_baseline.txt solved"

        # Report first (writes nothing) so the comparison is in the log for review.
        python scripts/pick_blocks.py --base outputs/final.txt --alt outputs/k9_baseline.txt \
            --taus $TAUS --ks $KS >> "$LOG" 2>&1

        if python scripts/pick_blocks.py --base outputs/final.txt --alt outputs/k9_baseline.txt \
                --taus $TAUS --ks $KS --take-alt 0.32,9 0.49,9 0.68,9 \
                --output outputs/final_bestof.txt --force >> "$LOG" 2>&1; then
            BESTOF="outputs/final_bestof.txt"
            note "MERGED    final_bestof.txt (k=9 from baseline, k=49/484 from near-tau)"
        else
            note "FAILED    merge failed — shipping near-tau final.txt unchanged"
        fi
    else
        note "FAILED    k=9 best-of re-solve failed — shipping near-tau final.txt unchanged"
    fi
else
    note "SKIPPED   k=9 best-of (base is not a complete solve)"
fi

# --------------------------------------------------------------- stage 4: audit what we ship
# Audit the MERGED file, not a predecessor of it (decided 2026-08-15 23:45).
run_audit() {   # run_audit <file>; rc 0 == passed
    log "auditing $1"
    python scripts/audit_submission.py --input "$DS" --solution "$1" \
        --taus $TAUS --ks $KS --exact-radius 400 --confirm-radius 800 \
        --workers 12 >> "$LOG" 2>&1
}

# Never START a ~60 min audit so late that it cannot finish before an 08:00 wake-up.
AUDIT_LATEST=$(date -d "today 06:45" +%s)

AUDIT_OK=0
AUDIT_TARGET="${BESTOF:-$BASE}"

if [ "$DRY_RUN" = "1" ]; then
    note "DRYRUN    skipped audit"
elif run_audit "$AUDIT_TARGET"; then
    AUDIT_OK=1
    note "AUDIT     PASSED (rc 0) on $(basename "$AUDIT_TARGET")"
    package_as "$AUDIT_TARGET" "AUDITED (preferred)"
else
    note "AUDIT     *** FAILED *** on $(basename "$AUDIT_TARGET")"
    # Marko 2026-08-16 00:35: on failure, retry WITHOUT the k=9 best-of, then re-audit;
    # keep "ship unaudited final.txt" as the backup if that fails too.
    #
    # Dropping all three k=9 swaps yields exactly `final.txt`, so the retry target IS the base
    # file — no re-merge is needed, and nothing has to guess which k=9 block was at fault.
    if [ -n "$BESTOF" ] && [ "$(date +%s)" -lt "$AUDIT_LATEST" ]; then
        note "RETRY     re-auditing $(basename "$BASE") with the k=9 best-of dropped"
        if run_audit "$BASE"; then
            AUDIT_OK=1
            # NOT a loss: dropping the best-of keeps the base file's own k=9 blocks. It gives up
            # only the *potential upside* of the baseline objective, which the audit just showed
            # was negative anyway. An earlier version of this string said "~470 claims given up",
            # which was simply wrong and alarming to read at 04:00.
            note "AUDIT     PASSED on $(basename "$BASE") — k=9 best-of dropped (its blocks overclaimed; no claims lost)"
            package_as "$BASE" "AUDITED, k=9 best-of dropped"
        else
            note "AUDIT     *** FAILED on $(basename "$BASE") TOO *** — shipping unaudited (approved backup)"
            package_as "$BASE" "UNAUDITED — both audits failed, REVIEW BEFORE UPLOAD"
        fi
    else
        note "RETRY     skipped (no best-of, or past the 06:45 guard) — shipping unaudited"
        package_as "$BASE" "UNAUDITED — audit failed, REVIEW BEFORE UPLOAD"
    fi
fi

# ------------------------------------------------------------ stage 6: official evaluator
# Verification, not a gate — it confirms what we already audited. Recorded for the operator.
SHIP_SRC="${SHIP_FILE:-$AUDIT_TARGET}"
log "official evaluator on $SHIP_SRC (all nine blocks, one process)"
if [ "$DRY_RUN" = "1" ]; then
    note "DRYRUN    skipped evaluator"
elif ( cd "$EVAL" && SCORE_DATASET="$REPO/$DS" \
        SCORE_SOLUTION="$REPO/$SHIP_SRC" \
        SCORE_SUMMARY="$REPO/outputs/official-score-final.json" \
        pnpm exec vitest run --config vitest.score.config.ts --reporter=verbose ) >> "$LOG" 2>&1; then
    note "EVALUATOR COMPLETED on $(basename "$SHIP_SRC") -> outputs/official-score-final.json"
else
    note "EVALUATOR did not exit clean — check the log; this does NOT block the upload"
fi

if [ -f "$REPO/outputs/official-score-final.json" ]; then
    python - <<'PY' >> "$LOG" 2>&1
import json, pathlib
p = pathlib.Path("outputs/official-score-final.json")
d = json.loads(p.read_text())
print("OFFICIAL SCORE SUMMARY:", json.dumps(d)[:2000])
PY
    note "SCORE     summary written to outputs/official-score-final.json"
fi

rule
log "run-out complete"
note "DONE      run-out finished at $(stamp)"
write_status
