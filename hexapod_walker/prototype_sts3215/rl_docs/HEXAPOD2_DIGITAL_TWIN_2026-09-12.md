# Hexapod 2 digital twin — 2026-09-12

## Result

The trace-replay and validation-matrix capability now exists, but Hexapod 2
does **not** yet have a calibrated flexible digital twin. A true serial-joint
probe modestly improves the overall held-out matrix over the rigid-loaded
baseline (13/21 versus 11/21 attitude gates), but it makes PS200's already
underpredicted roll smaller. A uniform six-leg root-flex probe makes the
held-out result worse. Both remain off by default: the result supports dynamic
post-encoder compliance as a general twin feature, but shows that simple linear
flex is not the missing PS200 mechanism.

This note is based on the working-tree replay code and these generated reports:

- `/tmp/hexapod2-rigid-air-v2.json`
- `/tmp/hexapod2-rigid-loaded-v2.json`
- `/tmp/hexapod2-flex-loaded-v2.json`
- `/tmp/hexapod2-series-fit-v1.json`
- `/tmp/hexapod2-series-holdout-v1.json`

Those `/tmp` files are ephemeral. The durable inputs are
[`hexapod2_replay_matrix.json`](../rl_move/sim/hexapod2_replay_matrix.json),
which pins 25 unique Robot Lab CSV artifacts by SHA-256, and the commands below.

## Corrected replay clock and alignment

The previous replay could create divergence by construction. The corrected
path now:

1. Selects the contiguous first-to-last active `walk` or legacy `run` window,
   retaining brief interior `hold` rows rather than concatenating commands on
   either side of an interruption.
2. Uses strictly increasing `mono_s` when present and falls back to `t_s` only
   for legacy logs. Thus the recorded 25, 50, and 100 Hz controllers retain
   their real timing; 100 Hz rows are no longer stretched by a 20 ms minimum.
3. Treats row `k` as feedback at `t[k]`, holds `cmd[k]` over
   `[t[k], t[k+1]]`, and compares the resulting state with row `k+1`. It no
   longer advances a command before comparing with its own row or invents a
   final median-duration interval. Cumulative substep rounding avoids drift.
4. Converts robot-absolute joint angles to MuJoCo-relative joint coordinates
   during initial settling as well as during replay, and vertically places the
   mesh from its lowest collision geometry rather than giving it an artificial
   tick-zero fall.
5. Compares the hardware `ComplementaryAttitude` output with the same estimator
   driven by simulated gyro and specific force. Simulated rigid-chassis truth is
   retained as a separate `sim_true_*` metric.

For PS200, the Robot Lab run start precedes the first CSV `unix_s` by
`0.427584 s`. That gives a nominal `video time = trace time + 0.427584 s`, but
cam2 duplicated/froze its first approximately four encoded seconds. Therefore
the first roll peak cannot be validated at a precise video frame, and later
video is qualitative until camera capture timestamps are logged end to end.

## The 25-run protocol

The fit/holdout boundary was fixed before evaluating flex:

- **Fit, 4 traces:** PS200 forward `+0.10 m/s`; walkteach forward
  `+0.08 m/s` as a low-roll negative control; AMP forward `+0.06 m/s` as a
  cross-family anchor; allheading MLP forward `+0.08 m/s` as a second low-roll
  control.
- **Holdout, 21 traces:** every repeat; reverse, crab, and yaw commands; older
  sessions; the RL-only policy; and failure-mode traces. The seven represented
  families are PS200 (2 total), walkteach (6), allheading MLP (9), AMP (4),
  `dep_tip1` (1), `stotight45_seed13` (2), and
  `rl_only_widen8_crutchoff_s0` (1).

Tracker translation is not in these CSVs and is not silently used. Runs with an
invalid Robot Lab tracker result remain usable for joint/IMU replay and are
flagged accordingly. The matrix attitude gate requires both:

- peak-roll error `<= max(2 deg, 30% of hardware peak)`; and
- roll-waveform RMSE `<= 3 deg`.

Parameters may be selected using only the four fit traces. The 21 holdouts are
for rejection/generalization, not iterative tuning.

## Aggregate matrix result

All values below are split medians. `Peak error` is the absolute error between
hardware and simulated-estimator peak relative roll. `Wave RMSE` is the full
relative-roll waveform error. `q RMSE` covers moving encoder joints.

| Explicit replay configuration | Fit gate | Fit peak error | Fit wave RMSE | Fit q RMSE | Holdout gate | Holdout peak error | Holdout wave RMSE | Holdout q RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rigid + air servo fit | 1/4 | 2.84 deg | 3.62 deg | 3.06 deg | 7/21 | 2.21 deg | 2.45 deg | 2.68 deg |
| Rigid + loaded servo fit | **2/4** | **2.16 deg** | 3.41 deg | 3.57 deg | **11/21** | **1.73 deg** | **2.42 deg** | 3.43 deg |
| Uniform root flex + loaded fit | 1/4 | 4.81 deg | **3.27 deg** | 3.33 deg | 6/21 | 2.37 deg | 2.50 deg | **3.29 deg** |
| First-pass series hip/knee flex + loaded fit | **2/4** | **1.65 deg** | **3.12 deg** | 3.42 deg | **13/21** | **1.34 deg** | **2.25 deg** | **3.28 deg** |

The loaded servo file is an earlier loaded bench fit, not a Hexapod-2-specific
calibration. The air fit remains the legacy simulator default unless explicitly
selected. The matrix configurations are explicit and do not establish a new
training default.

### Per-family rigid-loaded result

For families with repeats, values are median `[range]`. `Sim peak` is the
simulated complementary-estimator peak, not chassis quaternion truth.

| Family | n | HW peak roll | Sim peak roll | Gate | Caveat |
|---|---:|---:|---:|---:|---|
| PS200 | 2 | 14.89 `[13.08, 16.69]` deg | 3.12 `[2.67, 3.57]` deg | 0/2 | Severe repeatable underprediction |
| walkteach | 6 | 3.07 `[2.78, 4.22]` deg | 2.34 `[2.10, 3.10]` deg | 6/6 | Useful low-roll negative control |
| allheading MLP | 9 | 3.58 `[1.53, 7.48]` deg | 3.61 `[2.80, 5.25]` deg | 5/9 | Direction/session dependent |
| AMP | 4 | 4.25 `[3.70, 7.97]` deg | 4.11 `[3.27, 4.68]` deg | 2/4 | Fit forward trace underpredicted; one yaw waveform misses |
| `dep_tip1` | 1 | 11.30 deg | 9.16 deg | 0/1 | Peak is close, but waveform RMSE is 10.68 deg |
| `stotight45_seed13` | 2 | 6.25 `[6.17, 6.33]` deg | 2.98 `[2.80, 3.16]` deg | 0/2 | Underpredicted; Robot Lab quality flags apply |
| RL-only widen8 | 1 | 3.66 deg | **17.90 deg** | 0/1 | Strong overprediction; sim true peak is 18.62 deg |

The RL-only counterexample is important: PS200 and stotight need more modeled
roll, while this policy already has about five times too much in the rigid sim.
No single global "more flex" setting can repair all families.

### True series-joint probe

The more physical implementation retains each named servo joint and encoder on
an upstream carrier, then inserts a coaxial passive output hinge before the
link and its descendants. This makes `output angle = encoder angle + flex`
without changing the 18-action/observation contract, and it is wired through
the CPU, shared MJX, replay, domain-randomization, and rise-bank paths.

Four bounded candidates were compared on the fit split only: the existing
first-pass `180/120 N m/rad` hip/knee estimates, softer `60/40`, very soft
`30/20`, and a soft L4/L5-only selection. Softer settings reached roughly
6–7 deg hidden deflection but still produced only 1.4–3.4 deg PS200 roll and
worsened other fit gaits. Only the first-pass candidate preserved 2/4 fit gates
and improved the aggregate fit errors, so it was frozen in
[`joint_series_flex_probe.json`](../rl_move/sim/joint_series_flex_probe.json)
before a single holdout evaluation.

That frozen candidate improves held-out gate count from 11/21 to 13/21, median
peak error from 1.73 to 1.34 deg, waveform RMSE from 2.42 to 2.25 deg, and
encoder RMSE from 3.43 to 3.28 deg. However, it moves PS200 in the wrong
direction: the fit trace falls from 3.57 deg rigid to 2.70 deg series-flex
against 16.69 deg hardware; the held-out repeat falls from 2.67 to 2.18 deg
against 13.08 deg hardware. Hidden deflection is only 1.23–2.67 deg across
holdouts. This is a promising general compliance representation, not a PS200
replication or a measured Hexapod-2 parameter set.

## What the servo telemetry settles

The CSVs contain the robot's own command, encoder, current, acquisition-age,
and loop-timing channels—not pose inferred from the camera. Across the matrix,
freshness is about 8 ms at 100 Hz, 13 ms on PS200's 50 Hz run, and 31 ms on
legacy 25 Hz runs. The observed encoder ceiling is approximately 34–36 deg/s,
consistent with the deployed 400-count/s write limit. Effective
command-to-encoder response delay, including profile travel, is typically
about 0.25–0.30 s. PS200 is therefore neither a stale-feedback artifact nor a
secret faster servo mode.

`fit_servo_residuals.py` fits latency, speed scale, zero offset, and reversal
play per physical servo using only the four fit traces. Its cross-family gate
retained five diagnostic parameter deviations, but the combined candidate did
not generalize: held-out median moving-joint RMSE worsened from 2.975 to
3.046 deg, 8/21 runs improved and 13/21 worsened. The PS200 holdout changed
only from 3.257 to 3.235 deg (0.7% better). The generated report therefore
marks the candidate unsafe to integrate and emits a neutral integration
payload. This says the remaining servo error is load/gait dependent; it does
not support a fixed per-servo correction as the cause of PS200's roll.

## Why the uniform leg-root flex probe is rejected

The probe added one passive local-Y hinge at every leg root with identical
`30 N m/rad` stiffness, `0.1 N m s/rad` damping, zero friction/preload, and a
`[-6, +6] deg` range. It was diagnostic only. Across the 25 runs its maximum
hinge motion was 3.31–4.90 deg (median 4.02 deg).

It fails causally and statistically:

- It reduces the held-out pass count from 11/21 to 6/21 and worsens held-out
  median peak error from 1.73 to 2.37 deg.
- On fit PS200, hardware peak roll is 16.69 deg; rigid-loaded produces
  3.57 deg, while root-flex produces only 3.35 deg despite 3.79 deg of hinge
  motion. The PS200 holdout is likewise 13.08 deg hardware versus 2.42 deg
  root-flex.
- It invents roll in a fit negative control: walkteach rises from a 2.78 deg
  hardware peak to a 7.81 deg simulated-estimator peak.
- Its uniform, reversible root spring cannot express per-leg spline/backlash,
  yoke or tibia bending, foot compression/slip, hysteresis, a support-foot loss,
  or the subsequent swing-foot catch indicated by PS200.

Do not enable this probe in training or call it calibrated. The implementation
remains useful as an opt-in topology experiment, with `leg_mount_flex.enabled`
still `0` in the normal configuration.

## PS200 causal evidence

Primary trace: Robot Lab run `cc274e771141`,
`rl_drive_20260911_233603.csv`, 14.976 s at median 49.97 Hz.

### IMU and gyro

The CSV has estimator roll/pitch and gyro but no raw accelerometer channels.
Gyro integration nevertheless shows the excursions are not mainly an
accelerometer-only estimator artifact:

| Trace interval | Measured roll change | Integrated `gyro_x` |
|---|---:|---:|
| 0.98–1.42 s | +17.06 deg | +16.06 deg |
| 2.36–2.88 s | +11.67 deg | +11.59 deg |
| 3.92–4.36 s | +14.50 deg | +14.40 deg |

Across nine positive peaks, integrated gyro and estimator roll change differ by
at most about 1.6 deg. This is a real rotation of the IMU, although a flexible
IMU mount is still distinguishable from chassis rotation only with an external
pose reference or a second rigidly mounted IMU.

### Encoder FK, support, and current

- At every positive peak, encoder FK identifies the nominal support tripod as
  L0/L2/L4. Its rigid support-plane roll over the trace is only about
  `-1.16 to +1.34 deg`. At 1.42 s it predicts approximately `-0.2 deg` roll
  and `+6.4 deg` pitch, while the IMU reports `+15.9 deg` roll and
  `-0.4 deg` pitch.
- At 1.42 s the nominal support polygon still contains the chassis origin with
  about 49 mm minimum margin. A small global CoM shift is therefore not enough
  to explain the event.
- L4 is the only negative-Y/right-side foot in that support tripod. During the
  first onset its hip (`j13`) reaches 0.396 A with +5.35 deg command error at
  0.98 s, then 0.468 A with +7.76 deg error at 1.16 s as roll begins.
- At the 1.42 s arrest, nominal swing-leg L5 knee (`j17`) reaches 0.273 A and
  lags its command by 7.60 deg. At the analogous 4.38 s event it reaches
  0.442 A and lags 7.92 deg. Applying the measured roll to encoder FK lowers
  L5 by roughly 46 mm relative to L2, more than its nominal roughly 31 mm
  clearance, so an unintended L5 floor catch is geometrically plausible.
- At 4.54 s the maximum encoder-command error has collapsed to 1.23 deg while
  body roll remains 10.14 deg. That is direct evidence for motion/contact after
  the encoder rather than command tracking alone.

The likely event class is therefore load-dependent post-encoder deformation or
backlash that unloads one support foot, followed by body pivot and swing-foot
contact. The load-bearing joint changes between cycles, so the evidence does
not justify declaring one permanently bad L4 joint.

### Video and tether

Once cam2 begins updating normally, it shows a large one-sided chassis lurch
that is absent from the MuJoCo video. Startup duplication prevents an exact
frame-to-first-peak measurement, and the overhead camera has too few frames for
structural metrology. Red/black leads lie near the right/near foot sweep and are
absent from sim, but no reviewed frame shows a taut pull, snag, or a foot
clearly pinning a lead. The tether is a plausible confound, not yet the primary
twin parameter.

## As-built geometry uncertainty

[`robots/hexapod-2.yaml`](../robots/hexapod-2.yaml) confirms only the owner's
robot-wide description: two lower yaw bearings and one upper bearing, with a
switch to spacer-equipped horn-joint parts in progress. It explicitly leaves
the following unrecorded:

- bearing model and dimensions;
- exact installed chassis, coxa, bearing-support, femur, and knee-yoke
  revisions;
- an exact CAD snapshot, branch, or revision for the assembled robot;
- which spacer-compatible parts are installed on each leg, the selected source
  revision, spacer dimensions, fasteners, and retrofit completion state; and
- whether every leg retains the two-lower/one-upper arrangement during retrofit.

The early rigid-yaw-support design is only an inferred reference. The current
rigid-hip design has one lower and one upper bearing and is not an exact match.
Consequently, mesh accuracy must not be confused with as-built accuracy.

## Capability versus calibration/default status

| Item | Implemented capability | Calibrated/default status |
|---|---|---|
| Corrected trace replay and SHA-pinned 25-run matrix | Present in the current working tree | Analysis tool only; no training-default change |
| Per-servo residual fitter using encoder telemetry | Present; fit-only identification plus untouched holdout report | Candidate rejected and neutral payload emitted; no servo-default change |
| Simulated complementary estimator and chassis-truth metric | Present in replay | IMU position remains `(0,0,0)` until measured |
| Raw acceleration logging | Logger source appends `ax_g`, `ay_g`, `az_g` from calibrated `state.imu_accel`, in g | Existing 25 CSVs lack these columns; no sealed post-change hardware run is evidence here |
| Uniform leg-root hinge | Implemented and opt-in | Probe rejected; default off |
| Per-joint post-encoder series hinge | Opt-in topology/plumbing exists for selected yaw/pitch/knee joints across CPU/MJX/replay | First-pass probe modestly improves holdouts but misses PS200; no measured Hexapod-2 table or default enablement |
| Legacy `struct_comp` | Existing gain-reduction/reported-angle approximation with first-pass estimates | Not a measured dynamic Hexapod 2 flex model; the explicit matrix baselines above do not fit it |
| Air/loaded servo profiles | Both selectable | Air is the legacy sim default; loaded is a prior bench candidate, not a Hexapod 2 calibration |

Raw accel is appended at the end of new CSV rows to preserve all historical
column positions. Before relying on it, deploy the logger and seal one short
stationary-plus-rock run demonstrating finite values, correct signs, gravity
magnitude, and synchronized timestamps.

## Reproduce the matrix

From `hexapod_walker/prototype_sts3215`:

```sh
# Authenticated fetch through the existing Robot Lab client, followed by
# manifest SHA-256 verification. Credentials are not command-line arguments.
uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split all --fetch-only

uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split all --model-source mesh --servo-params air --no-fetch \
  --out /tmp/hexapod2-rigid-air-v2.json

uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split all --model-source mesh --servo-params loaded --no-fetch \
  --out /tmp/hexapod2-rigid-loaded-v2.json

uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split all --model-source mesh --servo-params loaded --no-fetch \
  --leg-mount-flex-json rl_move/sim/leg_mount_flex_probe.json \
  --out /tmp/hexapod2-flex-loaded-v2.json

uv run python -m rl_move.sim.fit_servo_residuals \
  --data-dir /tmp/hexapod2-replay-matrix \
  --max-nfev 60 \
  --out /tmp/hexapod2-servo-residual-fit.json

uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split fit --model-source mesh --servo-params loaded --no-fetch \
  --joint-series-flex-json rl_move/sim/joint_series_flex_probe.json \
  --out /tmp/hexapod2-series-fit-v1.json

# Run once only after freezing the candidate above.
uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split holdout --model-source mesh --servo-params loaded --no-fetch \
  --joint-series-flex-json rl_move/sim/joint_series_flex_probe.json \
  --out /tmp/hexapod2-series-holdout-v1.json
```

For the next candidate, tune only on fit, freeze the complete JSON and its
hash, then run the holdout once:

```sh
uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split fit --model-source mesh --servo-params loaded --no-fetch \
  --joint-series-flex-json /absolute/path/to/candidate.json \
  --out /tmp/hexapod2-series-fit.json

uv run python -m rl_move.sim.replay_hexapod2_matrix \
  --split holdout --model-source mesh --servo-params loaded --no-fetch \
  --joint-series-flex-json /absolute/path/to/frozen-candidate.json \
  --out /tmp/hexapod2-series-holdout.json
```

## Next decisive measurements

1. **Separate chassis motion from IMU-mount motion.** Run the same bounded
   PS200 command with a second rigid chassis IMU and a synchronized chassis
   AprilTag. Log raw accel/gyro from both.
2. **Remove the tether confound.** Repeat with power/data leads supported from
   overhead and outside every foot sweep. A change in the periodic right-side
   collapse makes the tether a modeled external load; no change clears it.
3. **Measure post-encoder deflection directly.** At identical commanded and
   encoder angles, photograph/tag the servo output, horn/yoke, femur, tibia,
   and foot first unloaded, then under known three-leg and one-leg loads. Cycle
   load/unload to measure backlash and hysteresis per leg rather than assuming
   a common spring.
4. **Measure contact state.** Add temporary foot force/FSR sensing or a force
   plate and a high-frame-rate close view of L4/L5. Test whether L4 unloads
   before the roll and L5 contacts at arrest.
5. **Record the as-built robot.** Photograph bearing stacks and part markings,
   measure the bearings/spacers, and update the per-leg retrofit map before
   treating any CAD mesh as ground truth.
6. **Calibrate, then generalize.** Fit a minimal selected-joint series model
   and contact parameters to the four fit runs, require that low-roll controls
   remain low, then evaluate all 21 holdouts. Do not expose the candidate to RL
   training until it improves the held-out matrix without creating the RL-only
   overprediction failure.
