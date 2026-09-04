# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~09:4x (meta): transtress/cont canary quartet
FINISHED + prestaged, triage owed (Next item 1); steering axis awaits
the cont{,-s1} confound read (Next item 2). 08-3x banner (operator
directive fb_20260904T074505: over_current audit — see
`logs/ckpt_eval/oc_audit_09-04/OC_AUDIT_SUMMARY.md` + CURRENT_TRUTHS
ruling (rail hits alone never condemn; cap29's 2.9 threshold can NEVER
trip vs the 2.64 A rail); `eval_cmd_stress.py` promotion suite +
cur_rail_frac/cmd_rate/jerk/slew_sat telemetry (champion pins the
37.5 deg/s slew cap 30-70% of transition ticks); `goal.mode_seq_stress`
lever, default OFF bit-exact; snapshot 2751a537) — details archived:
`archive/standwalk_STATUS_journal_2026-09-04ee_trim.md`.

## Next (updated 09-04 meta)

1. **Universal-command branch (operator directive 09-04) — TOP ITEM.**
   All 4 canaries FINISHED + prestaged (~08:5x): `cap29-stdwalklohi-
   transtress{,-s1}` (transition-stress diet: mode_seq_stress grammar
   + 2.5-9 s segments + 3 s cmd resample) vs `cap29-stdwalklohi-
   cont{,-s1}` (matched plain continuations = baselines). Gate:
   `eval_cmd_stress` (seed base 93000) — zero MECHANICAL terms,
   completion/walk within bands of control, smoothness medians not
   worse; over_current reported separately, never vetoes alone. If the
   diet holds at 2M, next rung is an acquisition-length transtress
   run; if smoothness stays pinned at the slew cap, THEN design a
   measured action-rate/jerk objective (semantics-bank entry first).
2. **Steering branch — READ `cont{,-s1}` AS THE MISSING CONTROL FIRST
   (meta 09-04).** Every steering-lever FAIL (~26 canaries, 6 lever
   families) was scored against the FROZEN cap29-stdwalklo-hi{,-s1}
   checkpoints; the one prior continuation control (dualcontinue-
   noyawcredit) ALSO dropped yaw_credit/log_std_split. cont{,-s1} =
   plain 2M continuations, mechanisms kept — run their pure-turn
   probe_turn_authority vs the frozen baseline BEFORE any new lever/
   gait-structure/gate-renegotiation move: if plain continuation alone
   breaches the 10% pure-turn cap, the whole FAIL wall measured
   continuation drift, not lever harm, and the axis must be re-scored
   against matched-continuation controls. selomegaboost4p0-s1 verdict
   still owed: checkpoint IS on the controller (pulled 07:12); its
   prestage evals died with old train-4 — rerun `ops.sh podeval` on a
   live pod. Rise-stall branch stays CLOSED (09-03o archive).
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa,cc,dd}):**
   architecture-split; yaw-arm-scale dose x seed grid (4/4 FAIL);
   `combined_yaw_amplify_scale` + "detangle" idea (both REFUTED
   zero-training); update-size/reward/exploration/anchor/turn-skip/
   yaw-credit/diet/duration/switch-jump/frame-blend/current-confound/
   combined-tick-anchor-skip/omega-boost/combined-yaw-boost sweeps;
   cap29 acquisition (PARTIAL); log_std anneal dose grid (`hi` PASS,
   `mild` FAIL); sto/det convergence-at-scale (PASS); resamplematch
   diet-match-rate hypothesis; rise over_current dig-in/faithful
   replay; steering/rise-stall semantics-bank twins (both PASS);
   IK-feasibility groundwork.

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd}. Current
> state = newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 meta ~09:4x)

All pods idle (transtress/cont quartet finished, awaiting triage).
train-4 OOMKilled 08:06 -> deleted + recreated from the fixed 4Gi-dshm
scaleout spec (meta 09-04); still Pending (g142d86 at 98% CPU requests,
other tenants) — when it goes Running, run `bootstrap_train_pod.sh
hexapod-mjx-train-4` + `pod_torch_capability.py install` before use.
g131eec is now SchedulingDisabled (train-2/3 keep running). Every OTHER
track remains non-launchable by design (`joystick`/`amp`/`cpg` DONE or
maintenance-only; `walkcurr` RETIRED; `todaypolicy` DELIVERED).

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

