# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~17:5x (idle-kick, Next item 2, branch (a) —
**ROOT CAUSE FOUND (zero-training) + LEVER BUILT + 4-ARM CANARY BATCH
LAUNCHED**): diagnosed WHY the combined-tick wz collapse happens
before touching `tripod_gait.py`: per-leg IK never fails and coxa-yaw
excursion is LARGER under combined than pure-turn (ruling out an IK/
workspace-clipping bug), but `info["walk_loadslip_ratio"]` rises ~20%
combined vs pure-walk, and boosting the omega TERM in the teacher's
foot-target formula alone (independent of any clip) recovers wz
smoothly — this is a friction/thrust-ALLOCATION effect: vx (0.08 m/s)
numerically dominates the per-leg omega contribution (omega*r~0.018
m/s), so almost all of the shared ground-reaction budget goes to
forward thrust, starving yaw. Built the fix as a BC-anchor-teacher
lever (not a `tripod_gait.py` class edit — same effect, lower risk):
new `train.bc_anchor_teacher_omega_boost` (env-side, `sim_env.py`,
default 1.0 = bit-exact identity, gated to combined ticks only,
mirrors `bc_anchor_walk_combined_skip`'s gating) multiplies the omega
fed to the teacher's `TripodGait.set_velocity` only when vx_ref!=0 AND
wz_ref!=0. Proven zero-training on the SCRIPTED teacher itself via a
new `probe_turn_authority.py --scripted-omega-boost` flag: boost 1.0
-> 2.0 raises combined wz_med 0.072->0.160 rad/s (+122%) at vx_med
0.034->0.026 (-24%); boost 1.5 -> wz_med 0.117 (+62%) at vx_med 0.032
(-6%); pure-turn/pure-walk PROVEN bit-exact untouched (9 new tests in
`test_probe_turn_authority.py`, 4 new pinned-equality tests in
`test_bc_anchor.py`, 101/101 + 9/9 green; also fixed an unrelated
pre-existing stale-constant test failure caught incidentally). Batch-
launched the 2-dose x 2-seed matched grid (operator 08-22 batching
rule) against the SAME already-PASSED controls as branch (b)
(`cap29-stdwalklo-hi{,-s1}`, no duplicate control spend):
`cap29-stdwalklohi-omegaboost{1p5,2p0}{,-s1}`, all 4 RUNNING. Same
pre-registered gate shape as branch (b)'s canary (beat the
yawdensity_canary_s1 comparator both signs, <=10% pure-turn/straight-
walk regression vs control). Snapshot `d6f83ade`
(`exp/standwalk-combined-omega-boost-09-03`). One backlog item hit an
unrelated launcher infra snag (stale `linux_control/vision_ui` dir on
`hexapod-mjx-train-6` blocking its code-sync tar, left over from the
09-03 AprilTag-tracker submodule extraction) — cleaned the pod
directory and re-queued; all 4 now RUNNING. NEXT CYCLE: read all 4
combined-tick `probe_turn_authority.py --vx-cmds` results vs the gate.

Earlier updates (17:2x combskip verdicts/branch-b REFUTED, 16:4x
branch-(b) lever build+launch, 16:0x combined-probe mechanism
discovery, 15:2x rollout-trace tool, 15:0x semantics-bank twins, and
everything before) moved VERBATIM to `archive/standwalk_STATUS_
journal_2026-09-03m_trim.md` (which points on to `...-03l_trim.md` —
noted gap: that file and the `09-03{a..k}`/`09-02{f,h}` files it in
turn points to do not exist on disk, unrepaired here).

## Next (updated 09-03 ~17:5x)

1. **Rise-stall branch (open):** tool + raw data DONE 09-03 ~15:2x
   (`eval_checkpoint.py --rollout-trace-out`, two real qpos/action/
   current traces off the seed1 checkpoint's silent-stall/over_current
   shapes). STILL OPEN: build the faithful-replay rise-stall twin in
   `test_task_semantics.py` from those traces (existing twin is
   hand-built from aggregate numbers only).
2. **Steering branch — TOP ITEM. Branch (b) REFUTED 09-03 ~17:2x;
   branch (a)'s omega-boost lever (see Update) is IN FLIGHT, 4-arm
   canary batch RUNNING** (`cap29-stdwalklohi-omegaboost{1p5,2p0}
   {,-s1}`). NEXT CYCLE: read all 4 vs the gate (beat the
   yawdensity_canary_s1 comparator both signs, <=10% pure-turn/
   straight-walk regression vs the `cap29-stdwalklo-hi{,-s1}`
   controls). On PASS (either dose): promote to the next full
   acquisition rung. On FAIL both doses: the `tripod_gait.py` class-
   level geometry edit (shared hardware-adjacent code, its own
   before/after validation) or a combined-tick-targeted course/yaw
   reward term are the remaining candidates. Prior
   findings still hold: turn-in-place authority alone is strong
   everywhere (wz ~0.18-0.23 on 0.25 cmd); diet-rate, structural
   co-occurrence (`walk_yaw_zero_frac`), and combined-tick
   BC-anchor-skip are ALL refuted, 2 seeds each. Must-fix riders for
   whatever arm eventually launches: (a) current-cap trip threshold
   must sit BELOW the 2.64 A model ceiling (cap 2.9 silently disables
   over_current); (b) verify `safety.max_current_a`/speed keys in the
   ledger `extra_args` explicitly, names lie; (c) investigate the
   family-wide Q3 training-reward collapse (all lineage members incl.
   both combskip seeds) before trusting any 2M canary endpoint again.
3. **Closed (archives 09-02{,b..h}, 09-03{a..m}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip
   sweeps; cap29 acquisition (PARTIAL); log_std anneal dose grid (`hi`
   PASS, `mild` FAIL); item 0 sto/det convergence-at-scale (PASS);
   resamplematch diet-match-rate hypothesis (refuted both doses/seeds);
   rise over_current dig-in (genuine lineage fragility, not an
   instrument defect); steering/rise-stall semantics-bank twins (both
   PASS).

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

