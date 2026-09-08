# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T11:51:15+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1

**hypothesis**: Matched joint-space (OFF) control for the seed11 cont10m durability read above: does this arm's own 40M performance (0 falls/24, speed 0.17-0.21 m/s, gait_valid 10/24, near-parity with ON's 11/24) hold, degrade or diverge from ON at 10M more steps -- seed11 is the outlier pair (near-parity, not a real ON/OFF gap at 40M), so this depth read tests whether the gap opens up late like seed7's did, or the near-parity holds.

**gate**: MATCHED CONTROL: read together with s11-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read (1.82/1.89/1.83/1.94). Report whether the near-parity gait_valid (10/24 vs ON 11/24) holds, or a gap opens at depth like seed7 showed (22/24 vs 10/24).

