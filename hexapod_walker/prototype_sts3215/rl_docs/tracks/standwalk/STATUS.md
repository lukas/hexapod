# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~07:2x (**selomegaboost dose3.0/seed0 arm reports:
CANARY FAIL - MECHANISM, 1st of the 4-arm grid to close, same
sign-asymmetric-pure-turn-erosion pattern as every prior teacher-lever
candidate despite this one's clean zero-training validation.**)

`probe_turn_authority.py` on the finished `cw-standwalk-stage2-
dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-
selomegaboost3p0` checkpoint (full 84-key non-train cfg-set replayed,
2 probe seeds averaged) vs the matched `cap29-stdwalklo-hi` seed0
control: pure-turn wz_med +0.166/-0.215 vs control +0.223/-0.250 (25.5%/
14.0% regression, BOTH signs breach the pre-registered 10% cap);
combined-tick (vx=0.08) wz_med +0.084/-0.181 vs control +0.110/-0.170
— positive sign is WORSE, failing the "beats control on both signs"
bar outright regardless of the negative-sign gain. Training reward
genuinely healthy (rising monotonically to 290 at the final step, no
flat tail) so this is the mechanism failing, not a starved run. Same
failure signature as every predecessor on this axis (uniform
omega_boost, yaw_arm_scale, combined-dose ablations, yawboost) —
RL fine-tuning erodes pure-turn even when the teacher-side lever is
bit-exact-by-construction on pure-turn ticks. 3 sibling arms
(selomegaboost4p0, -4p0-s1, -3p0-s1) still finishing/awaiting their
own triage — full axis-close verdict needs all 4; see Next item 2.

Prior banner (candidate build + all-4-launched note) moved to
`archive/standwalk_STATUS_journal_2026-09-04bb_trim.md`.

## Next (updated 09-04 ~07:2x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md`. No reward code
   changed; a future fix should price sustained near-ceiling current
   directly (`over2A_s`-style), not a stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM, 1/4 arm reports FAIL, awaiting 3
   siblings (selomegaboost4p0, -4p0-s1, -3p0-s1) to close the axis.**
   dose3.0/seed0 already breaches BOTH pre-registered branches (pure-
   turn regression >10% both signs AND combined-tick fails to beat
   control on the positive sign) — see Update above. If the other 3
   arms fail the same sign-asymmetric way (matching every prior
   teacher-lever: uniform omega_boost, yaw_arm_scale, combined-tick
   BC-anchor-skip), the geometry/teacher-lever axis closes for good
   and the honest next move is a gait-STRUCTURE change (per-leg
   period/tripod-grouping during combined ticks, not yet tried) or an
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
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb}. Current state =
> newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~07:2x)

All 4 selective-omega-boost canary grid runs (train-1/2/3/4) have
finished/reported to W&B; pods free again (11/12 free per
capacity.py — one pending). No launchable next arm this cycle: the
axis's own decision rule needs the other 3 siblings' verdicts before
a new lever can be designed (a gait-structure-change candidate isn't
built yet). Every OTHER track remains non-launchable by design
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

