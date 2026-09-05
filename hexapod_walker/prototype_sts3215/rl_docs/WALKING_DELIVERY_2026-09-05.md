# Smooth walking delivery — 2026-09-05

This implements the [walking review](../docs/WALKING_REVIEW_2026-09-05.md).
The immediate milestone is a measured, repeatable physical canary using the
already tested walking checkpoint. Smooth room-scale walking is not yet a
demonstrated result.

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
experimental settings, not a deployment recommendation without noise checks.

Keep the policy at 100 Hz. First inspect estimator response against recorded
encoder/IMU data and benchmark sensor/bus service. Evaluate a bounded filter
candidate only after that review; faster feedback remains useful particularly
sideways, but increasing poll rate alone is not the full explanation. Do not
run these weights at 50 Hz. A 50 Hz policy would require training and validation
at that rate, justified by measured hardware limits.

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

Advance only after reviewing camera, engagement, deadlines, sensor ages,
electrical telemetry and the stop. A successful canary is permission to
consider separately bounded repetitions, not proof of smooth walking or a
reason to jump straight to a long unsupervised course.
