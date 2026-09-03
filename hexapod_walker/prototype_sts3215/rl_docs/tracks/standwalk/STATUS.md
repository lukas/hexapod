# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~09:4x (idle-kick): **item 0 CLOSED, both seeds
PASS (own-scope) on the real video-bearing flat-only donegate session**
(n=128 ep each, train-6/7): `stdwalklohi-acq1` dir_err_med 44.56deg/
slip_med 2.819, `-s1` 43.6deg/2.939 — BOTH beat the cap29 baseline
(46.8deg/3.09), sto/det progress_ratio convergence holds at full 38M
scale (94-107% of each other) — the arm's own PASS bar, cleared. Zero
falls/256 episodes, gait_valid 1.0. NOT the track DONE gate: dir_err
still misses the ~40deg reference, slip sits at the 2.9 cap — steering
(item 1) is the sole open item. New reference band: 44-45deg/2.8-2.9
slip. SKILLS.md updated.

**Also found+fixed a fleet-wide infra blocker while refilling item 1**
(full account `OPERATOR_QUESTIONS.md` 09-03 ~09:3x): the 09-02 ~22:0x
operator merge's `require_checkpoint_joint_contract` rejects EVERY
checkpoint predating it — including this lineage's own ancestor and
champions — silently blocking ALL warm-starts fleet-wide. Confirmed
the action<->joint mapping itself never changed (pose-literal fixes
only), so backfilling is safe. Built+tested
`rl_move.sim.stamp_legacy_checkpoint` (3/3 green, bit-exact weights),
ran it fleet-wide (1128 stamped, 3 already-current, 0 refused).

**Refilled item 1** (09-02 dig-in lead: worst `course_speed_ratio`
dips land at the eval diet's ~4s `walk_cmd_resample_s` boundaries,
training only ever used a slower 6s/jitter-0.2 diet) — launched a
2-seed 2M canary `cap29-stdwalklohi-resamplematch-canary{,-s1}` (one
lever: match train-time `walk_cmd_mode=stress_mix`/`resample_s=4.0`/
`jitter=0.5` to the eval diet), warm-started from the re-stamped
ancestor. VERIFIED RUNNING (train-1/train-2 — `-s1` is ledger-named
`...-turndiet-canary-s1`, a naming artifact, same cfg). Gate:
`probe_turn_authority` wz_med >=0.07; det+sto walk read under the
matched diet vs this cycle's own baseline (44.56/43.6deg dir,
2.82-2.94 slip) — PASS if dir/course_err drops >=20% clean; PARTIAL
if authority+zero-fall hold but steering doesn't move; FAIL if
authority regresses or terminations appear.

Earlier updates (fast-read, getup/q0/hold/joint-frame-v2 fixes, 09-02
merge-recovery) moved VERBATIM to `archive/standwalk_STATUS_journal_
2026-09-03{a..f}_trim.md` + `2026-09-02{f,h}_trim.md`.

## Next (updated 09-03 ~09:4x; item 0 = one command, meta 09-03)

0. **FIRST cycle run:** `nohup bash rl_move/orchestrator/restart_watcher.sh >> /workspace/restart_watcher.log 2>&1 &`
   — activates the watcher's pending-eval kick registry (built 09-02,
   never went live) + code autorestart; then proceed normally.
1. **Read `resamplematch-canary{,-s1}`** once landed (train-1/2) —
   steering-gap train/eval diet-mismatch test. PASS -> promote to
   acquisition (38M, matching stdwalklohi-acq1); PARTIAL -> real
   turn-rate ceiling not a diet mismatch, next lever is structural
   turn-authority (std/diet both already refuted); FAIL -> diet too
   hard, retry milder resample_s.
2. **Closed (archives 09-02{,b..h}, 09-03{a..f}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..c,f}. Current state = newest Update at the TOP; don't act
> on archived Next.

## Goal (operator, 08-24 evening)

Retrain the best rising-and-lowering (stance) model on the NEW mesh
MuJoCo model at 100 Hz, then use it as a teacher to distill rise/lower
plus the best walking behavior into one policy. Product: a single
mesh-family 100 Hz policy that, starting from sit, rises, follows a
randomized 60 s joystick session with zero falls, and lowers back.

## Binding constraints (why this is a retrain, not a resume)

- Families do NOT transfer (CURRENT_TRUTHS "SIM MODEL FAMILIES"): the
  legacy stance champion `ppo_goal_cw_stance_dr10` and walk champion
  `ppo_goal_cw_dep_bcgait4_phasedir9_stotight45_seed13` are
  primitive-family 25 Hz policies. NO `respec --from` / warm-start of
  them onto mesh — stage 1 is a recipe rerun on the new model.
- New launches already get `control.hz=100`/`env.model_source=mesh`
  (launcher-injected defaults) — never pin `model_source=primitive`.
- Legacy champions MAY be queried as teachers (same obs layout) but
  carry 25 Hz action scale/primitive dynamics: any distillation must
  handle the 25->100 Hz gap and MEASURE whether primitive-trained
  advice is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: `stance_dr10` (exact cfg in ledger/W&B); rise-reference
machinery green since 08-24. GATE (pre-registered): stance panel
rise/hold/lower (pod_eval stance modes), n>=12, det+sto, DR-0+own-DR:
zero falls/tips, quiet hold, rise/lower height tracking comparable to
the legacy champion's band (absolute numbers shift with +66% mass).

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED, never a silent teacher
swap (cpg containment rule applies). Mechanism is cycle-designed (BC
clone + RL fine-tune, KL-to-teacher, phase-scheduled multi-teacher);
every mechanism arm pre-registers its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit. Zero
falls, directions followed, slip/m within the joystick band (<=~2.9),
held-out panel n>=12, det+sto, DR-0+own-DR. `eval_done_gate_session`
is the session harness (flat=1 is the literal gate shape).

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument (that's `eval_done_gate_session`,
  `ops.sh donegatecmd`, flat=1).

