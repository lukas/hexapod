# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~01:5x (idle-kick, item 0's read still mid-flight):
**Found + fixed a THIRD instance of the joint-frame-v2 stale-plant-
literal bug — this time inside `test_task_semantics.py` itself**, the
one file the 09-02 ~23:5x audit had cleared ("every ~16 TripodGait
import uses `sim_gait_compat` consistently"). That audit was right
about the TripodGait path but missed 12 helpers that ALSO build a RAW
plant pose (`plant_rad`/`stork_rad`/`topple_rad`/`bellysit_rad`/
`_stopcurrent_rollout`'s own literal) fed straight to `q_rad_to_action`,
bypassing `sim_gait_compat` — same bug, same fix shape: added
`RAW_PLANT = (20.0, 100.0)` (robot_abs equivalent of `WALK_PLANT`'s
sim-relative 80) for the bypass literals only; `WALK_PLANT` itself is
unchanged (still correct for the TripodGait path). Decisive zero-
training A/B on `_stopcurrent_rollout`'s still/brace twins: at the
stale literal "still" drew MORE current (0.439A) than "brace" (0.322A,
BACKWARDS) and the isometric-fight charge barely fired (0.97 vs the
1.0 bar); at the fix, "still" settles to 0.160A and "brace" separates
cleanly at 0.268A with a 16.1-pt margin. Verified: `test_stopcurrent_
reprices_the_isometric_fight` now PASSES (was one of the 09-02 ~23:5x
"10 plant-literal-cascade" reds); the other 9 in that set (4 walkcurr_
pf-family, low-priority/retired-track, + 5 with confirmed DIFFERENT
root causes) correctly stay red, not papered over. A full whole-file
regression is running in the background (`/tmp/full_after_fix.log`,
not finished at cycle end) to confirm zero regressions beyond the
targeted 10-test check; the manual per-site code audit (all 12 touched
call sites individually read) already gives high confidence. **Found
but NOT fixed:** a related, likely LARGER bug where several helpers
(`_hold_rollout`, `_lower_rollout`, `_getup_rollout`'s freeze/stilt)
feed raw `env.data.qpos` (MuJoCo-native, i.e. mujoco_rel) straight to
`q_rad_to_action` without the `mujoco_rel_rad_to_robot_abs_rad()`
conversion — measured on `_hold_rollout`'s "quiet" policy: un-fixed it
drifts 4.12mm off its settled height over 15s; converting q0 first
drops that to 0.44mm. Flagged for a dedicated next dig-in (full
derivation: `OPERATOR_QUESTIONS.md` 2026-09-03 ~01:2x-01:5x entry) —
touches more helpers than one cycle should rush. No training-default
cfg touched. Snapshotted+pushed. Item 0 (`cap29-stdwalklohi-acq1{,
-s1}` flat-only session read) confirmed still progressing live on
train-6/7 throughout (dr0 sto sub-pass ~20-25/32, normal pace).

Earlier 09-02 updates (the second joint-frame-v2 bug across 8
production/test files, the merge-recovery emergency, the
`k_walk_course_income` plant-stance-literal root-cause+fix, the
`stdwalklohi-acq1{,-s1}` 38M finish + item-0 session-read dispatch,
config archaeology, the stdwalklo grid launch+read, cap29 zero-
training session read + windowed course-metrics tooling) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-02h_trim.md`
and `archive/standwalk_STATUS_journal_2026-09-02f_trim.md`.

## Next (updated 09-02 ~18:3x)

0. **READ `logs/ckpt_eval/cw_..._stdwalklohi_acq1{,_s1}_donegate_
   flatonly/session_verdict.json`** once both land (in flight on
   train-6/7, n=32 det+sto DR-0+own-DR each): does the sto/det
   walk-progress convergence survive to full budget, and does
   direction_err_med/slip_per_m_med improve on the cap29-acq1
   baseline (46.8 deg/3.09)? Gate text in the ledger. PASS -> new
   steering/slip reference; PARTIAL (falls+convergence hold, steering
   doesn't) -> item 1 is the next target; FAIL (sto regresses at
   scale) -> credit-assignment angle (08-31 yaw-credit probe) is next.
1. Steering gap (windowed course_err ~22-23 deg, cap 2.9) — was
   secondary to the sto/det asymmetry; worst course_speed_ratio dips
   land at the ~4s `walk_cmd_resample_s` boundaries, consistent with
   the closed turn-authority ceiling (wz_med 0.075-0.21). Revisit once
   item 0 reads back.
2. **Closed (full list in archives):** update-size constraints, reward
   pricing, exploration magnitude, anchor dose, turn-skip, yaw-credit
   clip doses, mixedsession/diet scoping, duration-mismatch,
   switch-jump/ramp/height/mass/frame-blend/cap-diagnostic/current-
   confound (see 09-02{,b..f} archives), cap29 training-time
   acquisition (PARTIAL, steering/slip didn't transfer), walk-core
   log_std anneal dose grid (`hi` PASS 2/2, `mild` FAIL - dose too
   low, both closed this cycle-window).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`, `2026-09-02d_trim.md`, `2026-09-02e_trim.md`,
> `2026-09-02f_trim.md`, `2026-09-02g_trim.md`, `2026-09-02h_trim.md`.
> Current state = newest Update at the TOP; don't act on archived Next.

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
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B); rise-reference machinery green since 08-24.
GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument; the gate read is
  `eval_done_gate_session` (`ops.sh donegatecmd`, flat=1).

