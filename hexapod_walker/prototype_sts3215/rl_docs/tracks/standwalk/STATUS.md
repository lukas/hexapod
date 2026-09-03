# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~22:1x (**Candidate (i) harness BUILT + first read:
the scripted teacher's YAW joint saturates the SafetyLayer slew clip
on combined ticks but almost NEVER on pure-turn ticks at the SAME
|wz_cmd| — hypothesis (a) CONFIRMED on the open-loop reference.**)

Built `rl_move/sim/probe_joint_tracking.py` (+ 3 tests, all green) per
Next item 2's own prescription: drives the LIVE mesh/100Hz sim with
the scripted `TripodGait` teacher and records, every walk-mode tick,
`desired` (open-loop IK target) vs `cmd` (env's post-SafetyLayer-clip
target, `env._cmd`) vs `actual` (physics-settled `joint_position`),
split per axis (yaw/hip/knee) and PURE-TURN (vx=0) vs COMBINED
(vx=0.08) at the identical `wz_cmd=+-0.25`. Result (15s episodes,
det. scripted policy, seeds 0/1 identical since no DR):
**yaw-axis clip saturation frac (fraction of walk ticks where the raw
per-tick yaw delta alone exceeds `max_delta_q_deg`): pure-turn 0.0%,
combined 47.7%** — every cell, both wz signs, both seeds, exactly
reproduced (symmetric, deterministic). p90 accumulated yaw
desired-vs-commanded gap: pure-turn ~0deg, combined 8.3deg. The
downstream actuator/physics tracking gap (`cmd` vs `actual`) does NOT
show the same asymmetry — if anything it is SMALLER on combined for
yaw specifically (2.4deg med) than pure-turn (4.3deg med), i.e. once
the SafetyLayer has already truncated the target, physics has an
easier (smaller) residual to chase. **This answers Next item 2's own
question: the combined-tick turn-authority loss lives in the
SafetyLayer clip stage, specifically on the yaw joint, not in
downstream stance-leg slip/contact-force competition** — no falls in
any probe cell. Root mechanism (not yet fixed): `_foot_target_in_body`
sums `vx` and `omega*r*sin/cos(leg_angle)` into one raw per-leg
velocity vector before the yaw-angle IK solve; adding a nonzero `vx`
term changes the per-tick yaw-angle swing enough to blow the slew
budget that a rotate-only command never touches — exactly the
"vx+omega superposition formula" candidate (i) named, now measured
rather than inferred. Evidence:
`logs/ckpt_eval/joint_tracking_cap29_scripted_09-03.json`. Prior
banner (candidate (ii) 4/4 FAIL close) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03q_trim.md`.

## Next (updated 09-03 ~22:1x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Candidate (ii) CLOSED (4/4 FAIL).
   Candidate (i)'s root-cause chain is now MEASURED (see banner):
   the SafetyLayer yaw-slew clip fires on ~48% of combined-tick legs
   and ~0% of pure-turn ones, at identical |wz_cmd| — the harness
   (`probe_joint_tracking.py`) is reusable for validating any fix.**
   Still NOT launch-ready (no `tripod_gait.py` edit made this cycle —
   editing blind was the exact mistake candidate (ii) and its
   predecessors avoided by pre-registering a gate first). Next
   sub-steps, in order:
   - Design ONE falsifiable `tripod_gait.py` geometry fix that
     specifically shrinks the per-tick YAW delta on combined ticks
     without shrinking the pure-turn yaw delta (candidates: a
     stride-time-budget split that discounts `omega`'s contribution
     to `_foot_target_in_body` when `vx!=0`, or clamping/pre-slewing
     the OPEN-LOOP target itself before IK so the teacher never asks
     for more than `max_delta_q_deg` can deliver in the first place).
   - Validate the fix with `probe_joint_tracking.py` FIRST (zero
     training): combined-tick yaw clip-sat-frac should drop toward
     the pure-turn baseline (~0%) while pure-turn's own clip-sat-frac
     and achieved wz/vx stay unchanged (matched control, same tool).
   - Only once that zero-training gate passes does a BC-anchor/GRU
     canary (mirroring the candidate (i)/(ii) launch shape) spend GPU
     budget — this preserves the "measure before launch" discipline
     4 refuted mechanisms already paid for.
   - Prior findings still hold: turn-in-place authority alone is
     strong everywhere (wz ~0.18-0.25 on 0.25 cmd); diet-rate,
     structural co-occurrence (`walk_yaw_zero_frac`), combined-tick
     BC-anchor-skip, teacher-omega-boost, and combined-tick reward
     boost are ALL refuted, 2+ seeds/doses each — 4 independent
     reward/BC-anchor mechanisms down; candidate (i) is the only one
     that touches the actual open-loop geometry rather than the
     reward/BC-anchor supervision layered on top of it.
3. **Closed (archives 09-02{,b..h}, 09-03{a..q}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip/
   omega-boost/combined-yaw-boost sweeps; cap29 acquisition (PARTIAL);
   log_std anneal dose grid (`hi` PASS, `mild` FAIL); item 0 sto/det
   convergence-at-scale (PASS); resamplematch diet-match-rate
   hypothesis (refuted both doses/seeds); rise over_current dig-in
   (genuine lineage fragility, not an instrument defect); rise-stall
   faithful replay (CLOSED, see item 1); steering/rise-stall
   semantics-bank twins (both PASS); candidate (i) IK-feasibility +
   naive slew-saturation groundwork (superseded by the per-axis
   split above, see archive 09-03q for the superseded framing).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q}. Current state = newest Update at the TOP; don't
> act on archived Next.

## Fleet capacity note (09-03 ~22:1x)

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

