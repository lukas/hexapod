# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~10:3x: **item 1 (resamplematch/turndiet-canary-s1)
CANARY PASS (mechanism)/behavioral: diet-match REFUTED as the sole
steering-gap driver, cross-seed replicated.** `turndiet-canary-s1`
(seed 1 of the resamplematch pair): `probe_turn_authority` is strong
(wz_med 0.216-0.220/-0.177-0.180 rad/s vs +-0.25 cmd, err_med
0.064-0.074, well above the 0.07 floor) — turn AUTHORITY is intact.
But a same-instrument fast walk-only read (`eval_checkpoint.py
--modes walk`, n=16 x {dr0,ownDR} x {det,sto} = 64 eps, no video,
spare pods) shows the diet-match lever does NOT cleanly win:
`direction_err_med` 37.6/42.5/39.8/44.1deg is flat-to-worse vs the
44.56/43.6deg session baseline (no subgroup clears >=20%);
`course_err_1s_med` is a genuine mixed bag — 30-45% BETTER under
DR-0 (15.1/18.3 vs 22.6-28.2 baseline) but 65-100% WORSE under own-DR
det (44.8 vs 22.6-28.2); `slip_per_m_med` is UNIFORMLY WORSE in every
subgroup (3.47/4.54/4.50/4.65) vs both the session baseline
(2.82-2.94) and a newly-established same-instrument PARENT baseline
(`stdwalklohi-acq1` own fastwalkcheck: 2.29/2.92/2.97/3.12,
`logs/ckpt_eval/standwalk_stdwalklohi_acq1_s0_fastwalkcheck/`) —
breaching the gate's ~3.0 slip ceiling every time. Termination rate
(1/16 owndr/sto) matched the PARENT's own established own-DR noise
floor (also 1/16 in that subgroup), not a new fall mode. Video frame
strips confirm clean six-leg gait, gait_valid 1.0 throughout.
**Cross-seed replicated** almost number-for-number by the
`resamplematch-canary` sibling (seed 0, verdicted separately, harsher
CANARY-FAIL: a NEW immediate-tilt own-DR fall, 3/16 owndr/det eps —
**this cycle's own raw fastcheck data for that SAME checkpoint shows
0/16 terms in that subgroup**, a discrepancy between two nominally-
identical `eval_checkpoint.py` reads worth a future dig-in, not
reconciled here; direction/course/slip numbers agree closely either
way). Net conclusion both readings share: the diet mismatch is NOT
the (sole) driver — matching it buys DR-0-only, inconsistent course
gains at a real slip/own-DR cost. (Addendum: the resamplematch-canary
verdict's falls sub-claim was REVISED after this cross-check — my
own-DR 3/16-terms read reproduced byte-identical across 2 of my own
invocations, but is unreconciled against this cycle's 0/16-terms read
of the same checkpoint; likely a knife-edge own-DR draw landing on
opposite sides of the tilt_roll boundary between processes, not a
clean deterministic difference. Dig-in flagged in
OPERATOR_QUESTIONS.md, doesn't change the FAIL verdict — steering-
not-improved + slip-breach alone already fails the gate's PASS bar.)
**Both mild-dose canary seeds now RUNNING**
(`cap29-stdwalklohi-resamplematch-mild-canary` train-1,
`-mild-canary-s1` train-2, seed pair launched this cycle, ~2M steps
each, near done at cycle end) — read both before any further
diet-family arm. If they also fail, pivot
to structural turn-authority (not diet): probe-confirmed authority is
strong turn-IN-PLACE; untested is whether forward+turn CO-OCCURRENCE
is under-trained (`walk_yaw_zero_frac=0.5`/`walk_turn_in_place_
frac=0.30` held constant across every diet arm so far).

Earlier updates (item 0 close, joint-frame-stamp fix, fast-read,
getup/q0/hold/joint-frame-v2 fixes, 09-02 merge-recovery) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03g_trim.md`
+ `2026-09-03{a..f}_trim.md` + `2026-09-02{f,h}_trim.md`.

## Next (updated 09-03 ~10:3x)

1. **Read `resamplematch-mild-canary`** once landed (train-1) — does a
   milder resample_s/jitter dose avoid the own-DR fall/slip cost while
   still nudging steering, or does even this dose fail (implicating
   `walk_cmd_mode=stress_mix` itself, not the resample rate)? PASS ->
   promote; FAIL both dose levels -> diet family closed, pivot to the
   structural forward+turn co-occurrence lever above (untested:
   reducing `walk_yaw_zero_frac`/`walk_turn_in_place_frac` so more
   training episodes require simultaneous forward+turn, since the
   probe shows turn-IN-PLACE authority is already strong).
2. **Closed (archives 09-02{,b..h}, 09-03{a..g}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS); resamplematch/turndiet-s1
   diet-match hypothesis (refuted, this update).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..c,f,g}. Current state = newest Update at the TOP; don't act
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

