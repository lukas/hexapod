# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~21:1x (**Candidate (ii) (`reward.walk_yaw_
combined_boost`) CLOSED: 4/4 canary cells FAIL — pure-turn regression
blows the 10% cap every time, even where the combined-tick number
itself beats the comparator.**)

Read the full 4-cell batch (`cap29-stdwalklohi-yawboost{3p0,6p0}
{,-s1}`) with `probe_turn_authority.py --vx-cmds` (full training
cfg-set replayed per checkpoint for an exact obs-contract match) vs
each cell's seed-matched control (`cap29-stdwalklo-hi{,-s1}`).
Pure-turn regression vs control / combined-vs-comparator(+0.110/
-0.171): 3p0(s0) 46.9%/17.8% regression, + WORSE than control (0.063),
- beats; 3p0-s1 18.2%/28.1%, + fails (0.101), - beats; 6p0(s0)
26.8%/10.8%, + fails (0.101), - fails too (0.133); 6p0-s1 15.3%/31.2%,
+ beats (0.120), - beats (0.188). Every cell blows the pre-registered
<=10% pure-turn regression cap (the gate's own disqualifying clause),
most by 2-4x; only one of four (6p0-s1) even clears the combined-tick
comparator on both signs, and it still fails the regression cap. No
falls in any probe rollout (32/32 `fell=False`); training reward shows
the same rider-(c) Q3 dip/recovery shape as every cap29 sibling — a
mechanism trade-off, not a training-collapse story. **Candidate (ii)
REFUTED at every dose (3.0/6.0) and seed (0/1)**: boosting the
yaw-kernel income on combined ticks reallocates supervision away from
pure-turn ticks through the shared GRU/value-function update — correct
in its FIRING gate, not clean in its EFFECT. Verdicts + evidence on
ledger/W&B (`logs/ckpt_eval/probe_turn_authority_yawboost{3p0,3p0_s1,
6p0,6p0_s1}_combined_09-03.json`). Earlier build/launch note moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03p_trim.md`.

**Candidate (i) groundwork (not a validated harness yet — Next item
2):** per this item's fallback, started the zero-training diagnosis a
`tripod_gait.py` geometry edit needs before any GPU spend. (1) IK
feasibility is NOT the bottleneck: walking the scripted teacher's own
`_foot_target_in_body -> _leg_ik` chain at the combined command
(vx=0.08, wz=+-0.25) over a full 15s episode, `_leg_ik` never returns
`None` and the tightest workspace margin is 47mm — always reachable.
(2) The `safety.max_delta_q_deg=0.375` slew cap is already deeply
saturated in BOTH regimes (raw per-tick joint delta median: pure-turn
0.93deg/tick, 82% over cap; combined 0.99deg/tick, 99.6% over cap) —
both ~2.5x over the cap already, which is odd given achieved body wz
is ~3x higher for pure-turn (0.22-0.25) than combined (0.07-0.19): if
slew-clipping alone drove the gap, both should saturate similarly.
This points AWAY from "the vx+omega superposition formula is simply
wrong" and toward the loss living downstream — either the SafetyLayer
clip interacting differently with a two-term (translate+rotate) vs
one-term (rotate-only) raw target, or genuine stance-leg contact/slip
physics competing for a shared thrust budget. Neither sub-hypothesis
is measured yet; DIG-IN flagged for the live-sim desired-vs-actual
joint-tracking instrument this needs (see Next item 2).

## Next (updated 09-03 ~21:1x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Candidate (ii) CLOSED 09-03 ~21:1x,
   4/4 FAIL (see banner). Candidate (i) is the only remaining named
   lever, and its own harness is NOT yet built** — this cycle only
   did zero-training groundwork (IK-feasibility check: clean, not the
   bottleneck; slew-clip saturation check: both pure-turn and
   combined already 2.5x over the `max_delta_q_deg` cap, which
   complicates rather than confirms a pure open-loop-geometry-bug
   story — see banner for both). DIG-IN flagged this cycle (see
   bottom of the orchestrator log) for the deep-root-cause chain a
   `tripod_gait.py` edit needs before any launch:
   - Instrument the LIVE sim (not just the open-loop `desired_deg()`
     trajectory) to compare desired-vs-actual per-tick joint angle
     during a scripted combined rollout, split pure-turn vs combined
     ticks — does the SafetyLayer clip MORE severely (in a way that
     differentially removes rotation vs translation displacement) on
     combined ticks specifically, or does actuator tracking hold and
     the loss instead shows up as stance-leg slip/contact-force
     competition between the two commanded axes?
   - Only once that split is measured does a `tripod_gait.py` edit
     (e.g. a stride-time-budget split between vx/omega demand, or a
     priority weighting when the combined raw target exceeds the slew
     budget) have a falsifiable target; editing blind risks another
     REFUTED-mechanism cycle on shared hardware-adjacent code.
   - Prior findings still hold: turn-in-place authority alone is
     strong everywhere (wz ~0.18-0.25 on 0.25 cmd); diet-rate,
     structural co-occurrence (`walk_yaw_zero_frac`), combined-tick
     BC-anchor-skip, teacher-omega-boost, and now the combined-tick
     reward boost are ALL refuted, 2+ seeds/doses each — 4 independent
     reward/BC-anchor mechanisms down before candidate (i).
3. **Closed (archives 09-02{,b..h}, 09-03{a..p}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip/
   omega-boost/combined-yaw-boost sweeps; cap29 acquisition (PARTIAL);
   log_std anneal dose grid (`hi` PASS, `mild` FAIL); item 0 sto/det
   convergence-at-scale (PASS); resamplematch diet-match-rate
   hypothesis (refuted both doses/seeds); rise over_current dig-in
   (genuine lineage fragility, not an instrument defect); rise-stall
   faithful replay (CLOSED, see item 1); steering/rise-stall
   semantics-bank twins (both PASS).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p}. Current state = newest Update at the TOP; don't
> act on archived Next.

## Fleet capacity note (09-03 ~21:1x)

All 11 GPU slots are free. Every OTHER registered track is currently
non-launchable by design, not by neglect: `joystick` DONE (08-23
`stotight45-seed13`), remaining 100Hz-polish thread deferred to this
track; `amp` DONE at M5 (08-23), M6 is `[operator]` hardware;
`cpg` DONE (09-03 banner: gate GREEN, adoption A/B'd 3x, no further
Next items); `walkcurr` RETIRED (08-31, no further agent launches);
`todaypolicy` DELIVERED (08-30), its own Next list closed 1-3 with
nothing further queued. `standwalk` is the only track with an open
gate, and its only Next item (2, candidate (i)) is correctly withheld
pending the harness above — launching a geometry-edit arm without it
would repeat the exact "launch first, root-cause after" mistake this
item's own prior branches were refuted by.

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

