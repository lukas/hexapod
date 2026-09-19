# Driving the physical robots — start-of-session checklist

Written after a 2026-09-18 session where the first 40 minutes went to the wrong
robot. Everything here is read-only or has its own guards; the tools it points
at refuse to move an armed robot.

## 1. Look before you touch

```bash
# from prototype_sts3215/
uv run python linux_control/fleet.py status      # both robots: servos, armed, new-motor?, bus V, last commands
```

`status` calls `plan_swap` per robot, so a replaced servo (which joins the bus
as **ID 1** with a factory zero, `name "ID1"`, `joint null`) shows up as
`NEW MOTOR` on the row for the robot that actually has it. Do not infer the
robot from what someone said — the operator has said "hexapod2" for the `.39`
robot the code calls **hexapod1**. The bus is the source of truth.

The `last:` lines are the attributed command journal (`GET /api/commands`). A
click on the `:8898` hub page shows up as `mac-hub via <ip>`; a stray drive
from another session is visible here before you start.

## 2. Know which camera sees which robot

```bash
uv run python linux_control/fleet.py eye hexapod2.local
```

- **hexapod.local** (red/blue, AprilTag lids): laptop server cam 1
  (`http://Lukass-MacBook-Pro-2.local:8766/snapshot/1.jpg`, stream `/raw-stream/1.mjpg`).
- **hexapod2.local** (purple lid, chassis tag 119): Studio ELP **side** camera
  (`hexapod-cameras snapshot --role side`), partial view.
- Studio **top** camera (floor-fitted) frames whichever robot is in the tag
  area; use it for gait metrics and run `hexapod-cameras check --role top`
  first — it flaps around the 6 px drift limit when bumped, refit with
  `hexapod-cameras calibrate floor --role top`.
- Laptop server cam 0 is a workbench. The `~/.claude/CLAUDE.md` table calling
  cam 1 "hexapod 2" is stale; trust this file / a live frame.

## 3. Replace a servo

`linux_control/motor_swap.py status|assign|zero|check` (see the README section
"Replacing a servo"). The `check` step's gentle `/api/setup/wiggle` reports
"did not reach target" on ~half a limp robot's joints from floor friction —
that is not a fault; the `--amp 15` bench wiggle with `--stream` is the real
camera confirmation.

## 4. Stand → walk → lower

- `POST /api/rl/stand`, poll to done, then read `/api/status`: compare the new
  joint's `load_pct`/`current_a` with its five siblings (a trapped/wrong-zero
  leg was two hips at ~25 % vs ~12 %). Watch bus `volt`; under ~10.8 V lower
  and stop (the Sep 13/14 brownout band).
- hexapod1's MCU snapshot IMU age flaps to 240–320 ms under motion while
  positions stay fresh, so drives trip `feedback stale during stream` ~1 s in
  and refuse restarts for ~30 s. It is the IMU lead, not the gait; reseat it
  before trusting hexapod1 walk data. `gait_sweep.py` retries the stale start.
- End limp: `POST /api/rl/lower`, then `/cmd X`. Never leave a robot holding
  torque unattended; servo watch (65 °C cutoff) is the only guard.

## 5. Compare gaits

`linux_control/gait_sweep.py run|analyze|table` (README "Comparing gaits"):
floor-fit check, top-camera recording, alternating/`--keep-in`-bounded
exposures, stale-start retry, 10.8 V floor, lower+limp at the end, then
`gaits.json` in the Lab scorecard shape for `hexapod-lab2 import --gaits`.
