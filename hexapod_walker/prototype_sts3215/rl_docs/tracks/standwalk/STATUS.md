# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~05:2x (**Confound-isolation pair READ — the
architecture-split axis is now DEFINITIVELY CLOSED, not provisional.
`TripleGruActorCriticPolicy` is dead; the sole live steering lever is
the teacher-side branch.**)

`cap29-stdwalklohi-dualcontinue-noyawcredit{,-s1}` (same start
checkpoint/steps/reward/goal/obs cfg-set and same dropped
`train.yaw_credit_coef/_vf_coef/_grad_clip` +
`--gru-dual-log-std-split`/`--log-std-anneal-core` mechanisms as the
Triple canary, but plain `--gru-dual`) finished and was read with the
same `probe_turn_authority.py --vx-cmds` (85-key non-train cfg-set
replay) instrument against the same `cap29-stdwalklo-hi{,-s1}`
control. Both pre-registered readings landed, and they agree:

- **Reading (A) CONFIRMED — the pure-turn loss is the mechanism drop,
  not the architecture.** This Dual-continuation regresses pure-turn
  `wz_med` 11.8-26.5% both signs, both seeds — matching the
  already-closed Triple canary's own 12.7-27.7% loss on the SAME
  confound-matched cells almost exactly. Dropping yaw_credit/
  log_std_split during ANY further continuation costs ~12-27% pure-
  turn authority by itself; those mechanisms are load-bearing, the
  architecture swap is not implicated by the pure-turn axis at all.
- **Reading (C) CONFIRMED — architecture bought nothing on
  combined-tick either, even with the identical confound in both
  arms.** This Dual run's own combined-tick (`vx_cmd=0.08`) `wz_med`
  beats or matches Triple's on all 8 matched cells (both signs, both
  seeds) — 2 cells even beat the ORIGINAL FROZEN control outright.
  Triple never wins a single combined-tick cell against a plain
  continuation sharing its own confound.
- Reading (B) (mechanisms innocent, pure-turn holds inside the 10%
  cap) did NOT land — ruled out by (A).

**Net: the architecture-split (`TripleGruActorCriticPolicy`) lever is
CLOSED for good — 2/2 Triple canary FAIL, confound now explained
rather than provisional, and even a maximally-favorable matched
comparison shows zero-to-negative combined-tick benefit.** Do not
build the `yaw_critic.py`-on-Triple follow-up, and do not spend a
"mechanisms-kept" clean Triple rerun either — (C) already answers the
practical question (architecture vs. plain continuation) on its own
terms, independent of how (A) vs (B) landed; a cleaner rerun would
only add methodological polish to an already-decided comparison. The
dualcontinue runs themselves are disqualified from adoption by their
own pure-turn regression (>10% cap) — they are explanatory controls,
not new candidates. Full per-cell numbers: ledger / W&B notes for
`...-dualcontinue-noyawcredit{,-s1}`.

**Steering branch state after this closure:** every policy-side lever
tried so far is now refuted (BC-anchor dose/skip x2 seeds, teacher
omega-boost x2 doses x2 seeds, combined_yaw_arm_scale x2 doses x2
seeds, walk_yaw_combined_boost x2 doses x2 seeds, TripleGruActorCriticPolicy
x2 seeds, and now the mechanism-drop confound explaining Triple's own
pure-turn loss). The ONE standing, independently-verified finding that
hasn't been chased yet is teacher-side: the scripted `TripodGait`
itself only retains ~33% of its pure-turn `wz` once walking forward
combined (09-03 16:1x). That is now the sole active lever — see Next.

Prior banner (`TripleGruActorCriticPolicy` build + 2/2 FAIL + the
confound discovery) moved VERBATIM to `archive/standwalk_STATUS_
journal_2026-09-04y_trim.md`.

## Next (updated 09-04 ~05:2x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM, now teacher-side ONLY.** Every
   policy-side lever (BC-anchor dose/skip, teacher-omega-boost,
   combined-yaw-arm-scale, combined-yaw-boost, GRU architecture split)
   is refuted; the architecture-split confound is resolved (see
   banner). The one open, positive lead: build a fix on the SCRIPTED
   `TripodGait` teacher itself for its own combined-motion
   turn-authority loss (09-03 16:1x: only ~33% of pure-turn `wz`
   survives at `vx_cmd=0.08`, dose-monotone not a step-clip) —
   candidate mechanism is a shared foot-contact/thrust budget under
   the tripod gait's per-leg omega/vx allocation. Validate any
   geometry fix zero-training first with `probe_turn_authority.py
   --policy scripted --scripted-omega-boost`/`--scripted-yaw-arm-scale`
   (or a new scripted-side lever) BEFORE spending any RL fine-tune
   budget on it — that is what let every refuted policy-side lever get
   closed cheaply. Do not re-open the architecture-split axis
   (Triple/yaw_critic.py) — it is done.
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}, 09-04{v,w,x,y}):**
   architecture-split (`TripleGruActorCriticPolicy`, 2/2 FAIL +
   confound-isolation pair explaining it, 09-04); yaw-arm-scale
   candidate (i)-v2 dose x seed grid (4/4 FAIL); update-size/reward/
   exploration/anchor/turn-skip/yaw-credit/diet/duration/switch-jump/
   frame-blend/current-confound/combined-tick-anchor-skip/omega-boost
   (both directions)/combined-yaw-boost sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS); resamplematch diet-match-
   rate hypothesis (refuted both doses/seeds); rise over_current
   dig-in (genuine lineage fragility, not an instrument defect);
   rise-stall faithful replay (CLOSED, see item 1); steering/
   rise-stall semantics-bank twins (both PASS); candidate (i)
   IK-feasibility + naive slew-saturation groundwork (superseded).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y}. Current state = newest
> Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~05:2x)

Both `dualcontinue-noyawcredit{,-s1}` confound-isolation runs
verdicted this cycle (CANARY FAIL - MECHANISM, informative — see
banner), freeing 2 GPU slots. No GPU launch this cycle: the only
open Next item (teacher-side `TripodGait` fix) needs zero-training
validation FIRST (candidate geometry/allocation fix + a
`probe_turn_authority.py --policy scripted` proof, mirroring how every
prior policy-side lever was screened before spending a canary) — that
tool-building/validation step is not built yet, so there is no
pre-registered arm ready to launch. Every OTHER track remains
non-launchable by design (`joystick`/`amp`/`cpg` DONE or maintenance-
only; `walkcurr` RETIRED; `todaypolicy` DELIVERED). All 11 reachable
GPU pods free.

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

