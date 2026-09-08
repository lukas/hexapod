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

## Result

(to be filled in by the measurement — this README is committed before
the fullmesh run; the smoke run on the twin plant, 1 cell/6 s, only
validated mechanics: gain +1.5%, spread 30 ms, no verdict weight)
