# Walking review — September 5, 2026

The shortest evidence-supported route to smooth walking is to finish the real controller integration, measure and reproduce this robot's dynamics, and improve one repeatable gait. Another broad reward, architecture, or training-budget sweep is a lower priority. This is an engineering recommendation, not a demonstrated fix.

Scope: current STS3215 project, physical assembly record, control/simulation code, local hardware traces, published Robot Lab results, and August 5–September 5 RL campaign records. The live cloud status was newer than the checkout and was consulted directly. Cloud/run timestamps sometimes use UTC; September 5 UTC includes September 4 evening in California. The live Robot Lab index contained three physical-result records and one framework dry run; additional, newer hardware traces were available locally. Review was read-only apart from this report: no robot motion, deployment, training launch, or control-code edits.

| Finding | Evidence | Consequence |
|---|---|---|
| Actual walking exists, but sustained smooth walking is not demonstrated | September 3 RL forward pilot: 45.9 mm forward, 20.1 mm lateral in about 2.35 s; 19.5 mm/s. Other cardinal directions and a short direction-changing course completed. September 4's newer forward trial lasted 1.9 s. | Treat these as canaries, not cruising acceptance. |
| Speed is lost both before and during transfer | At 80 mm/s requested, the hardware-tested policy achieved about 34.6–43.9 mm/s in simulation and 19.5 mm/s on the measured hardware forward pilot. | Better simulation transfer alone does not deliver the requested speed. |
| The deployed observation/action timing differs from simulation | Latest trace: 100 Hz decisions, 50 Hz writes, 10 Hz snapshots, 97 overruns/192 ticks. Hardware joint-velocity and attitude filters run at the snapshot cadence. | Reproduce this exact transport and filtering before judging or retraining the policy. |
| The physical body/contact response differs substantially from the twin | Matched gait-14 records: mean joint RMSE 2.123°, mean peak hardware IMU tilt 10.279°, versus simulated rigid-body 0.275° and estimator 0.724°. | Investigate loaded feet, contact, assembly compliance and attitude estimation together; encoder agreement alone is insufficient. |
| L5 is not uniquely abnormal in the latest unloaded test | Six-leg screen: L5 hip/knee loops 0.615°/0.350°; L1 hip 0.761°; L0 knee 0.474°. L4 is unusually tight at 0.147°/0.088°. | Finish the comparable loaded screen before singling out L5 or buying replacement actuators. |
| Steering has both missing functionality and a trajectory limit | Hardware no-yaw-v2 has no yaw command. In newer scripted simulation probes, combined walk/turn causes yaw slew clipping on 47.7% of samples versus 0% for pure turn. | Add and verify steering feedback and an achievable command envelope; more yaw reward alone has poor support. |

The hardware speed estimate is a short, floor-tag-referenced pilot measurement, not a repeated precision benchmark. Its report uses sparse before/after chassis detections. The lateral displacement is substantial, but its exact ratio should not be treated as a stable long-distance drift coefficient. The apparent 5.31° RL command/encoder RMSE is also contaminated by held, asynchronous feedback; it is not comparable to the synchronized scripted-gait RMSE.

The latest September 4 forward trace stayed upright, with maximum relative tilt 8.2°. Sampled video frames corroborate leg cycling and short translation without a visible tip. The following two attempts failed during stand at tick zero, before walking: approximately 17 ms of synchronous reading already exceeded the 10 ms control budget. Those records do not demonstrate a new gait failure or a current broken servo.

1. **Finish and verify one consistent control implementation.**

   The working tree already contains substantial timing/freshness changes: asynchronous stand/lower, snapshot-age limit reduced from 250 to 150 ms, fresh-sample handling, and sampler cleanup. They must be reviewed and verified, not reimplemented blindly. The latest physical trace still reports the older 250 ms allowance; it does not prove these changes are deployed or successful.

   Freeze the policy hash, joint frame/contract, model, safety slew, motor speed/acceleration, decision rate, write rate, sensing rate and filter implementation in one manifest. Benchmark actual timestamps with normal telemetry/camera load. Neural inference averages about 0.56 ms in the newest run; transport and scheduling deserve attention before replacing the network.

   Run a paired offline test of the same frozen policy under (A) nominal simulation, (B) the real 50 Hz write/10 Hz held-observation path with the exact hardware filters, and (C) measured jitter/latency. Hardware derives joint velocity by filtered finite differences; simulation reads current MuJoCo velocity. A fixed attitude-filter coefficient applied at 10 Hz is not equivalent to applying it at 100 Hz. These code differences are established; the paired test determines their performance cost.

   Choose an achievable physical contract and train/evaluate against it. Do not simply run a 100 Hz checkpoint at 50 Hz. Likewise, the scripted gait's 2000/80 motor settings and the tested RL policy's 400/20 settings are distinct conditions, not interchangeable tuning knobs.

2. **Establish a real baseline and define smoothness operationally.**

   Keep scripted gait 9 as the physical reference: its four complete trials achieved approximately 15.9 mm/s forward and 15.6 mm/s backward at a 30 mm/s command. Gait 14's paired bidirectional median was 10.75% worse, so it has not earned replacement status. The RL canary's modestly higher achieved speed used a much larger requested speed and a different motor contract; that comparison alone does not establish superior efficiency or control.

   Compare the hardware-tested PPO policy with its frozen behavior-cloning parent under their identical supported contract. The parent already had slightly better simulation progress and slip. Keep verified stand/hold/lower behavior separate from walking. The user's smooth-walking objective does not require one network to learn all transitions.

   Record actual engaged walking time, floor-referenced velocity/course, velocity variation, chassis attitude/rates, visible foot clearance and stance slip, stop/restart transients, sensor age, deadlines, and real electrical/thermal telemetry. Cross-check IMU tilt against visual chassis pose: acceleration and estimator artifacts can resemble rocking. Old camera recordings require timestamp-aware interpretation; some raw files play roughly four times too slowly, and processed derivatives must not be indexed with raw frame numbers.

   Proposed initial acceptance target, not an existing result: repeat a full 60-second supervised course within the available floor area on three trials, including straight travel, both turn directions, stops and restarts, without resets/falls/dragged legs. Target at least 0.03 m/s on straight segments, median straight-segment course error below 10°, and materially lower measured rocking/speed variation than gait 9 under comparable conditions. Set final tilt/rate bounds from a validated estimator and baseline. Expand the command-speed training range before asking the fixed-0.08 m/s policy to follow this new variable-speed specification.

3. **Fit the assembled robot, then make targeted mechanical changes if measurements justify them.**

   The physical-unit record says legacy two-piece coxa and thinner yaw bearings; current CAD has a fused coxa and a different bearing stack. Compression spacers are not recorded installed. A freshly generated current-CAD mesh is therefore not automatically the actual robot, and new coxa parts are not automatically drop-in replacements.

   Finish the all-six-leg planted comparison with matched pose, load, floor and timing. Earlier L5 loaded loops remained above L4's, but the latest complete six-leg comparison was unloaded. Encoder loops without measured force or component-local markers cannot identify whether the cause is servo output, horn, fasteners, bearing, printed link or contact. If a reproducible loaded outlier remains, use a controlled component intervention or swap to localize it. Check foot contact and mass distribution as well as joints.

   Fit the simulator to held-out walking/contact data, not just supported air motions or one scalar speed. Include measured timing, loaded response, deadband/hysteresis where supported, friction and body attitude response. Randomize uncertainty around this fit. Existing quasi-static compliance and actuator-fit options are useful infrastructure, but their presence does not prove the selected configuration represents this unit.

4. **Deliver steering with feedback and joint-feasible trajectories.**

   The hardware-tested no-yaw policy translates in four directions at one command magnitude. It cannot provide the full variable-speed, turning behavior needed to walk around a room. Its velocity-observation mode intentionally substitutes the command rather than measured body velocity; that is its trained contract, not an accidental implementation bug. Adding real velocity feedback would be a controller/policy change requiring validation.

   The older CPG result is promising evidence for feedback: yaw trim reduced low-friction turn overshoot from about 1.33–1.35 to 1.07. However, the physical CPG loader imports gait parameters, not that complete feedback loop, and the historical artifact predates the current joint contract. Regenerate and integrate it before claiming its simulation gate applies on hardware.

   Newer teacher probes expose an achievable-command limitation: adding 0.08 m/s translation reduced achieved yaw from about 0.220 to 0.072 rad/s, with large additional slew clipping. A reasonable new controller mechanism is to govern simultaneous translation/yaw demand smoothly, slowing translation as steering consumes available joint motion, with gyro/heading feedback and feasible foot trajectories. This is a proposal to test. Do not relax safety slew limits or repeat the already-refuted fixed-demand duty-skew experiments as the first response.

5. **Resume focused RL only after those controls and measurements are credible.**

   The month produced useful infrastructure, teachers and simulation controllers. It also supplied negative evidence: prior-free walking was retired after many mechanisms and two final 150M-step runs that still stood in place. Roughly 24 recent steering reward/supervision arms and four multiteacher canaries failed to produce the required improvement. This is evidence against repeating those recipes, not proof that all RL or all gait designs cannot work.

   The newest September 5 stress-trained candidate completed 32/32 episodes without falls, but had direction error 42.26° and slip/m 3.696 versus references around 43.6–44.6° and 2.819–2.939. It is not a clean upgrade. The verdict branch named `FALL` should not be confused with an observed fall. Earlier green joystick/AMP/CPG gates refer to specific tests, often older 25 Hz primitive models; AMP's separate joystick stress test still failed. The delivered mesh bundle had progress ratio 0.418 and no yaw authority.

   After a validated controller/twin exists, compare one bounded residual or teacher-guided RL improvement against the frozen baseline, with identical evaluation conditions and protected stop/turn/stance behavior. Residual control is an engineering proposal, not an established project result. Require better physical progress/course/smoothness, not just increased reward or zero falls. Simulated current is an uncalibrated torque proxy and cannot certify real motor safety.

The live orchestrator showed zero running runs, no backlog and 313 verdicted entries in its live window. That is not a verified total count for the month. Idle GPUs are appropriate while the next useful hypothesis is a controller/measurement problem. The recommendation is to prioritize hardware delivery; no campaign settings were changed.

Evidence links:

- [Published hardware walking record](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/9c7ee551789f42fb93589e367ea15fad) and [local session analysis](../rl_move/hardware_traces/RL_HARDWARE_SESSION_20260903.md).
- [Latest local forward trace](../rl_move/hardware_traces/rl_walk_trial_20260904_232355/robot_rl_drive_20260905_062416_summary.json), [first following stand failure](../rl_move/hardware_traces/rl_walk_trial_20260904_232754/summary.json), [second following failure](../rl_move/hardware_traces/rl_walk_trial_20260904_232829/summary.json).
- [Scripted-gait campaign](../rl_move/hardware_traces/GAIT_TEST_SESSION_20260901.md), [physical assembly](../robots/hexapod-1.yaml), [joint-flex status/results](../robots/experiments/hexapod-1-joint-flex/status.yaml), [published all-leg screen](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/0ab3781b4f3b42daa0d8d71de5d1575c).
- [Controller](../linux_control/rl_policy.py), [hardware state estimator](../rl_move/robot_state.py), [simulation state](../rl_move/sim/sim_env.py), [CPG status](../rl_docs/tracks/cpg/STATUS.md), [physical CPG loader](../linux_control/cpg_controller_loader.py).
- [Live standwalk status](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/standwalk/STATUS.md), [cycle log](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/log.md), [run ledger](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/runs.md), [current interpretation corrections](../CURRENT_TRUTHS.md).
- Relevant external context: [Tan et al., sim-to-real locomotion](https://arxiv.org/abs/1804.10332) identifies actuator and latency modeling as transfer tools; [Liu et al., motion-prior hexapod locomotion](https://arxiv.org/abs/2511.03167) demonstrates a real-hexapod motion-prior approach. These support the general direction, not a prediction that their results transfer to STS3215 hardware.
