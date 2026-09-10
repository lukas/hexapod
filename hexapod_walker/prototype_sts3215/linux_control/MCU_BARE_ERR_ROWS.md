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
`"ERR"` (`replyErr()`), from two paths:

* `feedHostByte` `binState == 4` rejects a bad checksum / bad `n` and
  replies inline — that is a **corrupted** byte;
* `loop()`'s desync guard resets a `binState` left dangling by a
  **missing** byte, once `now - lastHostMs > HOST_BIN_DESYNC_MS`
  (**10 ms**). The test runs once per `loop()`, so behind a streaming
  pass the reply is delayed by up to about one `FB_PERIOD_MS`
  (**100 ms**).

All six rows land in the second path: 12.9–14.5 ms (spread **1.6 ms**)
and 103.8–104.2 ms (spread **0.44 ms**). So a byte went missing, and
none arrived corrupted.

Which byte is constrained too. All six frames were `n=0`, i.e. five
bytes (`A5 5A cmd 00 xor`) — note this is **not** the 113-byte `W`/`S`
case the firmware's RX-ring comment describes. Losing `A5` or `5A`
leaves the parser in ASCII mode, which yields `no_a5`, not `ERR`. Only
a loss among the trailing three bytes leaves `binState` dangling for the
guard to reset. So each event is a **single dropped byte**, host→MCU,
after the frame header was already accepted.

The discriminator against a marginal cable is the **direction
asymmetry**:

* MCU→host was byte-perfect in all six events — a clean `ERR\r\n`, and
  `pre_a5_hex` is exactly `455252` with nothing else in front of it.
* Across 2026-09-10 there is **no** `checksum_mismatch`, no
  `bad_header`, and no garbage `pre_a5` row, alongside thousands of
  checksum-verified `p`/`f`/`s` replies (run 1 of `9e65cca8` alone
  completed 1560/1560 ticks with zero error rows).

A marginal connector or bad ground corrupts **both** directions and
produces bit-flips — which would surface here as the inline
`checksum_or_bad_n` reject, and none occurred. Clean single-byte drops
in one direction only, answered on a firmware timer, are a host-byte
servicing race, not a connection fault.

**What this evidence does not pin down** is why that byte went missing.
The firmware names the plausible race itself — the hardware FIFO "can
overflow before `hostPump()` gets another chance to drain it", which is
why `loop()` refuses to enter a pass while `binState != 0`. Run 2 of
`9e65cca8` faulted under commanded motion, the highest pass load, once
in 1445 ticks. That is consistent but not proven by these artifacts; the
`desync_resets` counter below is the measurement that would settle it.

Finally, the `03:46:47Z` `W->OK ack_rejected` row the plan listed is a
`W n=18` frame — the 113-byte class — reaching the host through the
sync-write ack path rather than `_bin_txn`. Plausibly the same firmware
`ERR`, surfaced by different host code. Do not pool its timing with the
six above, and do not assume this note's conclusion covers it.

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
* **The `checksum_or_bad_n` band must not inherit this conclusion.** A
  bad checksum with every byte present is corruption, not loss, and is
  exactly what a marginal line would produce. None was seen on
  2026-09-10, so the classifier's "torn frame" label is right for
  today's data — but if that path starts appearing, re-open the cable
  question rather than reusing this note.
* **No transport retry.** A torn frame never executes, so retrying it is
  semantically safe, but any retry must still emit the row — suppressing
  it would silently bypass a guarded plan's stop policy.
