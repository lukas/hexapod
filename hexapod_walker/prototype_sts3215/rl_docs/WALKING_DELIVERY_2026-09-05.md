# Smooth walking delivery — 2026-09-05

This implements the [walking review](../docs/WALKING_REVIEW_2026-09-05.md).
The immediate milestone is a measured, repeatable physical canary using the
already tested walking checkpoint. Smooth room-scale walking is not yet a
demonstrated result.

## Follow-through on the remaining issues

These are parallel engineering tasks, not prerequisites piled onto a walk.

| Issue | Concrete decision or change | Remaining physical work |
|---|---|---|
| Delayed joint feedback | Keep 100 Hz; expose velocity alpha through the existing drive API and trial CLI so A/B runs need no config edits or restarts. `.8` improved both simulated directions versus `.3`. | Run the same walk with each value; retain it only if physical behavior improves. |
| Attitude estimator | Keep `.98`. Changing only attitude to `.9039208` improved forward progress `.294 → .319` but worsened sideways `.297 → .280`; sideways slip also worsened. | Cross-check actual rocking against video when interpreting runs; no attitude change is needed to try velocity filtering. |
| Inner-loop transport | Fix the firmware path that starves full-state acquisition during frequent S requests; preserve command priority and existing health reads. Current CPU inference is already fast enough. | Target-board build and firmware deployment remain separate from the first filter comparison. Then measure 20 Hz sensing before claiming a faster operating rate. |
| Gait baseline and transfer fit | Keep the existing policy and gait 9 as references; retain measured differences between the full-mesh diagnostic and legacy physical assembly. | Use successive walking runs to compare progress/rocking and fit loaded/contact response. Do not label the CAD model an exact physical twin. |
| Steering and policy runtime | Integrated the completed obs-75 MLP / obs-81 dual-GRU exporter and hardware runtime, preserving the filter override and shared recurrent state. Reject the tested command-scaling/time-slicing approaches as broad walking upgrades. | The no-yaw canary still cannot demonstrate turning. The new runtime enables testing existing candidates; it does not establish their physical steering or Uno Q inference timing. |
| Further RL | The active orchestrator is handling its existing work; no duplicate training or new gait search was launched here. Velocity/attitude isolation gives a specific transfer target. | Compare the resulting useful candidates against the physical baseline, without waiting for every model uncertainty to disappear. |
| Next robot | Prefer compact, serviceable load paths, individual servo power feeds, and independently driven servo buses. | Build one improved leg before copying it six times; no present evidence justifies replacing every servo. |

The attitude-only report is
`logs/ckpt_eval/deployed_transport_noyaw_v2_20260905_attitude_only/report.json`.
Design details and primary sources are in the
[mechanical lessons](../docs/NEXT_ROBOT_MECHANICAL_LESSONS_2026-09-05.md) and
[wiring lessons](../docs/NEXT_ROBOT_WIRING_LESSONS_2026-09-05.md).

The merged controller/runtime/CLI changes passed **159 focused tests**. The
firmware scheduler passed **11 tests** that compile its actual production loop
with mocked IO; removing the fix reproduces full-health starvation at 50/100 Hz
snapshot requests. This is not a target-board build or a bus timing measurement.
The physical robot was checked over HTTP: idle/limp, 18/18 servos, IMU healthy.
No deployment, firmware flash, or motion occurred in this continuation.

Commits: per-trial alpha `464b43d31`; firmware scheduling `d57ead668`;
runtime/exporter integration `70536488d` and `3a9556f40` (from the separate
policy task). These additions do not require a fresh source-hash match to the
old queued manifest; record the actual version used for the experiment.

The cloud verification finished in cycle `20260905T080130_operator-kick`.
It used a **different actor and regenerated 3.490 kg model**, so its noise
screen is supporting mechanism evidence rather than an exact replication of
the frozen canary. Its combined faster filters retained a forward advantage
at the chosen 1× simulated noise and lost it at 2×. Those are assumed noise
levels, not measured hardware noise; they do not decide the physical A/B result.
The old instruction to wait for a measured-noise report is superseded by
Lukas's direction to run concrete experiments. Full cloud details remain in
[the verification branch](https://github.com/lukas/hexapod/blob/codex/smooth-walking-delivery-verify-20260905/hexapod_walker/prototype_sts3215/rl_docs/WALKING_DELIVERY_VERIFY_20260905.md).

## Delivered infrastructure

- Robot Lab understands `external_guarded` jobs. They wait for an operator;
  the automatic worker cannot claim them. External completion retains the
  queued identity and verifies the submitted specification.
- The guarded queue client checks the server capability before submitting,
  verifies every receipt, and reuses matching plan IDs. A truncated listing
  cannot silently authorize a duplicate. Submission must be serialized;
  cross-client atomic deduplication is not implemented.
- The benchmark records actual walking engagement and sensor/write timing.
  Historical traces without these fields retain unknowns. Separate short
  runs cannot be combined into a claimed continuous 60-second trial.
- Controller changes preserve the trained policy clock while coalescing bus
  writes, reject stale feedback and unverified HTTP capture timestamps, and
  quarantine the serial bus if a background reader cannot be joined. The
  physical controller has not been deployed by this task.

## Fixed-policy cadence comparison

The frozen hardware actor was evaluated at 100 Hz throughout, with different
write/acquisition cadences. Same seed, forward and sideways commands, 10 seconds
per cell. Domain randomization was off.

| Policy / write / feedback Hz | Forward progress ratio | Forward slip/m | Sideways progress ratio | Sideways slip/m |
|---|---:|---:|---:|---:|
| Nominal simulator | .433 | 2.289 | .379 | 2.503 |
| 100 / 50 / 10 | .294 | 4.310 | .297 | 3.859 |
| 100 / 50 / 50 | .368 | 3.012 | .359 | 2.854 |
| 100 / 100 / 10 | .339 | 3.515 | .309 | 3.383 |
| 100 / 100 / 100 | .414 | 2.357 | .369 | 2.629 |
| 100 / 50 / 50, original 10 Hz filter bandwidth | .296 | 4.089 | .280 | 4.083 |
| 100 / 50 / 10, faster filters | .366 | 3.112 | .327 | 3.352 |

All cells completed without termination. The follow-up isolates a substantial
**filter-response mismatch**: keeping the slow filter bandwidth removes most
of the 50 Hz sensing gain, while faster filters at the existing bus cadence
recover nearly all the forward gain. The latter used velocity alpha `.83193`
and attitude alpha `.9039207968`, versus `.3` / `.98` today. They match the
approximate response time of the original coefficients at 50 Hz; they are
experimental settings; these results do not establish performance on the robot.

Keep the policy at 100 Hz. The next physical comparison needs only the existing
`velocity_filter.alpha` setting changed from `.3` to `.8`, retaining attitude
alpha `.98`, the same policy/gait, and the same 100/50/10 Hz rates. A matched
velocity-only simulation gave forward progress `.294 → .327` (+11%) and sideways
`.297 → .337` (+13%), with slip per meter reduced 16% and 15%. Both 10-second
episodes completed without termination. The actor/model/motor hashes match the
earlier baseline. This isolates one useful change without new training or bus code.
The report is `logs/ckpt_eval/deployed_transport_noyaw_v2_20260905_velocity_only/report.json`.

Noise analysis can proceed alongside this experiment; it is not a new admission
gate. Try the bounded physical comparison using existing stop protections,
then keep or reject the setting based on the actual walking. Do not run these
weights at 50 Hz merely to match bus writes.

These are diagnostics on the current **4.80573 kg full-mesh model**, with a
training configuration reconstructed from export metadata and the training
log. They are not a reconstruction of the original 3.49 kg training twin or a
hardware speed prediction. The filter-isolation follow-ups cover only two
directions and do not establish behavior with real sensor noise. Simulated
current remains an uncalibrated proxy. The replay
does not reproduce readiness, controller transitions or the live 150 ms
freshness stop for custom long-gap traces.

Reports, complete configs and model/motor hashes are preserved under
`logs/ckpt_eval/deployed_transport_noyaw_v2_20260905*`. The feature is default-off;
MJX refuses it until that backend can reproduce its timing contract.

## Validation and code state

- Controller/API/bus, benchmark, replay and envelope regressions: **132 passed,
  two expected skips** for untracked hardware traces and optional planted
  protocols. The tracker source was supplied on `PYTHONPATH` for import only;
  the isolated checkout does not initialize that submodule.
- Robot Lab: **69 passed**. The tested package is installed in the local Lab
  runtime; live health and source hash verified after restart while idle.
- `make robot-check`: **42 syntax checks and 12 composed-policy guards passed**,
  plus JavaScript and whitespace checks. Its path quoting now works for a
  workspace directory containing spaces.
- A broader simulator check encountered the existing
  `test_drag_charges_loaded_translation` threshold failure; the replay author
  reproduced the identical value on prepatch `sim_env.py`.
- Controller commit: `96b54760f`. Replay and cadence evidence: `f68e1181a`.
  These are on `codex/smooth-walking-delivery`; the shared working checkout's
  unrelated edits have been preserved.
- The later upstream time-slicing experiment was merged; all **17** updated
  envelope tests passed with the corrected slip-history behavior retained.

Follow-up operator note `fb_20260905T075426_969b3d` and cycle
`20260905T080130_operator-kick` hand the frozen actor and checked-in evidence to
the orchestrator for a matched noise-sensitivity screen and corrected
stop/restart slip measurement. The cycle was observed reading the delivery
branch. This work is CPU-only; the physical filter settings are unchanged.

## Orchestrator experiment

Durable request `fb_20260905T071610_749846` produced cycle
`20260905T071621_operator-kick`, commits `02fc8507` and `817aa770`.
The cycle ran a scripted-gait command-envelope comparison: 10 command
scenarios, two seeds, three arms. Because domain randomization was disabled,
the seed repetitions were identical: this is one deterministic observation
per condition, not 60 independent robustness trials.

| Combined translation and yaw | Original controller | Scale all axes | Prioritize yaw |
|---|---:|---:|---:|
| Forward progress / requested distance | 0.372 | 0.239 | 0.166 |
| Yaw course / requested yaw | 0.24 | 0.25 | 0.42 |
| Median achieved yaw rate, rad/s | 0.070 | 0.080 | 0.168 |

Scaling all axes is rejected: it loses progress without meaningfully
improving turning. Prioritizing yaw has a substantial speed cost and remains
an opt-in research candidate. Neither is promoted to the robot. No PPO run
was launched by this request.

Review subsequently found that the evaluator carried foot-position history
through zero-command pauses. Restart could then charge paused displacement
as commanded slip. The corrected evaluator advances history every tick and
stamps `slip_metric_version=commanded_intervals_v2_stop_history_advanced`.
Original cloud artifacts remain unchanged. Their slip values require a rerun;
the progress/yaw conclusions above do not depend on that calculation.

## Next physical milestone

Robot Lab job [`bf30596891a0481b9e812abbf5af9cf3`](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/bf30596891a0481b9e812abbf5af9cf3)
is **waiting for an operator**. Its [exact plan](tracks/todaypolicy/hardware_delivery/timing_canary_plan.json)
and [receipt](tracks/todaypolicy/hardware_delivery/timing_canary_receipt.json)
are checked in. No physical execution has occurred.

The [benchmark protocol](HARDWARE_WALK_BENCHMARK.md) prepares a single
3-second forward command window, fixed 0.08 m/s, no yaw, using
`hardware-walk-noyaw-v2-canary`. Arming occupies part of that window, so
actual learned-policy engagement must be measured separately.

The operator must authorize and supervise the existing STEP acquisition,
bounded forward trial, stop, and planned lower. First deploy and verify the
reviewed controller version, check live source timestamps and three fresh
healthy scans, and confirm the physical posture matches the logical frame.
Queueing this plan does not execute or authorize motion. No firmware or CAD
change is part of this delivery.

Following Lukas's request to reduce process, the benchmark generator no longer
requires a pinned tag layout, exact source-hash match, or a separate timing
report to attempt a walk. These instructions supersede those process prerequisites
without changing the job's motion. The existing Lab entry retains the original
specification: its API does not accept notes on a waiting job, so no replacement
job was created. Continue repetitions within the authorized scope
after a stable stop, and use the evidence available to choose the next change.

Orchestrator feedback `fb_20260905T081113_6f0872` communicates this correction
and cancels the extra command-envelope rerun requested earlier. It is filed
for the next decision cycle; the active cycle has not acknowledged it yet.
