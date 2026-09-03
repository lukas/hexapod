# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~13:3x: **item 1 seed0 (`yawdensity-canary`)
VERDICTED CANARY FAIL - MECHANISM; seed1 stays the concurrent cycle's
open DIG-IN (below) — do not let this close the family alone.**
Same walk-only steering read (n=16, dr0/ownDR x det/sto, no-video,
harsh eval-diet override): walk/det dir_err_mean_med 40.65deg (flat
inside the 38-41deg FAIL band); course_err_1s_med_med 23.49deg
(dr0)/18.88deg (ownDR) — 1.5-2.4x WORSE than the FAIL band's own
9.6-12.6deg, not better; slip_per_m_med 4.32-4.47, above the ~3.8
ceiling. `probe_turn_authority`: clean (wz_med 0.18-0.23 rad/s, zero
probe falls) — the miss is steering-while-walking-forward specifically,
not a general turn regression. gait_valid 16/16 in 3/4 subgroups
(15/16 in the 4th). This clears the gate's own FAIL branch ("worse
than the ancestor on any axis") on the primary dir/course/slip
metrics ALONE — that call does not depend on the termination question
below, so seed0 is verdicted now rather than waiting on seed1's
reconciliation. **Caveat carried forward, not resolved**: seed0's
own-DR-det group has the SAME failure shape seed1 shows at high rate
(one `over_current` term at t=17.77 with `seq_end_seg_mode=rise`) —
at seed0's low incidence (1/16, plus one unrelated late `hold_min_load`
in the hold segment matching prior baseline noise) this reads as
noise, but seed1's 7-12/16 rate in EVERY subgroup says it may be a
real (dose- or seed-dependent) rise-phase fragility inside the mixed
walk->rise mode_seq episode under the forced harsh diet, possibly an
INSTRUMENT defect (the canary-family gate's mode_seq mixing), not a
checkpoint property. Do NOT treat seed0's clean-looking termination
count as proof the anomaly is seed1-only until the reconciliation
item below (isolated per-mode rise-only gate/owncfg, no mode_seq
mixing) actually reads clean on seed0 too. **Verdict on the
STRUCTURAL branch stands regardless**: walk_yaw_zero_frac (0.5->0.2)
does not close the steering gap on seed0, matching the diet-rate
branch's own closure — both pre-registered branches of the track's
turn-authority fork are refuted on seed0. The FAMILY-WIDE escalation
call (full reward-mechanism redesign) stays open pending seed1's
termination-anomaly reconciliation, per the concurrent cycle's own
Next item 1 below — do not launch a redesign arm until that resolves,
since if it's an instrument defect the "escalate" conclusion itself
would be built on a miscalibrated gate. Evidence: ledger verdict on
`yawdensity-canary`, `logs/ckpt_eval/standwalk_yawdensity_canary_
walkcheck/*/report.json`, `logs/ckpt_eval/probe_turn_authority_
yawdensity_canary.json`.

Previous update, 2026-09-03 ~13:2x: **item 1 (yawdensity-canary) built
+ read both seeds — FLAGGED DIG-IN, NOT verdicted (seed1 side).** `probe_turn_authority`:
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

## Next (updated 09-03 ~13:3x)

1. **seed0 CLOSED (verdicted CANARY FAIL - MECHANISM this cycle,
   see Update above): the structural forward+turn co-occurrence lever
   (walk_yaw_zero_frac 0.5->0.2) does not close the steering gap —
   dir_err flat, course_err/slip WORSE than the FAIL band. seed1 STILL
   OPEN — reconcile its seed-asymmetric rise-phase `over_current`
   anomaly (7-12/16 terms in every subgroup, `seq_end_seg_mode=rise`,
   vs seed0's 1/16 at the same failure shape) before ruling on whether
   it's checkpoint fragility (seed noise) or a mode_seq-mixing
   instrument defect in the canary gate itself**: read the standard
   prestage gate/owncfg evals (isolated per-mode rise-only rollouts, no
   mode_seq mixing) once synced on train-3/train-4 for BOTH seeds — if
   seed0's isolated rise-only read is also clean (expected, given its
   low mixed-episode incidence), that's evidence FOR the instrument-
   defect branch (seed1 drew unlucky under a flawed mixed-mode gate,
   not a real checkpoint difference), which would also caveat seed0's
   otherwise-clean-looking termination count above.
2. **Escalation to a full reward-mechanism redesign** (both
   pre-registered branches of the turn-authority fork — diet-rate AND
   structural — are now refuted on seed0's steering metrics): DO NOT
   launch a redesign arm until item 1's reconciliation resolves the
   instrument-defect question, since an escalation built on a
   miscalibrated gate would misdirect the whole next design. Flagged
   dig-in-tier (root-cause chain behavior<-incentive<-pricing<-sim
   defect before any reward patch), matching how amp's analogous
   slip/yaw-tip mechanism closure was handled.
3. **Closed (archives 09-02{,b..h}, 09-03{a..h}):** update-size/
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

