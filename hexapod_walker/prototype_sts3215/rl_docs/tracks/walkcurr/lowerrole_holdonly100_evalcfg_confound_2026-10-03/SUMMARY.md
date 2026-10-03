# ROOT CAUSE FOUND: the holdonly100 "92% forward" / matched-seed
# PASS-MECHANISM win was an eval-cfg auto-replay confound, not a real
# checkpoint-weight improvement. REVERSED. (2026-10-03, zero GPU spend)

## Plain-English summary
The lower-role champion swap adopted earlier today (`goal.lower_hold_
only_frac=1.0`, "holdonly100") looked like a real, matched-seed-proven
improvement (+16/+21/+28 on n=36 at 3 training seeds). It wasn't. The
automated gate harness was silently grading the candidate on an EASIER
version of the task than the baseline it was compared against — every
`lower` episode for a holdonly100 checkpoint started already crouched
at the target depth (skipping the actual descent), while the baseline
was graded on the real task (stand -> walk -> gently descend all the
way to belly rest). Once both are graded on the SAME real task,
holdonly100 does not beat the plain recipe at any of 3 matched seeds —
and the most extreme dose (frac=1.0, s0) scores 0/36 on the real task
(it never practiced descending at all). All 4 affected ledger verdicts
reversed PASS/PARTIAL -> FAIL this cycle; the harness bug is fixed
(`pod_eval.py`, tests added) so it cannot recur for this key class.

## How this was found
Refilling the walkcurr track's "re-derive a clean baseline" Next item
(from `lowerrole_sectoraware_fix_2026-10-03`'s own Part 3, which had
already flagged — but not root-caused — a same-day reproducibility gap
in a related panel), a fresh large-n (n=20/heading/arm, n=160/arm
total) 8-heading rerun was done first (see `lowerrole_fulldir_n20_
2026-10-03/raw/`, zero GPU, ~2 min wall-clock parallelized across 16
cells on the controller's 128 cores). That panel's own heading=0 cell
(10%, both with and without `--lower-rot60`) was wildly inconsistent
with the track's own headline number for this exact checkpoint
("holdonly100-s3, 92% forward, ADOPTED"). Rather than file this as
another "inconclusive, noisy" result, this cycle chased it to ground:

1. Confirmed the checkpoint file is BYTE-IDENTICAL everywhere (md5
   matches controller vs its training pod hexapod-mjx-train-2) and
   unchanged since save (mtime predates every eval that used it) —
   ruled out a checkpoint-overwrite race.
2. Confirmed code is unchanged across the relevant commit range (`git
   diff --stat` between the retrain-variance-calibration-close commit
   and the sectoraware-fix-build commit touches only new ADDITIONS —
   `rot60_lower.py` + its wiring — nothing in the shared eval path).
3. Confirmed determinism holds on the SAME pod that produced the
   original number (train-2): a fresh run there NOW gives 2/18+5/18
   (same as the controller), not the archived 16/18+17/18 — ruling out
   a controller-vs-pod hardware/numerics difference.
4. Found the ACTUAL artifact the 92% number came from still on disk
   (`logs/ckpt_eval/cw_stance50hz_rlonly_lowerrole_scratch_sac_s3_
   drramp_holdonly100_acq1_lifecyclegate/gate_seed{0,100}.json`) and
   diffed it episode-by-episode against a fresh same-command rerun:
   `trk_err`/`dist_m` (computed during the deterministic rise+walk
   phases, BEFORE the lower handoff) match EXACTLY every episode — so
   the walk-phase physics are reproducible and the handoff state is
   bit-identical. Only the `lower_ok`/`lower_fall` outcome differs,
   almost every episode. Same input state, same checkpoint, different
   outcome -> the divergence is INSIDE the lower-phase execution.
5. Found the actual AUTOMATED command that produced the artifact in
   `orchestrator/pod_eval.py` (`lifecyclegate` auto-launch, wired
   2026-10-03): it passes `--lower-cfg
   {lifecycle_lower_cfg_delta(all_cfgs)}` — the run's OWN training
   --cfg-set minus the versioned recipe's base CFG_ARGS. For a
   holdonly100 checkpoint, `goal.lower_hold_only_frac=1.0` is NOT in
   the base recipe (it's a new key), so it survives into the delta and
   gets REPLAYED at eval. The hand-typed "repro command" this item's
   own earlier SUMMARY.md documented (and every forensics panel this
   week copied) used ZERO `--lower-cfg`, believing that "matched the
   official protocol exactly" — it did not.
6. DECISIVE CONFIRMATION: re-ran the exact documented command WITH
   `--lower-cfg goal.lower_hold_only_frac=1.0` added back —
   reproduces the archived artifact BYTE-FOR-BYTE (16/18 + 17/18,
   identical `lower_fall`/`lower_ok` per episode). Mechanism nailed.

## Why this key changes the TASK, not just a training-side weight
`goal_task.py`'s `lower` mode sampler (`goal.lower_hold_only_frac`):
with probability `frac`, the episode skips the descent ramp entirely
and starts ALREADY at the full target depth, height reference flat at
target for the whole episode ("concentrated, undiluted practice at
exactly the sustained-hold sub-skill" per its own design comment). At
frac=1.0 this is not a dose of extra practice, it is the ONLY task a
holdonly100 checkpoint ever sees in training: it has never performed
an actual descent. Evaluating it with the SAME flag at eval time tests
exactly the sub-skill it was trained on — informative for "did the
curriculum change teach the sub-skill it targeted" but NOT a measure of
composed-lifecycle readiness (the real target task), and not a fair
comparison against a baseline scored with delta=[] (the plain
recipe's own --cfg-set has no such key, so it was always scored on the
real full-descent task).

## Corrected matched-seed table (TRUE protocol: zero `--lower-cfg`,
both recipes, same training seeds, same stance/walk/heading=0, n=18 x
seed{0,100}=36, direct-arm `lower_ok`; raw JSON in `raw/`)

| seed | plain (drramp-acq1) | holdonly100 (TRUE eval) | archived (confounded) claim |
|---|---|---|---|
| s0  |  26/36 (72%, standing champion, unaffected) | **0/36 (0%)**  | 27/36 (75%) PARTIAL |
| s2  |   5/36 (14%) | **2/36 (6%)**  | 21/36 (58%) PASS-MECHANISM |
| s3  |  12/36 (33%) | **7/36 (19%)** | 33/36 (92%) PASS-MECHANISM, ADOPTED |
| s4  |   2/36 (6%)  | **1/36 (3%)**  | 30/36 (83%) PASS-MECHANISM |

holdonly100 does not beat plain at ANY of the 4 seeds under the real
task; it is worse at every one (consistent with the mechanism: it
trades away real-descent capability for pure hold-sub-skill practice).
This matches the s2/s3/s4 gate's OWN pre-registered FAIL branch
("scores similarly or lower at >=2/3 matched seeds -- confirms the
whole lever-harm campaign ... was noise") and the s0 gate's own FAIL
clause ("the policy loses the real-entry-pose hold transition it never
practices under frac=1.0") — both gates were right about what FAIL
would mean, the harness just never actually tested that condition.

## What this reverses / changes
- Ledger: `cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s2,s3,s4}-
  drramp-holdonly100-acq1` all PASS/PARTIAL -> FAIL this cycle (own
  verdict text has the per-run detail).
- `walkcurr/STATUS.md`: the "ADOPTED...holdonly100-s3 new champion"
  paragraph is WRONG; champion reverts to `drramp-acq1 s0` (26/36),
  unchanged from before the whole holdonly100 excursion. The `goal.
  lower_hold_only_frac` lever is CLOSED at both doses (0.5 and 1.0),
  now for a real reason (catastrophic real-task regression) rather
  than "noise."
- `todaypolicy`'s `bundle_rlonly_lifecycle_v2` lower-role swap to
  holdonly100-s3 (91.7%/100% composed, reusing this same confounded
  artifact) is REVERTED to `drramp-acq1 s0` this same cycle.
- The 8-heading "does the forward gain generalize off-axis" framing
  (`lowerrole_fulldir_headingsign_forensics_2026-10-03`,
  `lowerrole_sectoraware_fix_2026-10-03`) had no real 92%-forward
  baseline to generalize in the first place — its headline framing is
  retired, but its RAW per-episode mechanistic observations (over_
  current dominance, the universal L2/L5-hip pair, the heading-sign
  split candidate, the rot60_lower.py tool itself) are untouched
  factual findings about the TRUE-protocol checkpoint and remain
  available evidence; they were just never validly contrasted against
  a "92% forward, needs to generalize" premise.
- A fresh, protocol-consistent (zero `--lower-cfg` throughout, n=20/
  heading/arm, n=160/arm total) 8-heading panel for THIS SAME s3
  checkpoint was already run this cycle (`lowerrole_fulldir_n20_
  2026-10-03/raw/`) as part of chasing this down: direct-arm aggregate
  24/160 (15%), no clean heading-sign split at this n (negative 17%
  vs positive+180 19%, well inside binomial noise) — roughly uniform,
  unimpressive performance across all headings under the TRUE
  protocol, consistent with (not contradicting) the corrected matched-
  seed table above. The `--lower-rot60` sector-aware wrapper built
  earlier today remains untested at a decisive n (its own panel was
  also noise-dominated at n=64/arm); not re-chased this cycle given
  holdonly100 itself is now closed.

## Harness fix (prevents recurrence)
`orchestrator/pod_eval.py`: `lifecycle_lower_cfg_delta` now excludes a
named tuple of episode-sampling-curriculum keys (`goal.lower_hold_
only_frac`, `goal.lower_partial_frac`, `goal.lower_belly_start_frac`,
`goal.lower_start_bank`, `goal.lower_start_bank_frac`) from the eval-
time `--lower-cfg` replay, regardless of what the candidate trained
with — the composed gate must always grade the real target task, only
physics/reward/safety cfg keys should ever be eval-replayed. Tests in
`tests/test_pod_eval_lifecycle_curriculum_key_strip.py` (orchestrator
checkout) pin this both ways (the named keys stripped, an unrelated
goal.* key untouched, the pre-existing dr_stage_ramp_steps/base-CFG_
ARGS behavior unchanged).

## Next
1. Champion for composed lifecycle readiness is `drramp-acq1 s0`
   (26/36 forward, TRUE protocol) — unchanged, back to the pre-10-03
   state. No new lever is pre-registered; the terminal L2/L5-hip
   over_current concentration remains the open, unsolved mechanism
   (walkcurr/STATUS.md's standing "no cheap next lever identified"
   gap stands, now on the correct baseline).
2. Any FUTURE lower-role lever that touches a goal.lower_* episode-
   sampling key should state explicitly in its own gate text whether
   the eval is meant to test the trained sub-skill (replay the key,
   useful for curriculum-design diagnosis only) or composed-lifecycle
   readiness (never replay it) — this ambiguity is exactly what broke
   here.
3. Not done this cycle (scope/budget): auditing whether any OTHER
   already-CLOSED lower-role lever (`lower_start_bank`/`entrybank020`,
   `lower_partial_frac`) was scored through the same confounded
   auto-replay path before today's fix. Those items were hand-podbg'd
   by separate cycles rather than through the 2026-10-03 auto-harness,
   so are LESS likely affected, but this was not verified; flag before
   relying on their exact numbers for a new decision.
   **RESOLVED same-day (refill cycle, zero GPU):** checked every
   `entrybank020`-family ledger entry (the only other closed lower-
   role lever touching a `goal.lower_*` episode-sampling key; grepped
   all `goal.lower_partial_frac`/`goal.lower_belly_start_frac` ledger
   entries -- none exist, those keys were never actually trained/
   scored as a named lever despite existing in code). Confirmed each
   entrybank020 verdict's own text (e.g. ledger
   `004531`/`004532-..-entrybank020-noqvelrestore-acq1`) calls
   `eval_lifecycle_handoff_rlonly.py --lower` directly with an
   explicit `n=12/arm`, not the `pod_eval.py lifecyclegate`
   auto-launcher (which this SUMMARY's Part 1 dates as "wired
   2026-10-03", i.e. it postdates every entrybank020 run by days) --
   confirmed NOT affected by this confound. The entrybank020 closure
   stands as scored. No other closed verdict needs re-checking.
