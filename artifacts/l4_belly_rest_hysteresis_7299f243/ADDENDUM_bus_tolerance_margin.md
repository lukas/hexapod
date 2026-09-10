# Addendum — the reviewed one-row `bus_timing` tolerance is marginal for a 156 s run

This is an engineering observation from experiment `7299f243`, recorded for the
follow-up analysis job. **It is not a licence to widen the interlock, and this
experiment did not widen it.**

## What happened

Run 1 halted at 16:47:45.294Z on the plan's own stop condition — "any new
`/api/errors` row **beyond a single self-recovered transient bus_timing
retry**". Two rows arrived inside the 156 s window:

| # | ts | msg | disposition |
|---|---|---|---|
| 1 | 16:45:59.694Z | `P->p ascii_err 15.8ms` | TOLERATED (self-recovery confirmed) |
| 2 | 16:47:45.294Z | `P->p ascii_err 15.1ms` | HALT — allowance already spent |

Both are the *same* class the plan names as tolerable: `bus_timing`, `src` mcu,
`level` error (not critical), `reason` `ascii_err` with `n = 0`, bare `ERR`
reply attributed by `classify_bare_err_reply()` to the documented
`desync_guard` torn-frame reject path. Only the **count** exceeded the
allowance. The run reached ~126 s of 156 s (1230 of 1560 CSV rows).

## Why two rows is an ordinary outcome, not a new fault

Inter-arrival gaps between this robot's recent `mcu` `bus_timing` rows:

- **idle:** 879, 332, 280, 4686, 1932 s
- **during run 1:** 72 s, 106 s

The difference is traffic, not health. Idle traffic is only the low-rate
status/feedback polls (`S->s`, `F->f`). A sysid run adds the executor's own
**10 Hz position poll** — on the order of 1560 extra bus transactions across
the window — and *both* run-1 rows were `P->p`, i.e. on exactly that poll path.
At a roughly constant per-transaction torn-frame rate, the expected number of
rows per 156 s run is around 1. A tolerance of exactly 1 therefore sits right
at the distribution's mean, so a halt is likely on a material fraction of runs.

Treating the per-run count as Poisson with mean ≈ 1 gives ≈ 26 % chance of
≥ 2 rows in any single attempt — which matches this family's observed history
rather than contradicting it:

| run | allowance spent | outcome |
|---|---|---|
| L0 `881677a0` | 1 of 1 | completed 1560/1560 |
| L1 (run 2) | exceeded | **halted** on this interlock at 05:14:30Z |
| L3 `7b565e2a` | 1 of 1 | completed |
| L3 `022f2098` | 0 of 1 | completed, zero rows |
| L4 run 1 | exceeded | **halted** |
| L4 run 2 | see `summary.md` | — |

So this interlock has now halted 2 of 6 runs in the family — close to the ~26 %
the traffic argument predicts, and the L1 halt happened at the *same point of
the same reviewed trajectory* and was recovered the same way (re-pose, retry).

## What this does and does not justify

**Does not justify:** widening the tolerance inside this experiment. The
one-row allowance is reviewed, it is the plan's own written stop, and it fired
correctly both times. Weakening a safety interlock to obtain a result is not
available, and the retry here ran the identical protocol under the identical
guard.

**Does justify raising, as a separate question:** the interlock currently
conflates *how many torn frames occurred* with *whether the bus is unhealthy*.
Every row observed in this family has been the same self-recovering
`desync_guard` torn frame with `n = 0`, and in run 1 the bus was demonstrably
fine afterwards (`bus_available` true, not quarantined, 18/18 servos, and the
executor kept ticking to 1230 rows). Candidate directions for the analysis job,
each needing its own review:

1. **Rate-based rather than count-based.** Tolerate torn frames at up to some
   rate (e.g. ≤ 1 per 60 s) with the existing per-row self-recovery
   confirmation, instead of a fixed budget of 1 per run regardless of run
   length. A 156 s run and a 20 s run currently get the same budget.
2. **Fix the source instead of the tolerance.** The rows are torn frames on the
   host↔MCU serial link (`MCU_BARE_ERR_ROWS.md`, commit `c1f8067c`). Reducing
   the torn-frame rate — or making the executor's `P->p` poll retry a torn
   frame without emitting an `/api/errors` row when it self-recovers within the
   same tick — removes the problem rather than tolerating more of it.
3. **Leave it alone and accept retries.** The interlock is cheap to hit and
   cheap to recover from (re-pose + retry, ~5 min), and it is genuinely
   protective for row classes that are *not* self-recovering torn frames.
   Accepting ~1 retry per 4 runs may simply be the right trade.

Direction 2 is the only one that improves both safety and throughput, and it is
the recommended one. Nothing here should be actioned without its own review;
the protocol, its parameters and its interlocks are unchanged by this addendum.
