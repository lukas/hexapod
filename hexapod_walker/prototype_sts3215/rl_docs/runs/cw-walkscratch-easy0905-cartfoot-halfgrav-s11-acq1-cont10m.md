# cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T11:52:07+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1

**hypothesis**: Does the halfgrav cart_foot (ON) seed11 arm's 40M ACQ PASS (0 falls/24, speed 0.20-0.24 m/s, gait_valid 11/24, forward-only, systematic leg1 dropout in both det panels) hold, degrade, or recover at 10M more training, extending the cont10m depth check (seed7 held its band, this is a 3rd seed and the one whose ON advantage did NOT clearly beat its own OFF sibling at 40M).

**gate**: RETENTION at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 11/24 band, slip/m staying within +/-20% of the 40M read (1.61/1.58/1.50/1.69). Report whether the chronic leg1 det-mode dropout (12/12 episodes) persists, clears, or worsens -- this is the seed where ON did not show seed7/10's clear gait_valid advantage over OFF.

