# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~23:0x (**Candidate (i)-v2 built + zero-training
gate PASSED: a NEW `TripodGait.combined_yaw_arm_scale` lever shrinks
the combined-tick yaw clip without touching pure-turn at all — 4-cell
RL canary LAUNCHED to test survival through fine-tune.**)

Two same-mechanism variants closed first, zero-training: (1)
discounting omega on combined ticks (mirror of the already-refuted
`bc_anchor_teacher_omega_boost`, dose<1) does NOT help even at the
scripted level — combined `wz_med` gets MONOTONICALLY WORSE as the
discount strengthens (1.0->0.3: 0.0723->0.0620 rad/s), because the raw
per-tick yaw delta is a period-INDEPENDENT direct function of physical
foot velocity — any uniform demand scaling (either sign) trades
achieved rotation 1:1 against clip relief; this closes the WHOLE
omega-scaling axis (boost refuted 4/4 at the RL stage 09-03 17:5x,
discount now refuted zero-training). (2) The literal candidate (b)
text ("pre-slew the target to the same cap") is mathematically a
NO-OP: the raw signal is already a constant-slope triangle wave, so a
same-cap rate limiter already achieves the max amplitude — no
"reversal waste" to recover upstream.

**The new lever**: `TripodGait.desired_deg()` gained
`combined_yaw_arm_scale` (default 1.0 bit-exact) which inflates ONLY
the `atan2` denominator used to back out the yaw SERVO ANGLE from a
leg's true tangential foot swing — hip/knee IK still use the TRUE
`r_planar`/z target, so placement/lift are untouched; only the
commanded yaw excursion shrinks. Gated to combined ticks only (mirrors
the omega-boost gate) so pure-turn is bit-exact (8/8 seeds/signs
verified). Zero-training gate (dose 1.0->2.0): `probe_turn_authority
--scripted-yaw-arm-scale` combined `wz_med` improves 0.0723->0.0807
(+11.6%) / -0.0738->-0.0791 (+7.2%) at flat `vx_med`, pure-turn stays
EXACTLY 0.2198 every dose; `probe_joint_tracking` confirms the
mechanism — combined `clip_sat_frac_yaw` drops 0.477->0.226 (pure-turn
untouched). Past dose ~2.5 the gain reverses (non-monotonic, real).
Wired via `train.bc_anchor_teacher_yaw_arm_scale`; 7 new tests +
3 probe tests green; full `test_bc_anchor.py` (105/105) rerun, same
PRE-EXISTING unrelated failures as unmodified `main` in two other
semantics files (confirmed via `git stash` A/B), no new breakage.
Snapshot `cce362ba` (`exp/standwalk-yaw-arm-scale-lever-09-03`).

**LAUNCHED**: 2-dose (1.5, 2.0) x 2-seed canary respec'd from the
matched comparators `cap29-stdwalklo-hi{,-s1}` (+ rider (a)
`safety.max_current_a=2.5`): `cap29-stdwalklohi-yawarm{1p5,2p0}{,-s1}`,
all 4 VERIFIED RUNNING (train-1/2/4/5). NEXT CYCLE: read with
`probe_turn_authority --vx-cmds` vs the pre-registered gate (beat
`cap29-stdwalklo-hi{,-s1}`'s own combined read +0.110/-0.171 on BOTH
signs, <=10% pure-turn/straight-walk regression) — read the FULL
reward curve first (rider c: every cap29 sibling so far showed a Q3
dip/recovery shape that is not itself a fail signal). Prior banner
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03r_trim.md`.

## Next (updated 09-03 ~23:0x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Candidate (i)-v2 (`combined_yaw_arm_
   scale`) BUILT, zero-training gate PASSED, 4-cell RL canary
   (`cap29-stdwalklohi-yawarm{1p5,2p0}{,-s1}`) LAUNCHED this cycle —
   see banner for the full mechanism/evidence.** NEXT CYCLE: read it
   against the pre-registered gate (beat the `cap29-stdwalklo-hi
   {,-s1}` combined read +0.110/-0.171 on BOTH signs, <=10% pure-turn/
   straight-walk regression; read the FULL reward curve first, rider
   c). If PASS: the first candidate to touch open-loop geometry (not a
   reward/BC-anchor layer on top of it) and survive a canary — bracket
   a tighter dose or go acquisition-length. If FAIL: the omega-scaling
   axis (both directions) AND yaw-arm-scale would all be closed,
   meaning the achieved-wz ceiling may be a genuinely hard structural
   limit of this recipe's BC-anchor/reward stack, not geometry-
   fixable — next lever would need to touch WHAT the BC-anchor
   supervises (e.g. phase-scheduled anchor strength), or redirect
   effort to `standwalk`'s other remaining gap. Prior findings still
   hold: turn-in-place authority alone is strong everywhere (wz
   ~0.18-0.25 on 0.25 cmd); diet-rate, structural co-occurrence
   (`walk_yaw_zero_frac`), combined-tick BC-anchor-skip, teacher-
   omega-boost (both directions), and combined-tick reward boost are
   ALL refuted, 2+ seeds/doses each.
3. **Closed (archives 09-02{,b..h}, 09-03{a..r}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip/
   omega-boost (both directions)/combined-yaw-boost sweeps; cap29
   acquisition (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild`
   FAIL); item 0 sto/det convergence-at-scale (PASS); resamplematch
   diet-match-rate hypothesis (refuted both doses/seeds); rise
   over_current dig-in
   (genuine lineage fragility, not an instrument defect); rise-stall
   faithful replay (CLOSED, see item 1); steering/rise-stall
   semantics-bank twins (both PASS); candidate (i) IK-feasibility +
   naive slew-saturation groundwork (superseded by the per-axis
   split above, see archive 09-03q for the superseded framing).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r}. Current state = newest Update at the TOP;
> don't act on archived Next.

## Fleet capacity note (09-03 ~23:0x)

4 of 11 GPU slots spent on the item-2 canary batch (train-1/2/4/5); 7
free. Every OTHER track is non-launchable by design (`joystick`/`amp`/
`cpg` DONE or maintenance-only; `walkcurr` RETIRED; `todaypolicy`
DELIVERED). `standwalk`'s only Next item now has a launched, gated
canary in flight — next cycle's job is to read it, not launch more
speculative arms ahead of that read.

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

