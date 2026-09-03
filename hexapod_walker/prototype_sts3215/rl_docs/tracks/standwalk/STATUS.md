# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~23:2x (**Candidate (i)-v2 dose x seed grid now 3/4
FAIL. Both dose-2.0 cells (seed0 AND seed1) are in: dose 2.0 is WORSE
than dose 1.5 on every axis — pure-turn regression grows and the
combined-tick win degrades from "clean both-signs win" (dose 1.5,
seed0) to sign-asymmetric-or-outright-losing. Only the seed1/dose1.5
twin (a concurrent cycle) remains to close 4/4.**)

`cap29-stdwalklohi-yawarm2p0-s1` (seed1, dose 2.0) verdicted FAIL-
MECHANISM. `probe_turn_authority.py --vx-cmds` (full 84-key non-train
cfg-set replayed against a FRESH seed1 control run — the cached 17:19
seed1-control probe predates the probe-usage-gotcha fix and was NOT
reused, per this ledger's own gate text "read against the seed1
control instead"): pure-turn `wz_med` (seed-avg) +0.207/-0.180 vs
seed1 control `cap29-stdwalklo-hi-s1` +0.226/-0.247 → regression 8.3%
(+, inside the 10% cap) / 27.4% (-, blows it) — same shape as every
sibling cell (the negative side always breaks first). Combined-tick
(`vx=0.08`) `wz_med` +0.109/-0.136 vs the seed1 control's own combined
read +0.087/-0.142 → positive side beats cleanly (+26%) but negative
side is WEAKER than its own control (-4.5%) — sign-asymmetric, same
failure shape as combskip/omegaboost/yawboost-lodose, and a step down
from dose 1.5's clean bidirectional win. No falls on any turn row
(12/12); reward quarters `[23.5, 59.3, -200.6, 116.8]`, final `ep_rew_
mean` 164.6 — same Q3 dip/recovery shape, weakest final value of the
four cells so far but still positive/still climbing in Q4, not a
collapse. FAILS both gate clauses. Combined with the already-verdicted
`yawarm2p0` (seed0, dose 2.0: pure-turn regression 22.7%/25.0%, BOTH
over cap; combined-tick sign-asymmetric, positive side actually below
the control's own read) and `yawarm1p5` (seed0, dose 1.5: clean
bidirectional combined win, but regression 11.7%/25.4% still blows the
cap), the dose x seed grid is now 3/4 FAIL, with a clear dose-response:
1.5 is the family's best cell (only one to win combined on both signs)
and 2.0 is strictly worse on every measured axis at both seeds tried.
Only `yawarm1p5-s1` (seed1, dose 1.5, a concurrent cycle's run as of
this writing) remains. Full verdict + evidence: `rl_docs/runs/cw-
standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-
cap29-stdwalklohi-yawarm2p0-s1.md`, `logs/ckpt_eval/probe_turn_
authority_yawarm2p0_s1_combined_09-03.json` vs `logs/ckpt_eval/probe_
turn_authority_cap29_stdwalklo_hi_s1_combined_09-03_fullcfg.json`.

**PROBE-USAGE GOTCHA (still logged, not yet a code fix — see prior
banner, archived below, for the full writeup):** always replay the
FULL non-`train.*` cfg-set from the checkpoint's own training command
for any `probe_turn_authority.py --vx-cmds` read; the 5-flag shorthand
silently freezes the policy. This cycle additionally re-ran the seed1
control fresh under the full cfg rather than trusting the pre-gotcha
17:19 cached file, since that file's provenance (shorthand vs full)
was never logged at write time.

**NEXT CYCLE:** read the `yawarm1p5-s1` twin once available (it may
already be verdicted by its concurrent cycle by the time you read
this — check `rl_docs/runs/...yawarm1p5-s1.md` and the ledger status
before re-deriving anything). If it also FAILS (likely, given the
dose-2.0 pattern and the seed0/dose1.5 cell already failing on the
regression clause alone), candidate (i)/(i)-v2 and the whole
omega/yaw-arm-scaling axis close 4/4: no single-scalar dose on this
lever clears the pure-turn cap without giving up the combined win, at
either seed. Item 2 should then escalate to a structurally different
lever (phase-scheduled BC-anchor strength, per the redesign spec's
next class) rather than another dose/seed on the same mechanism — do
NOT pre-launch that new mechanism before the 4th cell confirms; it is
new reward/task-mechanism work and needs its own `test_task_
semantics.py` bank pass before any training launch regardless. Prior
banner moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-
03t_trim.md`.

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

## Fleet capacity note (09-03 ~23:2x)

All 4 item-2 canary cells finished training; 3/4 read (seed0 dose1.5,
seed0 dose2.0, seed1 dose2.0 — all FAIL, see banner). The last cell
(`yawarm1p5-s1`, seed1 dose1.5) was `in-cycle` to a concurrent triage
claim as of this writing — do not re-read it without first checking
whether it has already been verdicted. 11/11 GPU slots FREE. No launch
this cycle: the pre-registered next step (close 4/4 before deciding
whether to escalate to phase-scheduled BC-anchor strength) explicitly
waits on that last seed1 read, and the escalation target is a NEW
reward/task mechanism that needs its own `test_task_semantics.py` bank
pass before any training launch regardless — jumping to design it now,
ahead of the 4th confirmation and without that bank, would be
premature on both counts. Every OTHER track is non-launchable by
design (`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr`
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

