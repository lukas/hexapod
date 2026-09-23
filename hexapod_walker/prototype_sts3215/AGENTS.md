# Agent conventions — prototype_sts3215

The repo-root `AGENTS.md` governs everything here: subtract first, goals
(`RL_GOALS.md`, `RL_PLAN.md`), worktrees, `uv`, tests, standing authorization
and hardware safety (`EMERGENCY_HANDLING.md`; before a new recovery routine also
`RECOVERY_LESSONS.md` and `linux_control/ROBOT_OBSERVE.md`).
The orchestrator, those research-rule docs and its state live in https://github.com/lukas/hexapod-orchestrator; config gates are temporary: adopt the value into `config.yaml` or delete the gate, with tests, once the run that needed it is verdicted.

## Feet never slide under load (hardware rule, Lukas 2026-09-22)

A foot that carries weight does not move across the floor. Not a little, not at
low current: it stresses the plastic and adds uncertainty to every maneuver.
Feet move only through the air (lift, place), one tripod at a time; the body
moves only on planted feet whose commanded path keeps them where they are
under the REAL leg kinematics (`rl_move/sim/compare_standup.RealLegFK`, not
the naive 2-link model). Before any stand / sit / re-plant / lower is tried
on a robot, run it through `rl_move/sim/lower_sim.py`: `run()` reports
`PASS_zero_slip` against `SLIP_GATE_MM` (3 mm of loaded-foot travel). A
maneuver that fails the gate is not a candidate, whatever else it achieves.
Measured 2026-09-22 with the real model: the exported STEP stand-up sweeps the
loaded feet 44 mm during its push, the removed TUCK 19 mm, the old tuck lower
23 mm, the reversed STEP 22 mm, and a planted six-leg descent 99 mm; none pass.
Slip is NOT the whole score. Lukas judged, on the robot, the reversed STEP sit
(22 mm sim slip, pulled inward) far better than a tripod-stepping lower with
half the slip: it is one continuous motion with all six legs sharing the load
(peak 20 % of the weight on one leg, no load handoffs until the belly is
down) versus 36 % on one leg and 22 handoffs in 4 s. Report three numbers for
any stand/sit: loaded-foot slide, peak single-foot load share, load-handoff
count; inward slide beats outward. The sit-down is the STEP stand-up played
backwards with per-robot fold caps (`api/standup.py` `_FOLD_CAPS`: hexapod2
hip -52 / knee 125, its mechanical stops); do not invent another lower.
Also: never move six loaded legs at once; never hold a fight (a static hold
reads ~0.3 A total); never drop the robot; never deploy (the service boots
limp) while a robot is off its belly.

## MuJoCo robot simulation

Start with [`sim_viewer/README.md`](sim_viewer/README.md). From this
directory, the canonical foreground MuJoCo + web UI entry point is:

```sh
sim_viewer/sim_web.sh
```

It opens the native MuJoCo viewer and serves the controller at
`https://localhost:8443/rl` (`http://localhost:8898/rl` as the HTTP fallback),
launching through `uv run mjpython` on macOS. The one-window interactive
policy and gamepad player is `sim_viewer/sim_play.sh`.

To show a recent walking checkpoint being driven, use the orchestrator
wrapper rather than reconstructing the run configuration by hand:

```sh
bash ~/hexapod-orchestrator/orchestrator/ops.sh drivevideo <run-name> \
  --script human_turn --seconds 29 --policy-mode deterministic
```

`drivevideo` resolves the checkpoint, carries the run's own configuration,
verifies the full-mesh model and writes `drive.mp4` under `logs/manual_drive/`.

Command-bearing render paths draw render-only cues from
`rl_move/sim/command_indicator.py` (green planar direction, amber yaw, blue
rise/lower); they never enter the physics.
