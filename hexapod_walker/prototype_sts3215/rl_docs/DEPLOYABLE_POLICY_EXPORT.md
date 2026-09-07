# Deployable policy export

This is the repeatable path from an SB3 checkpoint to the single JSON file
used by MuJoCo replay and the Uno Q. It supports both the original two-layer
MLP actor and the unified mode-gated dual-GRU actor. Export never moves the
robot and never deploys a service.

## Supported observation contracts

All walk layouts start with the common 68-wide joint/IMU/action/goal
observation. The remaining fields are appended in this frozen order:

| Width | Tail after the common 68 | Runtime |
|---:|---|---|
| 72 | `vx_ref, vy_ref, vx_meas, vy_meas` | MLP |
| 74 | obs 72 + `sin(phase), cos(phase)` | MLP |
| 75 | obs 74 + `wz_ref / 0.5` | MLP |
| 81 | obs 75 + `[hold,rise,lower,walk,turn,quad]` | persistent dual-GRU |
| 93 | obs 75 + 18 joint-health values | MLP |

Velocity fields are divided by 0.15 m/s. The deployable
`walk_obs_body_vel=2` contract copies the commanded `vx_ref,vy_ref` into the
measured-velocity slots. The phase clock advances at `meta.phase_hz` while
translation is commanded, and also while yaw alone is commanded when
`meta.walk_phase_run_on_yaw=true`.

The obs-81 one-hot order is part of the file metadata and validation refuses
any drift. Both GRU cores execute on every tick. The last three one-hot slots
select the locomotion core; the first three select the stance core. Do not
reload the file, recreate its model object, or reset hidden state at a command
or mode change. Reset only at a true control-episode boundary.

## 1. Pull and identify the checkpoint

Reuse the orchestrator helper; it resolves the run record instead of guessing
a W&B filename:

```sh
bash rl_move/orchestrator/ops.sh pullckpt <run-name>
shasum -a 256 rl_move/sim/policies/ppo_goal_<run-name>.zip
```

New checkpoints carry `joint_frame=robot_abs` and
`joint_contract=robot_abs_tibia_v2`. Export fails closed without those
stamps. For a checkpoint created before stamp support, preserve the original
and stamp only a named copy:

```sh
cp rl_move/sim/policies/ppo_goal_<run-name>.zip \
  /tmp/ppo_goal_<run-name>.robot_abs.zip
uv run python -m rl_move.sim.stamp_legacy_checkpoint \
  /tmp/ppo_goal_<run-name>.robot_abs.zip
```

Stamping records an existing coordinate fact; it does not alter weights. The
tool refuses a checkpoint that already declares a different contract.

## 2. Export with the training contract

Use the same exporter for MLP and dual-GRU checkpoints. Architecture is
detected from the checkpoint. The exporter serializes actor weights only and
runs deterministic parity before it writes the output.

```sh
uv run python -m rl_move.sim.export_policy_np \
  --policy <checkpoint.zip> \
  --out /tmp/<policy-name>.json \
  --name <policy-name> \
  --training-hz 100 \
  --extra-meta '{
    "phase_hz": 1.333333,
    "walk_phase_run_on_yaw": true,
    "walk_speed_min_m_s": 0.08,
    "walk_speed_max_m_s": 0.08,
    "max_delta_q_deg": 0.375,
    "bus_write_speed": 400,
    "bus_write_acc": 20
  }'
```

Copy these values from the run's actual launch command. Do not borrow them
from a nearby lineage. Obs 75 and 81 exports require a positive phase rate and
an explicit yaw-clock contract; validation catches omissions before the file
can enter a picker.

The dual-GRU matrices are base64 float32 arrays inside JSON. This is not a
lossy conversion: SB3 stores these parameters as float32. It makes the cap29
actor about 2.9 MiB instead of a much larger decimal-list JSON and keeps the
artifact self-contained.

## 3. Validate and test locally

```sh
uv run python -m rl_move.np_policy validate /tmp/<policy-name>.json
uv run pytest -q \
  rl_move/tests/test_np_policy.py \
  rl_move/tests/test_deployed_policy.py \
  rl_move/tests/test_export_policy_np.py
```

Exporter parity covers 200 ticks, all six mode slots, multiple mode changes,
and multiple episode resets. It checks both action output and recurrent hidden
state against SB3. Unit tests independently compare the NumPy GRU equations to
`torch.nn.GRU` and cross-check the obs-81 one-hot against `walk_task.py`.

For a candidate intended for hardware, also run the existing exported-runtime
MuJoCo/replayed-transport check and the no-motion hot-path timing probe. A
successful weight parity result does not prove the full sensor/write loop can
meet the checkpoint's 100 Hz contract.

## 4. Upload without selecting or moving

After code/runtime review, the portable file can be uploaded to a robot or the
local sim service:

```sh
uv run python -m rl_move.np_policy push /tmp/<policy-name>.json \
  --host http://hexapod.local:8080
```

Upload is storage only. Selecting roles, starting a session, standing, and
walking are separate operator actions. A unified obs-81 controller must use
one shared loaded model object for its walk and hold/mode roles so recurrent
state stays continuous. The hardware runner recognizes both the same path and
the byte-identical live-slot copy made by the policy picker, then reuses one
actor object. It refuses an obs-81 drive session if walk and hold resolve to
different payloads.

The complete no-motion setup is:

```sh
ROBOT_URL=http://hexapod.local:8080
POLICY_FILE=<policy-name>.json

# Store the artifact (same as the `np_policy push` command above).
curl -sS -X POST "$ROBOT_URL/api/rl/policies?name=<policy-name>" \
  -H 'Content-Type: application/json' --data-binary @/tmp/$POLICY_FILE

# Make policy metadata and the fixed-duration Walk action resolve to it.
curl -sS -X POST "$ROBOT_URL/api/rl/policy_select" \
  -H 'Content-Type: application/json' -d "{\"file\":\"$POLICY_FILE\"}"

# For persistent obs-81 joystick drive, both roles must name this artifact.
curl -sS -X POST "$ROBOT_URL/api/rl/roles" \
  -H 'Content-Type: application/json' \
  -d "{\"role\":\"walk\",\"file\":\"$POLICY_FILE\"}"
curl -sS -X POST "$ROBOT_URL/api/rl/roles" \
  -H 'Content-Type: application/json' \
  -d "{\"role\":\"hold\",\"file\":\"$POLICY_FILE\"}"

# Read-only confirmation; none of the commands above move the robot.
curl -sS "$ROBOT_URL/api/rl/policy"
curl -sS "$ROBOT_URL/api/rl/roles"
```

Do not turn those setup calls into a walk request. Robot Lab experiments
remain `external_guarded` until an operator explicitly starts them. The
current obs-81 hardware surface emits `walk` and `hold` mode slots only;
learned rise/lower and other transition modes remain separately gated work.

## Verified examples (2026-09-05)

| Candidate | Source SHA-256 | Export | Parity |
|---|---|---:|---:|
| `cw-walkteach-scripted-allhead-acq12m` | `a813c4a692081978359042f825aaf5c4b43b58f91ffcd6db365a80d6827f4167` | 575 KiB, obs-75 MLP | max action error `1.79e-7` |
| `cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi` | `5fd267c0f7491900881daeb34e416f6c45d8a1b4a815e809de9deac32ac28b49` | 2,941 KiB, obs-81 dual-GRU | max action error `1.19e-7`; hidden error `4.62e-7` |

These are software-parity results, not physical approval. The first cap29
Robot Lab request remains a bounded walk-only canary; learned rise/lower,
height changes, and turns require separate evidence and authorization.
