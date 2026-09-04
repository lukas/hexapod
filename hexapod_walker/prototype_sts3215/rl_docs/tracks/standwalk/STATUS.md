# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~08:3x (**OPERATOR DIRECTIVE fb_20260904T074505
executed: over_current AUDITED (2.64 A = forcerange rail image, trip
knife-edge in uncalibrated constants, counterfactual replay shows NO
fall/stall past the trip), transition-stress promotion suite BUILT
(`eval_cmd_stress.py`), and the transtress-diet canary pair LAUNCHED
(arm+matched control x 2 seeds, train-6/7/8/9).**)

Audit: `logs/ckpt_eval/oc_audit_09-04/OC_AUDIT_SUMMARY.md` +
CURRENT_TRUTHS ruling — rail hits alone never condemn a policy;
`audit_over_current.py` classifies RAIL_MOVING vs CORROBORATED_STALL;
note safety.max_current_a=2.9 (cap29 training) can NEVER trip (rail
2.64 < 2.9) while 2.5-riders trip on ANY sustained rail. New telemetry
on every eval episode: cur_rail_frac + cmd_rate/jerk/slew_sat (the
champion spends ~30-70% of transition ticks AT the 37.5 deg/s slew cap
— smoothness headroom is real). New training lever
`goal.mode_seq_stress` (SEQ_NEXT_STRESS: rise->lower, walk->hold;
default OFF bit-exact). Snapshot 2751a537, 65 tests green + 8 new.

Steering branch unchanged: selomegaboost 3/4 FAIL, 4th arm
(selomegaboost4p0-s1) finished, prestage evals running — its triage
still belongs to the concurrent cycle; gait-structure candidate still
gated on that verdict (unchanged Next item).

Prior banner (selomegaboost3p0-s1 FAIL) archived:
`archive/standwalk_STATUS_journal_2026-09-04ee_trim.md`.

## Next (updated 09-04 ~08:3x)

1. **Universal-command branch (operator directive 09-04) — TOP ITEM.**
   4 canaries RUNNING: `cap29-stdwalklohi-transtress{,-s1}`
   (transition-stress diet: mode_seq_stress grammar + 2.5-9 s segments
   + 3 s cmd resample) vs `cap29-stdwalklohi-cont{,-s1}` (matched
   plain continuations = baselines). Gate: `eval_cmd_stress` (seed
   base 93000) — zero MECHANICAL terms, completion/walk within bands
   of control, smoothness medians not worse; over_current reported
   separately, never vetoes alone. If the diet holds at 2M, next rung
   is an acquisition-length transtress run; if smoothness telemetry
   stays pinned at the slew cap, THEN design a measured action-rate/
   jerk objective (semantics-bank entry first — not yet written).
2. **Steering branch — 3/4 arms FAIL, awaiting selomegaboost4p0-s1
   verdict (concurrent cycle).** If it fails the same sign-asymmetric
   way, the teacher-lever axis closes; honest next move is a
   gait-STRUCTURE change or DONE-gate turn-authority renegotiation.
   Do not launch the gait-structure candidate until that verdict
   lands. Rise-stall branch stays CLOSED (09-03o archive).
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

## Fleet capacity note (updated 09-04 ~08:3x)

4 GPU pods training the transtress/cont canary quartet (train-6/7/8/9,
2M each); train-2/4 hosting the watcher's selomegaboost4p0{,-s1}
prestage evals; rest free. Steering-axis follow-up still gated on the
selomegaboost4p0-s1 verdict (concurrent cycle). Every OTHER track
remains non-launchable by design (`joystick`/`amp`/`cpg` DONE or
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

