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
