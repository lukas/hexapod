# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~10:1x (this cycle — klrolltight2 DIG-IN resolved,
reward-decomposed critic BUILT + tested + launched). Plain English:
**closed the last open fork on the update-size-constraint axis, then
built and launched the campaign's next lever (a critic that learns a
SEPARATE value for the yaw reward alone) — its 2M canary pair is
training now, not yet readable.**

1. **klrolltight2 DIG-IN resolved** (verdict: ACQ PARTIAL -
   GUARD-REJECT-ALL, CRITIC-ONLY ARTIFACT, AXIS CLOSED). `--kl-
   rollback=0.01` rejected EVERY post-unfreeze actor update
   (rollback_count=457, actor tensors bit-identical 2M->38M via direct
   state_dict diff) — an accidental critic-only continuation, not a
   genuine tighter-dose test; its nominal wz "PASS" is a false
   positive (untouched init carried forward). Fork decided: no guard
   scale-down-and-retry fix funded — the whole freeze/value-warmup/
   kl-rollback family already closed this window (klrolldriftmatch
   matched-drift, n=4) at a ceiling a repaired guard would only
   re-discover. Dose axis stops at 0.02.
2. **Built the reward-decomposed (yaw-component) critic**
   (`rl_move/sim/yaw_critic.py`, the campaign's own named next lever —
   see the archived 09-01 ~09:0x head for the root-cause/scope).
   `value_net_yaw` mirrors `value_net` off core-A's (locomotion)
   DETACHED critic trunk, trained via its own hand-derived GAE
   (cross-checked bit-identical against SB3's own
   `compute_returns_and_advantage` on a random buffer) over
   `reward_walk_yaw` alone; a separate (undetached) actor
   policy-gradient step uses the yaw-only normalized advantage
   (mathematically equivalent to summing it into the PPO advantage at
   ratio=1 — matches this codebase's `mirror.py`/`bc_anchor.py`
   separate-step house style, no sb3-contrib internals touched). New
   cfg keys `train.yaw_credit_coef`/`_vf_coef` default 0/OFF, bit-exact
   when off (pinned by test). 13/13 `test_yaw_critic.py` green.
   Snapshots: `exp/yaw-decomposed-critic-standwalk-turnauth`,
   `exp/yaw-decomposed-critic-fix-cudnn-and-checkpoint-shape`.
   **Two real bugs found and fixed on the FIRST on-pod attempt (both
   invisible to CPU unit tests, both now pinned by new regression
   tests):** (a) `collect_rollouts` leaves the policy in eval mode;
   a cuDNN RNN backward pass on GPU requires training mode to have
   been set before the matching forward or the C++ backend raises —
   fixed by `policy.set_training_mode(True)` at the top of the aux
   step. (b) the yaw head must NEVER be a registered `nn.Module`
   attribute or live in `policy.optimizer`'s param groups: every
   launch here is a warm start, and a plain (yaw-credit-unaware)
   `.load()` — used by the trainer's own bg-video helper,
   `probe_turn_authority`, `pod_eval`, the gate harness — reconstructs
   the policy from the checkpoint's OWN saved `policy_kwargs` then
   crashes on `Unexpected key(s) in state_dict` / a param-group-count
   mismatch. Fixed by keeping the head in a plain (non-`nn.Module`)
   list with its OWN independent optimizer, invisible to
   `state_dict()`/`policy.parameters()`/the main optimizer entirely —
   every checkpoint this mechanism saves is byte-identical in shape to
   a non-yaw-credit one.
3. **Canary pair launched** off `turnpay-canary` (the campaign's
   pre-registered plan): `cw-standwalk-stage2-dualbc6-turncap-
   mirroraug-yawcredit-ctrl-canary` (matched control, coef=0, DONE at
   2M) and `...-yawcredit-canary-rr1` (treatment, yaw_credit_coef=1.0/
   vf_coef=0.5, `-rr1` because attempt 1 crashed on bug (a) above and
   a W&B run already existed under the base name — training now,
   confirmed past the crash point). Gate: PASS/PROMOTE if final wz_med
   beats the control by >=0.02 both signs with gait/progress held;
   INFORMATIVE if within ~0.01-0.02 (try a higher dose or shared-trunk
   variant next); FAIL if gait/progress regress hard (cut dose). NOT
   YET READABLE this cycle — next cycle's triage reads both finals.

Previous entry (2026-09-01 ~09:0x, JOINT CLOSE 2/2 on the
matched-actor-training-steps confound + the klrolltight2 DIG-IN
flag) preserved VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md` (appended
09-01 ~10:1x) — do not re-derive; read it there if needed.)


## Next (meta 09-01 ~10:1x — current queue, in order)

1. **Read the yaw-credit canary pair** (both launched this cycle, see
   the Update banner): `...-yawcredit-ctrl-canary` (control, done at
   2M) vs `...-yawcredit-canary-rr1` (treatment, training). PASS/
   PROMOTE if treatment's final wz_med beats control by >=0.02 both
   signs with gait/progress held; INFORMATIVE if within ~0.01-0.02
   (next: coef 3.0-5.0 or a shared, non-detached trunk variant); FAIL
   if gait/progress regress hard (cut dose 5-10x).
2. **Standing bar (unchanged):** every new dual distillation must
   pass pre-RL probe_turn_authority >=0.10 both signs (mirror-augment
   is the known fix); RL arms on this line are funded as turn
   RETENTION only, never turn discovery.
3. **Closed lines — do not refund:** update-size constraints (actor-
   freeze, value-warmup, kl-rollback 0.05/0.02/~0.01, incl. the
   guard-reject-all 0.01 artifact; matched-drift confirmed n=4),
   reward pricing (turnpay 1x/5x, yawscale 5x/15x, k_yaw_still, turn
   density), exploration magnitude (log_std -0.8/-0.2, ent-coef),
   anchor dose/isolate-update, turn-skip. Evidence:
   archive/standwalk_STATUS_journal_2026-09-01_trim.md.


> Journal archives (VERBATIM, meta trims): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 ~03:1x
> through 09-01 ~10:1x in
> `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
> Current state lives in the newest Update at the TOP of this file;
> do not act on archived Next items.

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
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B). The rise-reference machinery (`extract_rise_ref.py`,
rise bank) is green as of 08-24. Bank/semantics-check the stance
reward ON MESH before the first launch (mass went 2.104 -> 3.50 kg;
thresholds calibrated on primitive may rank behaviors differently).

GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.


## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.

