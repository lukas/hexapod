# Design note: reopening the off-axis-heading front-pair (leg0/leg5) sacrifice

Required by `STATUS.md` WAITING-ON ("any reopening starts with a written
first-principles design note") after `CURRENT_TRUTHS.md`'s 2026-09-10
closure of `decleg` (all 3 easy-pilot arms FAIL) left "no untried
structural idea remains named." This note inventories every closed
mechanism, states the one geometric fact that explains WHY the front
pair specifically, and names the next candidate with a falsifiable gate.

## The problem, one sentence

The `rl_only` walking champion (`ppo_goal_..._widen8_..._cont10m`) walks
cleanly at on-axis (forward-ish) headings but chronically parks its two
FRONT legs (leg0 = +30°, leg5 = -30° mount angle, closest of all six legs
to the forward axis) at off-axis commands (±90°, ±135°, 180°), skating on
the other four — a fingerprint named LEGPARK-SKATE throughout this
campaign, unchanged across every fix tried.

## Full closure inventory (do not re-fund any of these without new evidence)

| # | Mechanism class | Instances tried | Result |
|---|---|---|---|
| 1 | Termination pricing | over_current/leg-sacrifice dose escalation (joystick `movecur1` 1x/2x/5x) | CLOSED — reconverges to the identical exploit at every dose |
| 2 | Reward price (duty-ratio, load-slip, swing-gap) | MIN-mode dose10, sum-aggregation dose25 (dose-corrected), swing-count-floor x3 seeds/2 lineages | CLOSED — MIN-mode is the best of these (shipped default); sum-agg/swing-floor add nothing beyond it |
| 3 | Exposure / batch composition | heading reweight (83%), heading-gain dose-scale, 100%-isolation curriculum | CLOSED end-to-end, 0%→83%→100% exposure, zero effect at any point |
| 4 | Exploration (entropy/log_std) | `headexplore` wide/held log_std, 3 seeds | CLOSED — ACQ FAIL-MECHANISM; sto-mode partial recovery is fully explained by cause #6 below, not genuine progress |
| 5 | Self-distillation | `heading_selfdistill`, per-heading policy self-imitation | CLOSED — FAIL-MECHANISM |
| 6 | PPO-loss level | per-heading advantage normalization (`heading_adv_norm`) | CLOSED — 2/2 seeds, 0/30 vs 1/30 pooled, nowhere near the 6/15 bar |
| 7 | Critic calibration | value-vs-realized-return diagnostic | INCONCLUSIVE (dominated by an OOD full-pin-episode reward-scale artifact) — does not license a mechanism either way |
| 8 | Kinematic reachability | rollout-trace action-box saturation check at h+90/h180 | CLOSED — legs 0/5 are NOT railed; 30-98% of box headroom sits unused, ruling out "box too narrow" |
| 9 | Architecture | `decleg` decentralized per-leg actor: plain, gSDE, half-gravity | CLOSED, all 3 — plain entrenches the identical fingerprint at parity budget; gSDE finds a WORSE failure (falls); half-gravity entrenches FASTER |

Nine independent classes, ~20+ arms, zero passes. This is the strongest
"exhausted the obvious levers" state this campaign has recorded for any
open question.

## The one fact that ties it together (read from the mesh, not assumed)

`mesh_mujoco/hexapod_mesh_mjx.xml` body mount angles: L0=+30°, L1=+90°,
L2=+150°, L3=-150°, L4=-90°, L5=-30° — **leg0/leg5 are the two legs
mounted closest to the forward axis of all six.** A forward command asks
them for the smallest reorientation of any leg; a 90-180° command asks
them for the LARGEST (they must swing through more than a right angle
relative to their own mount radius to contribute usefully), while the mid
legs (±90° mount) are already pre-aligned for lateral commands and the
rear legs (±150°) are already pre-aligned for reverse. Combined with
finding #8 (not box-railed) this rules out "cannot physically reach it"
and instead says: **the front pair's contribution at off-axis headings
requires a qualitatively different, less-natural joint trajectory than
any other leg ever needs for any command it's already good at** — a
harder per-state exploration target than a uniform noise/reweight/
critic-rescale treats it as, which is consistent with why none of
classes #1-7 (all of which treat every leg/heading interchangeably or
rescale a shared signal) moved the needle, and why decentralizing the
actor (#9, which still explores with the same PPO/Gaussian primitive,
just per leg) didn't either.

## What's actually different about the remaining candidate

Every exploration-adjacent lever tried so far (#3 exposure, #4 entropy/
log_std, #9 decleg) is a variant of **broadening how often or how loudly
the SAME on-policy Gaussian action noise gets sampled.** None of them
changes what gets REWARDED for being visited. The one exploration
PRIMITIVE never tried on this problem is a **state-novelty intrinsic
bonus (RND, Burda et al. 2018)** — reward for reaching observations the
predictor can't yet predict, independent of task return. This is already
built and wired end-to-end in this exact trainer (`rl_move/sim/
rnd_vec.py`, `train_ppo_mjx.py --rnd-coef`), so this candidate costs zero
new code, only a new hypothesis and launch.

**This is not free of history: RND was tried on this codebase before and
closed** (`RL_LOG.md` 08-23, 6+ arms, "RND-as-a-class fully refuted").
Read that closure precisely before reusing the mechanism: it targeted a
DIFFERENT problem in a DIFFERENT regime — a from-scratch, fresh-init
composite that had **never learned to walk at all** (static belly-sit or
all-legs-airborne hover, 0/6 gait_valid globally), and found that a
whole-observation novelty bonus at every dose (0.02-1.0) still converged
to the SAME collapsed static pose — a bootstrapping/ignition failure, not
a narrow behavioral tic in an otherwise-working gait. The champion this
note is about already walks cleanly with 4/6 legs at on-axis headings;
the question here is whether the same intrinsic-reward code, applied to
a policy that is NOT frozen and NOT collapsed, can pay for visiting the
specific joint-state region (front-leg active swing at extreme headings)
its own good overall reward currently never visits. That is a genuinely
different regime for the same mechanism, not a re-run of the closed
finding — but it is an honest reuse, not a new invention, and the gate
below is written strict enough to say so cleanly either way.

**Risk to flag going in:** the intrinsic bonus is computed over the FULL
observation, not scoped to the sacrificed legs or to off-axis headings —
it could just as easily reward novelty from the already-working forward
gait's natural variation and do nothing for the front pair specifically,
or (worse) destabilize the already-good on-axis behavior chasing novelty
elsewhere. A leg/heading-scoped variant (masking RND's obs input to just
the sacrificed legs' channels, or gating it on heading) would target the
mechanism much more precisely, but needs new code (obs-slicing plumbing,
tests) not yet built — named here as the fallback if the plain full-obs
canary below is inconclusive rather than cleanly negative.

## Canary (pre-registered before launch)

`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-rndexplore-canary2m`:
respec of the family's own common base
(`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-selfdistill-canary2m`,
which carries every prior lever's cfg key present but zeroed/inert —
the same clean shared ancestor every other single-lever canary in this
closed family used), single new lever `--rnd-coef=0.02` (the gentlest
dose the 08-23 closure tried, chosen deliberately conservative since
this is a WARM-STARTED already-competent policy, unlike the from-scratch
runs that dose was originally tried on — an aggressive bonus risks
damaging on-axis performance for no gain). 2M steps, phase=canary,
mesh_mjx, matches this family's config bit-for-bit otherwise.

**Gate.** MECHANISM-HEALTH: `reward_per_tick`/`ep_rew_mean` stay in the
same band as the sibling selfdistill/adv-norm canaries (no order-of-
magnitude collapse), `reward_rnd_intrinsic`/`intrinsic_mean` logged and
decaying over the run (proves the predictor is actually learning, not
inert), zero new falls vs baseline. **Efficacy PASS:**
`--pinned-heading-panel --baseline <frozen champion>` (n=3 det per
heading, both seeds pooled) `gait_valid` at the 5 chronically-broken
headings >= 6/15 combined, AND on-axis (forward) `gait_valid` does not
regress below the champion's own clean baseline (guards against the
named risk above). **FAIL:** gait_valid stays at/below the closed
0-2/15 floor with the same sacrificed-leg fingerprint, OR on-axis
performance regresses — either closes this candidate too, at which
point every named exploration/exposure/price/critic/architecture class
is closed and the next idea needs the leg/heading-scoped RND variant
(new code) or a genuinely different structural mechanism not yet
conceived. **CONTINUE per the 08-21 ruling** if reward is cleanly
rising/healthy and gait_valid is trending up but short of the bar at 2M.

Evidence for this note: `CURRENT_TRUTHS.md` 2026-09-09 ~19:4x through
2026-09-10 (top entry); `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09
~13:3x (kinematic-reachability close) and 2026-09-08/09 (mount-angle
read); `RL_LOG.md` 08-23 22:1x-23:5x (RND closure, from-scratch regime);
`rl_move/sim/rnd_vec.py`, `rl_move/sim/train_ppo_mjx.py` (`--rnd-coef`,
already wired, zero new code this note).

## Addendum, 2026-09-10 (refill cycle, after both plain full-obs AND
heading-gated RND closed 2/2 seeds each): per-leg obs-masking variant —
this note's own named fallback for a clean heading-gate FAIL — built
and launched

The heading-gate canary above closed CLEAN-FAIL, 2/2 seeds, byte-
identical to the untouched parent at every off-axis cell (not merely
unhelpful — the strongest possible negative read, `CURRENT_TRUTHS.md`
2026-09-10). Per this note's own text ("the next idea needs the leg/
heading-scoped RND variant (new code) or a genuinely different
structural mechanism"), the harder named fallback is the one still
untried: **mask WHAT the RND target/predictor nets see, not WHEN the
bonus pays out.**

**Why this is a genuinely different mechanism, not a third dose of the
same closed idea.** Both closed RND variants computed the intrinsic
bonus over the FULL observation (full-obs) or gated WHEN it pays out
by commanded heading (heading-gate) — both still let the front pair's
own joint-state novelty compete for bonus income against the five
OTHER legs' and the body's own natural variation, all baked into one
shared predictor. The obs-mask variant restricts the predictor/target
nets' INPUT to only the sacrificed legs' own columns (`leg0`, `leg5` —
q_rel/qd/prev_action triplets), so the ENTIRE bonus budget is novelty
in exactly the joint-space region the design note's mount-angle
argument says is under-practiced, on every tick regardless of
commanded heading (deliberately heading-agnostic, unlike the closed
gate — the kinematic argument is about what trajectory the legs need
to practice, not when the practice should be rewarded).

**Built (zero re-derivation of the per-leg obs-column enumeration):**
`rnd_vec.py` gained `obs_mask_idx` (new `RNDVecWrapper` kwarg, default
`None` = bit-exact original full-obs path — no column selection at
all) plus a `_select()` helper used uniformly by `step_wait` (obs-rms
update/normalize, target/predictor forward, ring-buffer push) and
`train_predictor`'s replay path; the heading-gate's own `cos_heading`
read is fixed to always index the FULL raw obs regardless of masking
(the two levers compose safely, though this canary uses obs-masking
alone). `train_ppo_mjx.py` gained `--rnd-obs-mask-legs` (comma-
separated leg indices, e.g. `0,5`), which calls `decleg_policy.
joint_walk_leg_slices` — the exact same per-leg obs-column
enumeration the (now-closed) `decleg` architecture already built and
unit-tested — rather than hand-deriving a new index map a third time.
9 new tests (`rl_move/tests/test_rnd_vec.py`): empty/out-of-range mask
rejected, `None` bit-exact-equivalence to the pre-09-10 wrapper,
network/obs-rms/ring sized to the masked dim not the full obs, obs-rms
and ring state reflect ONLY the masked columns after a step, and a
multi-tick probe showing intrinsic reward depends only on the masked
columns (unmasked-column variation leaves it unchanged; masked-column
variation changes it). Full file 17/17 green; touched-file suite
(`test_rnd_vec.py`+`test_decleg_policy.py`+`test_heading_selfdistill.py`
+`test_heading_adv_norm.py`) 52/52 green. `--help` smoke-parses the new
flag. Snapshotted before launch.

**Canary (pre-registered before launch):**
`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-rndobsmask-
canary2m`: respec of the SAME shared parent the heading-gate canary
used (`...-rndexplore-canary2m-clean`, i.e. the plain full-obs
`--rnd-coef=0.02` arm, NOT the heading-gated one — obs-masking and
heading-gating are independent levers, tested one at a time per
RESEARCH_RULES §10 discipline), single new lever
`--rnd-obs-mask-legs=0,5`. 2M steps, phase=canary, mesh_mjx, otherwise
bit-for-bit identical to the family.

**Gate.** MECHANISM-HEALTH: `ep_rew_mean`/`reward_per_tick` in the same
band as every sibling canary in this family at this depth (no
order-of-magnitude collapse), `rnd/intrinsic_mean` logged and decaying
over the run (predictor genuinely learning, not inert — same
diagnostic as every prior RND arm; no `gate_off_axis_frac` analog
exists for this variant since it does not gate by heading), zero new
falls vs baseline. **Efficacy PASS:** `--pinned-heading-panel
--baseline <frozen champion cont10m parent>` (n=3 det+sto/heading,
both seeds pooled) DET `gait_valid` at the 5 chronically-broken
headings >= 6/15 combined AND on-axis (0°/±45°) `gait_valid` does not
regress below the champion's own clean baseline (this variant fires on
EVERY tick including on-axis ones, unlike the closed heading gate, so
on-axis regression is a live risk here specifically — watch it
closely). **FAIL:** gait_valid stays at/below the closed 0-2/15 floor
with the same sacrificed-leg fingerprint, OR on-axis regresses —
closes this candidate too, at which point the design note's ENTIRE
named list (full-obs RND, heading-gated RND, per-leg obs-masked RND)
is exhausted and the next idea must be a genuinely different
structural mechanism, not another RND variant of any kind.
**CONTINUE per the 08-21 ruling** if reward is cleanly rising/healthy
and gait_valid is trending up but short of the bar at 2M.

Evidence: `rl_move/sim/rnd_vec.py` (`obs_mask_idx`/`_select`),
`rl_move/sim/train_ppo_mjx.py` (`--rnd-obs-mask-legs`),
`rl_move/sim/decleg_policy.py` (`joint_walk_leg_slices`, reused
unmodified), `rl_move/tests/test_rnd_vec.py` (17/17 including the 9
new obs-mask tests); `CURRENT_TRUTHS.md` 2026-09-10 (heading-gate
closure, this addendum's own trigger).

## Addendum 2, 2026-09-10 (refill cycle, after RND's entire named list closed
0/3 AND `decleg` independently closed 0/3): a 13th mechanism class —
weight-SHARED, mount-frame-relative per-leg actor — built and launched
as a cheap ignition pilot

**This is NOT a re-fund of the closed `decleg` family.** Read the
`decleg` closure (`CURRENT_TRUTHS.md` 2026-09-10, "no untried
structural idea remains named") precisely: it refutes SIX INDEPENDENT
per-leg towers (Schilling et al.'s own design — no cross-leg weight
sharing exists anywhere in `_DecLegExtractor.leg_nets`, by
construction). Independent towers cannot transfer a skill from one
leg to another even in principle: leg3's tower and leg0's tower are
different objects with different weights no matter how much either
one learns. That is a real, first-order structural difference from
what follows here, not a dose/seed/exploration variant of the same
mechanism — the closure's own "not another per-leg-actor variant"
line is read as "don't re-fund independent-tower decleg again",
not as "no per-leg-structured architecture may ever be tried again."

**The new idea, one sentence:** tie ALL SIX leg towers to ONE shared
set of weights, and feed each tower the commanded heading rotated
into THAT LEG'S OWN mount-angle frame (instead of only the raw
world-frame heading already in the shared obs tail) — so the same
physical ask ("swing N degrees off your own straight-ahead") looks
identical to the shared tower regardless of which leg is asked,
which is the precondition for the tower to actually reuse a skill
learned at leg3's easy heading when leg0 is later asked for its
mount-angle-equivalent hard heading.

**Why this specific pair of levers, not either alone.** Weight-tying
alone still feeds the tower the RAW absolute heading (a shared-dim,
not per-leg) — the same raw number means "your easy direction" to one
leg and "your hardest direction" to another, so a tied tower has no
way to recognize the two situations as equivalent even with identical
weights. The mount-relative feature alone (independent towers, each
fed its own rotated heading) changes nothing structurally: each tower
is still its own separate function, so there is still nothing for a
skill to transfer THROUGH. Only the combination gives the tied tower
an input where "leg0 asked for 180 degrees" and "leg3 asked for 0
degrees" are the SAME vector (mount angles 30 and -150 both put a
180-vs-0 pair at the identical -150 degrees relative-to-own-mount
angle — verified exactly, not just claimed:
`test_heading_rel_cos_sin_leg0_180_matches_leg3_at_forward`,
`test_shared_heading_rel_leg0_at_180_matches_leg3_at_forward` in
`rl_move/tests/test_decleg_policy.py` prove the rotated feature and
the tied-tower output are BIT-IDENTICAL between those two situations).

**Built** (`rl_move/sim/decleg_policy.py`, both new constructor kwargs
default OFF = bit-exact original independent-tower behavior, verified
by the existing 6/6 tests plus 2 new ones unchanged):
- `LEG_MOUNT_ANGLES_DEG` / `leg_mount_unit_vectors()` — the mesh's own
  per-leg mount angles (30/90/150/-150/-90/-30 deg), the exact fact
  the original design note (top of this file) named as the geometric
  root cause.
- `heading_rel_cos_sin(cos_cmd, sin_cmd, mount_cos, mount_sin)` — pure
  2D frame rotation, framework-agnostic (works on floats/numpy/torch).
- `_DecLegExtractor(..., share_leg_weights=False, heading_rel_idx=None)`
  — `share_leg_weights=True` builds ONE tower and references it N_LEGS
  times in the `ModuleList` (`nn.Module.named_parameters()` dedups by
  tensor identity, so the optimizer sees each weight once and every
  leg's gradient accumulates into it — standard weight-tying, same
  mechanism an RNN cell reused across timesteps relies on).
  `heading_rel_idx=(vx_ref_idx, vy_ref_idx)` appends `[cos_rel,
  sin_rel]` to every leg's local input.
- `train_ppo_mjx.py`: `--decleg-share-legs` / `--decleg-heading-rel`
  (both require `--decleg`, fail closed otherwise); the heading index
  is resolved post-venv via `heading_selfdistill.heading_vref_index`
  (reused, not re-derived — same obs-layout contract decleg and
  heading_selfdistill already share).
- Tests: 8 new (`test_decleg_policy.py`, 14/14 file green): rotation-
  math correctness, the leg0-180/leg3-forward equivalence (both at the
  pure-function AND the tied-tower level), default-off bit-exact input
  width, weight-identity + gradient-accumulation-through-tying, and a
  combined-kwargs PPO save/load roundtrip.

**What this pilot does NOT yet test.** Exactly like `decleg`'s own
first arm, this launches on the cheap `easy0905` forward-ONLY
ignition recipe (`goal.walk_heading_max_rad=0.0`) — deliberately, to
front-load "does a tied tower even ignite a coordinated six-leg gait
at all" as its own cheap question before spending budget on the
harder multi-heading recipe. Under a FIXED forward heading, the
rotated feature is a constant per leg (no transfer to exercise) — this
canary is pure `share_leg_weights` ignition-health, not the
heading-transfer hypothesis itself. **Next stage if this passes:**
respec onto the champion's actual multi-heading `widen8`/`crutchoff`
recipe (the only place the transfer hypothesis can be tested), never
this cheap recipe alone.

**Launched** (`backlog add`, from-scratch, byte-identical to
`cw-walkscratch-easy0905-decleg-base-{s0,s1}` except one added lever
`--decleg-share-legs --decleg-heading-rel`; 2M steps, phase=discovery,
track=walkcurr):
`cw-walkscratch-easy0905-declegshare-headrel-{s0,s1}`.

**Gate (pre-registered).** MECHANISM-HEALTH PASS (matches the
original decleg-base canary's own text): finite/decreasing PPO loss,
no NaN, real six-leg articulation under stochastic sampling by 2M
steps (a settled/static deterministic mean this early is NOT a
failure, matching every prior canary's own gate). FAIL (mechanism):
loss diverges/NaN, or one or more leg towers show zero gradient/frozen
output (a wiring defect distinct from "hasn't learned yet"). If PASS:
next step is the acquisition continuation (matching decleg-base's own
+18M/+20M budget) to check the tied tower reaches walking competence
at all, THEN — only if that clears — graduation to the multi-heading
recipe to test the actual transfer hypothesis (not this cycle).

Evidence: `rl_move/sim/decleg_policy.py` (`heading_rel_cos_sin`,
`leg_mount_unit_vectors`, `_DecLegExtractor` kwargs),
`rl_move/sim/train_ppo_mjx.py` (`--decleg-share-legs`,
`--decleg-heading-rel`), `rl_move/tests/test_decleg_policy.py`
(14/14); `ops.sh entry cw-walkscratch-easy0905-decleg-base-s0` (the
byte-identical parent spec this respecs in spirit).

## Addendum 3, 2026-09-12 (idle-kick refill; 15/15 GPU free, backlog+
pending_evals empty, every other track independently re-confirmed closed
this window): a 14th mechanism class -- the joystick track's own
cert-gated heading-widening curriculum, never applied here -- built
(zero new code) and launched

**Why this is genuinely different from every closed class above.**
Classes #3 (exposure/batch composition, incl. the 100%-isolation
canary) and #4-#7 (exploration/self-distill/PPO-loss/critic) all
either kept the full 8-way heading mix present in every batch the
WHOLE run, or removed forward practice entirely for the whole run
(isolation). None of them used a monotonic, MASTERY-GATED ramp: start
where the champion is already competent (forward, +-45), and widen the
practiced heading cone ONLY once a deterministic held-out assay
certifies real competence+retention at the current width, exactly the
curriculum SHAPE standard curriculum-learning theory prescribes for
"policy already good at the easy sub-task, bad at a harder
generalization of it." This shape has never been tried on this
champion/question -- every prior curriculum-flavored attempt (isolation,
reweight) was static-composition, not progressive-widening-with-gates.

**It already exists.** `goal.walk_curriculum` / `--walk-curriculum-version`
(`rl_move/sim/walk_curriculum.py`, `WALKCURR_BUCKETS_V6` through `_V9`)
is mature, heavily field-tested machinery built for the JOYSTICK track's
own DONE-gate (bridge_10s -> front45 -> side90 -> rear135 -> rear180 ->
fullcircle, each rung cert-gated on a deterministic held-out assay,
retention-checked before promotion, V9 is the latest cert-metric fix of
V8's already-working bucket scope) -- confirmed by grep against this
track's own `STATUS.md` and `RL_LOG.md` that it has never once been
combined with the `widen8`/`crutchoff`/dose10 champion or this exact
off-axis-heading question. Contract-safe: it only reschedules WHICH
commands get trained on (a deterministic function of measured
competence), never touches the actor's action distribution or
introduces a teacher/demo signal -- stays inside `walkcurr`'s `rl_only`
no-BC/no-motion-prior contract exactly like the already-used exposure/
reweight levers did.

**Built:** nothing (zero new code). Confirmed via `walk_task._sample_
walk_curr` that once `goal.walk_curriculum` is on, it fully owns
command generation (`goal.walk_heading_set`/`walk_heading_max_rad`/
`walk_stop_frac` become inert, verified by reading the source, not
assumed) -- so this is a pure recipe change: swap the champion's
static 8-way `goal.walk_heading_set` for `--walk-curriculum
--walk-curriculum-version=9`, warm-started from the champion's own
retention-confirmed checkpoint (`--init-from-source`, allowed for
V5-V9 per the code's own documented exception list), `--episode-seconds`
raised 20->60 (V6-V9's own hard requirement: training episodes must
cover the longest bucket's `duration_s=60s`). Everything else (dose10
duty-ratio/swing-gap reward pricing, DR, action box, safety) inherited
byte-identical from the frozen champion.

**First attempt crashed at argparse** (`cw-walkscratch-crutchoff-s0-
widen8-plusduty-walkcurr9-canary2m`, r0): the respec blindly inherited
`--best-ckpt` from the champion's own recipe, which `--walk-curriculum`
explicitly forbids (`SystemExit`: "owns best-checkpoint selection...
drop --best-ckpt/--ev-stop-min") -- caught by the trainer's own
pre-flight validation before any GPU-second was spent, zero W&B run
created. Verdicted `CANARY FAIL - INFRASTRUCTURE` (launch-config
mistake, not a finding) and relaunched clean as `-r1` (best-ckpt
dropped, otherwise byte-identical) via `backlog add` (hand-built arg
list, since `respec` has no "drop an inherited bare flag" primitive)
-- VERIFIED RUNNING train-0, fps ~4369.

**Pre-registered gate (2M canary, phase=canary):** MECHANISM-HEALTH:
boots/trains past init, >=1 real cert round logged (walkcurr admission
log shows a fresh assay, not stuck at `cert_round=0`), no NaN/crash,
`reward_per_tick` in the champion's own -1..-4/tick band, no new-fall
spike. EFFICACY PASS: frontier (`active_n`) reaches bucket>=4
(`side90`, the first genuinely off-axis rung) within 2M steps AND a
`--pinned-heading-panel` read at on-axis headings (0/+-45) shows
`gait_valid` unregressed vs the frozen champion. EFFICACY CONTINUE
(08-21 ruling): frontier measurably advancing (past bucket 1) with
reward/competence trending up even if bucket>=4 isn't reached at 2M --
license a budget continuation, not a verdict. FAIL: frontier stuck at
bucket 0/1 for the whole run (the SAME certifying-forever-at-bridge/
front45 pattern the joystick track's own certfreeze v6/v7 saga hit)
with the unchanged sacrificed-leg fingerprint on a pinned-heading-panel
read at the still-locked headings, OR on-axis regresses -- this would
mean the joystick-tuned per-bucket gate thresholds (e.g.
`slip_per_m_max=2.0`) are miscalibrated for this champion's own
physics/reward profile and the mechanism can't even get started here,
closing this as the 14th class.

Evidence: this file (13-class inventory above); `rl_move/sim/
walk_curriculum.py` (`WALKCURR_BUCKETS_V9`); `rl_move/sim/
train_ppo_mjx.py` (`--walk-curriculum`/`--walk-curriculum-version`,
pre-existing); `ops.sh entry cw-walkscratch-crutchoff-s0-widen8-
plusduty-walkcurr9-canary2m` (r0, LAUNCH_CRASH) and `...-r1` (VERIFIED
RUNNING train-0); `ops.sh entry cw-walkscratch-crutchoff-s0-widen8-
legdutyratio-swinggap-dose10-plusduty-acq1-cont10m` (champion/source).
