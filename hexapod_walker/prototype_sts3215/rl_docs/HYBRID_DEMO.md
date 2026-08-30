# Hybrid MuJoCo Demos

A hybrid robot candidate is a **controller/state composition**, not just
one checkpoint file. This matters because the transfer-shaped behavior
we want is:

1. start belly-down in a known state,
2. stand into the simulator's walk-ready state,
3. hand that state to a joystick walk controller,
4. return to walk-ready,
5. lower safely.

The headless demo tool is `rl_move.sim.hybrid_demo`; the normal operator
entrypoint is:

```sh
cd /workspace/hexapod/hexapod_walker/prototype_sts3215
bash rl_move/orchestrator/ops.sh hybriddemo <run> [out-dir] \
  [--script human|square|sweep|human_turn|turn] \
  [--wz-max 0.3] \
  [--policy-mode deterministic|stochastic] \
  [--stand-controller scripted|learned] \
  [--lower-controller scripted|learned] \
  [--stand-release stable|profile]
```

Use `hybriddemo` when comparing a policy plus its start/end states. Use
`drivevideo` only for walk-only rollouts that start from an already
settled plant episode.

## Default Composition

`hybriddemo` writes `composition.json` next to the video. The default
sequence is:

| Phase | Controller | State change |
|---|---|---|
| `stand` | `standup_modes.json` mode `step`, forward, or learned stance policy | `belly_zero` -> `step_stand` |
| `walk_ready_align` | pose blend to `[yaw=0, hip=20, knee=80] x6` | `step_stand` -> `walk_ready` |
| `walk_reanchor` | bookkeeping reset/restore, no body teleport | `walk_ready` -> `walk_ready` |
| `walk` | SB3 walk checkpoint under joystick script | `walk_ready` -> `walk_done` |
| `pre_lower_align` | pose blend back to sim walk start | `walk_done` -> `walk_ready` |
| `lower` | `standup_modes.json` mode `step`, reverse, or learned stance policy | `walk_ready` -> `grounded` |
| `limp` | torque-off MuJoCo settle | `grounded` -> `grounded` |

The bookkeeping re-anchor is the important handoff trick: the robot's
physical `qpos`/`qvel` are restored after an env reset, while the walk
policy's nominal plant frame, history, safety anchor, and servo profile
are reset into the distribution it trained on.

Learned stand defaults to `--stand-release stable`. That means the
headless demo does not wait for the full 15 s stance evaluation profile:
after the learned policy's own hold+ramp window completes, it requires a
short stable upright window (height, tilt, current) and then hands off to
the walk-ready alignment. Use `--stand-release profile` when the question
is validation/soak behavior instead of interactive joystick handoff.

## Artifacts

Each run writes:

- `drive.mp4`: full-sequence video.
- `contact_sheet.png`: quick visual strip.
- `composition.json`: controller/state plan.
- `summary.json`: full-mesh identity, phase marks, walk course metrics,
  current, tilt, termination, and gait/swing checks.
- `ticks.json`: per-control-tick telemetry.
- `transfer_manifest.json`: what maps to hardware and what is still a
  blocker.

Key comparison fields in `summary.json`:

- `terminated`, `termination_reason`, `phase_errors`.
- `model_variant`, `model_nmesh`.
- `walk_progress_ratio`: distance made along the command divided by
  requested command distance.
- `course_err_1s_med_deg`, `course_err_1s_p90_deg`,
  `wrong_course_frac_1s`: joystick direction following.
- `walk_wz_cmd_abs_max_rad_s`, `walk_turn_wz_err_med_rad_s`,
  `walk_hold_wz_med_rad_s`: yaw-rate command delivery and turn tracking
  for `human_turn` / `turn` scripts.
- `cur_max_a`, `cur_p95_a`, `roll_peak_abs_deg`,
  `pitch_peak_abs_deg`.

## Comparing Candidates

For policy comparisons, hold these fixed:

- same `--script`,
- same `--policy-mode`,
- same `--seed`,
- same stand/lower mode,
- same full-mesh model source.

Then swap only `<run>`. If a candidate needs a different start state,
write or edit a `composition.json` and pass `--composition`.

For stand/lower comparisons, hold the walk policy fixed and vary:

- scripted choreography with `--stand-mode` / `--lower-mode` among
  `step`, `tuck`, `drag`, and `blend`;
- learned stance with `--stand-controller learned` and optionally
  `--lower-controller learned`.

Use scripted `tuck` as the hardware-friendly stand/lower baseline when
the concern is foot drag or high lateral load. The hardware notes record
`tuck` as the clean 2.48 A stand-up path because it lifts/folds the feet
in the air before loading them; `blend` and `drag` are the foot-sliding
families and should be comparison/failure modes only. Example:

```sh
bash rl_move/orchestrator/ops.sh hybriddemo <walk-run> logs/manual_drive/<name> \
  --stand-mode tuck --lower-mode tuck --script human_turn --wz-max 0.3 \
  --policy-mode deterministic
```

For joystick-transfer videos, keep `--stand-release stable` so the
composition shows what an operator would actually feel: rise, stabilize,
handoff, drive. For stance-model validation, use
`--stand-release profile` and inspect the full hold tail.

The default learned stance checkpoint is the promoted mesh/100 Hz
stage-1 policy:

```text
rl_move/sim/policies/wandb_downloads/ppo_goal_cw_standwalk_stance_mesh2_stancemix_tuckclock_scratch8m/ppo_goal_cw_standwalk_stance_mesh2_stancemix_tuckclock_scratch8m.zip
```

Its matching deployable JSON export is:

```text
linux_control/policies/stand_stancemix_tuckclock_scratch8m.json
```

Use this before older learned stance policies (`stand_footlow2_hard1`,
`stand_holdbc1_hard1`, `stance_dr10`) when the target is the current
full-mesh/100 Hz MuJoCo transfer stack. It was promoted because the
cross-seed gate closed the single-policy rise/hold/lower stage-1
question: flat rise 12/12 seed0 and 11/12 seed1, hold 6/6+6/6, lower
6/6+6/6. It is still not hardware validated; it remains a simulation
candidate until read-only preflight and a supervised hardware ladder
say otherwise.

## Transfer Notes

The STEP stand/lower pieces already correspond to the robot-side
`linux_control/standup_modes.json` route. The walk piece transfers only
when the policy architecture has a deployed runtime:

- plain SB3 MLP policies can be exported with
  `uv run python -m rl_move.sim.export_policy_np ...`;
- transformer/recurrent SB3 checkpoints need a deployable runtime,
  a new exporter, or distillation into an exportable policy.

Before any physical robot run, do only read-only preflight first:
18 servos answering, IMU alive, pose near `sim_walk_start` or STEP
stand, tilt inside limit. Keep joystick commands inside the trained
envelope until a hardware ladder proves otherwise. Stop on tip,
brownout, high current, missing servo, or hot motor.
