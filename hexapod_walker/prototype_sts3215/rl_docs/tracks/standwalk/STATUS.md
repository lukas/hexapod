# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~13:2x: **item 1 (yawdensity-canary) built + read
both seeds — FLAGGED DIG-IN, NOT verdicted.** `probe_turn_authority`:
clean both seeds (wz_med 0.18-0.23 rad/s, zero probe falls). Walk-only
steering read (n=16, dr0/ownDR x det/sto, no-video, same instrument as
the diet-family canaries): det dir_err_med 40.7-45.5deg (vs the
38-41deg FAIL band)/slip 3.4-4.5 — ordinary continuation of "lever
doesn't move steering." But **seed1 shows a severe, seed-asymmetric
NEW failure**: 7-12/16 `over_current` terms in EVERY subgroup incl.
dr0-det (cleanest condition; seed0's dr0-det is 0/16) — and every
termination's `seq_end_seg_mode` is `"rise"`, not `"walk"` (fails
~15-17s in, deep into the mixed walk->lower->rise->hold episode, after
walk metrics already captured). Sto numbers also diverge wildly from
every prior canary here: dir_err 73-77deg/slip 11-18 (det/sto used to
track closely). Two unresolved hypotheses: (a) seed1 drew a genuinely
fragile RISE sub-skill, orthogonal to the tested lever (seed noise);
(b) the forced harsh eval diet degrades the walk segment enough that
RISE inherits a compromised state (implicates the mixed-episode gate
INSTRUMENT, not the checkpoint). The gate's own FAIL text is literally
satisfied ("new own-DR falls appear") but closing the whole lever
family + escalating to a full reward-mechanism change on an
unreconciled, seed-asymmetric, wrong-mode failure would be premature —
left unverdicted. The standard prestage gate/owncfg (isolated per-mode
rollouts, no mode_seq mixing) are independently computing on train-3/
train-4 and will give a clean rise-alone read to reconcile (a) vs (b).
Full numbers + per-subgroup n_term breakdown: ledger DIG-IN note on
`yawdensity-canary-s1`. Artifacts: `logs/ckpt_eval/standwalk_
yawdensity_canary{,_s1}_walkcheck/*/report.json`, `logs/ckpt_eval/
probe_turn_authority_yawdensity_canary{,_s1}.json`.

Earlier updates (resamplematch-mild-canary close, item 0 close,
resamplematch/turndiet-s1 diet-match refutation, joint-frame-stamp fix,
fast-read, getup/q0/hold/joint-frame-v2 fixes, 09-02 merge-recovery)
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03i_trim.md`
+ `2026-09-03{a..h}_trim.md` + `2026-09-02{f,h}_trim.md`.

## Next (updated 09-03 ~13:2x)

1. **Reconcile the yawdensity-canary-s1 seed-asymmetric rise-phase
   over_current anomaly before any PASS/FAIL/escalation call**: read
   the standard prestage gate/owncfg evals (isolated per-mode rise-only
   rollouts, no mode_seq mixing) once synced on train-3/train-4 to
   check whether seed1's rise sub-skill fails in ISOLATION too (true
   checkpoint fragility, orthogonal to the density lever — resolve as
   seed noise, verdict on det steering alone) or only inside the mixed
   walk->rise episode under the forced harsh diet (implicates the gate
   instrument's mode_seq composition, needs a protocol fix before this
   canary family can be trusted at all). Either way, close item 1 with
   a real verdict once reconciled: on the walk-steering evidence alone,
   det numbers already look FAIL-shaped (flat-to-worse vs the 38-41deg/
   ~3.8 band), matching every prior canary in this family.
2. **Closed (archives 09-02{,b..h}, 09-03{a..h}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS); resamplematch/turndiet-s1 +
   resamplematch-mild-canary{,-s1} diet-match-rate hypothesis (CLOSED,
   refuted at both doses/both seeds).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i}. Current state = newest Update at the TOP; don't act
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

