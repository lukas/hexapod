# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~17:2x (idle-kick, Next item 2, branch (b) —
**RESULT: CANARY FAIL - MECHANISM, both seeds, verdicted**): read the
`cap29-stdwalklohi-combskip{,-s1}` pair (finished, 2.03M steps) with
`probe_turn_authority.py --vx-cmds` against the pre-registered
comparator (`yawdensity_canary_s1` combined read, +0.145/-0.107) and
the matched control (`cap29-stdwalklo-hi{,-s1}`, same probe), 2/2
seeds: pure-turn wz_med regresses 10-24% vs control (over the 10%
cap), and the combined-tick (vx=0.08) gain is sign-asymmetric — beats
the comparator on the negative-turn direction, stays WORSE on the
positive direction. PASS needed both signs beating the comparator AND
<=10% pure-turn regression; neither clears. **Branch (b)
(`train.bc_anchor_walk_combined_skip`) is REFUTED — removing BC-anchor
supervision on combined ticks trades pure-turn accuracy for a partial,
lopsided gain, not a net win. Branch (a) (the `tripod_gait.py`
combined vx+omega foot-target geometry fix) is now the sole remaining
candidate** — see Next item 2. Evidence:
`logs/ckpt_eval/probe_turn_authority_comb{skip_s0,skip_s1,cap29_stdwalklo_hi,cap29_stdwalklo_hi_s1}_combined_09-03.json`;
verdicts on ledger/W&B.

Earlier updates (16:4x branch-(b) lever build + launch, 16:0x
combined-probe mechanism discovery, 15:2x rollout-trace tool, 15:0x
semantics-bank twins, 14:2x seed1 dig-in resolution, 13:3x seed0
verdict, 13:2x initial flagged dig-in, and everything before) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03m_trim.md`
(which itself points on to `...-03l_trim.md` — noted gap: that file
and the `09-03{a..k}`/`09-02{f,h}` files it in turn points to do not
exist on disk, unrepaired here).

## Next (updated 09-03 ~17:2x)

1. **Rise-stall branch (open):** tool + raw data DONE 09-03 ~15:2x
   (`eval_checkpoint.py --rollout-trace-out`, two real qpos/action/
   current traces off the seed1 checkpoint's silent-stall/over_current
   shapes). STILL OPEN: build the faithful-replay rise-stall twin in
   `test_task_semantics.py` from those traces (existing twin is
   hand-built from aggregate numbers only).
2. **Steering branch — TOP ITEM. Branch (b) REFUTED 09-03 ~17:2x
   (CANARY FAIL - MECHANISM, 2/2 seeds — see Update); branch (a) is
   now the sole remaining candidate: a carefully-validated fix to
   `hexapod_core/tripod_gait.py`'s combined vx+omega per-leg
   foot-target geometry** (shared hardware-adjacent code: own
   before/after `probe_turn_authority.py --vx-cmds` proof — pure-turn,
   pure-walk, AND combined reads all held or improved, no hardware
   regression — before any BC-anchor retrain spends GPU on top of it;
   if (a) also fails, try a combined-tick-targeted course/yaw reward
   term instead, never anchor-supervision removal again). Prior
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

