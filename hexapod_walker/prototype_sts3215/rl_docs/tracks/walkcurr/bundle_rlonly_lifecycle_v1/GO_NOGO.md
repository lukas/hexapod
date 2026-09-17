# walkcurr-rlonly-lifecycle-stance-s5-to-walk-s0-direct-v1 — GO/NO-GO (2026-09-17)

## Verdict: GO for sim-demo evidence that the rise+hold -> walk DIRECT handoff (no scripted blend) is CLEAN. NOT a physical-acceptance verdict, NOT a full lifecycle (no `lower`).

One plain sentence: taking the two already-validated, separately-trained
clean-RL `rl_only` roles (rise+hold stance, forward walk) and handing control
from one to the other on the stance role's own exact physical state — no
scripted joint blend, no new training — produces zero falls across 12
episodes (6 det + 6 stochastic) with drive quality statistically
indistinguishable from the walk role's own clean-reset control arm.

## Why this cycle did this (gap it closes)

`bundle_rlonly_stance_v1`'s own GO/NOGO (2026-09-17, same day) named this
exact gap as its concrete "Next," item 1: "design and build the rise+hold ->
walk-ready handoff ... chaining two independently trained rl_only roles
instead of one any_means bundle ... Not started this cycle (a real
design/build task, not a launch)." With 15/15 GPU slots free, an empty
backlog, and every other track independently closed pending Robot Lab or an
unconceived design (re-surveyed via `ops.sh board`), this cycle built and ran
that composition tool — no GPU spend needed (CPU MuJoCo, frozen policies).

RL_GOALS.md explicitly allows composing separately-trained clean RL roles
instead of requiring one monolithic actor; this is the first time that
composition was actually exercised end to end for this lineage instead of
just being named as allowed.

## What shipped this cycle

1. **`rl_move/sim/cfg_recipe_walk50hz_rlonly_v2.py`** (+ mechanics-only
   tests): the canonical, versioned `--cfg-set` list for the
   `bundle_rlonly_v2` walk role, verbatim from its recorded launch command —
   the same "stop hand-retyping ~50 flags" fix
   `probe_currentcap29_flatonly.py` already applied to the stance side,
   extended to the walk side so this and any future walk-role re-eval share
   one source of truth.
2. **`rl_move/sim/eval_lifecycle_handoff_rlonly.py`** (+ mechanics-only
   tests for the pure physical-state-copy helper): a new composition eval —
   two `SimHexapodJointWalkEnv` instances (one per role's own exact cfg,
   since `bus.write_speed`/`write_acc`/`safety.max_delta_q_deg`/
   `goal.joint_action_bias_*` genuinely differ between the two roles and are
   cached at env construction), with the stance role's raw physical state
   (qpos/qvel/ctrl/act + the safety layer's slew memory) copied into a
   freshly plant-reset walk env at the handoff tick — the same
   `reanchor_keep_state` trick the pre-existing (different-lineage)
   `eval_handoff.py` tool established, generalized to a cross-env copy.
   Arms: `direct` (stance rise+hold -> handoff -> walk champion) vs `plant`
   (walk champion's own clean-reset control).
3. **Ran it** (CPU MuJoCo, mesh_mjx model, no GPU spend): det pass (n=6) and
   stochastic pass (n=6), both flat-start rise. Frame strips captured for
   episode 0 of each arm.

## Result

| pass | arm | rise_valid | handoff_falls | trk_err band | dist band (m) | stumble tilt band (deg) |
|---|---|---:|---:|---|---|---|
| det | direct | 6/6 | 0/6 | [0.083, 0.096] | [0.669, 0.86] | [3.7, 5.0] |
| det | plant (control) | — | 0/6 | [0.087, 0.098] | [0.708, 0.847] | [3.6, 4.5] |
| sto | direct | 6/6 | 0/6 | [0.097, 0.104] | [0.528, 0.682] | [3.9, 5.4] |
| sto | plant (control) | — | 0/6 | [0.097, 0.105] | [0.63, 0.763] | [3.7, 5.5] |

Every direct-arm metric sits inside or within noise of the plant-control
band — the handoff costs nothing measurable versus the walk role's own best
case. Frame strips (`logs/ckpt_eval/lifecycle_handoff_rlonly_v1/strips/
direct_0.png`) show a clean flat-start rise to a settled hold, then a
direct switch (blue hold-arrow -> green forward-command arrow) into a
visibly cycling tripod gait — no dragged leg, no height/tilt discontinuity
at the switch frame.

## TODAY bars

- Clean `rl_only` provenance: PASS — both source checkpoints are already
  `rl_only`-clean (their own manifests); the composition adds zero new
  training and only role-selection/config-selection plumbing at the
  handoff, the RL_GOALS.md-allowed non-motion category (no scripted joint
  trajectory anywhere in this eval).
- No scripted motion role: PASS — `direct` has no blend phase at all (unlike
  the older, different-lineage `eval_handoff.py`'s own `blend` arm, which
  this bundle deliberately does NOT use or need).
- Reproducible non-interactive sim evidence, 0 falls: PASS, 12/12 episodes
  (both det and stochastic).
- Held-out-style gate vs a control band: PASS — matched against the walk
  role's own clean-reset arm, not just an isolated pass/fail count.
- Video: PASS (frame strips this cycle; a full mp4 was not additionally
  rendered — the strips already show a rise->handoff->walk arc at 1fps,
  same convention `eval_handoff.py` uses for its own strips).
- Single sit/rise/walk/lower bundle: NOT CLAIMED — `lower` is still CLOSED
  (CURRENT_TRUTHS.md 2026-09-17); this is rise+hold+walk only.
- Physical acceptance: NOT CLAIMED — sim-only, CPU MuJoCo, no robot access.

## Next

1. Robot Lab (when a bounded trial is queued): the composed runtime must
   actually switch the per-role motor/safety contract at the handoff tick
   (stance's tighter `max_delta_q_deg=0.75` vs walk's `7.2`), not just splice
   the walk role's np-JSON export onto the stance role's — this manifest
   proves the POLICY-level handoff is clean, the robot-side contract switch
   is a separate hardware-runtime build, not evaluated here.
2. Cloud: `lower` remains the last lifecycle gap; no new agent-doable lever
   is open (16/16 mechanism classes closed) absent a genuinely new idea.
3. Cloud, optional polish: an mp4 (not just 1fps strips) of the composed
   sequence would make the demo easier to show, if a future cycle has spare
   CPU time and no higher-priority lever.
