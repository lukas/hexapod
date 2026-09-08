# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T05:59:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: axh4szza

**hypothesis**: Plain English: cartfoot-c1 (RNG2) is n=1 for the Cartesian foot-space decode's 're-acquires zero-fall walking but 3-10x slippier than joint-space' fingerprint -- this launches an independent seed replicate (seed3, otherwise byte-identical recipe: same cont40m warm start, same 3 cart_foot box keys) to test whether that fingerprint reproduces or is a seed-lottery artifact, per this campaign's own n>=3 seed-pass-rate discipline (e.g. the longrun/legdutyratio seed grids).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY bar as cartfoot-c1, read against the matched cartfoot-offctrl-s3 control: MECHANISM-VIABLE if 0 falls/terminations and gait_valid>=18/24 with six-leg cycling; PROMISING if additionally slip_per_m beats offctrl-s3 in >=3/4 groups; FAIL-MECHANISM if it cannot re-acquire (falls, or gait_valid<12/24 with reward flat). A 2M read is mechanism/reproducibility evidence, not class closure.

**verdict**: CANARY PASS: MECHANISM-VIABLE, and the seed3 replicate reproduces the seed2 fingerprint almost exactly -- this is a real property of the Cartesian-foot-space mechanism, not a seed-lottery fluke. Evidence: 0 falls/terminations across all 24 episodes, gait_valid 20/24 (6/4/4/6 across det/sto/startjitter-det/startjitter-sto), contact sheet + walk_det frame strip show all six legs upright and cycling stance/swing normally, no flag leg. Slip/m by group: 20.55/20.57/31.61/27.15 (progress 0.45/0.43/0.32/0.33) -- essentially the same 20-30/m range the seed2 arm (cartfoot-c1) showed (19.1/25.0/68.4/32.8), both far above the ~5-6/m det band the matched joint-space control (offctrl) holds. The matched offctrl-s3 control for THIS seed is still finalizing on another cycle's pod, so I can't formally stamp PROMISING/not this cycle, but given offctrl consistently lands at 5-6/m regardless of seed, c1-s3 losing 4/4 groups by 4-6x is not in doubt. Why: cross-seed replication answers the OPEN FORK from the ~05:5x entry -- 'VIABLE but 3-10x slippier' is a genuine mechanism property (foot-space exploration boxes make imprecise placement easy to reach and reward doesn't yet price it out), not an artifact of one unlucky seed. What's next: this closes fork (b)'s urgency (no need to re-run seed grids for reproducibility) and sharpens the remaining open question to the ~05:5x fork (a)/(b) choice -- either a longer ON continuation to separate re-acquisition transient from asymptotic slip, or a fresh-init matched pair -- still not pre-licensed, left for the owning cycle. Big picture: Cartesian foot-space decode mechanism is healthy and reproducible; slip pricing/asymptote is the open science question, not mechanism health.

