# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T11:01:34+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-s1

**hypothesis**: Second seed of the sde+halfgrav survival-duration pricing fix. Plain English: sde+halfgrav arms learn to sprint ~0.7s then belly-flop because dying costs 10x less than the sprint pays; this arm charges early death in proportion to forfeited survival time so the same recipe should learn to stay up instead. Mirrors remcost-s0's fix on the s1 seed (fresh 40M from-scratch, cell design unchanged, same two default-off keys bank-proven in test_walkscratch_easy_pilot.py 17/17). Prediction-if-true: ep_len_mean climbs toward the 500-tick truncation instead of plateauing at sdehalfgrav-s1's 65-84-tick fingerprint, with v_along_cmd sustained rather than burst. Prediction-if-false: policy retreats to the ~0-income park basin (ep_len pins ~500, walk_speed ~0) -- meaning the cell's problem is gSDE x 0.5g exploration, not pricing.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: judge alongside remcost-s0 -- both climbing ep_len past the 65-84 tick fingerprint = fix confirmed, extend the cell; both park-pinned at ~0 income = exploration problem, stop funding sde+halfgrav.

**refused_reason**: a process for cw-walkscratch-easy0905-sdehalfgrav-remcost-s1 already exists on hexapod-mjx-train-7

