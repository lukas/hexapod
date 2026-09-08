# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T05:59:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: axh4szza

**hypothesis**: Plain English: cartfoot-c1 (RNG2) is n=1 for the Cartesian foot-space decode's 're-acquires zero-fall walking but 3-10x slippier than joint-space' fingerprint -- this launches an independent seed replicate (seed3, otherwise byte-identical recipe: same cont40m warm start, same 3 cart_foot box keys) to test whether that fingerprint reproduces or is a seed-lottery artifact, per this campaign's own n>=3 seed-pass-rate discipline (e.g. the longrun/legdutyratio seed grids).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY bar as cartfoot-c1, read against the matched cartfoot-offctrl-s3 control: MECHANISM-VIABLE if 0 falls/terminations and gait_valid>=18/24 with six-leg cycling; PROMISING if additionally slip_per_m beats offctrl-s3 in >=3/4 groups; FAIL-MECHANISM if it cannot re-acquire (falls, or gait_valid<12/24 with reward flat). A 2M read is mechanism/reproducibility evidence, not class closure.

