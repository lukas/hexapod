# 100 Hz RL on hardware: the timing failures and their real causes (2026-09-10)

**Read this before concluding "the robot can't run 100 Hz" or "retrain at
25/50 Hz".** The 100 Hz runner tripping with `timing overrun` has come up
repeatedly. On 2026-09-10 (first RL session on the second build,
`hexapod2.local`) it had THREE stacked causes, none of them the policy or
the Linux host loop. Companion doc: `BUS_AND_TIMING_DEBUG_2026-08-26.md`
(how the STREAM bridge works). Session artifacts:
`~/hexapod/tmp/walk_session/` (videos, episode CSVs, SESSION_NOTES.md).

## Symptoms seen

| Attempt | Route | Result |
|---|---|---|
| 100 Hz obs-74 walk | `/api/rl/walk` | trip after 3 ticks: "4 consecutive ticks missed the 100 Hz deadline"; mean service 21.8 ms, read 12.9 ms, write 4.4 ms |
| 100 Hz drive session | `/api/rl/drive/start` | trip after 0.5 s (52 late ticks); mean service 13.9 ms, read 12.0 ms |
| 25 Hz legacy walk, default export | `/api/rl/walk` | trip: runner adapted onto the 100 Hz inner stream = 4 reads per policy tick (76 ms service) |
| 25 Hz legacy walk, `--inner-hz 25` | `/api/rl/walk` | OK: 150 ticks, 0 overruns, 37 ms of the 40 ms budget |
| 100 Hz drive, after firmware flash | `/api/rl/drive/start` | 0.2 s, "feedback lost during hold" |
| 100 Hz drive, after fast-pass fallback | `/api/rl/drive/start` | 1.1 s, 112 ticks, mean service 9.5 ms, then "2 consecutive hard misses (60 ms late)" |
| 100 Hz drive, after full-pass timeout bound | `/api/rl/drive/start` | 68 ticks, trip on the walk-engagement tick (69.6 ms, all stages ~4 ms: host-side one-time cost) |
| 100 Hz drive, after runner grace-at-model-switch | `/api/rl/drive/start` | OK: 35.1 s / 3514 ticks reverse, then 31.0 s / 3102 ticks forward; mean 9.5 ms/tick, max 33 ms, 0 stale samples, no fall |

## Cause 1: the MCU was running pre-STREAM bridge firmware

`linux_control/mcu_feetech_bus.py` sends `STREAM 1` after `HELLO`. Old
sketches answer `ERR`; the driver then silently uses the legacy synchronous
path (`write_all` + `read_all_positions` + `read_imu`), where one 18-servo
read costs 9-13 ms. That alone makes 100 Hz impossible and 25 Hz marginal.

How to tell: the service journal / `web_drive.log` prints
`[bus] MCU stream mode ON` on a good bridge. If that line is missing after
`[bus] MCU Feetech bridge on /dev/ttyHS1`, the firmware is old. hexapod2's
`~/feetech_bridge/feetech_bridge.ino` was the 2026-08-26 sketch with zero
`STREAM` references.

Fix: `firmware/flash_feetech_bridge.sh arduino@<robot>.local`, then
`sudo systemctl restart hexapod-web`. After the flash the no-motion probe
(`GET /api/rl/timing?samples=200&read_samples=50`) read 5.8 ms mean /
7.5 ms max per snapshot (was 8.6 / 10.5) and `bus_bench.py --port mcu`
showed `read_snapshot` at 191 Hz with 764/764 frames OK.

## Cause 2: incomplete snapshots under host-paced snapshot polling (NOT wiring)

Even with STREAM firmware, ~40% of host snapshots came back with a servo
record flagged not-ok, so `RobotState.bus_ok` was False and the runner
counted the sample as lost ("feedback lost during hold"; the probe
reported `snapshot_read_errors` 14/30). The misses always hit IDs 4, 5, 6
(L0 knee, L1 yaw, L1 hip) -- the 3rd-5th slots of the 18-slot burst -- and
those servos answered direct reads perfectly.

First read (wrong): a marginal cable/connector on the leg 0 -> leg 1
segment. Ruled out by a four-condition rest test at 21:30 UTC:

| condition (robot limp on the floor unless noted) | passes | misses |
|---|---|---|
| MCU free-running, host idle, torque off | 1199 | 2 (0.2%) |
| host polling `S n=0` at 100 Hz, torque off | 508 | 225 (44%) |
| MCU free-running, host idle, torque on | 1197 | 2 (0.2%) |
| host polling `S n=0` at 100 Hz, torque on | 506 | 220 (43%) |
| 131 s walk (host `S n=18` step_all at 100 Hz) | 39513 | 270 (0.7%) |

Motion and torque are irrelevant; only host-paced snapshot-only polling
triggers it. Mechanism: after replying to a host `S` the sketch scheduled
its refresh pass 1 ms later, while the 128-byte reply was still leaving
the host UART. The reply's TX interrupts at 921600 baud landed on the
first few servo-bus reply windows of the pass and those slots timed out --
hence always the same three early IDs. Fix (this commit): `Serial1.flush()`
before the host-triggered refresh pass, plus per-slot miss counters
(`pos_slot_fails_id<N>` in `DBG`). Re-test: host-paced 100 Hz polling went
from 225/508 misses to 1/496.

Also kept: `streamFastPass()` does one bounded direct `FeedBack` read
(IOTimeOut 3 ms) for any slot that still fails, like `streamFullPass()`
already did, and reports `stream_pos_slot_healed`. With both changes the
host effectively never sees an incomplete snapshot.

## Cause 3: 100 ms library timeouts inside the MCU fallback

`streamFullPass()` (10 Hz current/load/volt/temp refresh, also run
synchronously by a host feedback request) retried failed slots with the
FTServo library default `IOTimeOut = 100 ms`, twice per slot. With IDs 4-6
failing often, the MCU went deaf to the host for 60-200 ms; the host saw
`max_service_ms 69.9` and tripped on "2 consecutive hard misses". Fixed by
bounding that fallback to 3 ms as well.

## Rules of thumb that fall out of this

- A `timing overrun` on the RL runner is a TRANSPORT diagnosis, not a
  policy-rate diagnosis. Check, in order: (1) `[bus] MCU stream mode ON`
  in the journal; (2) `GET /api/rl/timing` snapshot mean/max and
  `snapshot_read_errors`; (3) `bus_bench.py --port mcu --bridge-debug`
  counters `stream_pos_slot_fails`, `stream_pos_slot_healed`,
  `max_fast_pass_us`, `max_full_pass_us`.
- Every new robot build needs the current bridge firmware flashed as part
  of commissioning; motor setup alone does not do it.
- A legacy 25 Hz export must carry `--inner-hz 25`; otherwise the runner
  streams 4 inner steps (each a bus round trip) per policy tick.
- Host budget at 100 Hz with STREAM firmware on the Uno Q: `step_all`
  ~5 ms + obs/policy/safety ~1 ms. It fits, but the Python process also
  serves HTTP heartbeats, the 2 s ServoWatch `SCAN` (~15 ms) and the TFT
  thread, so expect occasional 10-20 ms ticks; the drive runner tolerates
  those (`DRIVE_TIMING_*` in `rl_policy.py`).
- Servo temperature telemetry shows single-sample spikes (39, 77 C) on this
  bus; the three-consecutive-sample rule in EMERGENCY_HANDLING.md is what
  keeps those from tripping anything.
- When a bus symptom clusters on a fixed set of IDs, test free-run vs
  host-paced vs torque on/off BEFORE blaming wiring; the same IDs will show
  up whenever the failure is a timing collision at a fixed offset into the
  burst.

## Cause 4: the runner's startup grace did not cover the model switch

With causes 1-3 fixed the drive loop ran at 9.5 ms/tick steady state but
still tripped, always on the exact tick the walk model engaged: that tick
cost 60-70 ms with only ~4 ms in read/write/obs/policy (one-time host
setup: async snapshot reader start plus the first `step_all` after a hold),
and the next tick inherited the lateness -> "2 consecutive hard misses".
`DRIVE_TIMING_STARTUP_GRACE_TICKS` only covered the first ticks of the
session. `_drive_timing_trip_reason` now also takes `ticks_since_switch`
and forgives the same 3-tick grace after every hold<->walk switch
(`model_switch_tick` in `_run_drive_session_impl`). Timing unit tests:
138 passed.

## Result (2026-09-10 ~20:55 UTC, hexapod2)

`walk_allheading_mlp_singleframe_acq1_stdanneal` (obs 74, 100 Hz, the
todaypolicy walk role) ran two full drive sessions on hardware:

| run | command | ticks | mean/max service | overruns (soft) | stale | tilt max | outcome |
|---|---|---|---|---|---|---|---|
| rl_drive_20260910_205338 | vx -0.08 | 3514 (35.1 s) | 9.57 / 31.3 ms | 852 | 0 | 2.9 deg | ended by operator stop, no fall |
| rl_drive_20260910_205737 | vx +0.08 | 3102 (31.0 s) | 9.54 / 33.5 ms | 637 | 0 | 3.1 deg | ended by operator stop, no fall; crossed ~1 m of floor on camera |

So 100 Hz RL IS deployable on the Uno Q with STREAM firmware. Behaviour
notes: the policy walks in a low shuffle (hip 9-22 deg, knee 76-88 deg,
yaw +-5 deg); forward progress on camera ~0.03-0.04 m/s, which matches its
own full-mesh sim rollout (forward vx med 0.031, reverse -0.028 m/s), i.e.
the speed-softness is the policy, not the transport. Reverse produced
little visible translation on this floor. `max_current_a` in the drive
summary reads 0.03-0.05 A, which is not credible for a standing robot
(hold currents are 0.1-0.35 A); the drive path's current telemetry needs
a look before it is used for anything.

The 50 Hz retrain order filed earlier today (RL_LOG 2026-09-10) predates
this result; 50 Hz remains a useful margin option, not a requirement.

## Addendum (23:00 UTC): IMU I2C lead was the other stall source

Later drives limped with "feedback stale during stream; hold unverified;
limped": the snapshot IMU age climbed past the runner's 150 ms guard while
positions stayed fresh. Bridge counters showed 225 IMU I2C read failures in
546k passes and a max IMU pass of 500 ms (Zephyr Wire has no timeout, so a
hung transaction blocks the whole MCU, which also stalls the servo stream).
After the operator reseated the MPU-6050 lead: 0 failures in 135k passes,
max pass 0.45 ms, no stale samples over four RL sessions. Firmware now
retries a runtime IMU dropout after 100 ms (was 1000 ms) and the runner
allows ~1 s (40 attempts) to confirm a hold after a stream loss before it
limps. A pinned/leaning robot after such a limp is recovered safely with
`POST /api/untrap {"force":true}` then `POST /api/safe_zero {}` (20% torque
fold first; do not call stand or safe_zero directly from a pinned pose).

## Addendum 2 (23:40 UTC): fail policy on IMU dropout while standing/walking

Before: any snapshot with IMU age > 150 ms was rejected; after 2 such ticks
the drive loop declared "feedback stale during stream", re-wrote the last
target and tried to CONFIRM the hold, but the confirmation also demanded a
fresh IMU, so an IMU-only dropout always ended in a limp -- a walking or
standing robot collapsed onto its belly (bad_walkteach_imu_limp clip in the
Robot Lab). A stale stream while in the HOLD model (learned hold policy)
skipped confirmation entirely and limped at once.

Now (rl_policy.py): the hold confirmation requires fresh, advancing servo
positions plus the pose/current/temperature/load envelopes; a stale IMU only
skips the relative-tilt check and the hold is reported as "IMU blind"
(`hold_after_stream_loss_sampled` carries `imu_blind`). The hold-model path
takes the same confirm-then-hold route as walking. A robot whose positions
cannot be confirmed still limps. Tests:
`rl_move/tests/test_rl_policy_stop_ordering.py` (IMU-blind hold, stale
positions still refuse, envelopes still enforced).
