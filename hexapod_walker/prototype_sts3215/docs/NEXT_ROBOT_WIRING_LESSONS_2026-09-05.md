# Walking transport and next-robot wiring — 2026-09-05

The current CPU is fast enough for the deployed policy. Improve fresh feedback
and command scheduling first; keep the existing 1 Mbps servo baud. For the next
robot, split communication into independently driven buses and distribute power
to individual servo pigtails. These are recommendations from code and saved
measurements, not claims that a new harness or firmware has been tested.

## What exists and what was measured

The documented as-built path is Linux `/dev/ttyHS1` at 921,600 baud → Uno Q MCU →
D0/D1 and FE-URT adapter → one half-duplex 1 Mbps TTL bus, servo IDs 2–19.
Power already has six leg branches; within each leg the feed enters the hip and
tees to yaw/knee. Logic has a separate battery tap and shares ground. Sources:
`firmware/WIRING.md:27`, `:594`; `linux_control/mcu_feetech_bus.py:55`.

Saved run `rl_move/hardware_traces/rl_walk_trial_20260904_232355/robot_rl_drive_20260905_062416_summary.json:251`
used 100 Hz policy, 50 Hz writes and 10 Hz asynchronous snapshots. Policy inference
averaged **0.563 ms** (max 1.304); writes averaged **3.986 ms** (max 19.085);
snapshot updates averaged **19.177 ms** (p95 40.610). There were 97 overruns in
192 ticks. This short, older run identifies transport/scheduling as the better
first target than buying a faster computer. It does not measure the current
integrated controller, and the summary's nominal duration is not proof of
continuous wall-clock walking.

The service runs Python under normal Linux scheduling; no real-time priority or
CPU affinity is configured (`linux_control/systemd/hexapod-web.service:14`).
Replacing inference hardware will not remove UART lock waits or MCU acquisition
latency.

## Wire-time budget

Assume 8N1, 10 bits/byte, healthy replies, no return-delay gaps, retries or software
overhead. The manufacturer's SDK uses `8 + N` bytes for a SyncRead request and
`N × (6 + L)` reply bytes for an L-byte register block. SyncWritePosEx writes
seven registers plus ID per servo: `8 + 8N` bytes.
[Feetech packet implementation](https://github.com/ftservo/FTServo_Arduino/blob/main/src/SCS.cpp),
[position-write implementation](https://github.com/ftservo/FTServo_Arduino/blob/main/src/SMS_STS.cpp).

| Independent bus population | Goal write | Position + speed, L=4 | Full state, L=15 | Write + fast read |
|---|---:|---:|---:|---:|
| 18 servos, current bus | 152 B / 1.52 ms | 206 B / 2.06 ms | 404 B / 4.04 ms | 3.58 ms |
| 6 servos, three parallel buses | 56 B / 0.56 ms | 74 B / 0.74 ms | 140 B / 1.40 ms | 1.30 ms |
| 3 servos, six parallel buses | 32 B / 0.32 ms | 41 B / 0.41 ms | 74 B / 0.74 ms | 0.73 ms |

The parallel rows are elapsed wire time only if buses run concurrently. One
blocking loop visiting three UARTs sequentially does not achieve that speedup.
On today's single bus, 100 goal writes + 90 fast scans + 10 full scans per second
occupy about **37.8%** of nominal wire bandwidth. Thus a scheduled 100 Hz outer
joint loop is plausible without changing baud; it remains unproven end to end.

On the separate host link, a combined S command is 113 bytes out + 133 back:
**2.67 ms** wire time at 921,600, **21.35 ms** at the supported legacy 115,200
fallback. A read-only S exchange is 138 bytes / **1.50 ms**; a full F exchange
with default IDs is 244 bytes / **2.65 ms**. Check the actual negotiated host
baud when interpreting runs. Byte layouts: `mcu_feetech_bus.py:65`, `:72`, `:900`.

Feetech specifies **1 Mbps maximum** for C018: increasing the servo baud beyond
that is unsupported. Its rated torque is 10 kg·cm, versus 30 kg·cm stall torque;
stall current is 2.7 A per motor. More bus bandwidth cannot fix a motor operating
near its load limit. [Feetech C018 specifications](https://www.feetechrc.com/525603.html).

## Smallest useful experiments now

1. Keep the same policy/gait and 100 Hz policy / 50 Hz writes while testing the
   estimator coefficients. Then compare **10 vs 20 Hz snapshots**, separately
   from the filter change. The existing asynchronous reader supports this;
   observe write jitter and actual state age as well as motion quality.
2. Use existing transaction timings and MCU DBG counters to locate time spent
   waiting for a bus lock, first reply byte, payload, or a parked command. The
   current 5 ms serial read timeout is a maximum wait, not an automatic 5 ms tax
   on every read; lowering it without evidence may only add wakeups.
3. The next firmware performance change should schedule fast scans around goal
   writes and guarantee a 10 Hz full-state pass. The current free-running scan
   parks incoming commands until acquisition finishes (`feetech_bridge.ino:1008`,
   `:1560`, `:1627`). A 15-byte health scan can take longer than a fast scan;
   failed slots also trigger direct reads. This is a concrete source of command
   latency to measure, not proof that every observed overrun has that cause.

Do not simply set snapshots to 50/100 Hz on the currently deployed firmware: the
`HOST_S_CONTROL_IDLE_MS = 30` early return suppresses background full-state
acquisition while S requests keep arriving faster than 30 ms
(`feetech_bridge.ino:150`, `:1622`). At 20 Hz there is still an idle window.
Increasing snapshot cadence needs to preserve health acquisition, rather than
repeatedly returning an old full-feedback cache. The delivery branch now changes
the pending snapshot refresh to run a due full-state pass instead of a fast pass,
and lets due health acquisition bypass the quiet-window return. This scheduling
fix is not flashed or measured on the robot. It does not add a physical acquisition
timestamp/sequence to F replies; successive host polls are still not independent
proof of successive physical health acquisitions. The present fast four-byte
position/speed read and slow fifteen-byte health read are already the right
payload separation. A future compact host reply can carry IMU/position plus
new health data in one transaction; do not remove current/temperature reads to
claim a higher loop rate.

## Next-robot harness

- **Default: three separate TTL buses, six servos each.** Give every bus its own
  UART and half-duplex interface. Six buses, one per leg, further reduce latency
  and isolate a broken connector if the selected controller exposes enough
  UARTs. Verify actual pin availability; the Uno Q MCU's peripheral count does
  not establish how many UARTs are accessible on its connectors. Keep Linux for
  policy/vision and make the MCU responsible for timed bus transactions.
- **Six power branches, each distributing directly to its three servos.** Keep
  the existing separate logic tap and shared reference. Use a branch splice or
  board before the three pigtails so a hip socket does not carry all three
  motors. Three stalled C018s draw 8.1 A; the existing claim that one whole leg
  is always below a 3 A connector rating is not valid in that condition.
  Molex specifies 3.0 A with AWG22 and 2.5 A with AWG24 for the cited Mini-SPOX
  family; exact clone terminals/crimps may differ.
  [Molex specification, section 4.2](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/526/5264/52641001-PS-000.pdf).
- **Separate short signal/reference pairs from high-current motor paths.** Use
  labelled, strain-relieved connectors and service loops at joints. Keep the
  existing motor-rail disconnect and make leg branches individually removable.
  Preserve signal ground; splitting data buses does not imply isolated grounds.
- **Measure voltage at the far servo under load and trunk/branch current.** Size
  conductors, connectors and branch protection from those measurements and their
  ratings. The current 20 A main-fuse and 9–13 A walking budget originate in the
  July simulated current model (`firmware/WIRING.md:684`, `:728`), not a measured
  qualification of sustained walking. A larger fuse is not a cure for voltage
  drop or an overloaded pigtail.

This investigation did not change the physical robot, its transport rates, or
service settings. The accompanying firmware scheduling patch and per-session
velocity-filter API are code changes prepared for later deployment.
