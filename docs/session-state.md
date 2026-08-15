# Current Session State

Operational state so the next session starts without rereading history. Say **"start session"** and
`/startup` handles the rest.

**Scope of this file:** what is true *now* — environment, validation, artifacts, next actions.
Detailed findings and their reasoning live in `docs/task-board.md`; the narrative of how each was
reached lives in commit messages, which are long and specific by design. Compressed from 693 lines
on 2026-08-09; nothing unique was dropped, but for the story behind a decision use `git log`.

---

# HANDOFF — 2026-08-15 09:30 PDT — DATASET IS LIVE, SOLVE IS RUNNING

# ⚠️ A NINE-BLOCK SOLVE IS IN FLIGHT. DO NOT START ANOTHER. DO NOT REBOOT. ⚠️

Deadline **2026-08-16 16:00 UTC / 09:00 PDT** — check `date -u` for what remains.

## Live process

```
pid 86851   giscup solve-all   launched 2026-08-15 09:30 PDT
log         outputs/solve.log            (tail -f this first)
output      outputs/final.txt  + outputs/final.json
partial     outputs/final.txt.partial    (rewritten after every block, deleted on success)
```

If `ps -p 86851` is empty, the solve ended — check the log tail and whether `outputs/final.txt`
exists before assuming failure. The exact command is in `docs/release-minute-commands.md` §4 with
the real parameters already substituted.

## THE PUBLISHED GRID IS NOT THE ASSUMED ONE

```
taus  0.32 0.49 0.68     (assumed since March: 0.25 0.5 0.75)
ks    9 49 484           (assumed since March: 50 500 1000)
```

Every downstream command needs `--taus 0.32 0.49 0.68 --ks 9 49 484`. The audit and the assembler
take them; **omitting them fails a correct submission.** This is precisely what the overnight
hardening was for.

## The dataset

Shipped **inside the evaluator repo** (`github.com/alowe/gis-cup-2026-evaluator`, commit `9af12a5`),
not as a link on the competition page. Copied to `data/`, never overwritten:

| | sample (March) | competition (August) |
|---|---|---|
| buildings | 12,860 | **50,000** (3.89x) |
| candidates | 157,454 | **613,666** |
| samples | 133,417 | **512,589** |
| matrix @ 400 m | 2.63 GB | **39.3 GB** |
| density | 610 bldg/km² | 437 bldg/km² (*lower*) |
| perimeter sum | 858,973 m | 3,300,183 m |
| total antennas (sum k) | 4,650 | **1,626** (fewer) |

md5 `cf36adb386b8caf1415cf359d578245b`. CRS **EPSG:32611**, `Polygon` only, bbox 10.6 x 10.8 km.

## All release-day stop conditions passed

- **`giscup inspect` stderr was empty** → the ID fallback did *not* fire, `properties.id` is real.
  (Recall: this warning is the only signal; it is not in the diagnostics JSON.)
- **`holes_count` 0** → the official loader will not reject this dataset. Task #11's stop condition
  is satisfied on the real data.
- **IDs are `1..50000`, unique, integer**, and `id` is the only property present.
- **The official loader parses it**: 50,000 buildings, no error, 4.9 s. Verified 2026-08-15 09:25
  via `benchmarks/loadonly.test.ts`. It coerces IDs to strings (`"1"`) — the same path that produced
  0 unknown IDs in March, so integer IDs are fine.

## The 39.3 GB matrix is NOT a memory problem — measured, not assumed

The machine has 24 GB RAM. Measured scan rates: **cached 4.07 GB/s, pages-dropped 4.09 GB/s**, raw
disk `dd iflag=direct` 4.2 GB/s. `marginal_gains` scans the memmap sequentially in 4096-row chunks,
so readahead hides the IO completely and the disk outruns the popcount pipeline. **Bandwidth-bound,
not residency-bound.** No lever was applied; the settled parameters (400 m, near-tau,
`--matrix-workers 8`, `--verify-workers 12`, `--candidate-stride 1`) all stand.

Do not "fix" this by adding a prune. It is not broken.

## Timing projection (extrapolated — replace with measurements as they land)

| phase | projection | basis |
|---|---|---|
| matrix build | ~4.6 h | March 5,971 s x 2.76 work ratio, 8 workers |
| greedy | ~4.3 h | 1,626 iters x 39.3 GB / 4.07 GB/s |
| verification | unquantified | scales with claims, not yet known |
| **total** | **12–16 h** | finish ~22:00–02:00 PDT |

The candidate-count prediction (613,666) was exact, which is some evidence the rest is sound — but
verification is the least-constrained leg and was ~82% of a March run.

## Decisions already made — do not re-open

- **All nine blocks get the official evaluator** before upload (Marko, 2026-08-15). ~1 h projected.
- **Local commits only; pushes need Marko's explicit word each time.** 14 commits were pushed at
  09:16 PDT with his go-ahead (`504d918..bdc0d43`); everything after that is local until he says so.
- **No solver tuning.** The near-tau quantile schedule maps our taus to 100/50/25 but was fitted at
  k=500 while the real ks are 9/49/484. That extrapolation is *known and deliberately unaddressed* —
  re-fitting on the day is the trap the runbook forbids.
- EasyChair access confirmed by Marko, form reachable.

## Downstream dry-run — DONE 09:42 PDT, and it paid for itself

Every downstream tool was run at competition scale against the real grid on a throwaway solution
(exactly `k` legal antennas taken from source vertices, empty claim lines), plus a deliberately
overclaiming negative control. **Nothing downstream is now being executed for the first time when
the real artifact lands.**

| tool | result |
|---|---|
| `audit_submission.py` (clean) | **PASS**, rc 0 — after the fix below |
| `audit_submission.py` (bogus) | **all 45 bogus claims caught**, rc 1 — not vacuous at 50k scale |
| `assemble_blocks.py` recovery | 6+3 blocks reassembled, **byte-identical**, rc 0 |
| recovery *without* `--taus/--ks` | refuses correct blocks: *"missing 9 of 9"* — the hardening's value, demonstrated |
| `package_submission.py` | 9 blocks, 1,626 antennas, 341.7 KiB, rc 0 |
| bundle's own tests | **366 passed, 2 skipped, 0 failed** |
| official evaluator | 9 blocks parsed, **0 invalid antennas, 0 warnings**, `vertexCount` 306,833 matches |

### The defect it caught: the six-decimal heuristic fails a correct submission here

**The competition dataset is stored at millimetre precision** — 89.4% of ordinates have exactly 3
decimals, 99.6% have ≤3. The March sample was 8–11 decimals. An antenna on a source vertex therefore
emits a short token through no fault of ours (and `%g` strips trailing zeros besides), so the audit's
`^-?\d+\.\d{1,6}$` guard flagged 591 tokens of a provably legal file and exited 1.

Fixed in `de03785`: the heuristic stays a hard failure on a high-precision source and becomes a
`[NOTE]` on a coarse one, because the hazard it proxies for is measured *exactly* by the
`eps=1e-7` boundary check. **Expect `notes: 1` on the real audit — that is correct, not a warning
sign.** Overclaim detection is unchanged and was proven by negative control. Tests 365 → 368.

### Official-evaluator cost model — measured, and counter-intuitive

| block | k | claims | time | per antenna-claim pair |
|---|---|---|---|---|
| 1 | 9 | 5 | 14.3 s | 318 ms |
| 2 | 49 | 5 | 79.3 s | 324 ms |

Linear in `k`, ~320 ms per pair — which cannot be reconciled with March's 41 min for 42,728 claims
until you notice **the evaluator early-exits the moment a claim clears tau**. A claim that verifies
stops after a few antennas; a claim that *fails* must exhaust all `k`. The control's claims were all
unreachable, so it hit the worst case every time.

**Consequence: evaluator runtime is dominated by failed claims.** Run our own audit (~10 s) first —
if it is clean the evaluator will be fast, and if the evaluator instead crawls, that *is* the alarm.
Do not start the evaluator on an unaudited file.

## What remains

1. ~~Downstream dry-run~~ — done, above.
2. Re-run the crash-recovery rehearsal against a **real** `final.txt.partial` once block 1 lands.
   The synthetic rehearsal passed; this only confirms the real file's formatting.
3. Re-project the finish time from the measured matrix-build duration (the 4.6 h figure is still
   extrapolated). The candidate-count prediction was exact, which is mild evidence for the rest.
4. When the solve finishes: audit → official evaluator (**all nine blocks**, Marko's call) →
   regenerate the bundle → **notify Marko, who will do the upload himself.**

---

# HANDOFF — 2026-08-15, overnight prep (00:15–01:00 PDT) — SUPERSEDED by the block above

# ⚠️ TODAY IS SUBMISSION DAY. THE DATASET PUBLISHES AT 09:00 PDT / 16:00 UTC. ⚠️

Written while Marko slept, on his instruction to work autonomously overnight and hand off at 08:00
PDT. **Nothing was pushed** — local commits only, per the standing rule and his explicit
reaffirmation. Several commits are ahead of `origin/main`; run `git log origin/main..HEAD --oneline`
for the exact set. **Pushing is recommended before the solve starts** — the tree is in materially
better shape than `504d918` and it is cheap insurance ahead of a 24-hour window — but it needs
Marko's explicit go-ahead.

## Run the day from `docs/release-minute-commands.md`

New tonight. It is the runbook's sequence with every flag filled in and the placeholders exported
once at the top, so nothing has to be composed at the release minute. `docs/submission-day-runbook.md`
remains the document you read when something does not look right.

## What changed today, before any of the prep

Checking the official page on release day surfaced five facts the repository had recorded as
unknown or wrong. **These are the highest-value lines in this handoff.**

| the repo believed (2026-08-10) | actually true (2026-08-15) |
|---|---|
| submission link "still unpublished" | **EasyChair**, live: `https://easychair.org/conferences/?conf=giscup2026`. Account required; Marko has one. |
| building ID field name unknown | the page names **`properties.id`**, required unique |
| boundary tolerance assumed `1e-8`–`1e-7` | **`0.001` m** — within 1 mm an antenna is *snapped and accepted*, not rejected |
| no official scorer exists | **`github.com/alowe/gis-cup-2026-evaluator`** — MIT, and it *is* the scorer |
| dataset is one geojson | ships a companion **`competition-parameters.txt`** |

The last one has teeth: the `(tau, k)` grid is **published data**, not a documented constant.

## Three defects found and fixed overnight

Each would have cost real time on the day; none was known at 2026-08-10.

1. **The runbook's ID stop-condition read a field that does not exist.** It said to stop if
   `DatasetInfo.id_fallback_used` is true "in diagnostics". `diagnostics.dataset_summary` never
   emits it, and the JSON's `id_property` is only an echo of the argument you passed. The fallback
   warns on **stderr** (`io.py:15-23`) and nowhere else — so the documented check would have passed
   silently on precisely the failure it exists to catch. **On the day: pipe stderr.** Fixed in the
   runbook, not in code; changing the diagnostics schema today is the worse trade.
2. **The `(tau, k)` grid was hardcoded in three places.** Two would have failed: crash recovery
   would have refused a correct set of blocks ("missing 9 of 9"), and `audit_submission.py` would
   have failed a *correct* submission at the last gate before upload. Now
   `giscup.assemble.subproblem_grid(taus, ks)` with `--taus`/`--ks` on both scripts.
   `packaging.EXPECTED_BLOCKS = 9` is a count and was deliberately left alone.
3. **Two shipped tests could only fail inside the submission bundle.** They read
   `.claude/commands/rehearsal.md`, which `packaging.SOURCE_TREES` does not ship. They had failed
   there — and only there — since 2026-08-10, quietly making the runbook's "shipped source passes
   its own tests" false. Now skipped when the file is absent; they stay load-bearing in the repo.

Also corrected: a runbook warning that had gone stale into being *wrong* — it said `solve-all` and
`rehearse.py` disagree on their `--objective` default and to treat it as live. That was fixed
2026-08-10 and is pinned by a test.

## Task #11 (holes) is settled, with evidence, after eight days

The official page said "will not have holes"; our sample has one on building 9448. **The page was
right.** The official loader rejects hole-bearing polygons outright —

```
DatasetValidationError: Building "9448" must contain exactly one ring and no holes.
{ code: 'HOLES_NOT_ALLOWED', featureIndex: 9447, buildingId: '9448' }
```

— and the organisers ship the *same* sample with that hole removed (216 bytes apart). **On the day,
`holes_count > 0` is a stop-and-escalate**, because it would mean the published dataset cannot be
loaded by the organisers' own scorer. Our defensive handling stays: it is stricter than the official
predicate, so it can only forfeit a claim, never create an overclaim.

## The official evaluator now runs here

`scripts/official_evaluator/` — driver, vitest config, and a README. It is browser-*delivered*, not
browser-*bound*; the scoring core is plain TypeScript over `@arcgis/core` and runs headless under
vitest. **It must run under vitest, not bare node** (`constants.ts` bare-imports `package.json`,
which needs the Vite transform).

**Validated before being trusted**, against every documented expected result the evaluator ships:
the six `ui-smoke` fixtures (via its own vendored suite, 73/73 green) and the full-sample
submission's documented score of **`1`**, reproduced exactly.

Two properties worth knowing before reading its output:

- **Only *claimed* buildings are evaluated.** Unclaimed ones are never checked — so overclaiming is
  the only way to lose points, and underclaiming is silently free.
- **Unknown claimed IDs are a warning, not an error.** An ID-field mistake surfaces as a quietly
  catastrophic score, never a crash. Same failure the stderr check catches one step earlier.

This retires the project's standing assumption that *"local validation is a rejection framework, not
a score estimator"* — **only partway**. It now sees the official *predicate* exactly. It still
cannot see **rank**, because scoring is relative (`team score / best submitted score`). Do not let a
good number become a reason to stop checking, or a bad one a reason to re-tune at hour 20.

## Official-scorer comparison of the March artifact

**`k=50` blocks — exact agreement**, run against the organisers' own copy of the sample:

| block | tau, k | our claims | official verified | failed | unknown IDs |
|---|---|---|---|---|---|
| 1 | 0.25, 50 | 1,659 | **1,659** | 0 | 0 |
| 4 | 0.5, 50 | 269 | **269** | 0 | 0 |
| 7 | 0.75, 50 | 148 | **148** | 0 | 0 |

All 50 antennas valid in every block — **our boundary placement passes the official 1 mm test.**

**`ANTENNA_SNAPPED` ×2 in block 7 is benign, and worth understanding rather than worrying about.**
The validator sets that flag whenever the nearest point on the segment is not *bit-identical* to the
submitted coordinate — `coordinatesEqual` is strict `===`, so it fires on any nonzero displacement,
however small. It is not a proximity complaint. Two of fifty antennas in that block are interpolated
edge points that differ from their own projection in the last bits; the other 48 sit bit-exactly on
vertices. Our own audit measures the same 50 antennas at **0 off-boundary at eps=1e-7**, four orders
tighter than the official 1 mm bar. Nothing to act on.

## Our own audit, re-run tonight against the modified script

`scripts/audit_submission.py` grew `--taus`/`--ks` tonight, so it was re-run on real data rather than
trusted to unit tests. `outputs/nine_bestof_400.txt` against the March sample, 400 m screen / 800 m
confirm, 12 workers — **AUDIT PASSED**:

- 9 blocks, no duplicated `(tau, k)`, all nine combinations present *(now reported from the derived
  grid: "9 blocks present", "the 9 official (tau, k) combinations")*
- exactly `k` points counted in every block; no coordinate looks six-decimal rounded
- **0 off-boundary at eps=1e-7, 0 unknown IDs**
- **all 42,728 claims hold exactly — 0 overclaims**

Log: `scratchpad/audit-rerun.log`. This matches the 2026-08-10 result exactly, so the hardening
changed no behaviour on the default grid.

**Full nine blocks — EXACT AGREEMENT, all 42,728 claims verified.** Completed 01:02 PDT, **41 min**
wall clock for 4,650 antennas and 42,728 claims at March size.

| block | tau, k | our claims | official verified | diff | failed | unknown | min |
|---|---|---|---|---|---|---|---|
| 1 | 0.25, 50 | 1,659 | **1,659** | 0 | 0 | 0 | 0.5 |
| 2 | 0.25, 500 | 9,349 | **9,349** | 0 | 0 | 0 | 4.7 |
| 3 | 0.25, 1000 | 12,279 | **12,279** | 0 | 0 | 0 | 8.5 |
| 4 | 0.5, 50 | 269 | **269** | 0 | 0 | 0 | 0.3 |
| 5 | 0.5, 500 | 4,247 | **4,247** | 0 | 0 | 0 | 4.5 |
| 6 | 0.5, 1000 | 8,063 | **8,063** | 0 | 0 | 0 | 13.1 |
| 7 | 0.75, 50 | 148 | **148** | 0 | 0 | 0 | 0.2 |
| 8 | 0.75, 500 | 2,222 | **2,222** | 0 | 0 | 0 | 2.9 |
| 9 | 0.75, 1000 | 4,492 | **4,492** | 0 | 0 | 0 | 6.4 |
| | **total** | **42,728** | **42,728** | **0** | **0** | **0** | **40.9** |

**The organisers' own scorer verifies every single claim we make.** Zero overclaims under the
official predicate, zero unknown IDs, and every block's antenna list accepted. Our audit and the
real scorer agree exactly, on all nine blocks, on the artifact we would have shipped.

That is the outcome this whole exercise was for. It does **not** predict rank — scoring is relative
— but it removes predicate risk entirely: whatever we score, it will not be lost to claiming
buildings the evaluator disagrees about.

**Budget ~45 min for this step on the day**, not the hour the runbook allows. Cost concentrates in
the high-`k`, high-claim blocks (block 6 alone is 13.1 min).

### Two findings worth keeping

**`ANTENNA_SNAPPED` fires at ULP scale and is meaningless.** 59 of 4,650 antennas across the nine
blocks, at distances of **1.1e-10 to 1.1e-9 m** — sub-nanometre, which at these coordinates is one
to two ULP. Confirms the reading above: these are interpolated edge points differing from their own
projection in the last bits, not antennas placed off the boundary.

**Building 9448 — the hole-bearing one — is claimed in three blocks and verified in all three.**
This empirically closes the task #11 assumption. We computed its coverage against *our* hole-bearing
copy, where the denominator includes the hole perimeter and coverage is therefore **underestimated**;
the evaluator scored it against *their* de-holed copy. The recorded prediction was that the error
runs in the safe direction — "it can only forfeit a claim, never produce an overclaim". It did not
even forfeit the claim. Confirmed rather than merely argued.

---

# HANDOFF — 2026-08-10, end of session  *(superseded by the block above; kept for its detail)*

# ⚠️ THE NEXT SESSION IS SUBMISSION DAY ⚠️

**Test data lands 2026-08-15. Deadline 2026-08-16. A 24-hour window, one submission, no score
feedback, ever.** This handoff was written on 2026-08-10 specifically so the submission-day session
does not have to think about anything except executing.

## Do these three things, in this order, before anything else

```bash
# 1. environment + green tests (5 min)
conda activate mz-giscup-26
cd /home/markolinux/projects/sigspatial_26
python -m pytest -q                    # must read 365 passed

# 2. put the downloaded extract in data/ -- NEVER overwrite it

# 3. INSPECT BEFORE SOLVING. This is the single highest-value five minutes of the day.
giscup inspect --input data/<the-new-file>.geojson
```

**Then open `docs/submission-day-runbook.md` and follow it top to bottom.** It is the operational
document; this file is only the state summary. Do not improvise a command sequence from memory.

**Every step below is already decided. Do not re-litigate any of it on the day** — the reasoning is
in `docs/task-board.md` and in `git log`, and re-opening a settled decision under time pressure is
the failure mode this project has spent a week eliminating.

| the day's shape | value | why |
|---|---|---|
| radius | **400 m** | #3b, #20 both measured. 600 m too slow, 300 m costs 0.79 subproblems. |
| objective | **`near-tau`** (the default) | #15. Wins 8 of 9 blocks. |
| `--matrix-workers` | **8** | Measured 2026-08-10: 12 is 2.2% *slower*. |
| `--verify-workers` | **12** | Serial costs ~12 h of the window. |
| `--candidate-stride` | **1** (off) | #9 closed 2026-08-10. Contingency only. |
| expected runtime | **4.64 h likely, 8.14 h bound** | Gate re-read PASS 2026-08-10 at 2.5x headroom. |

## The three things that can actually lose this

1. **The `--id-property` trap.** `io.py` silently falls back to the row index if the ID field is
   missing, and **every claim would then reference a nonexistent building while passing every
   structural check.** The page named `properties.id` on 2026-08-15, so the default is probably
   right -- but `giscup inspect` on the day is still the only way to settle it. **Capture stderr:**
   the fallback warns there and *not* in the diagnostics JSON. (This bullet said to read
   `DatasetInfo.id_fallback_used` from diagnostics until 2026-08-15; that field is not emitted.)
2. **A subproblem that does not finish scores ~0.** Scoring is relative and summed over nine
   independent subproblems. Partial output is written after every block to `<output>.partial`, and
   `scripts/assemble_blocks.py` merges a re-solve of only the missing blocks. Use it — do not
   re-run all nine.
3. **Auditing at the wrong radius.** `--exact-radius 400 --confirm-radius 800`. Confirming
   *tighter* than the solver verified generates false failures (25 of them, once). Confirm at the
   verification radius or wider, never tighter.

## Status in one line

**Everything that can be done before the extract exists, is done.** No open decisions, nothing
blocked on machine time. A complete, audited nine-block artifact exists **for the March sample** —
it is proof the pipeline works end to end, not the deliverable.

**Repository state at handoff:** commits `3f381bb` and `09cb5d8` are pushed to `origin/main`. The
2026-08-10 wrap-up documentation edits were pending commit when this was written — if
`git status` is dirty on the day, it is these docs and nothing else. **Check `git status --short`
and `git log --oneline -3` before assuming anything**, per the resume contract in `CLAUDE.md`.

## The submission artifact

**`outputs/nine_bestof_400.txt`** — 9 blocks, 4,650 antennas, **42,728 claims, audit PASSED, 0
overclaims.** Packaged as `outputs/submission/mz_giscup_26_submission_20260810.zip` (478.5 KiB,
94 files).

It is **per-block best-of**: lever A in eight blocks, **baseline in `(0.5, 1000)`**, because lever A
measurably loses that block at every quantile tested. Legitimate because the nine subproblems score
independently.

| artifact | claims | subproblems (of 9, vs the better of our own two) |
|---|---|---|
| baseline `nine_verifypar_400.txt` | 39,120 | 6.90 |
| lever A `nine_leverA_400_full.txt` | 42,556 | 8.98 |
| **best-of `nine_bestof_400.txt`** | **42,728** | **9.00** |

All three audited clean: `outputs/audit_v2.log`, `audit_leverA_full.log`, `audit_bestof.log`.
*(Our-options-only comparison, not a score prediction — competition rule 5 still holds.)*

**Structurally re-verified 2026-08-10, independently of the audit logs.** `nine_bestof_400.txt` is
27 lines, no separators, nine blocks in tau-outer/k-inner order, with **exactly k points counted**
in every block (50/500/1000 x3). Per-block claims are 1,659 / 9,349 / 12,279 / 269 / 4,247 / 8,063 /
148 / 2,222 / 4,492, **summing to exactly 42,728**. The `(0.5, 1000)` block reads **8,063**, which is
the *baseline* count and not lever A's 7,891 — so the per-block best-of really is in the file, not
just in the documentation. Bundle passes `unzip -t`.

**The packaged bundle's `source/` is now behind the repo** (it predates the 2026-08-10
`DEFAULT_OBJECTIVE` fix and the 350 -> 356 tests). Harmless — it is a March-sample bundle that must
be regenerated on the day regardless — but do not ship this zip.

## Decisions

| # | Decision | Status |
|---|---|---|
| **15** | Lever A is the shipped default | **DONE.** `--objective {near-tau,baseline}`, default `near-tau`. |
| **3b** | 400 m cull stands | **DONE.** Reinforced by #20 below. |
| **9** | 2x candidate prune | **CLOSED 2026-08-10 — default stays OFF, contingency only.** |
| **20** | Radii below 400 m | **CLOSED — measured and rejected.** |

**Every decision is now closed.** #9 was adopted as a *free* lever on a sizing measured in-sample,
with baseline greedy, pooled at k=500. Measured against the objective we actually ship it costs
**~0.07 subproblems** (−2.03% at `(0.75, 50)`). Marko re-decided it on 2026-08-10 with those
corrected numbers: **`--candidate-stride` ships at 1.** Buying ~1.7 h of headroom we do not need,
at a certain cost concentrated in the small-count blocks, is the wrong trade while the day
projection sits near 5 h of a ~20 h window. It stays **ranked first among the day-of levers**,
implemented, tested, and one flag away.

## The two time-buying levers, measured and ranked

This is what the submission-day runbook's "what to give up if the extract is bigger" section was
missing — it listed options with no ranking.

| lever | matrix build | greedy | total saved | score cost |
|---|---|---|---|---|
| **#9 `--candidate-stride 2`** | ~50 min | **~0.86 h** | **~1.7 h** | **~0.07 subproblems** |
| **#20 300 m cull** | ~50 min | **nothing** | ~0.8 h | **~0.79 subproblems** |

**#9 strictly dominates #20** — about twice the time saved at about a eleventh of the cost. 300 m
does not speed up greedy at all: the argmax is a popcount over every candidate row, and
words-per-row depends on *sample* count, not on how many bits are set, so a sparser matrix costs the
same to scan.

**If runtime must be bought on the day: prune first, cut radius only if that is not enough.**

## Official page — re-checked 2026-08-10  *(SUPERSEDED: re-checked again 2026-08-15, see the top block)*

`https://sigspatial2026.sigspatial.org/giscup.html`. This said **the submission link is still not
published**. **It was published on 2026-08-15 — it is EasyChair**,
`https://easychair.org/conferences/?conf=giscup2026`. The emails below are now break-glass only:
Aaron Lowe (`alowe@esri.com`) or Ashwin Shashidharan (`ashashidharan@esri.com`).

Everything else on the page re-confirmed against our docs, verbatim, with **no drift**: all five
dates; three lines per subproblem for nine subproblems; three taus x three ks; IEEE-754 doubles;
*"the polygons will not self-intersect and will not have holes"*; test dataset published 2026-08-15.

**Submission artifact shape confirmed** — *"a zip file including the following: 1. A text file with
the solutions for each of the sub-problems... 2. A folder that has your source code, along with
instructions for compiling and running the program."* That is exactly what
`scripts/package_submission.py` produces.

**The ID field name is still ABSENT from the page.** The `--id-property` trap is therefore live and
unresolvable before the extract lands: `giscup inspect` on the day is the only way to settle it.

## Next actions — the whole remaining list

1. **On the day, read `docs/submission-day-runbook.md` first**, then follow it. It carries the
   `--id-property` trap, the sizing sequence, the exact commands, and the ranked fallback levers.
2. ~~**Get the submission link.**~~ **RESOLVED 2026-08-15: EasyChair**,
   `https://easychair.org/conferences/?conf=giscup2026`, account required. Emails are break-glass.
3. **Regenerate the bundle from the August solution** — `python scripts/package_submission.py
   --solution outputs/final.txt`. The zip on disk is a March-sample bundle and its `source/`
   predates `3f381bb`. **Do not ship it.**
4. Only if solver code is edited on the day: re-run `/rehearsal` before trusting a projection.

**There is no preparatory work left.** If the extract has not landed yet, the correct action is to
re-read the runbook, not to find something to improve. Every tuning knob in this project was fitted
on the March sample, and the runbook's own last rule is *do not tune the objective on the day*.

---

# Environment

```bash
conda activate mz-giscup-26          # Python 3.11; required for all work
```

**Host: 16 cores, 24 GB RAM.** NumPy 2.4.6 (`np.bitwise_count` needs >=2.0), Shapely 2.1.2,
SciPy 1.17.1. **`ruff` and `mypy` are NOT installed** — `pip install -e .[dev]` if lint is needed.

## Validation status

**Re-run 2026-08-15, overnight:** `pytest -q` -> **365 passed**, `compileall` clean, the
nine-block artifact re-audited (0 overclaims of 42,728), and the packaging path rebuilt and its
shipped tests run inside the extracted bundle (363 passed, 2 skipped, 0 failed).

The 2026-08-10 run below is kept for its gate figures, which have not been re-measured since.

### Validation status — actually run 2026-08-10, end of session

```bash
python -m pytest -q                         # 356 passed  (365 as of 2026-08-15)
python -m compileall -q src tests scripts   # OK
giscup inspect --input data/GIS-cup-sample-dataset.geojson   # OK, EPSG:32611 preserved
python scripts/rehearse.py --input data/GIS-cup-sample-dataset.geojson \
    --cores 16 --measured-radius 400 --verify-workers 12     # PASS, 2.5x on the bound
```

**Gate re-run 2026-08-10 on a quiet machine after the objective fix: `MEASURED VERDICT: PASS`,
8.14 h bound / 2.5x, 4.64 h likely / 4.3x.** Log: `outputs/rehearsal_20260810.log`.

**The headline moved and it is worth knowing why.** The 6.87 h / 2.9x quoted everywhere before this
was costed at `baseline` while the solver ships `near-tau`. Costed correctly the bound is 8.14 h.
Nothing got slower — ~1.77 h of lever A verification was simply not being counted. Still a
comfortable PASS (2.5x against the 1.6x that rejected 600 m), but every planning figure written
between 2026-08-09 and 2026-08-10 was ~14% optimistic.

Committed through `3f381bb`; the matrix-measurement and gate-re-run work is the commit after it.
**Not yet pushed to `origin/main`.**

## Managing the multi-hour background jobs

These jobs are **memory-bandwidth bound, not core bound.** Four concurrent jobs cut the greedy pick
rate from 59/min to 34/min. Measured 2026-08-09: **12 workers buys essentially nothing over 8** for
the matrix build — an inferred 400 m/12-worker build (~102 min) lands on the measured 8-worker time
(99.6 min).

- **Use `nice -n 15` on the low-priority job** and let the scheduler arbitrate. Do not `renice` or
  `SIGSTOP` after the fact.
- **`pgrep -f <pattern>` matches your own shell**, because the pattern appears in that shell's own
  command line. On 2026-08-09 this killed an authorised 600 m build outright (exit 147 = 128+19).
  Match on something narrower, or filter out the current shell's PID. `ps -p <pid>` and
  `pgrep -P <pid>` are safe.
- **A killed matrix build is safe by design**: the metadata JSON is the completion marker, so a
  `.bits` file without its `.json` is rebuilt rather than trusted.
- **Piping a long job through `tail` hides all progress** — `tail` only flushes at exit. Watch the
  `.partial` file instead; `solve-all` writes one after every block.
- **A background shell ID does not survive a `/clear`; `outputs/` does.** Check files and `ps`
  before assuming a job died.

## Matrix cache — `outputs/cache`, 8.6 GB, 845 GB free

| radius | stride | candidates | visible pairs | build | key |
|---|---|---|---|---|---|
| 400 m | 1 | 157,454 | 8,194,226 | 99.6 min @ 8 w | `7a385189` **<- the one in use** |
| 400 m | 1 | 157,454 | 8,194,226 | **101.8 min @ 12 w** *(2026-08-10)* | `7a385189` (in `cache_bench/`) |
| 600 m | 1 | 157,454 | 8,891,506 | 434.5 min @ 6 w | `89846a10` |
| 400 m | 2 | 78,727 | 4,878,593 | 50.9 min @ 12 w | `7c422675` |
| 300 m | 1 | 157,454 | 7,529,996 | 48.6 min @ 12 w | `73e00daa` |

**The 12-worker row is a benchmark, not a second usable matrix.** It lives in
`outputs/cache_bench/` (2.6 GB, deletable) and is **byte-identical** to the production build —
`cmp` clean over 2.63 GB. Same key, same pairs, same everything but the clock.

**Settled by it, 2026-08-10:** 12 workers is **2.2% slower** than 8, not merely no faster; the
**stride-2 build saving is a matched 2.00x** (101.8 -> 50.9 min) rather than an inference; and the
parallel build is **deterministic**. Throughput reconciled to 0.03% against the stride-2 build
(92.5 vs 92.4 K checks/s). **Use `--matrix-workers 8` on the day** — the documented `solve-all`
command said 12 until 2026-08-10 and now says 8 in all four places it appears. The difference is
only ~2 min, so this is tidiness, not a lever.

**`--verify-workers` stays 12** — different stage, different scaling. Do not "simplify" both to the
same number.

**None can be reused on submission day** — the key includes the dataset digest. Keys also cover
candidate set, samples, radius, strategy, eps, and `interior_tolerance`, so a pre-#14 matrix can
never be silently reused.

## Data situation

**`data/GIS-cup-sample-dataset.geojson`** — the official March sample (6.3 MB, git-ignored,
obtained 2026-08-08). Every documented statistic matches exactly: 12,860 buildings, 78,727 exterior
vertices, 858,973.22 m perimeter, 1 hole-bearing polygon, EPSG:32611.

**The test dataset publishes 2026-08-15 16:00 UTC / 09:00 PDT — today.** Until it is on disk,
every solution-quality figure in this repository is fitted on the March sample; August is a
different extract. *(This line read "test data does not exist until 2026-08-15" until that date.)*

`outputs/synthetic_full.geojson` (regenerable via `scripts/make_synthetic_dataset.py`) is fine for
feasibility rehearsals but has no real street topology and omits the large-building tail.
**Never use it for solution-quality claims.**

## Estimation calibration — read before trusting a projection

Two distinct patterns, both live:

**1. Extrapolating a constant past the configuration it was measured in.** This produced every major
error in the project: the gate's verification constant (16.2x low), the 800 m build (2.6x), the
audit cost (16x), the "free" 2x prune, and the per-`(tau, k)` schedule. `gate_model` now *refuses*
to cost an unmeasured radius pair or objective rather than guessing. **Apply the same standard to
analysis scripts, which have no such guard.**

**2. A pooled figure hiding where the score actually lives.** Hit three times on 2026-08-09 alone.
Claim counts pooled across blocks say −5.4% for a 300 m cull; relative scoring says 0.79
subproblems, because the loss concentrates in small-count blocks worth exactly as much as large
ones. **Size every lever per block, never on the total.**

**In-sample sweeps rank well and predict margins badly.** `scripts/sweep_near_tau.py` counts off the
same grid the optimizer optimized on. It picked the right quantile ordering repeatedly, then missed
`(0.5, 1000)` by 3.2 and 5.5 points — enough to flip a decision both times.

**Timing projections have run optimistic six times and pessimistic once.** Treat any projection not
calibrated against a measured run with suspicion, in that direction.

## Known gaps, ranked

1. **Everything is fitted on the March sample.** Lever A's quantile schedule is a *tuned* parameter;
   the baseline objective has no such knob. This is the main argument for the escape hatch
   (`--objective baseline`) existing and staying tested.
2. **`(0.5, 1000)` ships baseline**, so the artifact mixes objectives. Deliberate and audited, but
   the submission is therefore not reproducible from a single command — see
   `scripts/assemble_blocks.py`.
3. **The cull radius is still a heuristic with no feedback.** 400 m discards ~9% of visibility;
   verification re-measures near-threshold buildings at 800 m, so the buildings that decide the
   score already get the wide view. Both directions are now measured: 600 m gains +4.1% for ~1.6x
   headroom, 300 m loses ~0.79 subproblems for ~0.8 h.
4. **`gate_model` uses the 4.70x contended verify speedup for its verdict**, deliberately, though
   7.3x was measured uncontended. The gate reports both; only the conservative one decides.
   **Reviewed 2026-08-10 and deliberately left alone — this is CLOSED, not outstanding.** The
   uncontended figure is already fully in the module: `MEASURED_VERIFY_SPEEDUP_UNCONTENDED = {12:
   7.30}`, reachable via `verify_speedup(w, contended=False)`, printed by `rehearse.py` as a third
   row, and pinned by four tests. The only step never taken is letting it set the **verdict**, and
   it should stay untaken: a feasibility gate that quietly gets more optimistic is exactly how #16
   happened. *(Docs previously called this "not acted on", which understated what exists.)*
5. **Greedy optimizes on the sampled matrix**, not the scored quantity. Deliberate — it is a search
   heuristic — but the objective and the claim decision measure different things.
6. Only `greedy` exists as an optimizer. `lazy-greedy` / `stochastic-greedy` / `hybrid` were deleted
   in #10 and are not roadmap markers.

## Repository

- Local root `/home/markolinux/projects/sigspatial_26`, remote
  `https://github.com/mzlatic1/mz_giscup_26.git`, branch `main`.
- **Standing rule: commits and pushes need Marko's explicit approval each time.**
- Do not commit datasets, generated outputs, visibility caches, or environments.
