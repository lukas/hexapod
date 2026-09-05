# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~04:0x: **mlcontprice8 literal DONE-gate read is IN
— FALL (item 1 CLOSED). Reward/architecture lever search for steering
is now EXHAUSTED (~20 arms); a new probe REFUTES the "cap is
miscalibrated" theory.** `session_verdict.json` (n=32, dr0+ownDR,
non-strict, train-9): zero falls, gait_valid 1.0, height_err 3.2mm —
clean. vs the standing best band (`cap29-stdwalklohi-acq1{,-s1}`:
dir_err 43.6-44.56deg/slip 2.819-2.939, n=128): dir_err_med 42.26deg
edges better but slip_per_m_med 3.696 is a clear regression (+26-31%,
breaches the 2.9 cap by far more than the baseline's borderline miss)
— the transtress/hold-load-price branch cost walk quality without
buying enough steering. Standing best stays `cap29-stdwalklohi-acq1
{,-s1}`, itself still short of gate. Combined with the already-closed
dose-bracket/DR-draw/steering-FAIL-wall/arch-swap/BC-anchor-turn-skip
axes (item 4), the reward+architecture lever space for steering/slip
is now **exhaustively searched** (~20 arms: yawarm/yawboost/omegaboost
/selomegaboost/combdose/combskip dose sweeps x2 seeds, log_std anneal
grid, sto/det convergence, resamplematch, `TripleGruActorCriticPolicy`
turn-core swap + `noyawcredit` control, DR-draw n=20 — all FAIL/
CLOSED; frozen `cap29-stdwalklo-hi{,-s1}` stays the reference). Also
this cycle: extended `probe_dir_floor.py` with an opt-in periodic
heading-resample mode (`--resample-s/-jitter/--heading-max-deg/
--blend-s`, default OFF=bit-exact; tests 3/3 green) to test whether
the 40deg `dir_err_cap` was calibrated against an easier static-
heading floor than the session's real 3s-resample/full-circle-heading
dynamic — **REFUTED**: teacher tick `dir_err_med` stays 8.6-9.2deg (2
seeds, 20 flips/60s) even under realistic resampling — the cap is
real/achievable, the ~42-44deg plateau is a genuine unclosed policy
gap. Evidence: `logs/ckpt_eval/..._mlcontprice8_donegate_flatonly/
session_verdict.json`; `/tmp/dirfloor_resample{,_s1}.json`. **No GPU
relaunch this cycle** — every known lever on this recipe is closed
(item 1); next step is a different mechanism CLASS (Stage 2's
pre-declared KL-to-teacher/multi-teacher), needing design+bank work.

Prior updates (09-04 ~13:2x..09-05 ~02:4x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a}_trim.md`.

## Next (updated 09-05 ~04:0x)

1. **Design + build a teacher-distillation mechanism that is NOT
   reward-coefficient dosing on the current recipe** (Stage 2's own
   pre-declared alternative: KL-to-teacher action-distribution match,
   or phase-scheduled multi-teacher). The dose-lever axis is closed
   and the cap-miscalibration theory is refuted (see Update) — the
   ~42-44deg vs teacher's ~9deg gap is real and needs a structurally
   different lever. Scope it, bank-prove any reward-semantics touch,
   THEN launch — the track's only remaining open lever.
2. **DR-draw correlation — CLOSED.** No dominant DR field at n=20;
   k=8 is the standing ceiling dose (now also known to cost slip on
   the literal gate — do not re-promote mlcontprice8 or raise dose).
3. **Steering branch — CLOSED, both seeds, all axes** (09-04 ~17:0x
   sweep + this cycle's architecture-swap/turn-skip/cap-recalibration
   closures). No further lever acquisition; frozen parents
   (`cap29-stdwalklo-hi{,-s1}`) remain the reference. Rise-stall
   stays CLOSED.
4. **Closed** (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa,cc,dd,jj,
   kk,ll}, 09-05a): architecture-split; lever/dose/seed sweeps incl.
   `TripleGruActorCriticPolicy` turn-core swap + `noyawcredit`
   control; `bc_anchor_walk_turn_skip` (`combskip`) ablation; cap29
   acquisition (PARTIAL); log_std anneal grid; sto/det convergence;
   resamplematch; rise over_current dig-in; semantics-bank twins;
   IK-feasibility groundwork; mlcontprice2/8/16 dose bracket (k=8
   ceiling, now known to cost slip); steering FAIL-wall dig-in;
   DR-draw correlation (n=20); mlcontprice8 literal DONE-gate read
   (FALL); dir_err_cap miscalibration theory (REFUTED).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,
> kk,ll}, 09-05a. Current state = newest Update at the TOP; don't act
> on archived Next.

## Fleet capacity note (updated 09-05 ~04:0x)

11/12 GPU slots free (train-6 was Pending on host CPU as of the last
Update — reconfirm before assuming). **No launch this cycle**: every
pre-registered arm and STATUS Next item resolved to CLOSED this cycle
(see Update) — the one surviving Next item is a design+build task
(new mechanism class), not a ready-to-queue arm; inventing an
under-designed reward tweak would be arm #21 of an already-refuted
class. Pods 1/2/3/5/8/10/11 may carry stale mixedsession/
eval_checkpoint jobs from verdicted runs — harmless CPU load, not
launch-blocking, but a slow-accumulating OOM risk on long-lived pods
(3rd+ incident) — cleanup lever: `ops.sh procs <pod>` + kill stale
multiprocessing-fork children before a memory-heavy `--shards`+
`--video` job. Every OTHER track non-launchable by design (`joystick`/
`amp`/`cpg` DONE/maintenance; `walkcurr` RETIRED; `todaypolicy`
DELIVERED).

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

