# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~06:1x: **multiteacher axis CLOSED 4/4, gate
renegotiation REFUTED, AND a first gait-STRUCTURE candidate built +
REFUTED — all zero/near-zero spend, same cycle.** (1) `multiteach-
b05-s1`/`-b10-s1` (seed1) match seed0 (05:40/05:41): all 4 cells fail
pure-turn (past the 10% cap) and/or the combined-tick beat-both-signs
clause, no falls — reward/supervision BC-anchor lever axis CLOSED for
good (~24 arms). (2) Item 2(b) (renegotiate the gate's numeric bar)
independently REFUTED 09-05 04:0x: scripted teacher's own resampled
dir_err floor (8.6-9.2deg) proves the caps real, not miscalibrated.
(3) New `TripodGait.combined_group_duty_skew` (default-off, bit-exact,
SAFE BY CONSTRUCTION — re-times one shared boundary between the two
existing tripod groups so the amplified-heavy group's swing widens,
always exactly one group swinging) built + unit-tested (7 new, 35/35
bank green), wired into `probe_turn_authority.py`; zero-training
scripted sweep (skew +-0.15/0.3/0.44 vs the 0.0 baseline, which
reproduces the pinned 0.0723/-0.0738 reference exactly) shows
combined-tick wz_med MONOTONICALLY WORSE with |skew| in BOTH
directions (0.0723->0.0721->0.0607->0.0284 / 0.0734->0.0599->0.0234)
— REFUTED, the same "no free lunch" pattern as every magnitude lever;
pure-turn stays bit-exact. No RL canary launched (premature given the
decisive negative read). Full derivation/evidence: archives
`2026-09-05{d,e}`.

Prior updates (09-04 ~13:2x..09-05 ~05:4x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a,5b,5c,
5d,5e}_trim.md`.

## Next (updated 09-05 ~06:1x)

1. **CLOSED: reward/supervision-side BC-anchor lever axis** (~24 arms,
   see Updates above) and **item 2(b) gate renegotiation** (REFUTED
   09-05 04:0x). Do not re-attempt a static/scheduled combined-tick
   BC-anchor reweight, and do not question the 40deg/2.9-slip caps.
2. **Gait-structure (item 2a) — whole-group duty skew CLOSED
   (REFUTED); axis still OPEN.** (i) cheap next step: extend
   `probe_joint_tracking.py` with `--group-duty-skew`, split its
   clip-saturation accounting by swing vs stance, to confirm/refute
   whether stance pays back what swing saves (unverified root-cause
   note above) — do this BEFORE (ii) a genuine PER-LEG duty split
   (legs decoupled from their group), which needs its own dedicated
   CoM-in-convex-hull-of-planted-feet stability probe (no longer
   safe-by-construction) and careful design pass — do not half-build
   it.
3. **Everything else CLOSED** (archives 09-02{,b..h}..09-05e; frozen
   parents `cap29-stdwalklo-hi{,-s1}` remain the reference, no further
   lever acquisition): architecture-split + `TripleGruActorCriticPolicy`
   swap; `combskip`/dose-bracket/log_std-anneal/sto-det-convergence/
   resamplematch sweeps; rise-stall + over_current dig-in; semantics-
   bank twins; IK-feasibility; mlcontprice2/8/16 (k=8 ceiling, costs
   slip); DR-draw (n=20, no dominant field); steering FAIL-wall
   dig-in; mlcontprice8 literal DONE-gate (FALL); dir_err_cap
   miscalibration (REFUTED); multiteacher blend {0.5,1.0}x{s0,s1}
   (FAIL, all 4); whole-group duty skew (REFUTED, this cycle).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,
> kk,ll}, 09-05{a,b,c,d,e}. Current state = newest Update at the TOP;
> don't act on archived Next.

## Fleet capacity note (updated 09-05 ~06:1x)

11-12/12 GPU pods free, backlog empty; no new standwalk GPU launch
this cycle (item 1 closed, nothing to launch; item 2's next step is a
CPU-only probe extension, not a training run). Every other track
non-launchable by design (`joystick`/`amp`/`cpg` DONE/maintenance;
`walkcurr` RETIRED; `todaypolicy` DELIVERED).

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

