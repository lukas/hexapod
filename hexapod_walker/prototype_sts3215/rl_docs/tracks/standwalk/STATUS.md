# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~20:2x (**Next item 2 candidate (ii) BUILT +
LAUNCHED: `reward.walk_yaw_combined_boost` harness + 4-arm canary
batch now RUNNING.**)

Item 2's own prescription ("pick one, build its validation/bank
harness, THEN launch a matched canary") is done for candidate (ii).
Built `reward.walk_yaw_combined_boost` (`walk_task.py`, default
1.0=bit-exact identity, mirrors `train.bc_anchor_teacher_omega_
boost`'s own gating): a MULTIPLIER, not a gate, applied only to the
existing `k_walk_yaw` kernel income on genuine combined ticks (linear
speed AND yaw rate both commanded) — corrected mid-build: an earlier
draft assumed (from `probe_turn_authority.py`'s stale docstring) that
this family trains with `k_walk_yaw=0`; the ledger's own cfg for
`cap29-stdwalklo-hi` shows `k_walk_yaw=1.0` applied to EVERY walk
tick already, so a zeroing GATE (the first design) would have
REMOVED supervision from the already-working pure-turn behavior
instead of adding it where degraded — a boost multiplier is the
correct surgical lever. Semantics bank
(`test_task_semantics.py`, "STANDWALK combined-tick-targeted yaw term
bank"): pins the measured sign-asymmetric exploit (positive combined
wz retains ~44% of pure-turn magnitude, negative ~68%, from the
cap29-stdwalklo-hi comparator) as a scripted twin the CURRENT
(boost=1.0) stack cannot distinguish from a symmetric-good twin
(asym/sym price within ~1% of each other), then proves boost=6.0
separates them by >600pts/ep — the mechanism has real gradient before
any GPU spend. 8 new/modified tests, all green (4 gate-mechanics +
the exploit-pinning test, plus `_steer_rollout` gained `return_terms`/
`tail_only`); full `-k "steer or yaw or turn or walkteach"` + all 101
`test_bc_anchor.py` tests rerun green except one PRE-EXISTING failure
(`test_kernel_yaw_ema_separates_accurate_tracking_from_undershoot`,
confirmed failing identically on unmodified `main` — not caused by
this change, not fixed this cycle). Also applied item-2 rider (a):
new arms set `safety.max_current_a=2.5` (below the measured 2.64A
model ceiling; the sibling canaries' `2.9` silently disabled
`over_current`). Snapshot `0b15f140`
(`exp/standwalk-combined-yaw-boost-lever-09-03`).

**LAUNCHED**: 2-dose x 2-seed canary batch, respec'd from the matched
comparators `cap29-stdwalklo-hi{,-s1}` (identical recipe minus the new
flag): `cap29-stdwalklohi-yawboost{3p0,6p0}{,-s1}`, all 4 VERIFIED
RUNNING (train-1/2/3/10). One infra snag hit 3/4 arms (`tar: ...
linux_control/vision_ui: Cannot open: File exists` on train-1/2/3,
the same AprilTag-submodule-extraction stale-directory class noted in
the 09-03 17:5x omegaboost launch) — cleared via `kubectl exec ... rm
-rf .../vision_ui` on the affected pods, then requeued; all 4 now
running clean. NEXT CYCLE: read the 4-cell canary
(`probe_turn_authority.py --vx-cmds` combined read vs the pre-
registered gate) — do NOT trust the raw final-step reward number
alone (rider c: the whole cap29 family, incl. both combskip seeds,
showed a Q3 training-reward collapse).

Earlier update, 2026-09-03 ~19:1x (Next item 2 branch-(a) 4-arm
omega-boost canary batch REFUTED 4/4; Next item 1 rise-stall faithful
replay CLOSED, mesh/primitive test-harness bug fixed) moved VERBATIM
to `archive/standwalk_STATUS_journal_2026-09-03o_trim.md`.

## Next (updated 09-03 ~20:2x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Candidate (ii) (`reward.walk_yaw_
   combined_boost`) BUILT + LAUNCHED 09-03 ~20:2x, awaiting the 4-cell
   canary read** (`cap29-stdwalklohi-yawboost{3p0,6p0}{,-s1}`, doses
   3.0/6.0 x seeds 0/1, all VERIFIED RUNNING). NEXT CYCLE: read
   `probe_turn_authority.py --vx-cmds` combined results vs the
   pre-registered gate (both signs must beat the cap29-stdwalklo-hi
   comparator AND the asymmetry must actually close, not just
   narrow), with a pure-turn/straight-walk regression check <=10% vs
   control. Do not trust the raw final-step reward alone — rider (c)
   (Q3 collapse, still unexplained) applies to this family. If ALL 4
   cells FAIL the same way branch (a) did, candidate (i) (`tripod_
   gait.py` class-level combined vx+omega foot-target geometry edit)
   is the only remaining lever — build its own before/after
   validation harness (extend `probe_turn_authority.py` to exercise
   the edited function directly) before any launch. Prior findings
   still hold: turn-in-place authority alone is strong everywhere (wz
   ~0.18-0.23 on 0.25 cmd); diet-rate, structural co-occurrence
   (`walk_yaw_zero_frac`), combined-tick BC-anchor-skip, and teacher-
   omega-boost are ALL refuted, 2+ seeds each — 3 independent
   mechanisms down before this one. Riders applied to this batch: (a)
   `safety.max_current_a=2.5` (was 2.9, above the 2.64A ceiling,
   silently disabling `over_current`); (b) key names verified against
   `rl_move/safety.py` directly, not assumed.
3. **Closed (archives 09-02{,b..h}, 09-03{a..o}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip/
   omega-boost sweeps; cap29 acquisition (PARTIAL); log_std anneal
   dose grid (`hi` PASS, `mild` FAIL); item 0 sto/det convergence-at-
   scale (PASS); resamplematch diet-match-rate hypothesis (refuted
   both doses/seeds); rise over_current dig-in (genuine lineage
   fragility, not an instrument defect); rise-stall faithful replay
   (CLOSED, see item 1); steering/rise-stall semantics-bank twins
   (both PASS).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o}. Current state = newest Update at the TOP; don't act
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

