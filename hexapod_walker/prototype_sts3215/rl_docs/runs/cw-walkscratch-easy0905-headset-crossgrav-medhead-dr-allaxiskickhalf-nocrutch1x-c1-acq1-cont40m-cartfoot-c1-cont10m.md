# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T05:52:55+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1

**hypothesis**: Plain English: the Cartesian foot-decode arm re-acquired 0-fall walking in 2M but with 3-10x the matched control's slip -- was that the re-acquisition TRANSIENT (slip converges as training completes the semantics switch) or the parameterization's asymptote? +10M continuation of cartfoot-c1 (same cfg/RNG2, keys ride along), read against the matched offctrl-cont10m at equal 12M cumulative depth. Also resolves the unexplained monotone ep_rew decline (-61 -> -224) seen during the 2M re-acquisition.

**gate**: 24-ep walk/walk_startjitter det+sto gate at 12M cumulative vs offctrl-cont10m: PROMISING if gait_valid >= 18/24, 0 falls, and mean slip_per_m within 1.5x the control band in >=3/4 groups (clear convergence); FAIL-MECHANISM (close the retrofit form; remaining option is the fresh-init equal-footing test) if slip stays >3x the control in >=3/4 groups or gait_valid degrades below 18/24; in-between = one more read only if reward is RISING per the 08-21 ruling. Also report whether train reward reversed its decline.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

