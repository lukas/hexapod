# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~07:0x (**SELECTIVE per-leg omega boost — the
untried candidate the prior cycle named — built, validated
zero-training, and now spending its first RL canary (2-dose x
2-seed, 4 runs, all VERIFIED RUNNING).**)

Unlike every REFUTED candidate on the "reshape the commanded yaw
ANGLE" axis (uniform `combined_yaw_arm_scale`, selective
`combined_yaw_amplify_scale`, the unwired "detangle" idea — archived
below), this lever changes the TRUE foot target: on a combined tick,
only the 3 legs the vx cross term ATTENUATES below their own
pure-omega magnitude get their foot displacement (dx/dy/dz, hip+knee
included) recomputed with a boosted omega — mirroring the
already-tried UNIFORM `train.bc_anchor_teacher_omega_boost` but
restricted to the legs that actually lose authority. New
`TripodGait.combined_selective_omega_boost` +
`probe_turn_authority.py --scripted-selective-omega-boost` +
`train.bc_anchor_teacher_selective_omega_boost` BC-anchor wiring (13
new tests, 149/149 green overall). Zero-training scripted-teacher
validation (real MuJoCo physics, not the kinematic replay): dose
3.0-4.0 raises combined wz_med from ~0.081/-0.077 to
0.20-0.24/-0.20-0.24 rad/s — BOTH signs, sign-SYMMETRIC (unlike every
prior lever) — with pure-turn/pure-walk BIT-EXACT untouched; beats
the uniform lever's own best dose on real wz (0.231 vs 0.168 rad/s).
Launched `cap29-stdwalklohi-selomegaboost{3p0,4p0}{,-s1}` (2M-step
canaries, respec off the `yawarm1p5{,-s1}` ancestor, that lever reset
to identity) against the same `cap29-stdwalklo-hi{,-s1}` control used
throughout — VERIFIED RUNNING train-1/2/3/4. Pre-committed decision
rule: sign-asymmetric pure-turn regression like every prior lever
closes the geometry/teacher-lever axis for good; clearing it makes
this the first candidate that is genuinely different in kind (real
torque, not commanded-angle reshape).

Prior banner (per-leg instrumentation + 2 REFUTED candidates closing
the angle-reshape axis) moved VERBATIM to `archive/standwalk_
STATUS_journal_2026-09-04aa_trim.md`.

## Next (updated 09-04 ~07:0x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md`. No reward code
   changed; a future fix should price sustained near-ceiling current
   directly (`over2A_s`-style), not a stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM, awaiting the selective-omega-boost
   canary above.** PASS bar (pre-registered in the ledger/gate text):
   combined wz_med beats the checkpoint-scope comparator (seed0
   +0.110/-0.170, seed1 +0.086/-0.142) on BOTH signs, pure-turn/
   straight-walk regression <=10% vs control, no new terminations.
   If it fails the same sign-asymmetric way as every prior teacher-
   lever (uniform omega_boost, yaw_arm_scale, combined-tick BC-
   anchor-skip), the geometry/teacher-lever axis closes for good and
   the honest next move is a gait-STRUCTURE change (per-leg period/
   tripod-grouping during combined ticks, not yet tried) or an
   escalated DONE-gate turn-authority renegotiation. Do not re-open
   architecture-split (Triple/yaw_critic.py) — done.
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa}):**
   architecture-split; yaw-arm-scale dose x seed grid (4/4 FAIL);
   candidate (iii) `combined_yaw_amplify_scale` (REFUTED
   zero-training); "detangle" idea (REFUTED zero-training, unwired);
   update-size/reward/exploration/anchor/turn-skip/yaw-credit/diet/
   duration/switch-jump/frame-blend/current-confound/combined-tick-
   anchor-skip/omega-boost (both directions)/combined-yaw-boost
   sweeps; cap29 acquisition (PARTIAL); log_std anneal dose grid (`hi`
   PASS, `mild` FAIL); item 0 sto/det convergence-at-scale (PASS);
   resamplematch diet-match-rate hypothesis; rise over_current
   dig-in; rise-stall faithful replay; steering/rise-stall semantics-
   bank twins (both PASS); candidate (i) IK-feasibility groundwork.

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa}. Current state =
> newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~07:0x)

4 GPU pods (train-1/2/3/4) now running the selective-omega-boost
canary grid (2 doses x 2 seeds, ~2M steps each, ~25-40 min ETA). 7
pods free. Every OTHER track remains non-launchable by design
(`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr` RETIRED;
`todaypolicy` DELIVERED).

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

