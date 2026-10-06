# rl_only lower-role terminal-stance: WHEN does the 2-leg habit form? (2026-10-06)

Zero-GPU, zero-retrain refill-cycle preflight (CPU MuJoCo eval only,
reused the already-adopted champion triple bit-exact: stance
`currentcap29-s5-klrollback05-acq15m`, walk `slew_smooth_s0`, lower
`lowerrole-scratch-sac-s0-drramp-acq1`). Tool: `eval_lifecycle_
handoff_rlonly.py --minload-trace-dir` (already built, no code
change). This is the "zero-GPU preflight" walkcurr/STATUS.md Next 3
requires before any canary spend on a genuinely new gait-phase/
contact-schedule mechanism against the converged L2+L5 terminal-
support habit. Question the terminal-support forensics doc
(2026-10-02) left open: that doc only inspected the LAST 100 ticks
(~2s) of 15s episodes and found L2+L5 dominant there at 13-17N vs <3N
elsewhere, identical in passing and failing episodes. It did not say
WHEN in the episode that concentration first appears — load-bearing
for a "isolate hold-phase practice" framing (already closed via
`lower_hold_only_frac`/decoupled terminal-hold specialist) assumed it
was a late-hold-specific skill gap.

## Method
Re-ran the exact `direct` n=18 seed=0 composed rise->walk->lower
capture with `--minload-trace-dir`, this time keeping the FULL
per-tick (750-tick, 15s @ 50Hz) `perleg_force_trace_n` for every
full-length episode (13/18; the other 5 truncate early on a fall) and
computing, per tick, the fraction of total body-support force carried
by the top-2 legs (`top2_share = sorted(force)[:2].sum() /
total_force`), averaged across all 13 full-length episodes.

## Finding: the concentration is near-immediate, not a late-hold drift
| t (s) | mean total force (N) | top-2-leg share of total |
|---|---|---|
| 0.0 | 4.5 | 0.23 |
| 1.0 | 33.7 | 0.84 |
| 2.0 | 34.4 | 0.77 |
| 3.0 | 35.0 | 0.88 |
| 5.0 | 34.7 | 0.82 |
| 8.0 | 33.7 | 0.89 |
| 10.0 | 35.1 | 0.88 |
| 12.0 | 32.9 | 0.92 |
| 14.0 | 34.2 | 0.92 |

Total support force is essentially flat (~33-35N, i.e. ~body weight)
from t=1s onward — the ramp (`goal.lower_ramp_s=5.0` on this lineage)
is still descending through t=1..5s, yet the 2-leg-dominant
distribution is ALREADY established (top2_share 0.77-0.88) within the
first second after initial ground contact, before the ramp is even
half done, and stays in the same 0.8-0.9 band for the entire remaining
~13s (ramp + hold) with no further narrowing trend. A naive per-leg
count at a loose 2N "loaded" threshold (not shown as a table here,
computed and inspected) looked noisier/showed 3-4 "active" legs
throughout — but those extra legs carry only a small residual share
(~10-20% of total split across 3-4 feet, ~1-3N each), consistent with
light stabilizing contact, not a materially different support
strategy. There is no "wide 4-leg stance during the ramp, abandoned
during hold" transient the way a coarse leg-count readout can suggest.

## What this closes / narrows
Confirms and SHARPENS (rather than overturns) the 2026-10-02 finding:
the L2+L5 habit is not a late-hold-phase skill gap at all — it is the
policy's essentially immediate, stable response to full ground contact,
present across the whole ramp+hold window alike. This removes the
remaining unstated premise behind any future "give it isolated
practice at the tail of the episode" framing (the explicit form,
`lower_hold_only_frac`/decoupled terminal-hold specialist, is already
closed in STATUS.md) — there is no distinct late-arriving sub-skill to
isolate; whatever drives the 2-leg choice is already fully determined
by ~t=1s, when the ramp is barely underway. A genuinely new mechanism
therefore cannot target "the hold phase" as a separate temporal regime
from "the ramp" — any contact-schedule intervention has to act from
the moment ground contact is re-established, not from a later hold-only
checkpoint, which makes a hold-phase-scoped (vs ramp-scoped) version of
any future lever a non-starter without a new argument.

## Next
Still UNSCOPED per walkcurr/STATUS.md Next 3 — no new lever identified
by this probe either, consistent with the 2026-10-04 hold-entropy
scoping doc's own conclusion (no exploration deficit, a converged
value-landscape optimum). This refines WHEN rather than WHETHER a
contact-schedule mechanism must act; it does not by itself justify a
canary. Evidence: `/tmp/lf_trace_full/minload/direct_*.json` (this
session's capture, rerunnable any time, zero GPU, ~3 min CPU, same
command as the 2026-10-02 doc with `--episodes 18 --seed 0`).
