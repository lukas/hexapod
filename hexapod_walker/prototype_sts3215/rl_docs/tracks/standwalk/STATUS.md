# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~15:0x (idle-kick, spec-first work on Next item 2):
**built + ran BOTH semantics-bank twins the item asked for
(`rl_move/tests/test_task_semantics.py`, `test_steer_while_walking_
beats_going_straight` / `test_steer_income_is_monotone_in_tracking_
accuracy` / `test_rise_stall_draws_more_current_and_less_height_than_
partial` / `test_rise_stall_prices_worse_than_honest_partial`) — ALL
FOUR PASS, under the yawdensity family's OWN reward.* cfg-set (course/
kernel/yaw stack for steer, mesh/100Hz rise stack + current_hot for
rise-stall).** This is a genuine, if unglamorous, finding: neither of
the two most obvious "reward literally prefers the bad behavior"
hypotheses holds. (1) STEER: forcing a simultaneous body-frame
(vx=0.08, wz=0.25) command and scripting a twin that tracks BOTH vs
one that tracks vx only and ignores wz, the tracking twin wins by
~230-300/ep on every seed, and income is MONOTONE increasing in
tracking-fraction all the way through 1.3x overshoot (no local
optimum short of full accuracy) — the course/yaw pricing terms, taken
in isolation on a scripted twin from a common start, do NOT reward
going straight over steering. (2) RISE-STALL: a hand-built "reach
honest partial height then keep fighting for +40deg more knee than
the actuator can hold" twin DOES sustain current near the family's
own ceiling (2.62A) and DOES end up lower than the honest partial
(69mm vs 121mm) — but it earns 1/3 the honest partial's return
(514-517 vs 1669-1720/ep, seeds 0-2), driven mostly by the rise_ref
tracking term collapsing once the target diverges, plus a smaller
current_hot charge. **Read this as narrowing, not closing, the
redesign**: it rules out the plain "the reward is upside-down"
explanation for both symptoms, which means the real driver is more
likely (a) the concurrent BC-anchor imitation supervision (trained
toward a straight-walking teacher) fighting the RL steering gradient,
or (b) a within-episode PPO exploration/credit-assignment gap once a
rollout is already deep into a bad rise state, or (c) a genuinely
different failure SHAPE than either scripted twin captures (no real
qpos/action trace survived the original dig-in to check against —
only aggregate metrics in `logs/ckpt_eval/yawdensity_s1_riseAB_
cap29cf/report.json`). Full bank + caveats in the test file itself
(STEER/rise-stall sections, bottom of the file). **Recommended next
step, not yet started**: before building a reward-code arm, either
(i) dump a real qpos/action trace from a fresh stalling rollout and
rebuild the rise-stall twin as a faithful replay, or (ii) run a
zero-training bc_anchor_walk_coef ablation specifically on the
steering-while-walking-forward axis (the existing anchor-coef
ablations were scoped to turn-in-place ticks only, per
`train.bc_anchor_walk_turn_skip`, never to combined walk+turn ticks).
**Unrelated pre-existing regression found while broad-testing this
change (NOT caused by it, confirmed via `git stash` on the identical
2 tests): `test_score_honest_ordering` / `test_score_flagleg_earns_
scraps` (the RISE stand-score bank, SCORE_OVERRIDES) both FAIL on
`main` as of this cycle — flagleg (151.7) now out-earns partial
(103.2). Likely fallout of today's joint-frame-v2 `_q0_robot_abs`
fixes elsewhere in this file (the RAW_PLANT/WALK_PLANT comments
document three such fixes already today) touching the shared
`_rise_rollout`/RISE_REF machinery this bank also uses. Not fixed
here (out of scope for this item, and other concurrent cycles are
already working that exact bug family) — flagging so it isn't
mistaken for fallout of the new steer/rise-stall banks.**

Earlier updates (14:2x seed1 dig-in resolution, 13:3x seed0 verdict,
13:2x initial flagged dig-in, and everything before) moved VERBATIM
to `archive/standwalk_STATUS_journal_2026-09-03j_trim.md` +
`2026-09-03{a..i}_trim.md` + `2026-09-02{f,h}_trim.md`.

## Next (updated 09-03 ~15:0x)

1. **CLOSED 09-03 ~14:2x (both seeds verdicted CANARY FAIL -
   MECHANISM; dig-in resolved)**: the seed1 rise `over_current`
   anomaly is GENUINE lineage rise-stall fragility, not an instrument
   defect — isolated rise-only DR-0 reads (no mode_seq mixing)
   reproduce it 6/8 det, 8/8 sto at the pair's own trained cap 2.5,
   and the cap-2.9 counterfactual shows the same behavior as silent
   45-62 mm height stalls with servos saturated. See the ~14:2x
   Update. The steering gate itself was NOT miscalibrated, so the
   escalation below stands on solid ground.
2. **STILL THE TRACK'S TOP ITEM — full reward-mechanism redesign for
   steering-while-walking-forward. Semantics-bank prerequisite PARTLY
   DONE 09-03 ~15:0x: both pre-registered twins built and PASS** (see
   the ~15:0x Update) — neither "course/yaw pricing rewards going
   straight" nor "an isometric rise-stall out-earns honest partial
   progress" holds as a plain reward-ordering bug. **Do NOT read this
   as clearing the arm to launch yet**: RESEARCH_RULES's semantics-
   bank-green gate is necessary but the PASS here means the obvious
   reward-shape fix has no target — launching a course/yaw reward
   tweak now would be shooting at a hypothesis the bank just refuted.
   Next sub-steps, in order: (i) either dump a real qpos/action trace
   from a fresh stalling rollout (no raw trace survived the original
   dig-in) and rebuild the rise-stall twin as a faithful replay, or
   run a zero-training `bc_anchor_walk_coef`/`bc_anchor_walk_turn_skip`
   -style ablation scoped to COMBINED walk+turn ticks specifically
   (every prior anchor-coef ablation here was turn-in-place-ticks
   only); (ii) only once one of those points at a concrete mechanism,
   design the actual redesign arm. Design inputs settled by the
   canary campaign (still true): turn-in-place authority is strong
   everywhere (wz ~0.18-0.23 on 0.25 cmd, zero probe falls, every
   recent run); the miss is specifically course-holding during
   commanded forward+turn mixes (dir_err 38-45deg, course_err_1s
   10-25deg, slip blows up sto/own-DR); diet-rate (resample matching,
   both doses) and structural co-occurrence (walk_yaw_zero_frac) are
   BOTH refuted 2-seeds each. Must-fix riders for whatever arm
   eventually launches: (a) current-cap semantics — a trip threshold
   above the 2.64 A model ceiling (cap 2.9) silently disables the
   over_current instrument; either price sustained saturation
   directly or keep the eval trip below the ceiling; (b) any arm
   respec'd off this family must set its cfg EXPLICITLY (the
   yawdensity pair proved names lie — verify safety.max_current_a and
   the speed keys in the ledger extra_args, not the run name); (c)
   investigate the family-wide Q3 training-reward collapse (~step
   1.0-1.7M of 2M, all three lineage members) before trusting any 2M
   canary endpoint from this ancestor again — a canary that samples
   its checkpoint inside the collapse-recovery window measures
   recovery luck, not the lever.
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

