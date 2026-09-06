# Walking with yaw: research and orchestrator guidance

Prepared 2026-09-06 UTC for Lukas's request to investigate simultaneous walking and yaw steering and advise the orchestrator.

The next useful improvement is to coordinate the feet for the requested combined body motion, and teach the policy combinations of speed and yaw that it can progressively master. Existing evidence does not justify another uniform yaw multiplier or a claim that steering is physically impossible. The first practical step is a small matched comparison using the existing controllers, with enough contact information to explain the result.

## Fit this into the work already running

At 03:01 UTC, operator cycle `20260906T030056` was implementing `robotwalk-smooth-20260906`: `cw-robotwalk-stride-20260906` and `cw-robotwalk-turns-20260906`, up to 8M steps each, one seed each, from Candidate B `cw-walkteach-scripted-allhead-acq12m`. That request already covers better teacher/stride search and combined yaw practice. Incorporate the recommendations below into those arms or their interpretation. Do not duplicate their launches, add another seed family, hold them for this document, or interrupt scratch learning and assistfade. These suggestions create no new physical-test prerequisites. The existing local RobotLab task owns deployment and physical trials.

The current Candidate B feedback reports real left/right arcs and releases; older claims that the delivered actor has no yaw channel describe a different bundle. Candidate B has the phase+yaw observation layout. Neither short arcs nor earlier heading-change videos establish reliable sustained combined-command tracking.

## What the experiment history establishes

| Evidence | Implication |
| --- | --- |
| Scripted teacher at `vx=.08 m/s, wz=±.25 rad/s` achieves about `+.0723/-.0738 rad/s`. | The teacher itself understeers substantially. |
| Frozen cap29 seed0 combined yaw `+.110/-.170`; seed1 `+.087/-.142`. Pure yaw is `+.223/-.250` and `+.226/-.247`. | Keep the frozen learned parents as controls; forcing stronger imitation of the weaker teacher can regress steering. These are historical results, not a matched comparison to today's Candidate B. |
| Combined yaw-joint slew clipping was frequent, but a later diagnostic `.375 -> 8 degree/tick` cap intervention barely changed teacher authority. | Clipping is observable, but it is not a sufficient causal explanation. Retain real limits. |
| Yaw-priority governor changes progress/yaw ratios `.372/.240 -> .166/.423`. | More rotation bought with a 55% translation loss does not solve the original combined command. |
| Fixed 1.6 s walk/turn time-slices and whole-tripod duty skew were unhelpful. | Close those tested settings, without extrapolating to all foot placement or contact scheduling. |

Sources: [teacher and seed0](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/standwalk/archive/standwalk_STATUS_journal_2026-09-03s_trim.md), [seed1](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/standwalk/archive/standwalk_STATUS_journal_2026-09-03u_trim.md), [cap intervention](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/standwalk/archive/standwalk_STATUS_journal_2026-09-04z_trim.md), [delivery comparisons](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/todaypolicy/hardware_delivery/STATUS.md).

Keep closed the already tested BC-dose, yaw-arm magnitude, selective omega-boost, multiteacher-blend and fixed-tripod-retiming families unless a new causal observation distinguishes the proposal. Ordinary continuation itself previously eroded pure turns: compare to the frozen parent and use the existing matched continuation evidence, not one unusually weak control. [Continuation confound](https://hexapod.cwd1f0-new-cluster.coreweave.app/llm/doc/rl_docs/tracks/standwalk/archive/standwalk_STATUS_journal_2026-09-04jj_trim.md).

## Research that changes the next experiment

1. **Coordinate feet around one body motion.** Fućek et al. demonstrate joystick-controlled hexapod translation/yaw with concentric foot trajectories and per-leg workspace/phase adaptation. This supports testing stance anchors and individual step timing, rather than repeating whole-tripod duty changes. [Primary paper, 2019](https://journals.sagepub.com/doi/10.1177/1729881419857997).
2. **Learn speed and yaw jointly.** Rapid Locomotion reports better command coverage with a joint speed–yaw grid curriculum than independent expansion of those axes. Use the idea at STS3215 speeds; its high-speed centrifugal limit is not automatically our cause. At `.08 m/s` and `.25 rad/s`, nominal lateral acceleration is only `.02 m/s²`. [Primary paper, Sections 3.3 and 4.1](https://journals.sagepub.com/doi/10.1177/02783649231224053).
3. **Separate motor and contact limitations.** Actuator-Constrained RL models the motor torque–speed region and investigates work distribution across legs. It motivates measuring loaded motor saturation and contact contributions separately from target slew clipping. Its quadruped parameters and gains are not STS3215 calibration. [Primary paper](https://arxiv.org/html/2312.17507v1).

These are research-supported design directions, not evidence that a particular replacement already works on this robot.

## First useful comparison: existing gait, actual geometry, contact attribution

The current `hexapod_core/tripod_gait.py` already forms a per-foot velocity from `v + omega × r` at a neutral radius. Do not describe it as simply mixing two joint-space primitives. `NoSlipGait` and `SE2FootGait` already implement anchored stance trajectories; reuse them for a comparison instead of inventing another controller. Their contextual CPG gate alternates translation and turn segments, so that success does not answer simultaneous steering.

**A local MuJoCo forward-kinematics check rules out the proposed hip-offset fix as a leading explanation.** The `HIP_Y=-25.65 mm` offset is nearly cancelled by the `+24.15 mm` pad offset: net tangential offset is about `-1.50 mm`. On both local XML variants, each 4.80573 kg, the current TripodGait's maximum same-neutral foot displacement error is **0.220 mm pure-turn and 0.732 mm combined**, for both yaw signs. Applying the older SE2 IK to the same displacements makes the error **2.665 mm and 7.755 mm**, respectively. An IK derived from the actual loaded chain reconstructs the targets to numerical precision. This sampled kinematic check is not a dynamic gait comparison, but it is sufficient to reject blindly adding the old hip offset. It does not establish the geometry of a different remote model.

Reproduction: [read-only FK script](research/walking_yaw_20260906/verify_mesh_fk.py) and [numeric results](research/walking_yaw_20260906/geometry_probe.json). It samples 151 phase points per case, with no dynamics steps or robot motion. The current geometry includes hip rise 38.4 mm and effective tibia-to-foot-site length 145.5 mm. Any SE2/CPG comparison should use this model's correct FK/IK rather than its legacy constants; preserve the same neutral pose in an ablation.

Likewise, exact circular motion alone is not a compelling explanation for the yaw deficit. At period `.75 s`, `vx=.08`, `wz=.25`, the centered linear-versus-exact stance endpoint difference is only about `.16–.54 mm` in the simplified geometry. Anchors, touchdown behavior, support loading and geometry consistency are the substantive hypotheses.

Within the existing stride arm, start with a few scripted matched cases: straight `.08`, pure yaw `±.25`, and combined `.08, ±.25`; then use `.02/.04/.08` forward and `±.125/±.25` yaw to identify where the problem begins. Allow settling and score complete gait cycles. Try both tripod start phases; identical deterministic reruns with a different unused seed are not independent evidence.

Use the same loaded model, joint frame, actuator limits and transport configuration for each comparison. Record these from the run configuration as part of the result; do not create a separate validation campaign. Historical ~3.49 kg and local ~4.806 kg assets are not interchangeable. The existing SE2 controller also limits/scales commands, including a default `.04 m/s` forward cap: report requested and applied commands and score against the original request.

Add only the instrumentation needed to distinguish causes:

- Requested/applied/measured body-frame translation and signed yaw; integrated heading as well as steady yaw rate.
- Per-leg desired, postclip and actual joint/foot motion, with stance phase and contact state.
- Per-leg ground-force yaw moment about the instantaneous whole-robot COM, integrated over a gait cycle. Include contact couples where available. This reveals whether some support legs cancel the yaw impulse generated by others.
- Contact-point slip, not just sphere-center travel; the existing `verify_noslip.py` distinguishes rolling from scrub. Keep support participation and roll/pitch alongside the tracking result.

If commanded stance motion is geometrically incompatible, correct geometry or foot placement while holding timing/posture fixed. If targets are consistent but planted legs cancel yaw impulse, investigate support load distribution, stance centers or a bounded per-leg step adjustment. If loaded actuator tracking is the loss, reshape the trajectory within the measured limits. An ideal kinematic path is not evidence of sufficient contact force.

Choose the next mechanism from these measurements. The code change should be optional with current behavior preserved when disabled; no firmware or CAD change is implied.

## Apply the curriculum to the existing turns arm

Explicitly sample simultaneous nonzero translation and both yaw signs from the start, in a small feasible region. Expand neighboring speed–yaw cells when both tracking measures improve; retain straight, pure-turn, reverse and neutral/restart cases. Include sideward commands and command transitions in the existing held-out joystick panel. The policy/export must actually receive `wz`; a change in travel heading with `wz=0` is a different task.

Use a compact grid of tracking results to expose left/right asymmetry and the tradeoff between speed and rotation. Separate metrics prevent an aggregate reward from hiding standstill, braking or worse pure turns. Preserve Candidate B as the matched baseline for these arms; historical cap29 results are context only. Do not force a better student back toward a weaker teacher on mixed commands. A teacher-conditioned residual/foot-placement policy is a possible follow-up if the stride arm produces a better source, not a reason to restart scratch learning or replace the current arm now.

A useful **research milestone**, not a new product or physical-test gate, is at least 20% relative improvement in combined yaw at `.08, ±.25`, with no more than 10% loss of translation or pure-turn authority, for each yaw sign under matched conditions. Also report absolute tracking and visible gait quality: a relative win from a weak baseline is not reliable joystick control. Existing 60-second joystick and sit/rise/walk/lower goals remain unchanged.

Persist the measured comparison, the selected mechanism and the next concrete action in the relevant track status. Continue autonomously within the already authorized arms and budgets; ordinary research decisions and report reads do not need Lukas to approve them.
