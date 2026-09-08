# Event-based phase-synchronization SCREEN on the frozen full-mesh plant
# (todaypolicy steering, 2026-09-08) — PRE-REGISTRATION

Operator focus note (fb_20260908T043135_664da2 cycle): screen event-based
phase synchronization using actual per-leg joint lag/contact events, as
distinct from the CLOSED global cadence / lift-lead / posture / omega /
arm / governor / command-re-projection / fixed-duty time-multiplex levers.
Rule applied verbatim: "A phase mismatch alone is not support: earlier
timing improvements lacked body yaw gain." This is a bounded CPU
measurement (scripted TripodGait, zero training, zero robot work, no
plant/limit/gate changes) that must PREDICT a sign-consistent gain before
any mechanism is implemented.

Probe: `rl_move/sim/probe_turn_eventsync.py` (copy here after the run);
unit bank `rl_move/tests/test_probe_turn_eventsync.py` (9 tests, green
before the measurement). Plant/config identical to the stance-arm /
cadence / twistfit closures: frozen full-STL model (34 meshes,
4.80573 kg, 100 Hz, `hexapod_mesh.xml` sha 7efb8e8a…), corrected-audit
cfg_set, seed 0, 15 s, cells (0.08, ±0.15) + straight guard (0.08, 0),
starts 0/π, unchanged servo contract (write_speed 400, write_acc 20,
slew 0.375 deg/tick, ceiling 350). Executed in the isolated worktree
`/workspace/hexapod-turnphase-wt/`. Parity: body medians + tick count
must reproduce the stance-arm baseline BIT-EXACTLY per cell.

## Pre-registered support bar (written BEFORE the fullmesh measurement)

SUPPORTED only if ALL of:

- **S1 (predictive gain):** best-case event-sync counterfactual —
  every mixed/degenerate loaded-support tick re-performs like an
  average pure-tripod-support tick — predicts a wz gain in the
  COMMANDED direction ≥ +10% of the measured |wz| on ALL FOUR arc
  cells. (The counterfactual deliberately over-estimates any real
  re-phaser, since tripod handoffs cannot be zero-duration; failing
  even the upper bound is decisive.)
- **S2 (event-detectable leg-differential signal):** inter-leg
  touchdown-offset spread ≥ 50 ms on every arc cell, OR max per-leg
  sign-differential (same start, +wz vs −wz) ≥ 30 ms. Otherwise the
  contact-event feedback reduces to a COMMON phase shift — closed
  territory (cadence: fractional lag 0.29→0.21 yet yaw REGRESSED both
  signs; lift-lead: executed gait already self-aligned, ~215 ms uniform
  pipeline lag, no gain from re-timing lift).
- **S3 (health):** the same counterfactual on the straight cells stays
  ≤ 0.0074 rad/s |wz| (measured baseline drift cap), zero falls, and
  bit-exact parity per above.

UNSUPPORTED ⇒ record the negative here + RL_LOG, implement NOTHING (no
probe-local mechanism, no preflight, no canary), and scope the next
distinct evidence-based step per the focus note.

Prior-evidence context (why S2 is the crux): the lift-lead closure's
per-leg xcorr lag table already shows contact lag 200–230 ms uniform
across ALL six legs, both turn signs, and the straight cell (inter-leg
spread ~30 ms ≈ 4% of the 0.75 s period; sign-differential ≤ 20 ms on
contact events) — the event signal looked common-mode there. This probe
measures actual per-event touchdown/liftoff offsets (not xcorr) plus
support-state-conditioned yaw, which no prior artifact recorded.

## Result (measured 2026-09-08 ~05:1x UTC; 6 fullmesh cells, ZERO falls,
## parity 6/6 BIT-EXACT vs the stance-arm baseline, verdict mechanical)

**SUPPORT BAR NOT MET — event-based phase synchronization is CLOSED as a
steering mechanism on this plant, with NO probe-local mechanism, NO
preflight and NO canary (pre-registered rule).** `supported=false`
(`eventsync_fm.json:support_verdict`): S1 FAILED decisively; S2 passed;
S3 passed. S1 is the gate that matters:

- **S1 (predictive gain) FAILED by an order of magnitude:** the
  best-case counterfactual (every mixed/degenerate-support tick
  re-performs like an average pure-tripod tick) predicts only
  **+2.8% / +3.4% / +2.8% / +2.2%** yaw in the commanded direction on
  the four arc cells — bar was ≥ +10%, and the baseline's own
  start-to-start scatter is ±1.5%. There is almost nothing for a
  re-phaser to harvest: pure-support states already cover ~90% of
  scored ticks, and mixed-state wz (≈0.029) sits near the overall mean
  (≈0.039), not far below it.
- **S2 (leg-differential signal) PASSED — which sharpens the negative.**
  At start π exactly one leg lands ANTI-PHASED (leg 4 for +wz at
  −120 ms vs the +205 ms common lag; mirror leg 2 for −wz at −110 ms;
  spreads 340/330 ms), a genuine, repeatable (IQR = 0) per-leg contact
  event mismatch. Yet those very cells' achieved yaw is NOT worse than
  the well-aligned start-0 cells (+0.0632 vs +0.0642; −0.0651 vs
  −0.0631 — the anti-phased −wz cell is the BEST of the four). This is
  the focus note's "a phase mismatch alone is not support" realized in
  data: gross per-leg event misalignment does not map to yaw loss.
  Outside that one leg the event signal is COMMON-MODE: per-leg
  touchdown offsets 190–220 ms, spread 20–30 ms (~3–4% of the 0.75 s
  period), sign-differential ≤ 20 ms, identical in the straight cell —
  contact-event feedback carries essentially no turn-direction
  information, so an event synchronizer collapses to the CLOSED common
  phase/cadence shift (cadence: lag 0.29→0.21 frac, yaw REGRESSED both
  signs).
- **S3 PASSED:** straight-cell counterfactual |wz| 0.0019/0.0004 ≤
  0.0074 cap; zero falls; parity bit-exact (body medians + 1300 ticks,
  all six cells).

Side observation (recorded, no claim of mechanism): turn conversion is
strongly tripod-dependent and sign-mirrored. In straight cells the two
tripods produce a structural ±0.036 rad/s yaw oscillation that cancels;
under a turn command the increment over that structural value is ~+0.064
during one tripod's support and only ~+0.018 during the other's
(mirrored for −wz; both starts). Mixed-support (handoff) ticks also
stall translation (vx_mean ≈ −0.002 vs 0.031–0.042). These are
conditional means over alternating dynamic states — descriptive, not
causal localization.

## Next distinct step (scoped, NOT launched)

Per the focus note's fallback ("otherwise document negative and scope a
new distinct evidence-based step"): the only unexplored, measured
residual this screen surfaced is the TRIPOD-ASYMMETRIC TURN CONVERSION
above (0.064 vs 0.018, sign-mirrored, reproduced at both starts). A
future bounded probe could measure per-foot yaw-moment impulses split
by tripod support state to test whether the poorly-converting tripod's
contribution is recoverable at all (it may be the same structural
oscillation seen in the straight cells, in which case it nets out and
is NOT a lever — the straight-cell decomposition suggests exactly
that). No gait dial is proposed; phase/cadence/lift/arm/omega/amplitude
/duty-slice levers are all closed. Scratch 042639's learned
foot-placement line is unaffected and remains the live steering owner.

Files: `eventsync_fm.json` (full per-cell events + support states +
mechanical verdict), `probe_turn_eventsync.py` (probe copy, committed
at `rl_move/sim/probe_turn_eventsync.py` 2858d37f), controller logs at
`logs/ckpt_eval/turn_eventsync_20260908/`.
