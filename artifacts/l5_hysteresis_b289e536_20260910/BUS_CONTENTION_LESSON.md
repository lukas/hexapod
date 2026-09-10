# Do not poll `/api/feedback` while a protocol is streaming

Measured on hexapod-1, 2026-09-10, while running experiment b289e536.

## The trap

`/api/feedback` and `/api/errors` are **not cheap reads**. Timed on an
*idle* bus, from this Mac:

| endpoint | latency | touches serial bus? |
|---|---|---|
| `/api/feedback` | **~5.1 s** | yes — full 18-servo scan, holds the bus lock |
| `/api/errors` | **~6.0 s** | reads `errors.jsonl` but still ~6 s |
| `/api/calibrate` | fast (polled at 0.15 s) | no |
| `/api/logs`, `/api/logs/<f>` | fast | no |
| camera server `:8766/preview/<i>.jpg` | **~0.002 s** | no |

Two consequences that are easy to get wrong:

1. **An external "5 Hz safety monitor" polling `/api/feedback` is not
   physically possible.** It runs at ~0.2 Hz. A harness that claims 5 Hz
   is silently getting one sample every 5 s. (The prior stand/sit runner
   in `artifacts/standsit_camera_recovery_20260910/` has this exact
   aspiration in a comment; it also only ever achieved ~0.2 Hz.)
2. **Worse, polling it during motion can cause the fault it is meant to
   catch.** It holds the serial bus lock for ~5 s, which starves the
   runner's own per-tick position read.

## What it actually did

Attempt 1 of the L5 hysteresis sweep, with a supervisor polling
`/api/feedback` in a loop, tripped at tick **349/1560**:

```
02:05:17.658Z bus_timing error  P->p no_a5 1002.9ms
02:05:18.392Z error            limp: joint 1 (ID 3) missed 3 consecutive reads
```

A 1002.9 ms bus stall on a position read, then the runner's
`MAX_MISSED_READS` interlock limped — correctly. Note the joint blamed
(j1 = L0 hip) is **not even on the leg under test**, and peak current was
a benign 0.0325 A. Three prior runs of the identical protocol hash, with
no concurrent poller, completed 1560/1560. Removing the polling made the
retry complete 1560/1560 with **0 overruns**.

So this presents as a "persistent servo loss" hardware fault and is
really self-inflicted host-side bus contention.

## What to do instead

- **During motion, poll nothing on the bus.** `sysid_runner` already has
  the real-time interlocks and they run inside the bus-owning thread
  with no contention: per-joint current (`max_current_a` over
  `current_trip_polls`), temperature (55 C, 3-poll debounce), tracking
  error against a *slewed* reference, `MAX_MISSED_READS`, stale-state,
  and limp-on-trip.
- **Supervise with the cameras.** Frames cost ~2 ms and never touch the
  bus, so continuous capture plus a freshness watchdog is free.
- **Detect a trip without the bus** by polling `/api/calibrate` and
  matching `TRIP` in `progress.msg` — that is how the runner reports it.
- **Read bus telemetry before and after**, not during: three advancing
  healthy 18/18 samples each side.
- **Don't trust `/api/calibrate`'s `running` flag to mean "finished."**
  It read `false` at t+18 s of a 156 s protocol while the robot was
  demonstrably still sweeping (`mode=demo`, `demo_running=true`, hip
  moving). Hold for the protocol's *deterministic* duration
  (`len(q_deg)/hz` from tick 0) and only then believe it. Latch tick 0
  from the progress message turning into `seg 1/…`, which the runner
  emits at tick 0 — the POST returns 12–13 s earlier, because telemetry
  admission alone is three ~5 s bus scans.

A single incomplete `/api/feedback` scan also legitimately returns
`null` joint entries; treat that as telemetry noise and resample for
three *consecutive* clean 18/18 samples rather than crashing or limping.
