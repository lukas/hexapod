# Smooth walking delivery — 2026-09-05

The corrected controller completed a short forward walk and normal lower using
the existing 100 Hz policy and velocity alpha `.3`. The 100 Hz bus capacity was
real: our asynchronous machinery and extra polling added costs, and CPU frequency
scaling during serial waits stretched host work further. Restoring combined S,
keeping the CPU at performance speed and removing duplicate polling recovered
this canary. Sustained smooth walking and perfect deadline delivery remain unproven.
The 50 Hz writes / 10 Hz sensing used in our first diagnostics were a chosen
asynchronous architecture, not an established hardware limit. There is no
evidence that the existing 100 Hz policy needs retraining at 50 Hz.
See the [project review](../docs/WALKING_REVIEW_2026-09-05.md).

## Current physical outcome

Controller `7e8c02540` is deployed, including combined-S restoration `278e7ae3e`,
telemetry cleanup `b79154044`, a performance-governor service setup and removal
of the trial runner's duplicate feedback polling. After four failed attempts,
the second restored alpha-`.3` trial completed a **3.124-second confirmed active
command window** at requested velocity 0.08 m/s, stopped normally and lowered
to limp. Alpha `.8` has **not run on hardware**; its old 10 Hz filtering hypothesis
does not automatically apply to restored 100 Hz observations. Four ordinary
STEP lowers completed successfully in total.

The successful controller episode reports 292 ticks, zero stale samples, no
error or fall, 0.51 A peak sampled current and 6.7° maximum relative tilt. Mean
service time fell from 14.346 to **9.822 ms**, but 52 overruns and a 69.958 ms
maximum remain. This is a successful bounded canary, not proof that every
100 Hz deadline was met: 291 CSV intervals average 10.915 ms, or **91.62 Hz**
observed cadence (median 10.058 ms, p95 14.548 ms, maximum 71.209 ms). Joint
command-to-encoder tracking RMS was **4.80°**, maximum 11.14°. The engaged CSV
rows span 3.176154 seconds; their logger-entry boundaries differ from the
runner's 3.124-second confirmed command window. Requested velocity is not
measured travel speed, and no calibrated displacement result is available.

This run used the unchanged 74-observation `hardware-walk-noyaw-v2-canary`
actor, exported-weight SHA-256
`58a9bbf7862dba467aeeba534225ffb450d69b4f3302fe22637cda955fee8d6d`, with
`robot_abs_tibia_v2`, 400/20 motor settings and 0.375° maximum command delta per
policy tick. It is the baseline, **not Candidate A** from the separate Robot Lab
queue. That queue retains its remaining candidates and serialized robot ownership.

| Attempt / recovery | Observed result |
|---|---|
| `rl_walk_trial_20260905_073851` | Drive stopped after 33 ticks on stale feedback; health age 162 ms, five good sampler samples, zero sampler errors. Open-browser zero heartbeats also restarted readiness. |
| `alpha03-retry1/rl_walk_trial_20260905_074002` | Arm refresh failed: joint 10 error was 10° against an 8° limit. The later inactive-session command refusal was a symptom. |
| `rl_walk_trial_20260905_074557` | Ownership fix removed competing commands, but drive still stopped after 15 ticks; peak write call 137 ms and a 17/18 feedback frame. Runner reported that live progress stopped advancing. |
| STEP lowers `20260905_074157` and `20260905_074708` | Both completed normally and ended limp. |
| `combined100/rl_walk_trial_20260905_081140`, controller `278e7ae3e` | Combined S delivered fresh feedback, but 12 consecutive 100 Hz deadlines were missed. The controller held the pose; 18/18 servos remained healthy and no fall was recorded. |
| STEP lower `20260905_081247` | Completed normally after the restored trial and ended limp; peak sampled current 2.84 A. |
| `combined100/rl_walk_trial_20260905_093126`, controller `7e8c02540` | Completed the forward command window, stopped normally, then completed STEP lower and limped. Lower peak sampled current 0.59 A; final joint error 1.1°. |

The first, failed restored trial logged 12 engaged rows spanning **188.556 ms** of wall time
(mean interval 17.141 ms). The summary's `duration_s=0.1` is policy time, not
measured wall duration. Mean service was 14.346 ms: combined S 8.382 ms,
observation 0.791 ms, inference 0.946 ms and safety 1.369 ms. Two F refreshes
cost 5.416/6.038 ms inside estimator conversion, outside the reported read/write
stage timers. Inter-row time also exceeded reported service by roughly 3 ms;
CSV formatting and live publication occur outside that timer, but their exact
shares have not been isolated. This is a complete-loop overhead problem despite
the fast isolated bus test. There were zero stale samples and only 0.1° maximum
relative tilt. No displacement estimate is available from this short attempt.

Local trial evidence is under `/tmp/hexapod-filter-hardware/`. Firmware scheduling
fix `d57ead668` compiled for `arduino:zephyr:unoq` (21,988 bytes program, 7,056
bytes globals) and was successfully flashed. The deployment log is
`/tmp/hexapod-flash-health-scheduling.log`.

The 30-second, 100 Hz bench held torque off and sent the same pose throughout:

| Transaction | Successful replies | Mean / p99 / maximum latency | Replies with all 18 positions | Elapsed |
|---|---:|---:|---:|---:|
| Before fix: read-only `S n=0` | 3,000/3,000 | 4.065 / 4.369 / 6.541 ms | 2,768 | 29.994 s |
| Before fix: targets + snapshot `S n=18` | 3,000/3,000 | 5.940 / 6.275 / 39.322 ms | 2,994 | 30.026 s |
| After fix: targets + snapshot `S n=18` | 3,000/3,000 | 6.019 / 8.822 / 19.748 ms | 2,998 | 30.035 s |

Neither bench recorded new firmware errors, desynchronization or checksum
failures. Before the fix, full-health acquisition almost stopped: zero new full
passes during read-only S and one during combined S. After the fix it advanced
**282 times in 30 seconds (about 9.4 Hz)**; maximum position/IMU ages were
6/12 ms. This confirms the scheduling fix on hardware while preserving 100 Hz
combined-S capacity. Occasional incomplete frames and deadline misses remain;
these torque-off results do not establish loaded walking timing. The earlier
39 ms outlier included 29.9 ms waiting for the host lock, with no firmware error;
it is not evidence of a physical servo problem.

Before/after records are `/tmp/hexapod-combined-s-before-health-fix.json` and
`/tmp/hexapod-combined-s-bench.json`. The loaded trial above shows why bus
capacity and complete-loop timing must be distinguished.

## Transport history and the delivery regression

- `912534a5c` (August 24) introduced combined `step_all`: one `S n=18`
  transaction sends targets and returns position/speed/IMU.
- `bb49b5d90` (August 26) changed firmware snapshots to cached replies. Its
  documented no-motion 100 Hz bench passed 3,000/3,000 transactions: 5.8 ms
  mean, 6.1 ms p99, 6.7 ms maximum, sensor ages around 6 ms or less.
  [The timing notes](BUS_AND_TIMING_DEBUG_2026-08-26.md) recommend combined S
  for high-rate control. That bench did not establish loaded walking performance.
- `f59125f88` (August 30) replaced persistent drive's combined-S path with
  separate writes and a 10 Hz background reader. `08891671f` then capped its
  writes at 50 Hz. The preceding combined-S reference is `fa690dec0`.
- **Our `96b54760f` added contention and new refusal conditions:** every
  background S now waits for a separate F health transaction before publishing;
  allowed age fell from 250 to 150 ms; startup requires three samples; motion
  initially depended on the age of the last complete health scan. That last
  check could stop on one incomplete scan before the intended debounce.
  `6fb29374d` corrected that health handling and prevented other browser/CLI
  clients from overwriting an owned drive command. Additional F contention
  remained. `863118a8d` adds UART write/flush/ACK timing to locate that cost.

The timed `/api/rl/walk` path retained direct combined S; only
high-rate stand/lower policy moves were newly switched to async in `96b54760f`.
Reverting that commit alone would not restore persistent drive's earlier
architecture. Restoration `278e7ae3e` returns persistent drive to combined S,
retaining the current frame, motor limits, command ownership and normal stop
behavior. Missing S feedback holds the target and retries; stopping requires
three consecutive misses for the same joint. The correction removes 80 net
controller lines. Its 169 regression checks and 11 affected checks passed.
Its first loaded failure led to the CPU and polling corrections below.

## CPU governor and unnecessary polling

The on-device CPU-only profiles reproduce controller stages with synthetic
state and a 6 ms sleep representing UART blocking. They do not access the bus
or measure physical walking. With `schedutil`, all four cores share one clock
policy; it fell from 2.016 GHz to 614.4 MHz during paced work. Continuous warm
work averaged 2.763 ms, but cold 100 Hz work averaged 5.468 ms and intermittent
work 6.607 ms. Warming the policy once did not prevent subsequent downclocking.

With the `performance` governor, the clock stayed at 2.016 GHz. The matched cold
100 Hz case averaged **2.778 ms**, and intermittent work **2.704 ms**. Other
profile cases retained scheduling variation, so these figures are not a promise
that every complete loop finishes under 10 ms. Records are
`/tmp/hexapod-loop-cpu-cadence-schedutil.json` and
`/tmp/hexapod-loop-cpu-cadence-performance.json`.

`7e8c02540` sets the performance governor when the controller service starts and
removes the runner's extra F/IMUR polling during active drive. Command replies
already contain live controller state; camera recording, controller CSV and
controller safety feedback remain. `b79154044` reduces repeated scalar rounding
and diagnostic serialization in the per-tick log path. These changes preserve
the 100 Hz trained policy and address measured implementation costs. The next
loaded canary completed, as recorded above; longer repeatability is still open.

## Earlier fixed-policy cadence simulation

These results describe the earlier asynchronous architecture. They are neither
a hardware rate limit nor validation of a physical filter change. The same
frozen hardware actor ran at 100 Hz in all cells: seed 0, forward and sideways,
10 seconds each, no domain randomization.

| Policy / write / feedback Hz | Forward progress ratio | Forward slip/m | Sideways progress ratio | Sideways slip/m |
|---|---:|---:|---:|---:|
| Nominal simulator | .433 | 2.289 | .379 | 2.503 |
| 100 / 50 / 10 | .294 | 4.310 | .297 | 3.859 |
| 100 / 50 / 50 | .368 | 3.012 | .359 | 2.854 |
| 100 / 100 / 10 | .339 | 3.515 | .309 | 3.383 |
| 100 / 100 / 100 | .414 | 2.357 | .369 | 2.629 |
| 100 / 50 / 50, original 10 Hz filter bandwidth | .296 | 4.089 | .280 | 4.083 |
| 100 / 50 / 10, faster filters | .366 | 3.112 | .327 | 3.352 |

All completed without termination. Within this simulator, maintaining the slow
filter bandwidth removed most of the faster-sensing gain. The faster-filter
cell used velocity alpha `.83193` and attitude alpha `.9039207968`, versus the
modeled `.3` / `.98`. This isolates a simulated filter-response effect.

A separate velocity-only `.8` / `.98` cell at 100/50/10 gave forward progress
`.294 → .327` (+11%) and sideways `.297 → .337` (+13%), with slip reduced 16%
and 15%. Changing attitude alone to `.9039208` improved forward `.294 → .319`
but worsened sideways `.297 → .280` and sideways slip. These remain hypotheses:
the physical baseline failed before `.8` could be tried. Do not carry the
10 Hz filter adjustment into a restored 100 Hz observation path automatically.

Reports, resolved configs and actor/model/motor hashes remain under
`logs/ckpt_eval/deployed_transport_noyaw_v2_20260905*`, including
`_velocity_only/report.json` and `_attitude_only/report.json`. These used a
**4.80573 kg full-mesh model** and a training configuration reconstructed from
export metadata and logs. They do not reproduce the original 3.49 kg training
twin or this unit's legacy physical assembly exactly. The replay omits readiness,
controller transitions and the live age cutoff for long-gap traces. Simulated
current is an uncalibrated proxy. Replay remains default-off; no MJX claim is made.

Cloud verification cycle `20260905T080130_operator-kick` used a different actor
and regenerated **3.490 kg model**. Its assumed-noise screen retained a forward
advantage at 1× noise and lost it at 2×; neither noise level was measured on
hardware. This is supporting mechanism evidence, not a replication or an
additional prerequisite. Details are on the
[verification branch](https://github.com/lukas/hexapod/blob/codex/smooth-walking-delivery-verify-20260905/hexapod_walker/prototype_sts3215/rl_docs/WALKING_DELIVERY_VERIFY_20260905.md).

## Other useful work retained

- Per-trial velocity alpha API/CLI (`464b43d31`) and command ownership permit
  controlled comparisons without persistent configuration changes. Observing
  an external drive in the browser no longer starts zero-command heartbeats.
- The obs-75 MLP / obs-81 dual-GRU exporter/runtime is integrated
  (`70536488d`, `3a9556f40`). This enables existing candidates to run; it does
  not demonstrate physical steering or their Uno Q inference timing.
- The firmware scheduler fix (`d57ead668`) prevents frequent S requests from
  indefinitely starving full-health acquisition. Eleven host tests compile
  its actual loop; the target-board build, flash and subsequent bus test passed.
- Initial controller/runtime/CLI checks passed 159 focused tests. Later
  ownership/guard/UI checks passed 29. These establish tested code behavior,
  not physical walking performance. The simulator's existing drag-threshold
  failure reproduced unchanged before the replay patch.
- Robot Lab can retain the existing guarded job identity and receive actual
  outcomes and evidence. Historical short traces without measured engagement
  retain unknown durations; command speed is never integrated into displacement.

The loaded-contact/body-fit work remains useful once control is repeatable.
Keep gait 9 and the hardware-tested no-yaw canary as references. Design findings
are in the [mechanical lessons](../docs/NEXT_ROBOT_MECHANICAL_LESSONS_2026-09-05.md)
and [wiring lessons](../docs/NEXT_ROBOT_WIRING_LESSONS_2026-09-05.md).
No broad PPO search or new gait family was launched by this delivery.

## Steering experiment outcome

Cycle `20260905T071621_operator-kick` tested ten scripted command scenarios,
two identical deterministic seeds and three arms. These are not 60 independent
robustness trials. For combined translation/yaw:

| Metric | Original | Scale all axes | Prioritize yaw |
|---|---:|---:|---:|
| Progress / requested distance | .372 | .239 | .166 |
| Yaw course / requested yaw | .24 | .25 | .42 |
| Median achieved yaw, rad/s | .070 | .080 | .168 |

Scaling all axes loses progress without useful steering improvement. Prioritizing
yaw pays a substantial speed cost; neither was promoted. The evaluator's
stop/restart slip history was subsequently corrected to
`commanded_intervals_v2_stop_history_advanced`; original slip values require
care, while the progress/yaw conclusion is unchanged. No PPO was launched.

## Continue from the actual outcome

Robot Lab job
[`bf30596891a0481b9e812abbf5af9cf3`](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/bf30596891a0481b9e812abbf5af9cf3)
was cancelled because its legacy pinned specification could not accept the
actual revised execution. It retains the historical [plan](tracks/todaypolicy/hardware_delivery/timing_canary_plan.json)
and [receipt](tracks/todaypolicy/hardware_delivery/timing_canary_receipt.json).
The [failed baseline result](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/b2aaf3b5acff4cd9bfd02309a15f4e90) records the first three failed
baseline attempts and two successful lowers; **50 artifacts were uploaded and
verified**. The [successful restored canary](https://robot-lab.cwd1f0-new-cluster.coreweave.app/experiments/311f9fa2e240401281e9b30bc319f436)
is registered separately with the actual controller, actor and measured timing.
The first combined-S failure, third lower, bus benches and CPU profiles are
retained locally for the evidence upload. The old job's hashes and single-run
description do not describe the revised deployments or outcomes.

Lukas authorized bounded experiments and relevant deployment during the active
task. Continue the concrete transport correction and observed tests; no new
permission, source-hash, tag-layout or reporting prerequisite is needed.
Keep the same no-yaw canary and its 100 Hz policy clock. Measure actual
engagement and behavior instead of treating requested duration as time walked.
