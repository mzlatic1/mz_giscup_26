# Submission-day runbook

**Test data 2026-08-15. Deadline 2026-08-16. One submission, no score feedback, ever.**
Scoring is relative (`team score / best submitted score`, summed over nine subproblems), so a
subproblem that does not finish scores ~0.

This page is the operational sequence. It exists because on the day the risk is not algorithmic —
it is clerical. Every step below is here because something went wrong at it during rehearsal.

Read `CLAUDE.md` first for the non-negotiable output constraints. This page assumes them.

**`docs/release-minute-commands.md` is the copy-paste companion** — the same sequence with every
flag filled in and no prose. Use it to *run* the day; use this page to understand it, and whenever
something does not look right.

## ⏰ THE CUTOVER SCHEDULE — real clock times, written 2026-08-15 10:50 PDT

**Deadline: 2026-08-16 16:00 UTC = 09:00 PDT.** The solve launched **2026-08-15 09:22 PDT**.

Until 2026-08-15 this page carried no clock times at all — only "Deadline 2026-08-16". There was no
named moment at which you stop waiting for a running solve and ship what you have. **That decision,
made at 04:00 under fatigue with no pre-agreed trigger, is how a one-shot submission gets missed.**
The times below exist so the decision is arithmetic, not judgement.

### Backward from the deadline

Target: **upload complete by 08:00 PDT**, a deliberate 1 h buffer against the 09:00 hard stop.

| by (PDT, Aug 16) | must have happened | budget |
|---|---|---|
| 08:00 | **uploaded to EasyChair** | 30 min |
| 07:15 | bundle built and eyeballed (27 lines, 9 headers, no blank separators) | 15 min |
| 05:45 | official evaluator **finished** | 90 min |
| 04:45 | `audit_submission.py` **finished** | 60 min |
| 04:00 | `k=9` best-of re-run finished (see below) | 45 min |
| **03:30** | **DROP-DEAD: a usable nine-block file must exist** | 30 min slack |

**03:30 PDT is the number to remember.** It is 18 h 08 m after launch, against a 12–16 h projection —
2 to 6 hours of slack. If the solve is still running at 03:30, it has already lost; stop it and take
the cutover path below.

### Checkpoints before then

| when | check | what a bad reading means |
|---|---|---|
| **14:15 PDT Aug 15** | `.json` sidecar in `outputs/cache/` | Matrix build was projected ~4.6 h (i.e. done ~14:00). Still absent ⇒ the projection is wrong; re-project from measured elapsed before doing anything else. |
| **~18:00 PDT Aug 15** | blocks in `outputs/final.txt.partial` | Re-project the finish from *measured* per-block times. This replaces the 12–16 h extrapolation with data. |
| **01:00 PDT Aug 16** | blocks done vs. remaining | **Go/no-go.** If the measured rate does not reach nine blocks by 03:30, decide the cutover now, while rested enough to think. |
| **03:30 PDT Aug 16** | — | Execute the cutover. No further deliberation. |

### The cutover path — proven end-to-end 2026-08-15, do not improvise it

There is a cliff here that is not obvious: **`packaging.inspect_solution` refuses any file that is
not exactly nine blocks** (`EXPECTED_BLOCKS = 9`). Six good blocks and no time left is therefore
indistinguishable from nothing at all — the packager rejects the file. Since scoring is per
subproblem, six real blocks plus three throwaways scores six blocks' worth; submitting nothing
scores zero. **`scripts/emergency_filler_blocks.py` closes that gap:**

```bash
python scripts/emergency_filler_blocks.py \
    --input "$DS" --partial outputs/final.txt.partial \
    --taus $TAUS --ks $KS --output outputs/final_filled.txt
```

Filler blocks are exactly `k` antennas taken **verbatim from source boundary vertices** with an
**empty claims line** — structurally legal, score 0, and incapable of overclaiming. Pre-existing
blocks are copied byte for byte; only the `(tau, k)` header is re-emitted, and it carries no
precision to lose. Verified on the real competition dataset 2026-08-15: 0 → 9 and 6 → 9 both
produced 27 lines in 8.2 s, the six pre-existing blocks came back `cmp`-identical, and
`audit_submission.py` returned **AUDIT PASSED, 0 off-boundary of 1,626 antennas, rc 0** in 8.3 s.

**Still audit and evaluate the filled file.** Filling fixes structure, not correctness.

### Where the step-5 estimate is wrong

The table below budgets **~10 min** for the audit. That figure is from the March sample, and the
2026-08-15 competition-scale dry-run that appeared to confirm it ran against a solution with **empty
claim lines** — it measured parsing, not verification. Real claims are the cost. Applying the
measured `0.090 s/building/1000-antennas` constant, a single `k=484` block claiming ~20k buildings is
~15 min on its own. **Budget 60 min for the audit; treat anything past 90 min as a signal, not
impatience.** The schedule above already uses 60.

The evaluator's ~45 min is likewise a March figure. Its runtime is dominated by *failed* claims
(~320 ms per antenna-claim pair, early-exit on success), so a clean audit implies a fast evaluator —
and **an evaluator that crawls is itself the overclaim alarm.** Budgeted at 90 min above.

### Closed decisions carried into this schedule

- **EasyChair login and submission form confirmed reachable by Marko, 2026-08-15.** The upload path
  is not an unknown.
- **`k=9` best-of is approved** (Marko, 2026-08-15). `near-tau`'s quantile schedule was fitted at
  `k=500`; the real grid includes `k=9`, a 55x extrapolation that is flagged everywhere and has never
  been measured. After the main solve, re-run the three `k=9` blocks with `--objective baseline`
  against the cached matrix and keep whichever verifies more buildings **per block**. This is
  selection between two finished, audited results — the same per-block best-of that produced the
  March artifact — **not** parameter tuning on the day. Approved for `k=9` only; `k=49` and `k=484`
  ship `near-tau` untouched.
- **Matrix-build speedups are off the table** (Marko, 2026-08-15) and were already measured out.

## The whole day at a glance

Verified 2026-08-10. Every parameter here is a closed decision — **do not re-open one under time
pressure.** Timings are for a March-sized extract (12,860 buildings); scale them by §3's sizing.
**Steps 5 and 6 are re-budgeted upward in the cutover schedule above — use those numbers.**

| # | step | command | time |
|---|---|---|---|
| 0 | environment, green tests | `pytest -q` -> **368 passed** | 5 min |
| 1 | **read `competition-parameters.txt`** | — | 5 min |
| 2 | **inspect before solving** | `giscup inspect` (capture **stderr**) | 5 min |
| 3 | size the run | `scripts/rehearse.py --cores 16 --measured-radius 400` | 10 min |
| 4 | solve nine blocks | `giscup solve-all` (radius **400**, matrix-workers **8**, verify-workers **12**) | **~5 h** |
| 5 | audit | `scripts/audit_submission.py --exact-radius 400 --confirm-radius 800` | ~10 min |
| 6 | **official evaluator** | `scripts/official_evaluator/` | ~45 min |
| 7 | package + submit | `scripts/package_submission.py` -> EasyChair | 15 min |

**Budget ~7 h of a 24 h window.** The gate's upper bound is 8.14 h at 2.5x headroom (re-read
2026-08-10). If sizing says materially worse, go to §8 — do not start improvising.

**Submission link — resolved 2026-08-15.** Submissions go to **EasyChair**:
`https://easychair.org/conferences/?conf=giscup2026`. An EasyChair account is required; Marko has
one. *(This section said "unpublished" until 2026-08-15.)* Break-glass only, if EasyChair is
unreachable: email **Aaron Lowe** (`alowe@esri.com`) or **Ashwin Shashidharan**
(`ashashidharan@esri.com`) — build the bundle first and ask early rather than letting a missing
upload path run out the clock.

---

## 0. Before anything (5 min)

```bash
conda activate mz-giscup-26
cd /home/markolinux/projects/sigspatial_26
python -m pytest -q                    # must be green before you touch the real data -- 368 passed
nproc; free -g; df -h .                # 16 cores, 24 GB, and the matrix needs ~2.6 GB free
```

`outputs/cache` holds 8.6 GB of **March-sample** matrices. None can be reused — the cache key
includes the dataset digest — but they are also not in the way. Delete them only if disk is tight.

Put the downloaded dataset under `data/`. **Never overwrite it.** `.claude/settings.json` denies
`Write`/`Edit` on `data/**`, but that guard does not cover shell redirects, `cp`, or an
`--output data/...` flag.

## 1. Read `competition-parameters.txt` BEFORE anything else (5 min)

The dataset download ships a companion parameters file. **It outranks every assumption in this
repository** — CLAUDE.md's source-of-truth order puts dataset inspection above repository docs.

Reconcile what it says against the assumed grid, `0.25/0.5/0.75` x `50/500/1000`. If it disagrees,
**the file wins**, and you pass the published values through to every step:

```bash
giscup solve-all       --taus <published> --ks <published> ...
scripts/audit_submission.py --taus <published> --ks <published> ...
scripts/assemble_blocks.py  --taus <published> --ks <published> ...   # recovery path only
```

Those three flags exist because the values were **hardcoded until 2026-08-15**. The audit would
have printed FAIL and exited 1 on a *correct* submission, and `assemble_blocks.py` would have
refused to recover a crashed run with "missing 9 of 9". Both are now arguments
(`giscup.assemble.subproblem_grid`), defaulting to the assumed nine.

Nothing in the solver core needs changing for a different grid: `solver.py` validates only
`0 < tau <= 1` and `k > 0`, and lever A's quantile schedule is a *function of tau*
(`optimize.default_near_tau_quantile`), so it adapts on its own.

## 2. Inspect the extract — do not skip this (5 min)

```bash
giscup inspect --input data/<the-new-file>.geojson 2>&1 | tee outputs/inspect.log
```

**Capture stderr.** *(Corrected 2026-08-15.)* This page used to say "if `DatasetInfo.id_fallback_used`
is true in diagnostics, stop" — **that field does not exist in the JSON.** `diagnostics.dataset_summary`
emits `path, crs, feature_count, geometry_types, id_property, bounds, holes_count, area, perimeter,
exterior_vertices` and nothing else, and its `id_property` is only an echo of what you typed. The
fallback announces itself as a **`UserWarning` on stderr** (`io.py:15-23`) and nowhere else. Absence
of that warning is the actual test — which you cannot see if stderr is discarded.

Check, and write the answers down:

| Question | Why it matters | Finding |
|---|---|---|
| What is the **ID property** called? | `io.py` silently falls back to the row index when the field is missing. Every claim would then reference a nonexistent building **while passing every structural check**. | The official page names `properties.id`, required unique (confirmed 2026-08-15). Pass `--id-property <name>` if it is not `id`. **Watch stderr, not the JSON.** |
| What is the **CRS**? | Tolerances are absolute in CRS units. The sample is EPSG:32611. | Do not assume; the code inspects, but you should too. |
| How many **buildings**, and total perimeter? | Drives every runtime projection below. The sample has 12,860. | If materially larger than 12,860, see §8. |
| Any **holes**? | **STOP AND ESCALATE if `holes_count > 0`.** | See below — this changed meaning on 2026-08-15. |
| Coordinate **magnitudes**? | At ~3.7e6 one ULP is ~5e-10 m. Everything about tolerance depends on this. | If magnitudes differ wildly from UTM 11N, stop and think. |

**Holes are now a stop condition, not a note.** This page used to say "holes are preserved and
included as obstacles" and leave it there. Tested against the official evaluator on 2026-08-15: its
loader **hard-rejects** a hole-bearing dataset —

```
DatasetValidationError: Building "9448" must contain exactly one ring and no holes.
{ code: 'HOLES_NOT_ALLOWED', featureIndex: 9447, buildingId: '9448' }
```

— and that is our March sample, on building 9448. The organisers' own copy of the sample is the
same file with that hole removed (the two differ by 216 bytes). So if the August extract reports
`holes_count > 0`, the official scorer **cannot load the file the organisers published**, which
means something is wrong upstream. Escalate; do not quietly strip the hole and proceed, and do not
assume our obstacle handling is the thing that needs to change. Our solver treating a hole as an
obstacle is *stricter* than the official predicate, not looser.

## 3. Size the run before committing to it (10 min)

```bash
python scripts/rehearse.py --input data/<the-new-file>.geojson \
    --budget-hours 20 --cores 16 --measured-radius 400 --verify-workers 12
```

**`--cores` and `--measured-radius` are the load-bearing flags here, and both default badly.**
`--cores` defaults to **1**, so omitting it sizes a serial day and the gate reads catastrophic;
`--measured-radius` defaults to **`None`**, which drops you onto the legacy analytic model instead
of the measured one. Pass both, every time.

**`--objective` no longer needs passing** — *(corrected 2026-08-15)*. This page previously said in
bold that `--objective near-tau` "is not optional, because the two defaults disagree", and that the
mismatch should be treated as live. **That was fixed on 2026-08-10 and the warning is now wrong.**
Both `giscup solve-all` and `scripts/rehearse.py` read `gate_model.DEFAULT_OBJECTIVE`, which is
`near-tau`, pinned by `tests/test_verify_workers_default.py`. Passing it explicitly is still fine
and still recommended for the log — it is simply no longer load-bearing. The reasoning below stands
on its own if you ever cost a *baseline* day.

Read **both** numbers it prints — upper bound and likely. The bound sets the verdict; the likely
figure is what to plan around. On the March sample at 400 m, costed at the objective we actually
ship, these read **8.14 h / 2.5× (bound)** and **4.64 h / 4.3× (likely)**, re-measured 2026-08-10.
*(They read 6.87 h / 2.9× and 5.14 h / 3.9× until then — those were costed at `baseline` while the
solver shipped `near-tau`, and are retired. Do not size the August extract against them.)*

**Pass `--objective near-tau` if the solve will use `--near-tau-quantile`.** Verification is not
the same price for both objectives: lever A parks buildings *at* the threshold by design, which is
exactly where exact interval coverage cannot short-circuit, and it measured **1.26** s per building
per 1000 antennas against baseline's **0.826**. Costing a lever A day as baseline hides **+1.77 h**
on the bound and **+0.86 h** on the likely figure. The two flags must agree — if `solve-all` gets
`--near-tau-quantile`, the gate gets `--objective near-tau`.

The gate **refuses** to cost a radius pair or an objective it was not measured at. That is
deliberate, and it is the same defect twice: the verification constant belongs to (400 m solve,
800 m verify) *and* to baseline greedy, not to the solver in general. Change
`--visibility-radius`, `--verify-radius-factor`, or the objective, and the gate stops rather than
lies. An unrecognised objective is refused rather than defaulted, because baseline is the cheapest
constant in the module and would be the worst possible fallback.

## 4. Solve (the long step — budget ~5–7 h at March-sample size)

```bash
time giscup solve-all \
    --input data/<the-new-file>.geojson \
    --id-property <from step 2> \
    --taus 0.25 0.5 0.75 --ks 50 500 1000 \
    --visibility-radius 400 \
    --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 \
    --verify-workers 12 \
    --output outputs/final.txt \
    --diagnostics outputs/final.json
```

**The objective now defaults to lever A** (`--objective near-tau`, adopted 2026-08-09). The
command above therefore runs lever A unless you pass `--objective baseline`. With no explicit
`--near-tau-quantile` it applies the measured tau schedule (tau<=0.375 -> 100, <=0.625 -> 50,
else 25), which is a *function of tau* and so cannot misalign if August's thresholds are not
0.25/0.5/0.75.

**A radius-free solve now fails rather than silently running baseline**, because lever A exists only
on the cached-matrix path. The error names both remedies.

**On the March sample lever A lost exactly one block, `(0.5, 1000)`, at every quantile tested**
(baseline 8,063 vs 7,891 at q=50 and 7,903 at q=100). The shipped artifact therefore takes baseline
for that one block. **Do not assume the same block loses on the August extract** — if the window
allows, re-solve the cheap blocks with `--objective baseline` and keep whichever wins per block,
merging with **`scripts/pick_blocks.py`** — *not* `assemble_blocks.py`, which refuses a duplicated
`(tau, k)` by design and so cannot perform a best-of merge at all (#31). If the window does not
allow, ship lever A everywhere; it wins eight of nine.

**On the August extract this was approved for `k=9` only** — the three cheap blocks. See
`docs/release-minute-commands.md`, "After the solve", for the exact two commands.

Notes that cost hours if forgotten:

- **`--verify-workers`** now defaults to `min(cores, 12)`, but pass it explicitly so the log
  records what ran. Serial verification costs ~12 h of the window.
- **`--matrix-workers` defaults to `1`.** Unlike `--verify-workers`, it has no host-aware default,
  so omitting it runs a ~13-hour single-threaded matrix build and nothing warns you. Passing it is
  load-bearing.
- **The matrix build cannot come from cache.** It is keyed on the dataset, so the new extract
  rebuilds from scratch — ~100 min at 400 m on the March sample. This is the largest single line.
  **Use `--matrix-workers 8`, not 12.** Measured as a matched pair 2026-08-10: 99.6 min at 8 workers
  against **101.8 min at 12**, byte-identical output. The build is memory-bandwidth bound, so the
  extra four workers contend rather than help. The command above said 12 until 2026-08-10.
- **Partial output is written after every block** to `outputs/final.txt.partial`. If the run dies
  at block 7, you still have six blocks. The `.partial` file is removed on success.

  **To use them**, re-solve only what is missing and merge — do not re-run all nine:

  ```bash
  giscup solve-all --input data/<file>.geojson --taus 0.75 --ks 500 1000 \
      ... --output outputs/blocks_89.txt          # only the missing subproblems

  python scripts/assemble_blocks.py \
      --input outputs/final.txt.partial outputs/blocks_89.txt \
      --output outputs/final.txt
  ```

  The assembler emits tau-outer/k-inner, copies coordinates verbatim, and **refuses** on a
  duplicated subproblem, a missing one, or a block whose coordinate count does not match its own
  `k`. It checks structure, not correctness — audit the assembled file afterwards.

  Watch the quantile mapping if you are shipping lever A: `--near-tau-quantile` maps positionally
  onto `--taus`, so a `--taus 0.75`-only re-run takes a single value (`25`), not all three.
- Progress prints per subproblem with an ETA weighted by antennas placed. It is pessimistic early
  and converges to <1% by block 7.

## 5. Audit before you believe it (~9 min at 12 workers; ~46 min serial)

```bash
python scripts/audit_submission.py --input data/<the-new-file>.geojson \
    --solution outputs/final.txt \
    --exact-radius 400 --confirm-radius 800 --workers 12
    # add --taus/--ks if competition-parameters.txt named a different grid (§1)
```

**Pass both radii explicitly anyway, so the log records what ran.** The command above is now
belt-and-braces rather than load-bearing: `--exact-radius` **defaults to 400.0 m** and
`--confirm-radius` to **800.0 m**, both matching `giscup.audit`. *(Corrected 2026-08-10. This
section previously said `--exact-radius` defaults to `None` and that omitting it costs hours. That
was true until `3f7db68` and is now false — verified against `scripts/audit_submission.py`.)*

**The trap it describes was real and the fix is what removed it.** The script used to default the
*screen* radius to `None`, meaning **unbounded** — every claim measured against the whole dataset
rather than against blockers within 400 m. That is the ~8-hour path, on the last gate before
submitting, selected by forgetting a flag. Found 2026-08-09 by running it that way twice and
watching a five-block audit pass 3 h 25 m without finishing. `none`/`unbounded` are still
available, explicitly, and still cost ~8 hours — **do not pass them on the day.**

**The two radii do different jobs** — 400 m screens cheaply, 800 m confirms only what the screen
flagged.

`--workers` defaults to `min(cores, 12)`; pass it explicitly so the log records what ran. This
step was single-core until 2026-08-09.

**Measured 2026-08-09** on five lever A blocks (27,803 claims, 1,550 antennas), both runs using
the two-stage radii above:

| | serial | 12 workers |
|---|---|---|
| wall clock | 28 m 51 s | **5 m 41 s** |
| speedup / efficiency | — | **5.08x, 96%** |
| verdict | identical to the parallel run, line for line | |

**Audit cost scales with claims x k**, exactly like the solver's verification, because every
claimed building is re-measured against every antenna. Fitting that against the run above gives
**0.090 s per building per 1000 antennas** at a 400 m screen — about 9x cheaper than the solver's
0.826 at 800 m, which is what the radius difference predicts. Projecting onto the March
baseline's nine blocks (30,354 building-k units): **~46 min serial, ~9 min at 12 workers.**

Do not size this step from claim counts alone. An earlier estimate did exactly that, using a
figure measured on `(0.25, 50)` at k=50, and came out 6x optimistic — `(0.25, 1000)` costs 20x
more per claim than that block does.

Must report: 9 blocks, exactly `k` coordinates **counted** per block, 0 off-boundary at
eps=1e-7, 0 unknown IDs, **0 overclaims**. The March baseline passed with 0 overclaims of
39,120 claims; the five audited lever A blocks passed with 0 overclaims of 27,803.

**Our eps is `1e-7`; the official bar is `0.001` m.** Confirmed by reading the evaluator on
2026-08-15 (`SPATIAL_TOLERANCE_METERS = 0.001`). Anything within 1 mm of a boundary is **snapped
onto it and accepted**, not rejected; beyond that it is dropped with `ANTENNA_OFF_BOUNDARY` and its
visibility is lost while it still counts against `k`. Our tolerance is four orders of magnitude
tighter, so passing our audit implies passing theirs — keep it tight and do not relax it to match.

**Confirm at the verification radius or wider — never tighter.** Auditing a 400 m solve and
*confirming* at 400 m produced 25 false failures and zero real ones; the worst read 0.1853 at
400 m and 0.5000 at 800 m. A tighter confirm is not conservatism, it is a guaranteed
false-positive generator. This applies to `--confirm-radius`; the *screen* is deliberately tight,
because a tight screen over-flags and the confirm stage then clears the false alarms.

## 6. Score it with the official evaluator (~45 min at March size — new 2026-08-15)

The organisers publish the scorer: **`github.com/alowe/gis-cup-2026-evaluator`**, MIT licensed. It
is a browser app, but it is browser-*delivered*, not browser-*bound* — the scoring core is plain
TypeScript over `@arcgis/core` and `rbush`, and it runs headless under vitest. This is the
strongest pre-submission signal that exists, and it is the one step this page never had.

See `scripts/official_evaluator/README.md` for setup and the exact commands.

**The clone already exists and is green — `/home/markolinux/projects/gis-cup-2026-evaluator`**
(evaluator commit `9af12a5`, `node_modules` installed, both driver files in place, `pnpm test` = 73
passed, verified 2026-08-15 10:37 PDT). Do not re-clone or re-install today; setup is not on the
critical path, and re-running it would be. Note the paths below are **relative to this repo**, so
pass them as absolute paths when running from inside the clone.

```bash
# in the evaluator clone, with the driver copied into benchmarks/
SCORE_DATASET=data/<the-new-file>.geojson \
SCORE_SOLUTION=outputs/final.txt \
SCORE_SUMMARY=outputs/official-score.json \
pnpm exec vitest run --config vitest.score.config.ts --reporter=verbose
```

**It must run under vitest, not bare node.** `src/core/constants.ts` opens with a bare
`import packageMetadata from "../../package.json"`, which needs the Vite transform.

**Start it the moment the solve finishes** and run the cheap `k=50` blocks first (`SCORE_BLOCKS=1,4,7`)
so a disagreement surfaces in a minute rather than an hour.

What the comparison means:

- **Agreement with our audit** → the strongest confirmation available. Proceed.
- **They verify fewer than we claim** → we overclaim under the official predicate. This is the
  failure mode that silently costs score, and the only cheap way to see it.
- **They verify more** → we left claims on the table. Record it; **do not re-tune under time
  pressure.**

Two properties of the official engine worth knowing before you read its output, both confirmed by
reading `evaluation-engine.ts` on 2026-08-15:

- **Only *claimed* buildings are ever evaluated** (`initializeEvaluationState` iterates
  `claims.uniqueKnownIds`). Buildings you do not claim are never checked. Overclaiming is the only
  way to lose points; underclaiming is silently free.
- **Unknown claimed IDs are a warning, not a fatal error** — they are excluded and evaluation
  continues. So an ID-field mistake shows up here as a quietly enormous score drop, not a crash.
  That is the same failure §2's stderr check exists to catch, one step earlier.

**Rehearsed 2026-08-15 on the March artifact** (`outputs/nine_bestof_400.txt`, 4,650 antennas,
42,728 claims), against the organisers' own copy of the sample: **exact agreement on all nine
blocks — 42,728 of 42,728 verified, 0 failed, 0 unknown IDs**, in **41 min** wall clock. Per-block
table in `docs/session-state.md`.

**Budget ~45 min at March size.** Cost concentrates in the high-`k`, high-claim blocks — block 6
`(0.5, 1000)` alone took 13.1 min while the three `k=50` blocks together took under a minute. Scale
by claims x k, not by block count.

Expect a scatter of **`ANTENNA_SNAPPED`** warnings — 59 of 4,650 antennas, at 1.1e-10 to 1.1e-9 m.
That is one to two ULP at these coordinates. The flag fires on any displacement that is not
bit-identical, so it is not a proximity complaint. **Ignore it.**

## 7. Package and submit

```bash
python scripts/package_submission.py --solution outputs/final.txt
```

If the solution file was produced by an older build carrying blank separator lines, add
`--normalize-legacy`. Files produced by current code need no such thing — they emit 27 content
lines with no separators.

Packaging is rehearsed end to end: bundle extracted to a clean directory, fresh venv, installed
per the shipped instructions, CLI works, real dataset loads, shipped source passes its own tests,
SHA-256 matches across source, bundle and manifest.

**Regenerate from the August solution — do not ship the zip already on disk.**
`outputs/submission/mz_giscup_26_submission_20260810.zip` is a **March-sample** bundle and its
`source/` predates commit `3f381bb`. It exists as proof the packaging path works.

**What the official page requires of the zip** (verbatim, re-checked 2026-08-10): *"a zip file
including the following: 1. A text file with the solutions for each of the sub-problems... 2. A
folder that has your source code, along with instructions for compiling and running the program."*
`package_submission.py` produces exactly this shape.

**Before you send it, confirm by eye:** 27 content lines, nine `(tau, k)` headers, no blank
separators, exactly `k` coordinates counted in each block, and a third line present in every block
even if empty.

**Submitting — EasyChair** (`https://easychair.org/conferences/?conf=giscup2026`), confirmed live
2026-08-15. An account is required. The archive may be `.zip`, `.tgz`, `.tar`, or `.gz`, and must
contain the solution text file plus a source folder with build/run instructions — exactly the shape
`package_submission.py` emits. Log in and confirm the submission form is reachable **before** the
bundle is ready; five minutes early beats discovering an access problem at hour 23. If EasyChair is
unreachable, email the organisers (`alowe@esri.com`, `ashashidharan@esri.com`) with the bundle
already built.

## 8. If the extract is much bigger than 12,860 buildings

Cost is roughly linear in buildings for verification and in candidates for the matrix build and
greedy. **Both time-buying levers were measured on 2026-08-09 and ranked. Neither is free — spend
them in this order, and only as far as you must.**

| order | lever | flag | time bought | score cost |
|---|---|---|---|---|
| 1 | 2× candidate prune | `--candidate-stride 2` | **~1.7 h** | **~0.07 subproblems** |
| 2 | 300 m cull | `--visibility-radius 300` | ~0.8 h | **~0.79 subproblems** |

**Both are OFF by default and that is a decision, not an oversight** (#9 re-decided 2026-08-10, #20
closed 2026-08-09). Do not reach for either unless §3's sizing says the window is genuinely
threatened. Spending a certain score cost against a contingency that has not materialised is the
failure this table exists to prevent.

1. **Prune the candidate pool 2× first — it strictly dominates.** It keeps the vertex half
   (`--candidate-stride 2`, implemented 2026-08-09) and buys roughly twice the time at about a
   eleventh of the cost. It halves the matrix build **and** halves greedy, because the argmax is a
   popcount over every candidate row.

   **It is NOT free**, despite an earlier sizing that said so. That figure — one serviced building
   of 14,708 — was measured in-sample, with *baseline* greedy, pooled at k=500. Against lever A it
   costs −0.18% at `(0.75, 500)` but **−2.03% at `(0.75, 50)`**, and under relative scoring the
   small-count blocks are worth exactly as much as the large ones.

2. **Cut the radius to 300 m only if the prune is not enough.** It buys *only* the matrix build —
   greedy costs the same, because a sparser matrix has the same number of rows of the same width.
   Measured cost across six blocks: −5.4% of claims but **0.79 subproblems**, concentrated in the
   low-k blocks (−28.3% at `(0.5, 50)`). Note it verifies at 600 m under the default factor 2.0,
   which is *tighter* than the 800 m the measurement used — so treat 0.79 as the optimistic bound.

3. **Raise `--verify-workers`** if the host has more than 16 cores. Do not expect more than the
   4.70× the gate models at 12 — though a *quiet* host measured 7.3×, and the gate now prints that
   as a third row without letting it set the verdict.

4. **Do not raise the radius.** 600 m was measured at 4.36× the build time of 400 m for +8.5%
   visible pairs, and 800 m was abandoned at 1.1× headroom.

5. **Do not lower `--verify-radius-factor` below 2.0** to save time. That is the pass that makes
   overclaims structurally impossible, and an overclaim is a correctness failure.

**Sizing rule that outranks all of the above:** size any lever **per block**, never on the total
claim count. Three separate levers were mis-sized on 2026-08-09 by pooling — the pooled figure
hides the small-count blocks, which is exactly where relative scoring lives.

## 9. What NOT to do on the day

- Do not round coordinates. `format(x, ".17g")`, always.
- Do not reproject, snap, or normalize the output.
- Do not emit a block with fewer or more than `k` points.
- Do not omit the third line of a block. It may be empty; it must exist.
- Do not tune the objective. Everything was fitted on the March sample; the August extract is a
  different extract, and a tuned parameter that does not transfer is worse than no parameter.
- Do not trust local validation as a score estimate. It is a rejection framework. It can tell you
  something is broken; it cannot tell you what you will score.

  **This survives the official evaluator, and is worth being precise about** *(2026-08-15)*. Running
  the organisers' own scorer (§6) removes the *predicate* risk: it tells you exactly which of your
  claims they will verify, which local validation could only approximate. It tells you nothing about
  **rank**. Scoring is relative — `team score / best submitted score` — so a number from §6 is a
  count of verified buildings, never a placing. Do not let a good count become a reason to stop
  checking, or a bad one become a reason to re-tune at hour 20.
