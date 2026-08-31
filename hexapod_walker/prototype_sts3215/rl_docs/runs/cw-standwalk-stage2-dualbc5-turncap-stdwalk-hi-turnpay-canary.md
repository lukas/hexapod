# cw-standwalk-stage2-dualbc5-turncap-stdwalk-hi-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-31T07:29:21+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**hypothesis**: Plain English: sibling dose to stdwalk-mild (log_std -0.8, std~0.45) on the SAME direct-raise-the-walk-core's-exploration-noise lever -- this arm tests a bigger jump (log_std -0.2, std~0.82) in case a modest widen still isn't enough for PPO to stumble into the turning behavior within 2M steps but a much wider one is (or, if walking collapses at this dose, that itself bounds how far this lever can go). Same base (dualbc5_turncap), same bank-proven OMNI turn reward stack, same stance-core cooling (-4.0 over 50pct) via this cycle's new multi-core log-std-anneal code, isolating ONLY the dose on the walk-core target.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered): PASS if wz_med clears 0.03 in the commanded direction both signs; joint with the -mild sibling as a 2-point dose-response read. Also check env/train/std actually reached >=0.65 by 200k steps and walk_det frame-strip for gait collapse -- a PASS requires 6-leg cycling preserved, not turning via toppling.

