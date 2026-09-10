# A bare-`ERR` `bus_timing` row is a torn frame, not a loose cable

Resolves the open item carried by experiments `376bea38` / `d4908236` /
`9e65cca8`: *"recurring host-MCU serial framing rows … cause is not
determinable from these artifacts"*, which left `9e65cca8` with a
`needs_inspection` safety disposition on 2026-09-10.

It **is** determinable from those artifacts. The rows are a protocol
reject from a live, responding MCU.

## The rows

Six on 2026-09-10, not the three the plan's `known_open_engineering_item`
listed. All six carry `reason=ascii_err`, `pre_a5_hex=455252`
(byte-exact `"ERR"`), `ascii_drains=1`, `pre_a5_lines=["ERR"]`, `n=0`:

| ts (Z) | cmd | `first_byte_wait_ms` |
|---|---|---|
| 00:01:54.623 | `F->f` | 104.230 |
| 00:38:33.170 | `F->f` | 104.209 |
| 00:49:23.607 | `S->s` | 103.794 |
| 03:00:34.289 | `P->p` | 14.480 |
| 04:30:29.324 | `P->p` | 13.351 |
| 05:14:30.087 | `P->p` | 12.904 |

The plan also listed `03:46:47Z`, but that row is
`W->OK ack_rejected`, a different reason — do not count it in this class.

## Why it is not the cable

`feetech_bridge.ino` answers a binary frame it cannot accept with a bare
`"ERR"` (`replyErr()`), from two paths, both meaning *this frame was torn
on the way in*:

* `feedHostByte` `binState == 4` rejects a bad checksum / bad `n` and
  replies inline;
* `loop()`'s desync guard resets a dangling `binState` once
  `now - lastHostMs > HOST_BIN_DESYNC_MS` (**10 ms**) and replies then.
  The test runs once per `loop()`, so behind a streaming pass the reply
  is delayed up to about one `FB_PERIOD_MS` (**100 ms**).

That predicts replies at ~10 ms, or ~10–110 ms when the guard sits behind
a pass. The measured waits are 12.9–14.5 ms (spread **1.6 ms**) and
103.8–104.2 ms (spread **0.44 ms**). Deterministic firmware timers, twice
over. A marginal connector produces a broad random spread and corrupt
bytes, not a byte-exact 3-byte token on a 0.44 ms-wide timer.

The tearing itself is already documented in the firmware: the host-UART
RX ring is smaller than one 113-byte `W`/`S` frame, so a frame landing
mid-acquisition-pass loses bytes. `hostPump()` exists to mitigate exactly
this. Run 2 of `9e65cca8` faulted under commanded motion, i.e. the
highest pass load — consistent, and it faulted once in 1445 ticks.

## What changed

`mcu_feetech_bus.classify_bare_err_reply()` annotates the trace with
`mcu_reply_err_bare`, `mcu_frame_reject_path`,
`mcu_torn_frame_suspected` and `mcu_desync_behind_stream_pass`.

**Annotation only.** `reason` stays `ascii_err`, the row stays
`kind=bus_timing`, `level=error`, `ok=false`, and every interlock keyed
on it — including a guarded plan's `api_errors_row` stop — behaves
exactly as before. A wait outside both firmware bands is reported
`unattributed` rather than being explained away.

## Not done here

* **`desync_resets` was not read.** `McuFeetechBus.debug_counters()`
  exposes the MCU's own counter but no HTTP route does, and reading it
  takes the serial bus lock — see `BUS_CONTENTION_LESSON.md`. Do not
  reset it; that destroys the running evidence.
* **No firmware change.** Making the desync guard emit a token distinct
  from an ASCII command failure would remove the ambiguity at the
  source, but needs a flash.
* **No transport retry.** A torn frame never executes, so retrying it is
  semantically safe, but any retry must still emit the row — suppressing
  it would silently bypass a guarded plan's stop policy.
