# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~04:5x: **item-1 mechanism BUILT + LAUNCHED:
phase-scheduled multi-teacher, the track's only surviving open lever.**
Every static combined-tick reweight/rescale (combined_skip,
combined_dose, yaw_arm_scale, omega_boost, selective_omega_boost —
the ~20-arm grid closed 09-04/09-05) held ONE fixed target/weight for
the WHOLE run; none varied the target over TRAINING PROGRESS. New
mechanism (`train.bc_anchor_multiteacher_blend`+`_schedule_frac`,
default 0.0/1.0 = legacy bit-exact off): sim_env runs a SEPARATE
persistent scripted-gait clock alongside the walk BC-anchor teacher,
same wall-clock ticks but forward speed always zeroed (the undegraded
pure-turn geometry a combined tick would command if turn-only) — a
first same-object double-query attempt was REFUTED by its own
regression test (TripodGait's EMA smoothing returns a stale dt=0 on a
same-tick 2nd call) before landing on the separate-object design.
`bc_anchor.py` blends the two targets at LOSS TIME (only it knows
`_current_progress_remaining`) ramping 0 -> the knob's value over the
first `bc_anchor_multiteacher_schedule_frac` of progress. 137/137
`rl_move/tests/test_bc_anchor.py` green (10 new). Snapshotted
(`exp/...multiteach-b05`). Launched as a pre-registered 4-arm canary
grid (blend {0.5,1.0} x seed {0,1}, schedule_frac=0.5 mirroring this
recipe's own `--log-std-anneal-frac 0.5`, 2M steps, same
probe_turn_authority gate the whole lever family uses) —
`...-cap29-stdwalklohi-multiteach-b{05,10}{,-s1}`, all 4 VERIFIED
RUNNING (train-2/3/5/+1). Next cycle: triage vs the same comparator
every prior lever in this family used (see `rl_docs/runs/...
-selomegaboost4p0-s1.md` for the exact numbers).

Prior updates (09-04 ~13:2x..09-05 ~04:0x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a,5b}_
trim.md`.

## Next (updated 09-05 ~04:5x)

1. **Triage the phase-scheduled multi-teacher canary grid** (4 arms,
   see Update). A 4/4 FAIL (same sign-asymmetric pure-turn regression
   as every prior static lever) closes the reward/supervision-side
   lever space for good, leaving only a gait-structure change
   (turn-dedicated tripod phase offset) or a DONE-gate renegotiation.
   A PASS/INFORMATIVE cell reopens acquisition follow-up.
2. **DR-draw correlation — CLOSED.** No dominant DR field at n=20;
   k=8 is the standing ceiling dose (now also known to cost slip on
   the literal gate — do not re-promote mlcontprice8 or raise dose).
3. **Steering branch — CLOSED, both seeds, all axes** (09-04 ~17:0x
   sweep + this cycle's architecture-swap/turn-skip/cap-recalibration
   closures). No further lever acquisition; frozen parents
   (`cap29-stdwalklo-hi{,-s1}`) remain the reference. Rise-stall
   stays CLOSED.
4. **Closed** (archives 09-02{,b..h}..09-05a): architecture-split;
   lever/dose/seed sweeps incl. `TripleGruActorCriticPolicy` turn-core
   swap; `combskip`/dose-bracket ablations; cap29 acquisition
   (PARTIAL); log_std anneal grid; sto/det convergence; resamplematch;
   rise over_current dig-in; semantics-bank twins; IK-feasibility;
   mlcontprice2/8/16 (k=8 ceiling, costs slip); steering FAIL-wall
   dig-in; DR-draw n=20; mlcontprice8 literal DONE-gate (FALL);
   dir_err_cap miscalibration (REFUTED).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,
> kk,ll}, 09-05{a,b}. Current state = newest Update at the TOP; don't
> act on archived Next.

## Fleet capacity note (updated 09-05 ~04:5x)

4 GPU slots now BUSY with the multiteacher canary grid (train-2/3/5/
+1), 7ish free. Stale mixedsession/eval_checkpoint jobs may still
linger on other pods — harmless CPU, not launch-blocking; cleanup
lever: `ops.sh procs <pod>`. Every OTHER track non-launchable by
design (`joystick`/`amp`/`cpg` DONE/maintenance; `walkcurr` RETIRED;
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

