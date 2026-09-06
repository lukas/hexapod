# cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:46:40+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-medhead-widenfwd-c2-deferartifacts

**wandb_id**: inb67bzx

**hypothesis**: A 2nd independent seed of the medhead-widenfwd 1g forward-composition (already CANARY PASS 23/24, matching seed-1) holds at full 40M ACQ scale, same as seed-1's own ACQ PASS (21/24).

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg (every-episode) pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style chronic sacrifice emerges.

**verdict**: ACQ PASS -- 2nd independent seed of the medhead-widenfwd 1g forward-composition holds at full 40M ACQ scale. Evidence: aggregate gait_valid 21/24 (majority, gate floor >=18/24; walk/det 5/6 sac=[0] ep4 IDENTICAL episode+leg as the parent's own 23/24 canary flag, walk/sto 5/6 new non-chronic sac=[5] ep2, walk_startjitter/det 6/6, walk_startjitter/sto 5/6 new non-chronic sac=[0] ep5), 0 falls/terminations across all 24 episodes, no chronic single-leg (every-episode) pattern (leg0 flags 2/24 eps, leg5 1/24, never repeating within a mode). Slip/m improved vs parent canary in the noisiest mode (walk/sto med 8.58 vs 12.84), progress ratios comparable. Contact sheet + both newly-flagged episode frame strips show clean six-leg tripod cycling throughout, no drag/skate/paddle-creep/collapse. Matches the established precedent for this composition family (widen2c1-irrfwd-c1-acq1, s1acq-widenfwd-c1-acq1): cleanest-source-holds-composition at ACQ scale. Next: candidate for the standing cont40m endurance batch alongside its siblings (medhead-widenfwd-c1-acq1-cont40m, medhead-irrfwd-c1-acq1-cont40m already running).

