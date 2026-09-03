# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~16:0x (idle-kick, Next item 2 sub-step (ii) —
the OTHER named branch, "zero-training ablation scoped to COMBINED
walk+turn ticks"): **found a genuine, quantified, reproducible NEW
mechanism candidate: the scripted TripodGait reference itself — the
BC anchor's own imitation target, and the thing every prior
turn-authority probe held vx_ref=0 while testing — loses turning
authority in smooth proportion to how much forward speed is
simultaneously commanded.** Extended `probe_turn_authority.py` with a
`--vx-cmds` sweep (new kwarg `vx_cmd`, default 0.0 = bit-exact prior
behavior — proven by a new pinned-equality test; body-frame vx read
via the existing `env._body_vel_xy()[0]`, robust to a rotating
heading), 4 new tests green
(`test_probe_turn_authority.py`). Three zero-training (no PPO)
readings, none touching a GPU:
1. **Scripted teacher, dose curve** (vx 0/0.02/0.04/0.06/0.08 m/s at
   fixed wz_cmd=0.25): achieved wz falls MONOTONICALLY and smoothly —
   0.220 -> 0.182 -> 0.138 -> 0.084 -> 0.072 rad/s — a graded
   trade-off, not a step/threshold clip (rules out a discrete IK/
   workspace-limit artifact in favor of a shared thrust/turn-authority
   budget under the tripod gait's own foot-contact physics).
2. **Scripted teacher, matched grid** (pure-turn vs pure-walk vs
   combined, wz=+-0.25, vx=0.08): pure-turn wz_med +-0.220 (healthy);
   combined wz_med crashes to +-0.072/-0.074 — the teacher itself
   RETAINS ONLY ~33% of its pure-turn authority once walking forward.
3. **Same grid on the actual trained checkpoint**
   (`..._yawdensity_canary_s1.zip`, own cfg): pure-turn wz_med
   +-0.197/-0.199 (matches the STATUS's known-good "wz~0.18-0.23"
   read); combined wz_med +0.145/-0.107 — RL narrows the teacher's
   deficit (74%/54% retained vs the teacher's 33%) but does not close
   it, and vx also degrades combined (pure-walk vx_med 0.033 ->
   combined 0.015-0.023). This is the first direct evidence that part
   of the "course-holding during forward+turn mixes" gap is INHERITED
   from the open-loop reference the BC anchor imitates, not purely an
   RL/anchor-training-dynamics artifact — a genuinely different class
   from every anchor-coefficient/diet/structural lever already refuted
   (all of those tested PURE turn-in-place ticks only). Evidence:
   `logs/ckpt_eval/probe_turn_authority_combined_scripted_09-03.json`,
   `..._combined_scripted_dosecurve_09-03.json`,
   `..._yawdensity_s1_combined_09-03.json`. Did NOT touch
   `hexapod_core/tripod_gait.py` (shared hardware-adjacent production
   code) this cycle — a geometry change there needs its own dedicated
   validation pass, not a same-cycle patch. No GPU launch: the two
   live redesign candidates this unlocks (fix the teacher's combined-
   command foot-target geometry, or add a combined-tick-targeted
   course/yaw reward gate) each still need their own semantics-bank
   proof or hardware-adjacent-code validation before spending budget —
   see Next item 2 below. Snapshot pending this update.

Earlier updates (15:2x rollout-trace tool, 15:0x semantics-bank twins,
14:2x seed1 dig-in resolution, 13:3x seed0 verdict, 13:2x initial
flagged dig-in, and everything before) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03l_trim.md` (which itself
notes a gap: the `09-03{a..k}`/`09-02{f,h}` files it in turn points to
do not exist on disk, unrepaired here).

## Next (updated 09-03 ~16:0x)

1. **Rise-stall branch (open):** tool + raw data DONE 09-03 ~15:2x
   (`eval_checkpoint.py --rollout-trace-out`, two real qpos/action/
   current traces off the seed1 checkpoint's silent-stall and
   over_current failure shapes). STILL OPEN: build the faithful-replay
   rise-stall twin in `test_task_semantics.py` from those traces (the
   existing twin is hand-built from aggregate numbers only).
2. **Steering branch — TOP ITEM. Mechanism found 09-03 ~16:0x** (see
   Update): a zero-training COMBINED walk+turn probe
   (`probe_turn_authority.py --vx-cmds`, no GPU) found the scripted
   teacher's own turn authority degrades in smooth proportion to
   simultaneous forward speed (33% of pure-turn wz retained combined);
   the trained checkpoint inherits a smaller but real version (74%/54%
   retained). Two concrete, NEITHER-started next actions: (a) a
   carefully-validated fix to `hexapod_core/tripod_gait.py`'s combined
   vx+omega per-leg foot-target geometry — shared hardware-adjacent
   code, needs its own before/after combined-probe proof (no
   pure-turn/pure-walk/hardware regression) before any BC-anchor
   retrain spends budget; (b) a combined-tick-targeted course/yaw
   reward gate (`vx_ref!=0 AND wz_ref!=0`, mirroring the already-
   refuted pure-turn-only `bc_anchor_walk_turn_skip`) — a reward
   MECHANISM change, needs its own `test_task_semantics.py` twin PASS
   before any launch per RESEARCH_RULES. Prior canary-campaign
   findings still hold: turn-in-place authority alone is strong
   everywhere (wz ~0.18-0.23 on 0.25 cmd); diet-rate and structural
   co-occurrence (`walk_yaw_zero_frac`) levers are BOTH refuted,
   2 seeds each — do not re-try either. Must-fix riders for whatever
   arm eventually launches: (a) current-cap semantics — a trip
   threshold above the 2.64 A model ceiling (cap 2.9) silently
   disables the over_current instrument; price sustained saturation
   directly or keep the eval trip below the ceiling; (b) any respec'd
   arm must set its cfg EXPLICITLY (the yawdensity pair proved names
   lie — verify `safety.max_current_a` and the speed keys in the
   ledger `extra_args`, not the run name); (c) investigate the
   family-wide Q3 training-reward collapse (~step 1.0-1.7M of 2M, all
   three lineage members) before trusting any 2M canary endpoint from
   this ancestor again.
3. **Closed (archives 09-02{,b..h}, 09-03{a..l}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS); resamplematch/turndiet-s1 +
   resamplematch-mild-canary{,-s1} diet-match-rate hypothesis (CLOSED,
   refuted at both doses/both seeds); rise over_current dig-in
   (CLOSED, genuine lineage fragility, not an instrument defect);
   steering/rise-stall semantics-bank twins (both PASS, refuting the
   plain reward-ordering-bug hypotheses).

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

