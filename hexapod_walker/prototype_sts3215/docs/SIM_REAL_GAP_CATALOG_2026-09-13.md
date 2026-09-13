# Sim-to-real gap catalog: hexapod2 RL gaits vs the MuJoCo twin (2026-09-13)

Question from Lukas: the real robot walks differently from MuJoCo under the RL
gaits. It does not put its feet down consistently, it rocks far more, and it
falls on some gaits and turns. Which physical effects are missing or wrong in
the sim, how big are they, and does fixing them make the sim behave like the
robot?

This note catalogs every difference I could measure from the recorded hexapod2
runs (Robot Lab v2, 25 pinned traces, 2026-09-10/11), the side-camera clips on
the vision PVC, and the sim, then reports the physics variants I tried, open
loop (replaying the robot's own commands) and closed loop (the frozen deployed
actors in the training env). It builds on
`GAIT_SIM_VS_HARDWARE_2026-09-11.md`, `rl_docs/HEXAPOD2_DIGITAL_TWIN_2026-09-12.md`,
`PS200_TRANSFER_PROBE_2026-09-12.md` and the lab's 2026-09-13 note that the
twin's roll is uncorrelated with the robot's. Nothing here was run on the robot
(it was off the network during this session). Tools and raw outputs are listed
at the end; every number can be regenerated.

## Summary

1. **The policies themselves stand and walk on three feet.** At 18 of the 21
   recorded hold poses the rigid sim rests on one tripod with the other three
   feet in the air (about 11 N per loaded foot, 0 N on the others), and closed
   loop the three deployable 50 Hz actors keep three or fewer feet down 77 to
   91 percent of the time, with swing feet clearing the floor by only 15 to
   29 mm (95th percentile). In sim that is fine because legs are stiff and
   exact. On the robot, 5 to 10 mm of load-dependent sag plus zero errors plus
   the tether decides whether the hovering tripod touches. That is the "feet not
   systematically on the ground" observation, and it is a policy habit the sim
   never charges for.
2. **The sim's servo is 4 to 60 times stiffer under load than the real one.**
   Loaded hips on the robot sag a median 0.8 deg and up to 3 to 5 deg under about
   1 N m; that is 22 to 79 N m/rad (median 35) at the hip and 10 to 24 (median
   14) at the knee. The fitted sim gains are 575 (hip) and 916 (knee) N m/rad;
   the training env's structural-compliance approximation brings that to
   137/106. The fit is profile-dominated (the 35 deg/s write profile hides the
   gain), so kp was never identified. A Feetech P gain of 32 gives full PWM at
   about 2.7 deg of error, i.e. roughly 47 N m/rad, which matches the sag data.
3. **The sim replays every run with its actuators pinned at the 2.2 N m clamp**
   (95th percentile of |tau| is 2.2 N m in all 25 replays), while the robot's
   per-joint current never exceeds 0.78 A and sits below 0.2 to 0.4 A at the
   99th percentile. The sim's joints are a bang-bang torque source; the real
   ones are a soft proportional band with gear friction holding static load.
4. **No single physics change reproduces the robot's roll.** Across 18 open-loop
   variants (friction 0.5 to 1.2, torque clamp 0.66 to 1.0 N m, gain 0.03 to
   0.1 times, soft or asymmetric series compliance, 0.5 to 2 deg backlash on
   different axes, air fit) the rank correlation between hardware and sim peak
   roll never exceeds 0.47, and closed loop every variant leaves the three actors
   at 1 to 2 deg peak roll with zero falls, against 2.5 to 16.7 deg on the robot.
   The only thing that made sim roll hardware-sized was the DR's bad-start
   axis (two joints 32 to 34 deg off at reset), which is a start-pose effect,
   not walking physics.
5. **Two things do move sim toward hardware and are cheap to adopt as
   domain-randomization ranges:** a position gain of 30 to 90 N m/rad (the
   measured value; closed loop kp x0.1 drops PS200 from 49 to 25 mm/s,
   walkteach from 32 to 11, allheading from 33 to 12, against 1.5 / 15 to 38 /
   6.5 to 11 on the robot, and it gives the best open-loop rank correlation of
   any actuator change), and a torque clamp of 0.4 to 0.7 N m (closed loop
   x0.2 alone gives 18 / 13 / 15 mm/s and 4.3 to 4.5 feet on the floor, the
   hardware "shuffle"; combined with kp x0.1 walkteach and allheading land at
   6 to 8 mm/s with 4.2 to 4.5 feet down). Neither changes roll, so the roll
   mechanism is still not in the model; see the theories section for what to
   measure next.

## What was compared

| source | content | where |
|---|---|---|
| Robot Lab v2 hexapod2 traces | 25 per-tick CSVs (18 encoder + 18 command + 18 current channels, estimator roll/pitch, gyro, loop timing), 2026-09-10/11, seven policy families, forward/reverse/crab/yaw | `rl_move/sim/hexapod2_replay_matrix.json`, fetched to `/tmp/hexapod2-replay-matrix/csv` by `replay_hexapod2_matrix --fetch-only` |
| side camera cam2 clips | 30 fps 1280x720 of the same runs (PS200 x2, walkteach x2, allheading, stotight45) | vision pod `hexapod-vision-lab:/data/clips/<run>/` |
| sim, open loop | `rl_move.sim.replay_trace._ReplaySim` (full mesh model, loaded servo fit, complementary-filter IMU) driven by the recorded commands | `sysid/simgap/replay_variants.py` |
| sim, closed loop | frozen deployed actors PS200, walkteach, allheading in `SimHexapodJointWalkEnv`, pinned 0.10/0.08 m/s, 10 s, 4 seeds | `sysid/simgap/closed_loop_variants.py` |
| vision foot timelines | red-boot-tip tracker at 30 fps, stance < 0.7 px/frame, swing > 1.8 px/frame | pod `/data/jobs/simgap/s1_foot_timeline.py`, outputs `/data/results/simgap/*.json` |

Hardware-only metrics per trace (hold droop, roll spectrum, timing, current) are
in `/tmp/simgap/hw_metrics.json` from `sysid/simgap/hw_metrics.py`.

## The catalog

Sizes are hexapod2 unless stated. "DR" says whether the training domain
randomization (`rl_move/sim/domain_rand.py`) spans the measured value.

| # | what differs | hardware evidence | sim today | covered by DR | size of gap | matters for |
|---|---|---|---|---|---|---|
| 1 | **Support set: three feet, other tripod hovering** | hold poses have one tripod's hips 8 to 23 deg higher than the other (e.g. PS200 hips 19.5/11.7/20.2/11.5/20.8/13.4 deg); rigid sim at those poses stands on 3 feet in 18/21 cases, 11 N per loaded foot | closed loop mean feet in contact 3.2 to 3.4; <= 3 feet 77 to 91 % of ticks; swing lift p95 15 to 29 mm | no term prices a hovering tripod; `reward.k_support_margin` exists (default 0) | structural | foot-placement consistency, rocking on a 3-point support |
| 2 | **Loaded joint stiffness** | hold-phase sag on the loaded tripod: hip median 0.8 deg, p10 3.3 deg, up to 4.9 deg, under 1.0 to 1.2 N m; knee 0 to 1.3 deg under 0.23 N m. k_hip 22 to 79 N m/rad (median 35), k_knee 10 to 24 (median 14). hexapod1 knees sag 2 to 6 deg on 120 s holds (`STATE_OF_THE_ROBOT_2026-09-11.md`) | kp 575 hip / 916 knee (loaded fit); sim hold sag 0.2 deg. Training env: struct_comp k=180/120 in series gives kp_eff 137/106 | kp +-20 %, struct_comp x0.5..2.0: lowest reachable kp_eff about 55 | 4 to 60x too stiff | body drop of 5 to 10 mm on every load transfer, foot touch-down timing, marginal-foot contact |
| 3 | **Torque delivered while walking** | per-joint current p99 0.1 to 0.4 A, max 0.78 A over 25 runs; median 0.006 to 0.013 A. Overload trips at "98 % load" stop runs | replay: |tau| p95 = 2.2 N m clamp in every run; closed loop the clamp is available at all times | torque_scale 0.80 to 1.05 (1.76 to 2.3 N m) | 3 to 10x more torque available in sim, if 1.2 A/N m; the mapping is uncalibrated | speed (sim 3 to 30x faster), shuffle, what happens when a foot catches |
| 4 | **Body roll amplitude and rank order** | peak relative roll 2.5 to 16.7 deg; rms 0.6 to 3.9 deg | replay 2 to 4 deg regardless of policy (rho 0.12, n=25); closed loop 1 to 2 deg, 0 falls | tipped_start, walk_push cover transients, not sustained rocking | 2 to 5x, uncorrelated | falls on PS200, stotight45, turns |
| 5 | **Roll spectrum** | 40 to 75 % of roll power at the stride frequency (0.7 to 1.4 Hz), 5 to 45 % at 2x stride; three runs dominated by sub-stride drift (allheading reverse 945e97: 91 % sub-stride, hold tilt -11.7 deg) | replay puts roll power at the stride line too but at half the amplitude; no slow drift | none | slow lean drift missing | heading drift, "leaning" starts |
| 6 | **Initial lean** | estimator roll/pitch at the hold before each walk: 0.4 to 6.8 deg roll, up to -11.7 deg; PS200 4.3 deg roll, -2.0 pitch | replay and env start level | tipped_start 6 to 18 deg in 30 % of plant episodes (reference stays level) | 2 to 12 deg | obs bias at walk start, which side the first collapse goes |
| 7 | **Control rate and feedback age** | the "100 Hz" policies ran at 71 to 86 Hz effective (period p95 15 to 17 ms, max 20 to 40 ms), PS200 50 Hz at 40 to 43 Hz; position age 7.7 ms p50 / 13 ms p95; 25 Hz policies exact | exact tick, fresh state | cmd_drop_prob <= 5 % only | 15 to 30 % slower loop | velocity observations, phase clock. Closed loop at 40 Hz: no roll change |
| 8 | **Foot motion statistics** (vision, near-side feet) | visible feet stationary 60 to 78 % of foot-frames, swinging 14 to 32 %; 56 to 75 % of frames show no swinging foot; stance bouts median 0.3 to 0.7 s, p90 3.3 to 3.9 s; swing bouts 0.1 to 0.4 s | replay: stationary 23 to 40 %, swinging 38 to 44 %, no-swing ticks 6 to 14 %; 4 to 9 % of ticks a foot is in contact and sliding > 77 mm/s | none | feet parked 2x longer on hardware; some feet stay put for seconds | the shuffle, travel ratio 10 to 45 %. Caveat: the tracker under-counts blurred swing feet |
| 9 | **Floor and foot friction** | hard speckled epoxy floor (cam2 frame); real mu never measured (`HARDWARE.md` drag test still open); turning under-predicted 10x, travel 10 to 45 % of command | foot mu 2.0 / floor 1.5, pair takes the max = 2.0; condim 6 | friction_scale 0.6 to 1.4, so pair mu 1.2 to 2.8 | unknown, likely 0.5 to 1.0 vs 2.0 | slip in turns and crab; mu 0.5 to 0.8 raises low-roll gaits' replay roll to hardware level but leaves PS200 |
| 10 | **Tether** | red and black power leads lie through the right/near foot sweep in every clip | absent | none | unknown | one-sided drag, foot snag; the PS200 collapse is always to one side |
| 11 | **Mass, CoM, inertia of hexapod2** | robot never weighed; hexapod2 has a different top plate and electronics stack from hexapod1 | mesh model = hexapod1 as built, 3.49 kg (pods used 4.81 kg from 09-03 to 09-11 by mistake) | mass 0.85 to 1.20, CoM +-12 mm | unknown | everything above |
| 12 | **Per-leg asymmetry** | AMP knee swing per leg 31/18/22/9/27/20 deg; hexapod2 hold sag differs 0 to 4.9 deg between legs of the same tripod; hexapod1 L2/L4 knees and L0 hip are the weak joints | identical legs | link length +-1.2 %/leg (about 2 mm), zero bias 1 deg (about 2.6 mm at the foot) | real per-leg foot-height scatter 5 to 10 mm vs 3 mm | which foot touches first |
| 13 | **Post-encoder play** | bench hysteresis 0.7 to 1.0 deg per joint (Aug); hexapod2 yaw bearing stacks non-standard | rigid; opt-in series hinge (linear spring) | none | unknown per axis | see variants: play on hip/knee damps sim roll and fills the hovering gap (feet 4.3 to 5.0); +-1 deg play on yaw only was the best single replay variant |
| 14 | **Servo velocity cap** | encoder ceiling 34 to 36 deg/s = 400 counts/s write profile | modeled (trapezoid profile) | vel_scale 0.85 to 1.10 | matches | none; stride clock transfers exactly |
| 15 | **IMU placement and estimator** | MPU-6050 at (2, -43, 25) mm on the chassis deck; complementary filter alpha 0.98 | replay IMU at (0, 0, 0); same filter | imu_pos +-70 mm, z -20 to 100 mm | small | lever-arm acceleration in roll estimate |
| 16 | **Start and stop procedures** | stops leave one hip 20 to 70 deg from walk-ready; stand routes through 10x step keyframes and safe_zero drops (`RISE_FALL_HEXAPOD2_2026-09-11.md`) | episode begins at a settled plant | bad_start (2 to 3 joints 8 to 35 deg off) covers the pose, not the procedure | procedural | several of the "falls" were transitions, not gait |
| 17 | **Battery** | 11.0 to 11.3 V at rest on hexapod2; hexapod1 dipped to 7.2 V under load | no voltage model; torque_scale 0.80 to 1.05 | partly | unknown under load on hexapod2 | torque and speed sag under load |

Trace `36141febdc20` (rl_only widen8) replays at 17.9 deg against 3.7 deg on
the robot in every variant; its hold rows show 10 to 21 deg command errors, so
the robot was not at the logged pose when the walk began. Treat it as a suspect
trace, not as evidence about compliance.

## Experiments

### Open loop: 25-trace replay matrix under physics variants

Each variant replays the robot's own command stream. Gate = the twin doc's
attitude gate (peak within max(2 deg, 30 %) and waveform rmse <= 3 deg) on the
4 fit / 21 holdout traces. rho = Spearman rank correlation of hardware vs sim
peak roll over all 25 (the lab's suggested metric). Ratio = median sim/hardware
peak. Feet = mean simulated feet in contact. Family columns are sim/hardware
median peak roll in degrees.

| variant | gate fit/hold | rho peak | ratio peak | median peak err | feet | PS200 | walkteach | allheading | stotight45 |
|---|---|---|---|---|---|---|---|---|---|
| baseline (rigid, loaded fit) | 2 / 11 | 0.12 | 0.81 | 1.73 | 2.9 | 3.1/14.9 | 2.3/3.1 | 3.6/3.6 | 3.0/6.3 |
| air fit | 1 / 7 | 0.44 | 0.34 | 2.23 | 3.2 | 1.6/14.9 | 1.1/3.1 | 1.1/3.6 | 2.0/6.3 |
| kp x0.1 (57/92 N m/rad) | 1 / 8 | 0.42 | 0.44 | 2.14 | 3.4 | 2.1/14.9 | 1.5/3.1 | 1.4/3.6 | 2.7/6.3 |
| kp x0.1 + joint friction 0.3 N m | 1 / 9 | 0.43 | 0.44 | 2.07 | 3.4 | 2.1/14.9 | 1.3/3.1 | 1.4/3.6 | 2.7/6.3 |
| kp x0.03 (17/27 N m/rad) | 1 / 8 | 0.47 | 0.38 | 2.37 | 3.8 | 2.1/14.9 | 1.1/3.1 | 1.3/3.6 | 2.4/6.3 |
| torque clamp x0.45 (1.0 N m) | 1 / 10 | 0.18 | 0.54 | 1.81 | 3.4 | 1.6/14.9 | 1.4/3.1 | 1.9/3.6 | 2.9/6.3 |
| torque clamp x0.3 (0.66 N m) | 1 / 10 | 0.34 | 0.43 | 2.04 | 3.8 | 2.4/14.9 | 1.2/3.1 | 1.5/3.6 | 2.9/6.3 |
| foot-floor mu 0.5 | 1 / 11 | -0.09 | 0.78 | 1.88 | 2.5 | 2.2/14.9 | 3.3/3.1 | 2.4/3.6 | 3.2/6.3 |
| mu 0.8 | 1 / 6 | -0.38 | 0.97 | 2.57 | 2.4 | 2.6/14.9 | 4.7/3.1 | 6.1/3.6 | 3.3/6.3 |
| mu 1.2 | 2 / 8 | -0.28 | 1.00 | 2.54 | 2.6 | 1.9/14.9 | 4.0/3.1 | 4.8/3.6 | 2.9/6.3 |
| soft series hip/knee 40/30 N m/rad, friction 0.05 | 1 / 11 | 0.39 | 0.48 | 1.87 | 3.7 | 2.4/14.9 | 1.7/3.1 | 1.6/3.6 | 3.0/6.3 |
| soft hips on legs 0/2/4 only (12 N m/rad) | 2 / 6 | -0.40 | 1.24 | 2.17 | 2.8 | 2.4/14.9 | 5.5/3.1 | 5.6/3.6 | 3.4/6.3 |
| soft hips on legs 1/3/5 only | 1 / 7 | -0.47 | 1.15 | 2.54 | 2.8 | 2.7/14.9 | 5.9/3.1 | 6.3/3.6 | 3.7/6.3 |
| backlash +-0.5 deg all joints | 1 / 11 | 0.11 | 0.46 | 1.87 | 4.3 | 1.8/14.9 | 1.4/3.1 | 1.5/3.6 | 2.2/6.3 |
| backlash +-1 deg all joints | 1 / 11 | 0.20 | 0.45 | 1.89 | 4.6 | 2.1/14.9 | 1.3/3.1 | 1.5/3.6 | 2.4/6.3 |
| backlash +-2 deg all joints | 1 / 10 | 0.11 | 0.47 | 2.10 | 5.1 | 1.8/14.9 | 1.5/3.1 | 1.5/3.6 | 2.3/6.3 |
| backlash +-1 deg hip and knee only | 1 / 10 | 0.17 | 0.48 | 2.11 | 4.5 | 2.4/14.9 | 1.7/3.1 | 1.6/3.6 | 2.2/6.3 |
| backlash +-1 deg yaw only | 2 / 12 | 0.37 | 0.81 | 0.85 | 3.0 | 3.5/14.9 | 2.5/3.1 | 2.9/3.6 | 3.4/6.3 |

Reading: nothing lifts PS200 or stotight45 toward their hardware roll while
keeping walkteach low. Lower friction and asymmetric hip softness raise roll
everywhere, which inverts the rank order (negative rho). Any compliance in
series with the encoder (soft spring, play) *reduces* replayed roll and puts
more feet on the floor, because the recorded commands already contain the
policy's reaction to the real roll; open-loop replay can only test physics that
amplifies asymmetry, not physics that absorbs it. Lower gain, lower torque and
the air fit all improve rank correlation to 0.34 to 0.47 while shrinking
amplitude: the ordering information the robot shows is in "how hard the servo
fights", not in a spring constant.

### Closed loop: frozen actors under the same variants

Median over 4 seeds, 10 s episodes, pinned forward command (PS200 0.10 m/s,
others 0.08). Hardware reference in the last block.

| variant | PS200 peak / rms roll, speed, feet | walkteach peak / rms, speed, feet | allheading peak / rms, speed, feet | falls |
|---|---|---|---|---|
| baseline (air fit, struct_comp on) | 1.3 / 0.57 deg, 49 mm/s, 3.2 | 1.5 / 0.54, 32, 3.4 | 1.6 / 0.43, 33, 3.3 | 0 |
| loaded servo fit | 1.6 / 0.66, 53, 3.1 | 2.0 / 0.98, 20, 3.4 | 1.7 / 0.53, 21, 3.4 | 0 |
| full training DR (dr_scale 1, 12 seeds) | 2.2 median, 9.7 max / 1.3, 42 | 2.2 / 1.4, 25 | 2.1 / 0.8, 27 | 0 |
| mu 0.6 | 1.4 / 0.58, 43, 3.2 | 1.7 / 0.55, 26, 3.4 | 1.6 / 0.45, 26, 3.3 | 0 |
| mu 0.9 | 1.5 / 0.57, 46, 3.2 | 1.8 / 0.64, 28, 3.4 | 1.4 / 0.49, 29, 3.3 | 0 |
| control 40 Hz instead of 50 | 1.0 / 0.55, 49, 3.2 | 1.4 / 0.62, 30, 3.4 | 1.4 / 0.44, 30, 3.4 | 0 |
| soft series hip/knee 40/30 | 1.6 / 0.61, 46, 3.4 | 1.4 / 0.53, 31, 3.7 | 1.7 / 0.46, 29, 3.7 | 0 |
| soft hips legs 0/2/4 | 1.4 / 0.78, 48, 3.2 | 1.7 / 0.61, 31, 3.5 | 1.6 / 0.48, 31, 3.5 | 0 |
| torque clamp x0.6 (1.3 N m) | 1.5 / 0.66, 48, 3.2 | 1.4 / 0.58, 32, 3.4 | 1.5 / 0.50, 32, 3.4 | 0 |
| torque clamp x0.45 (1.0 N m) | 1.7 / 0.61, 46, 3.2 | 1.6 / 0.54, 31, 3.4 | 1.5 / 0.52, 31, 3.4 | 0 |
| torque clamp x0.3 (0.66 N m) | 2.1 / 0.89, 35, 3.3 | 1.6 / 0.63, 27, 3.6 | 1.5 / 0.59, 26, 3.6 | 0 |
| torque clamp x0.2 (0.44 N m) | 1.9 / 1.02, **18**, **3.7** | 1.2 / 0.43, **13**, **4.5** | 1.1 / 0.39, **15**, **4.3** | 0 |
| kp x0.1 (57/92 N m/rad, struct_comp on) | 1.4 / 0.53, **25**, 3.2 | 1.3 / 0.56, **11**, 3.7 | 1.7 / 0.45, **12**, 3.6 | 0 |
| kp x0.1, struct_comp off | 1.7 / 0.58, 26, 3.2 | 1.3 / 0.60, 12, 3.6 | 1.3 / 0.39, 11, 3.5 | 0 |
| kp x0.1 + torque clamp x0.3 | 1.5 / 0.65, 23, 3.3 | 1.3 / 0.61, **6.3**, **4.5** | 1.1 / 0.39, **8.2**, **4.2** | 0 |
| kp x0.05 (29/46 N m/rad) | 1.0 / 0.47, 14, 3.3 | 1.2 / 0.52, 4.8, 4.2 | 1.5 / 0.46, 4.4, 3.9 | 0 |
| **hardware** | **13 to 17 / 3.5 to 3.9, 1.5 mm/s** | **2.8 to 4.2 / 0.8 to 1.5, 15 to 38** | **4.4 to 7.5 / 1.0 to 2.1, 6.5 to 11** | PS200 and stotight45 tip; turns fall |

The full-DR sweep is instructive: the two seeds that reached 6 to 10 deg roll
(for all three actors at once) were the ones whose reset drew the bad-start
axis (two joints 32 to 34 deg off). Nothing in the DR produces sustained
rocking during steady walking.

### Foot motion: side camera vs replay

Fraction of visible foot-frames that are stationary (hardware) vs fraction of
foot-ticks stationary in the replay of the same run, same speed thresholds:

| run | policy | hardware stationary / swinging | sim stationary / swinging | hardware stance bout median / p90 | hardware swing bout median / p90 |
|---|---|---|---|---|---|
| cc274e771141 | PS200 0.10 | 0.65 / 0.25 | 0.33 / 0.40 | 0.52 s / 3.9 s (sim 0.39 / 1.0) | 0.27 s / 0.60 s (sim 0.52 / 0.73) |
| 8263389349f6 | PS200 0.08 | 0.60 / 0.32 | 0.37 / 0.37 | 0.33 s / 3.8 s (sim 0.45 / 1.2) | 0.37 s / 1.1 s (sim 0.40 / 1.1) |
| 10f90c2597f3 | walkteach fwd | 0.78 / 0.14 | 0.12 / 0.42 | 0.67 s / 3.3 s (sim 0.17 / 0.35) | 0.15 s / 0.50 s (sim 0.33 / 0.48) |
| e6e216c01d62 | walkteach rev | 0.66 / 0.17 | 0.15 / 0.38 | 0.23 s / 1.5 s (sim 0.21 / 0.35) | 0.10 s / 0.30 s (sim 0.27 / 0.49) |
| ca3e7039d1d6 | allheading fwd | 0.77 / 0.11 | 0.14 / 0.40 | 1.05 s / 3.0 s (sim 0.18 / 0.32) | 0.10 s / 0.48 s (sim 0.29 / 0.47) |
| 867eb750b497 | stotight45 fwd | 0.65 / 0.21 | 0.22 / 0.28 | 0.37 s / 1.2 s (sim 0.28 / 0.54) | 0.17 s / 0.43 s (sim 0.32 / 0.72) |

The camera sees about two boots per frame (mean visible feet 1.5 to 2.2) and
under-counts blurred swing feet, so the swinging fractions are lower bounds.
The stationary fractions and the multi-second stance bouts are robust: on the
robot some feet do not move for 3 to 4 s while the gait clock runs at 0.7 to
1.3 Hz, and the swings that do happen are half as long as the sim's (0.10 to
0.37 s vs 0.27 to 0.52 s median). In the sim every foot cycles every stride
(contact duty 0.3 to 0.9 per foot) with stance bouts under 0.5 s. Sim speeds
were median-filtered over the same window as the tracker before thresholding.

## Theories, ranked by what the evidence supports

1. **Three-foot stance plus real compliance is the rocking mechanism, and it
   is a policy property before it is a physics property.** Every actor learned
   to carry the body on one tripod with the other three feet 5 to 20 mm up.
   With stiff sim legs that is a stable stool. With 20 to 40 N m/rad hips, the
   loaded tripod compresses 5 to 10 mm at the foot, the body leans 2 to 5 deg
   toward whichever leg sags most (the hold-phase tilt of 2 to 12 deg is exactly
   that), and each tripod exchange is a drop-and-catch. What kills it: a foot
   force or clearance measurement showing the hovering tripod actually shares
   load on the robot. What supports it: hold-probe (18/21 poses on three
   feet), hold tilt, hip sag confined to the loaded tripod.
2. **The servo model is qualitatively wrong under load: too stiff, too much
   torque, no stiction.** Measured gain 35/14 N m/rad vs 575/916; currents
   <= 0.78 A vs a 2.2 N m clamp used at the 95th percentile. Replay with
   kp x0.1 or torque x0.3 gives the best rank correlations (0.34 to 0.47) of
   any variant, and closed loop a 0.44 N m clamp reproduces the hardware speed
   collapse and the extra feet on the floor. It does not reproduce roll, so it
   is a necessary correction, not the whole answer. What kills it: the
   torque-limit and overload-protection registers on the servos (if they are at
   1000/80 %/20 % defaults the 0.78 A ceiling is a P-band effect; if lower, a
   configuration effect). Nobody has read them back on hexapod2.
3. **Something one-sided and load-triggered is still missing.** PS200 collapses
   the same way every cycle (five separated positive peaks per 10 s), rl_only
   collapses the other way; open-loop replay is blind to whatever it is
   (rho 0.12) and so is every smooth physics variant tried here and in the twin
   note. The candidates left are discrete: a foot catching the floor or the
   tether, a horn slipping under load on one leg, or a servo entering overload
   protection (torque cut to 20 % for a protection period). Each leaves a
   signature the CSVs can show: a joint whose current drops to zero while its
   error grows (protection), or a joint whose encoder tracks while the IMU
   rotates (post-encoder slip). The twin note already found the second pattern
   at the 4.54 s PS200 event (error 1.2 deg, roll 10 deg).
4. **Floor friction is lower than 2.0 and un-randomized below 1.2.** It does
   not explain roll, but it is the simplest explanation for turning at a tenth
   of the sim rate and for crab and reverse travel ratios. A 10-minute drag
   test (`HARDWARE.md`, wishlist item) settles it.

## What I would change in MuJoCo and training

Ordered by confidence that it closes a measured gap without a new measurement:

1. **Re-identify the position gain from load, not from steps.** Use the hold
   sag data (`sysid/simgap/replay_variants.py --hold-probe`, table in
   `/tmp/simgap/variants/hold_probe_baseline.json`) as the fit target: kp such
   that a 1.07 N m hip load sags 0.8 to 3 deg, i.e. kp 20 to 80 N m/rad with a
   Coulomb term of 0.1 to 0.3 N m. Then widen `dr.kp_scale_pct` around it. The
   current x0.8..1.2 around 575/916 never visits the real robot.
2. **Randomize the torque clamp down to 0.4 N m** (`dr.torque_scale` 0.2 to
   1.0 instead of 0.80 to 1.05). Closed loop this alone moves speed and feet
   in contact to hardware values for all three actors, with no falls, so it is
   safe to train against and it removes the sim's 3 to 30x speed optimism.
3. **Charge for the hovering tripod.** Either `reward.k_support_margin` > 0,
   or a per-leg foot-height offset randomization of +-8 mm (the measured
   per-leg sag scatter) so that a foot commanded 5 mm above the floor lands
   half the time. That is the observation Lukas made, stated as a DR axis.
4. **Recenter foot friction to 0.8 and randomize 0.5 to 1.5** once the drag
   test gives a number; the hook exists (`env.foot_friction_slide`).
5. **Log and randomize the control period.** A tick-jitter axis (period p95 =
   1.5x nominal, occasional 4x) is missing; the closed-loop 40 Hz test says it
   is not the roll mechanism, so this is hygiene, not the fix.
6. Do not adopt series play or soft series springs as a roll fix; both damp
   replayed roll. Yaw-only play (+-1 deg) is the one topology change that
   improved every open-loop metric at once (gate 12/21, median peak error
   0.85 deg); it is worth a bench measurement of yaw play on hexapod2's bearing
   stacks before a training arm.

## Measurements that would settle the open theories

- Weigh hexapod2 and photograph its as-built stack (catalog #11).
- Read back the servo EPROM: max torque (16), P gain (20), protection current
  (28), protection torque (34), protection time (35), overload torque (36) on
  all 18 (catalog #3, theory 2).
- Floor drag test with a boot on the epoxy floor (theory 4).
- One PS200 run with the tether suspended from above (theory 3).
- Hold the six-foot plant with a sheet of paper under each foot and pull:
  which tripod is loaded, and by how much (theory 1).
- A foot tracker that keeps identity through swing (the DINOv2 probe in
  `/data/results/contact` or AprilTags on the boots), so catalog #8 becomes a
  per-foot duty comparison instead of an identity-free one.

## Files and reproduction

All in `hexapod_walker/prototype_sts3215` unless noted.

- `sysid/simgap/hw_metrics.py`: hardware-only metrics per trace (hold droop per
  joint, roll spectrum bands, timing, current). Output
  `/tmp/simgap/hw_metrics.json`.
- `sysid/simgap/replay_variants.py`: open-loop matrix under variants
  (`--variant baseline|air|mu<f>|torque<f>|kp<f>|friction<f>|series:<json>`),
  per-run npz time series and `result.json` under `/tmp/simgap/variants/`;
  `--hold-probe` for static torques at the recorded hold poses.
- `sysid/simgap/summarize_variants.py`: the variant table above.
- `sysid/simgap/closed_loop_variants.py`: frozen actors under variants
  (`mu`, `torque`, `kp`, `dr`, `hz`, `series:`); rows and summary under
  `logs/ckpt_eval/simgap_closed_loop_<UTC>/` (this session wrote to
  `/tmp/simgap/cl/g1..g6`).
- `sysid/simgap/contact_compare.py`: vision timelines vs replay foot motion.
- `sysid/simgap/variants/*.json`: the series-flex tables (backlash, soft,
  asymmetric).
- Vision pod: `/data/jobs/simgap/s1_foot_timeline.py`, results
  `/data/results/simgap/*.json`, log `s1.log`.

Regenerate everything:

```sh
uv run python -m rl_move.sim.replay_hexapod2_matrix --split all --fetch-only
uv run python sysid/simgap/hw_metrics.py
uv run python -m sysid.simgap.replay_variants --variant baseline --variant kp0.1 --variant torque0.3
uv run python -m sysid.simgap.replay_variants --hold-probe
uv run python -m sysid.simgap.summarize_variants --md
uv run python -m sysid.simgap.closed_loop_variants --variant baseline --variant torque0.2 --variant kp0.1
uv run python -m sysid.simgap.contact_compare --variant baseline   # after copying /data/results/simgap/*.json to /tmp/simgap/vision/
```
