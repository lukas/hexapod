# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~03:5x (**`TripleGruActorCriticPolicy` (the 3rd-GRU-
core protected turn-tick lever item 2's banner scoped last cycle) is
now BUILT, fully unit-tested (26 new tests: architecture + CLI
validator + `--log-std-anneal-core turn`, all green; zero regressions
in `test_gru_policy.py`/`test_bc_anchor.py`/`test_gru_triple_cli.py`),
and LAUNCHED as a 2-seed canary against the `cap29-stdwalklo-hi`
control. First launch attempt crashed at 0 training steps on a
self-inflicted net_arch-derivation bug (caught cleanly by the
transplant's own shape check, no corruption); fixed same-cycle,
re-launched as `-r2`, both seeds VERIFIED RUNNING. Unread.**)

Built exactly per last cycle's scoped design
(`gru_policy.TripleGruActorCriticPolicy`: `core_a` walk/quad unchanged,
new `core_t` pure-turn with its own actor/critic/log_std head, `core_b`
stance byte-for-byte unchanged from Dual's contract; 3-way gate off the
frozen `MODE_ONEHOT_ORDER` tail). `gru_policy.dual_to_triple_transplant`
copies `core_b` verbatim and `core_a` into BOTH `core_a` and `core_t`
(turn starts as a copy of the current combined-tuned walk core, fresh
optimizer state). `bc_anchor._dual_core_param_groups` extended to a
generic 3-way `"a"/"t"/"b"/"shared"` classifier (both call sites —
`_gradnorm_diag_ctx`/`_percore_clip_ctx` — reworked to iterate an
arbitrary group set instead of a hardcoded `{a,b,shared}` dict, so
`bc_anchor_isolate_update`/`bc_anchor_percore_clip` stay correct on a
Triple policy without a silent misclassification). New CLI
`--gru-triple` (`train_ppo_mjx.py`): warm-start-only (requires
`--init-from` a Dual checkpoint + `obs.mode_onehot=1,
obs.mode_onehot_turn_cmd=1`; refuses `--gru-dual`/`--gru-experts`/
actor-only/policy-backbone transplants), builds a fresh Triple policy
and calls the transplant. Per the banner's own mitigation, `yaw_critic.py`
was NOT touched — the first canary drops `train.yaw_credit_coef`/
`_vf_coef`/`_grad_clip` and the Dual-only `log_std_split`/
`--log-std-anneal-core` mechanism entirely (warm-starting FROM a
yaw-credit-trained checkpoint is fine, yaw_credit is training-time
only) so this read isolates the core-split's own effect. Test bank:
`test_gru_policy.py` (slots/routing/3-way gradient isolation/save-load/
bptt/bc_anchor+detach_trunk/log_std_core targeting/transplant
correctness incl. a byte-equality + forward-match check) +
`test_gru_triple_cli.py` (validator + `--help` wiring +
`--log-std-anneal-core turn` parsing).

**Self-inflicted bug, caught and fixed same cycle:** the first launch
(`cap29-stdwalklohi-triplecore{,-s1}`) crashed at 0 steps —
`dual_to_triple_transplant`'s own shape check refused cleanly
(`mlp_extractor.policy_net.0.weight (64,256) -> (128,256)`): this
specific Dual lineage's checkpoints were built with `net_arch=None`
(SB3's own pre-`--net-arch`-flag default, `{'pi':[64,64],'vf':[64,64]}`)
while the fresh Triple construction blindly used the CLI's `--net-arch`
default `[128,128]`. Root cause: the new `--gru-triple` branch built a
FRESH policy using CLI defaults instead of the loaded checkpoint's OWN
resolved geometry (a plain `--init-from` warm start gets this for free
via `algo_cls.load()`; this branch builds a different policy class so
must reproduce it explicitly). Fixed: derive both `net_arch` and
`lstm_hidden_size` from the already-loaded `old.policy` object, never
from CLI defaults. Both entries marked FAILED in the ledger (0 GPU
budget lost beyond ~1 min of vec-env compile); relaunched as `-r2`,
both VERIFIED RUNNING within the same cycle. No corruption, no
retraining from a bad state — the transplant's fail-closed shape check
did exactly its job.

Gate (unread, 2M-step canary each):
`probe_turn_authority.py --vx-cmds` combined-tick `wz_med` must beat
`cap29-stdwalklo-hi{,-s1}`'s own combined comparator on BOTH signs
WITHOUT a pure-turn `wz_med` regression >10% vs the same control and
without new DR-0 walk-only terminations — the identical bar the whole
8/8-FAIL open-loop family was held to, so this is apples-to-apples
with that closed family. A PASS here would be the first mechanism in
this whole campaign to win combined-tick turn authority without
blowing the pure-turn cap.

Prior banner (the full `combdose0p6-s1-r3` FAIL verdict closing the
whole 8/8 open-loop lever family, plus the `TripleGruActorCriticPolicy`
design this cycle executed) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-04v_trim.md`.

## Next (updated 09-04 ~03:5x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. `TripleGruActorCriticPolicy` BUILT +
   tested + LAUNCHED this cycle (see banner) — a 2-seed canary
   (`cap29-stdwalklohi-triplecore-r2{,-s1-r2}`, 2M steps each) is
   RUNNING, unread.** NEXT: when finished, triage with
   `probe_turn_authority.py --vx-cmds` against the banner's
   pre-registered gate (beat `cap29-stdwalklo-hi{,-s1}`'s combined-tick
   `wz_med` both signs, pure-turn regression <=10% vs the same control,
   no new DR-0 terminations). If it PASSES: this is the first mechanism
   in the whole campaign to win combined-tick turn authority without
   blowing the pure-turn cap — next step is wiring `yaw_critic.py`'s
   yaw-decomposed critic onto the Triple policy (currently refused,
   Dual-only) for a second, stronger-signal canary, then an acquisition
   budget. If it FAILS: the representational-interference hypothesis
   itself needs re-examination (a fully isolated 3rd core still not
   fixing it would be strong evidence the problem is upstream of any
   architecture split — e.g. the shared BC-anchor teacher reference
   itself, per the 09-03 16:1x finding that the SCRIPTED teacher
   already loses 67% of its own turn authority combined with forward
   motion).
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

## Fleet capacity note (updated 09-04 ~03:5x)

`TripleGruActorCriticPolicy` built + tested + launched this cycle (see
banner): 2 GPU slots spent on `cap29-stdwalklohi-triplecore-r2{,-s1-r2}`
(2M-step canary each, both VERIFIED RUNNING after a same-cycle
self-inflicted-bug fix). Every OTHER track remains non-launchable by
design (`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr`
RETIRED; `todaypolicy` DELIVERED). Next cycle's job is triaging this
canary pair once finished (~2M steps at ~2-3k fps on an H200 is a
short wait) — do not launch a 3rd/4th seed before that read; two
matched seeds is the standard first-mechanism-health grid this whole
campaign has used throughout.

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

