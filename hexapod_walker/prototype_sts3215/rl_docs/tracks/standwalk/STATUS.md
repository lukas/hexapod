# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~02:4x (**`combdose0p6-s1-r3` FAIL-MECHANISM closes
the `bc_anchor_walk_combined_dose` axis 4/4 FAIL. Combined with the
already-closed yaw-arm-scale geometry axis, the WHOLE open-loop scalar-
weight/geometry lever family for item 2 is exhausted 8/8 FAIL. Built +
tested the first prerequisite piece of the next lever (protected
turn-tick sub-path); full architecture NOT yet built — see design
below. No new training launched this cycle.**)

`combdose0p6-s1-r3` (dose 0.6, seed1, 3rd launch attempt after 2
node-load infra deaths — see prior banner, archived) finally trained a
full budget (2,031,616 steps, quarters `[23.9, 53.1, -91.1, 140.9]`,
final `ep_rew_mean` 176.1, the family's own Q3-dip/Q4-recovery shape,
zero falls). `probe_turn_authority.py --vx-cmds`, full 84-key non-train
cfg-set (extracted straight from the run's own ledger `extra_args`,
minus `train.*`) replayed on the run's own pod, seed-avg vs the seed1
control `cap29-stdwalklo-hi-s1`'s cached `combined_09-03` read:
combined-tick (`vx=0.08`) `wz_med` WINS both signs cleanly (+0.1046 vs
ctrl +0.0868 = +20.4%; -0.1653 vs ctrl -0.1369 = +20.7% — the
STRONGEST combined-tick win of any dose-0.6 cell; its own seed0 twin
had COLLAPSED to a near-zero win at the same dose, so this is a real
seed-dependent swing, not a replay). But pure-turn (`vx=0.0`) `wz_med`
REGRESSES past the 10% cap on BOTH signs (+0.1996 vs ctrl +0.2279 =
12.4%; -0.2051 vs ctrl -0.2459 = 16.6%). Straight-walk drift shrinks
toward zero (not a regression). **Verdict: CANARY FAIL - MECHANISM** —
the identical signature every one of the 8 cells across both lever
families (4 geometry-scale doses + 4 anchor-weight doses) has now
shown: any dose/seed strong enough to win combined-tick wz blows the
pure-turn cap. Full verdict:
`rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r3.md`. Prior banner
(the full 4-cell dose-canary read + the node-load infra investigation)
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-04v_trim.md`.

**The open-loop lever family is now closed 8/8 FAIL — do not launch a
9th dose/scale variant.** Both lever families act on a SCALAR that
weights (or scales) the SAME shared walk-core's imitation pull; the
consistent 8/8 signature is strong evidence the interference is
representational (one GRU core computing both pure-turn and combined
behavior), not a pricing problem any scalar dose can fix.

**Next lever, designed this cycle (protected turn sub-path) — NOT yet
built as a trainable architecture, first safe prerequisite slice IS
built+tested:**

1. *(DONE this cycle, tested, snapshotted)* `obs.mode_onehot_turn_cmd`
   (`walk_task.py`, default 0/bit-exact-off): un-reserves
   `MODE_ONEHOT_ORDER`'s never-lit `"turn"` slot (the 08-11 comment's
   own "future re-scope needs no width change" — this IS that
   re-scope). On a walk-family tick, when the LIVE command is a PURE
   turn (`hypot(vx_ref,vy_ref)<=1e-3 and |wz_ref|>1e-3` — the EXACT
   threshold `sim_env.py`'s `_bc_pure_turn` already uses for the
   turn-skip/combined-dose tick tagging, so any future architecture
   routed off this bit sees the IDENTICAL tick partition the BC-anchor
   levers already reason about), the obs tail lights `"turn"` instead
   of `"walk"`; every other tick (combined, straight-walk, non-walk
   families) is untouched. 5 new tests in `test_mode_onehot.py`
   (bit-exact-off, turn-lights-on-pure-turn, combined-stays-walk,
   non-walk-modes-unchanged, documented precedence when combined with
   the pre-existing `mode_onehot_cmd`); also fixed 2 PRE-EXISTING
   unrelated test failures in the same file (`n_steps=80` was shorter
   than the 100-tick settle hold at the mesh-era 100 Hz default — a
   latent gap since the 08-24 25->100 Hz flip, unrelated to this
   change, fixed alongside since the root cause was already
   diagnosed). Full suite green: `test_mode_onehot.py` 23/23,
   `test_gru_policy.py`+`test_bc_anchor.py`+`test_mirror.py` 164/164
   (no regression from the new `_MODE_FAMILY["turn"]="turn"` entry).
2. *(NOT built — the actual gradient-isolation mechanism, scoped, not
   started)* A THIRD GRU core (mirroring the existing `_DualGRU`
   locomotion/stance split in `gru_policy.py`, and the further-
   generalized `_QuadGRU`/`ModeExpertsGruActorCriticPolicy` 4-expert
   precedent already in the same file) so PURE-turn ticks (now
   identifiable via item 1's bit) get their own actor/critic/log_std
   head, isolated by construction from the combined-tick gradient that
   is pulling the shared walk core off pure-turn — exactly the
   "protected sub-path" both prior banners named as the only untried
   axis. Design, scoped by reading the existing code (not guessed):
   - New `TripleGruActorCriticPolicy(GruActorCriticPolicy)` (or a
     `DualGruActorCriticPolicy` subclass) with cores `core_a` (walk +
     quad, unchanged role), `core_t` (new, turn), `core_b` (stance,
     UNCHANGED — keep the exact same attribute names/shapes as today's
     Dual class so core_b needs no new logic). 3-way gate from the
     onehot tail: `g_t=onehot[...,4]`, `g_b=onehot[...,:3].sum()`,
     `g_a=1-g_t-g_b` (exact partition, one bit lit per tick).
   - Warm start: a NEW transplant helper (same family as the existing
     `raw_policy_backbone_transplant`/`pad_obs_transplant` pattern in
     `train_ppo_mjx.py`'s `--init-from` branch) that builds the fresh
     Triple model, `PPO.load`s the old Dual checkpoint, copies its
     core_b -> new core_b verbatim and its core_a -> BOTH new core_a
     AND new core_t (turn starts as a copy of the current
     combined-tuned walk core, not from scratch — optimizer state
     fresh, same convention as every other architecture-changing
     transplant in this file).
   - **Named risk, found by reading the code, not by running anything:**
     `yaw_critic.py` (the `train.yaw_credit_coef`/`_vf_coef`/
     `_grad_clip` mechanism ACTIVE in this exact recipe) hard-requires
     `isinstance(policy, DualGruActorCriticPolicy)` and reaches
     directly for `policy.lstm_actor.core_a`/`lstm_critic.core_a` — it
     has NO generic hook. `bc_anchor.py`'s `_dual_core_param_groups`
     (used by BOTH `train.bc_anchor_isolate_update` and
     `train.yaw_credit_grad_clip`'s per-core clip) also hard-codes
     exactly 2 groups (`"a"`/`"b"`/`"shared"`) by name-matching
     `core_a`/`core_b`/`mlp_extractor_b`/etc — a `core_t`-named
     parameter would silently fall into the WRONG group (`"shared"`,
     unclipped/unisolated) without an explicit 3-way update. Wiring a
     Triple policy into THIS SPECIFIC recipe (which uses BOTH
     mechanisms) without updating both files first would silently
     break exactly the isolation machinery the whole point of this
     lever depends on — a subtle, hard-to-detect failure mode, not a
     crash. `bc_anchor.py`'s `bc_anchor_mean` dispatch IS already
     generic (`hasattr(pol, "bc_anchor_mean")`) — only a Triple-side
     override is needed there, no dispatcher change.
   - **Recommended mitigation for the FIRST canary** (single-lever
     discipline): fine-tune WITHOUT `train.yaw_credit_coef`/
     `_vf_coef`/`_grad_clip` active (warm-starting FROM a
     yaw-credit-trained checkpoint is fine — yaw_credit is a
     training-time hook, not a permanent weight change) so the first
     read isolates the core-split's own effect before touching
     `yaw_critic.py`'s Dual-only assumptions at all. Update
     `_dual_core_param_groups` to a 3-way `_group()` (add `"core_t"` /
     `mlp_extractor_t`/`action_net_t`/`value_net_t`/`log_std_t`
     name-matches -> `"t"`) regardless, since `bc_anchor_isolate_update`
     is active in this recipe and IS needed for correctness even
     without yaw_credit.
   - Test bank to build alongside (mirror `test_gru_policy.py`'s
     existing Dual/Experts suites, scaled down): bit-exact-off,
     3-way gate partition matches `walk_task.MODE_ONEHOT_ORDER`,
     routing selects the right core's mean, gradient isolation (a
     gradient on a core_t-only batch touches ONLY core_t params),
     save/load roundtrip, and the Dual->Triple transplant (core_a and
     core_t both equal old core_a immediately after transplant, core_b
     unchanged).
   Sizing this honestly: item 2 touches 3 files with active,
   currently-load-bearing mechanisms (`gru_policy.py`, `bc_anchor.py`,
   optionally `yaw_critic.py`) plus a new transplant path and a new
   test bank — a multi-cycle build, not a same-cycle one. Building it
   carelessly to hit "launch something" this cycle risks silently
   breaking `bc_anchor_isolate_update`/`yaw_credit_grad_clip`'s own
   isolation guarantees, which would confound the very question the
   lever exists to answer. Item 1 (tested, safe, real) is genuine
   forward progress; item 2 is scoped precisely enough for direct
   implementation next cycle with no re-discovery needed.

## Next (updated 09-04 ~02:4x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Whole open-loop lever family (yaw-
   arm-scale geometry axis + bc_anchor_walk_combined_dose axis) now
   CLOSED 8/8 FAIL — see banner.** Next lever (protected turn-tick
   sub-path, a 3rd GRU core): prerequisite `obs.mode_onehot_turn_cmd`
   tick-tagging BUILT + tested this cycle; the actual
   `TripleGruActorCriticPolicy` architecture + transplant + test bank
   is designed (exact touchpoints + the `yaw_critic.py`/
   `_dual_core_param_groups` entanglement risk named in the banner)
   but NOT built — multi-cycle scope, do not rush it to force a launch
   this cycle. NEXT: build `TripleGruActorCriticPolicy` per the
   banner's design, update `_dual_core_param_groups` to 3-way, add the
   Dual->Triple transplant + test bank, THEN launch one single-lever
   canary (yaw_credit OFF for the first read, per the banner's
   mitigation) from the `dualbc6...canary` base.
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}):** yaw-arm-scale
   candidate (i)-v2 dose x seed grid (4/4 FAIL, 09-04); update-size/
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
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04v. Current state = newest Update at
> the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~02:4x)

The whole open-loop dose/geometry lever family for item 2 is now
closed 8/8 FAIL (banner). The next lever needs real (multi-file,
multi-cycle) architecture work before it is safely launchable — see
item 2's design above. 0 of 11 GPU slots spent; every OTHER track is
non-launchable by design (`joystick`/`amp`/`cpg` DONE or maintenance-
only; `walkcurr` RETIRED; `todaypolicy` DELIVERED). This cycle spent
its budget building + testing the safe prerequisite slice
(`obs.mode_onehot_turn_cmd`) rather than rushing an untested 3-core
architecture onto a live H200 budget; next cycle's job is the
`TripleGruActorCriticPolicy` build itself.

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

