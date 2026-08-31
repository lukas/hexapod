# cw-standwalk-stage2-dualbc5-turncap-stdwalk-hi-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T07:43:26+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: dk3cd0vs

**hypothesis**: Plain English: sibling dose to stdwalk-mild (log_std -0.8, std~0.45) on the SAME direct-raise-the-walk-core's-exploration-noise lever -- this arm tests a bigger jump (log_std -0.2, std~0.82) in case a modest widen still isn't enough for PPO to stumble into the turning behavior within 2M steps but a much wider one is (or, if walking collapses at this dose, that itself bounds how far this lever can go). Same base (dualbc5_turncap), same bank-proven OMNI turn reward stack, same stance-core cooling (-4.0 over 50pct) via this cycle's new multi-core log-std-anneal code (plus the argv-parsing fix after the first attempt crashed pre-boot on a comma-list-vs-argparse-negative-number gotcha), isolating ONLY the dose on the walk-core target.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered): PASS if wz_med clears 0.03 in the commanded direction both signs; joint with the -mild sibling as a 2-point dose-response read. Also check env/train/std actually reached >=0.65 by 200k steps and walk_det frame-strip for gait collapse -- a PASS requires 6-leg cycling preserved, not turning via toppling.

**verdict**: CANARY FAIL - MECHANISM (joint with -mild sibling, 2-point dose-response, 6th+7th turn-authority mechanism classes refuted -- exploration MAGNITUDE now exhausted, see -mild verdict for full evidence text). This arm pushed the dose much further (log_std -1.5->-0.2, std 0.22->0.82 pinned by ~300k -- confirmed via env/train/std: 0.223 at 131k -> 0.52 at 262k -> 0.80 at 327k -> pinned 0.819 for the rest of the run, a genuinely huge action-noise widen, ~3.7x the parents std) to test whether a bigger jump than -mild would finally let PPO stumble into turning. It did not: probe_turn_authority (same 96-key own cfg, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) reads wz_med +0.0008/+0.0002 (wz_cmd=+0.25) and -0.0022/-0.0004 (wz_cmd=-0.25) -- if anything TIGHTER around zero than the -mild sibling, wz_p90_abs only 0.023-0.036, med|wz_err|=0.249, indistinguishable from full frozen-body. env/walk_yaw_kernel_factor erodes 0.41->0.08 (same shape as every prior canary); env/walk_wz stays pinned within +-0.01 the whole run DESPITE std=0.82 -- a policy exploring with 3.7x more action noise than the -mild arm shows literally no more wz variance during training, ruling out "not enough noise yet" at any practical dose. Reward crashes hard then partially recovers (quarters [53.5,43.2,-178.4,3.1], same shape as -mild and every sibling canary) -- not a rising-reward case. Own frame-strip (walk_det_0.mp4/.png pulled from train-2): straight-walk gait intact, no collapse, matching -mild -- the wider noise did not destabilize the base walking skill either, it simply never got redirected into turning. Conclusion (joint with -mild): a 2-point dose-response bracket (std 0.45 and 0.82, both confirmed-moved vs the untried 0.22 baseline) both land in the exact same near-zero wz band -- exploration MAGNITUDE at the action-noise level is REFUTED as the turn-authority bottleneck, cleanly, with a genuine dose gradient tested. NOT HARDWARE-READY. Evidence: logs/ckpt_eval/turn_probe_stdwalk_hi.json, wandb dk3cd0vs.

