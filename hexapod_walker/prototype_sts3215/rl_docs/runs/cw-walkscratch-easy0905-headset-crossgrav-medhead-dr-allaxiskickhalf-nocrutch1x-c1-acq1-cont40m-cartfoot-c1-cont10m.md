# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-08T05:53:34+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1

**wandb_id**: qay6bggy

**hypothesis**: Plain English: the Cartesian foot-decode arm re-acquired 0-fall walking in 2M but with 3-10x the matched control's slip -- was that the re-acquisition TRANSIENT (slip converges as training completes the semantics switch) or the parameterization's asymptote? +10M continuation of cartfoot-c1 (same cfg/RNG2, keys ride along), read against the matched offctrl-cont10m at equal 12M cumulative depth. Also resolves the unexplained monotone ep_rew decline (-61 -> -224) seen during the 2M re-acquisition.

**gate**: 24-ep walk/walk_startjitter det+sto gate at 12M cumulative vs offctrl-cont10m: PROMISING if gait_valid >= 18/24, 0 falls, and mean slip_per_m within 1.5x the control band in >=3/4 groups (clear convergence); FAIL-MECHANISM (close the retrofit form; remaining option is the fresh-init equal-footing test) if slip stays >3x the control in >=3/4 groups or gait_valid degrades below 18/24; in-between = one more read only if reward is RISING per the 08-21 ruling. Also report whether train reward reversed its decline.

**verdict**: Fork (a), read against its own pre-registered gate vs the matched cartfoot-offctrl-cont10m control (also verdicted this cycle, PASS, slip 5.09-5.77/m band). cartfoot-c1-cont10m at 10M cumulative: gait_valid 19/24 (5/4/4/6), 0 falls/terms in 24/24 -- clears the gait/no-fall floor -- but slip/m median 13.22/17.35/14.11/17.03 is 2.6-3.3x the control in ALL 4/4 groups, nowhere near the <=1.5x PROMISING bar (0/4 groups pass). Train reward fell the entire continuation (quarters -150.6 -> -397.1 -> -521.0 -> -576.3): decline is decelerating but never reverses, so the gate's own 'one more read only if reward is RISING' escape clause does not apply. It does not literally cross the numeric FAIL-MECHANISM line either (only 1/4 groups, not >=3/4, exceed 3x; gait_valid stays above 18/24), but with no rising-reward license for a further read and slip stuck 2.6-3.3x worse than the matched control after 10M extra steps, continuing this exact retrofit form is not justified. Closing fork (a) as not-promising; per the pre-registered OPEN FORK, the remaining option is fork (b): fresh-init cart-foot vs fresh-init joint-decode control at equal budget, which still needs its own design pass (the recipe was itself only ever reached via a long continuation chain, so a naive fresh pair at this exact recipe risks conflating 'neither parameterization learns this from scratch' with a mechanism result).

