# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~23:1x (**Candidate (i)-v2 seed0/dose1.5 read:
CANARY FAIL — combined-tick wins BOTH signs cleanly for the first time
via a pure geometry lever, but pure-turn regression still blows the
10% cap. Also found + fixed a probe-usage gotcha: the abbreviated
5-flag cfg shorthand used in prior verdict prose silently FREEZES the
policy (near-zero wz on a known-good checkpoint) — the full non-train
cfg-set must be replayed.**)

`cap29-stdwalklohi-yawarm1p5` (seed0, dose 1.5) verdicted FAIL-
MECHANISM. `probe_turn_authority.py --vx-cmds` (full 84-key non-train
cfg-set replayed — see gotcha below): pure-turn `wz_med` (seed-avg)
+0.196/-0.187 vs control `cap29-stdwalklo-hi` +0.221/-0.250 →
regression 11.7% (+) / 25.4% (-), BOTH over the 10% cap. Combined-tick
(`vx=0.08`) `wz_med` +0.143/-0.219 vs the pre-registered comparator
+0.110/-0.171 → BOTH signs beat it cleanly (+30%/+28% magnitude) — only
the second mechanism ever to do this (after `yawboost6p0-s1`; every
`combskip`/`omegaboost` cell was sign-asymmetric). No falls (8/8 probe
rows). Reward: quarters `[24.2, 74.9, -191.1, 137.2]`, final `ep_rew_
mean` 238.4 — same rider-c Q3 dip/recovery shape as every cap29
sibling, actually the family's best final value so far. Per the
pre-registered gate (needs both signs to beat the comparator AND
<=10% pure-turn regression), this FAILS on the regression clause alone
despite the genuine combined win — reinforcing a real pattern: 2/2
mechanisms that win the combined axis on both signs at once still cost
pure-turn beyond cap. `dose 2.0` (same seed) is still training; the
1.5-seed1 twin belongs to a concurrent cycle. Full verdict + evidence:
`rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-cap29-stdwalklohi-yawarm1p5.md`.

**PROBE-USAGE GOTCHA (logged, not yet a code fix):** `probe_turn_
authority.py --vx-cmds` requires the FULL non-`train.*` cfg-set from
the checkpoint's training command, not the 5-flag shorthand
(`goal.walk_yaw_cmd`, `obs.mode_onehot`, `goal.mode_seq`, `goal.walk_
phase_obs`, `goal.walk_obs_body_vel`) quoted in several prior verdict
paragraphs as "the cfg to match training obs width". Re-running the
KNOWN-PASSING control `cap29-stdwalklo-hi` with only those 5 flags
reproduces a near-zero/frozen `wz_med` (~0.002) even though the
checkpoint truly tracks turns fine (+0.221/-0.250 once the full cfg is
replayed) — almost certainly a missing `goal.walk_phase_hz`/`goal.walk_
phase_run_on_yaw` (or another goal.* field feeding the phase-obs
channel) putting the model on a badly out-of-distribution observation,
not a genuine behavior. `n_walk_ticks`/mode composition matched exactly
between the short and full cfg (mode sequencing is a DR-free function
of seed, independent of the policy), which is why this was not obvious
from tick counts alone — always diff wz_med against a fresh control
re-run with the SAME cfg-set before trusting a probe read, and default
to replaying the full training cfg-set for any future combined-tick
probe run. Every PRIOR combined-tick verdict in this branch (combskip,
omegaboost, yawboost, this run) that explicitly said "full training
cfg-set replayed" is unaffected; only the shorthand-cfg summaries in
verdict prose were ever at risk, and none of those summaries were
themselves used to compute the numbers quoted (spot-checked: the
quoted numbers match a full-cfg recompute for `omegaboost1p5` control
figures already in evidence).

**NEXT CYCLE:** read dose-2.0 (still training) and the 1.5-seed1 twin
once available; if both also show the same shape (real combined win,
disqualifying pure-turn cost), candidate (i)/(i)-v2 and the whole
omega-scaling axis close together, and item 2 should escalate to a
structurally different lever (phase-scheduled BC-anchor strength, per
the redesign spec's next class) rather than another single-scalar
dose on the same trade-off. Prior banner moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03s_trim.md`.

## Next (updated 09-03 ~23:1x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Candidate (i)-v2 (`combined_yaw_arm_
   scale`) 1/4 cells read: seed0/dose1.5 FAIL — see banner.** Combined
   axis genuinely wins both signs (2nd mechanism ever to do so, after
   `yawboost6p0-s1`) but pure-turn regression (11.7%/25.4%) still blows
   the 10% cap. NEXT CYCLE: read `dose2.0` (still training) + the
   `1.5-seed1` twin (concurrent cycle) the SAME way (`probe_turn_
   authority.py --vx-cmds` with the FULL non-train cfg-set replayed —
   see the probe-usage gotcha in the banner, do not use the 5-flag
   shorthand). If both remaining cells also show a real-but-
   disqualified combined win, candidate (i)/(i)-v2 closes 4/4 alongside
   the omega-scaling axis (both directions), meaning the achieved-wz
   ceiling under THIS reward/BC-anchor stack is a genuinely hard
   structural limit, not geometry-fixable at the single-scalar-dose
   level — next lever must touch WHAT the BC-anchor supervises (e.g.
   phase-scheduled anchor strength), not another multiplier on the
   existing one. Prior findings still hold: turn-in-place authority
   alone is strong everywhere (wz ~0.18-0.25 on 0.25 cmd); diet-rate,
   structural co-occurrence (`walk_yaw_zero_frac`), combined-tick
   BC-anchor-skip, teacher-omega-boost (both directions), and
   combined-tick reward boost are ALL refuted, 2+ seeds/doses each.
3. **Closed (archives 09-02{,b..h}, 09-03{a..s}):** update-size/
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
> 09-03{a..i,n,o,p,q,r,s}. Current state = newest Update at the TOP;
> don't act on archived Next.

## Fleet capacity note (09-03 ~23:1x)

All 4 item-2 canary cells finished training; 2/4 read this cycle
(seed0 dose1.5 + dose2.0, both FAIL — see banner), the seed1 twins are
locked to a concurrent cycle (`in-cycle` triage claim) — do not
re-read them. 11/11 GPU slots FREE. No launch this cycle: seed0 is
already 2/2 FAIL and the pre-registered next step (close 4/4 before
deciding whether to escalate to phase-scheduled BC-anchor strength)
explicitly waits on those seed1 reads, and jumping to the next
escalation now would risk duplicate/wasted design against whatever the
concurrent cycle's close-out finds. Every OTHER track is non-launchable
by design (`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr`
RETIRED; `todaypolicy` DELIVERED) — reconfirmed this cycle, all five
STATUS banners unchanged since the last check.

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

