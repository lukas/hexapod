# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CONTINUE

**created**: 2026-09-05T10:49:01+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-s0

**wandb_id**: nzt9ygav

**hypothesis**: Plain English: the sde+halfgrav arms learned to sprint for ~0.7s and belly-flop because dying costs 10x less than the sprint pays; this arm charges early death in proportion to the survival time it forfeits, so the same recipe should learn to stay up and walk instead. Fix = reward.term_cost_per_remaining_s=100 + term_cost_max=450 on the unchanged sdehalfgrav recipe, fresh 40M (from-scratch is the cell design; both keys default-off, bank-proven in test_walkscratch_easy_pilot.py 17/17: scripted sprint_fall twin +64.7 vs park +0.2 under the launched flat-24 diet REPRODUCES the exploit, -385.3 under the fix, survivors bit-exact; reward.alive rejected - it re-prices the park basin positive, the documented freeze-and-collect class). Prediction-if-true: ep_len_mean climbs toward the 500-tick truncation instead of plateauing at 65-84 ticks, with v_along_cmd sustained rather than burst. Prediction-if-false: policy retreats to the ~0-income park basin (ep_len pins ~500, walk_speed ~0) - meaning the cell's problem is gSDE x 0.5g exploration, not pricing, and the cell stops getting funded. Strongest alternative: partial - longer bursts (ep_len up 2-3x) that still fall, meaning the dose is right but the recipe cannot find a stable gait at 0.5g.

**gate**: Acquisition milestone at OWN physics (0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Secondary (fix-specific): ep_len_mean escapes the 65-84-tick plateau. Not met with signals rising = continue/realign per 08-21; FAIL on park-recapture (ep_len ~500 with walk_speed ~0 and flat reward) or flat everything.

**verdict**: ACQ CONTINUE: the survival-duration fix (term_cost_per_remaining_s) worked exactly as designed -- terminations/tilt_pitch+tilt_roll drop from 800-1600 down to 187-212 (out of 4096 envs) across 40M, ep_len_mean escapes the 65-84-tick plateau all the way to 1033/1034 (near-truncation), v_along_cmd rises 0.01->0.116, det gate shows 0/12(6) falls, fwd 3.34m/20s (0.17 m/s, well above the 0.03 bar), slip 1.86 (under the 2.9 band). BUT gait_valid is 0/6 det and 0/6 sto in every single episode: legs [1,4] are chronically sacrificed (duty<0.10 or 0-swing) in every det trial, confirmed on the contact-sheet frames (two legs permanently retracted while the other four skate the body forward) -- the same LEGPARK-SKATE fingerprint already class-confirmed on sde-s1-c2/s2-c2/sde-s0-c4 and on the sibling remcost-s1 (identical sac-leg IDs, identical pathology). Stochastic mode is worse: all 6 sto episodes TERM tilt_roll, fwd collapses to 0.14m/20s. ep_rew_mean is negative and drifting further negative (-650->-1087) purely because reward_walk_freeprog_pen (~-2.3 to -2.75/tick, dominant term) accumulates over a much longer surviving episode -- not evidence of a training regression, the termination-avoidance incentive (term_cost) still clearly dominates the marginal per-step decision (falls keep dropping, ep_len keeps rising). Per 08-21 ruling this is realign-not-stop: the remcost fix solved the SURVIVAL exploit it targeted but the walk reward is still misaligned on LEG UTILIZATION, which is exactly the gap the concurrent sde-*-c3gg gait-gate-bank repair pair is already addressing on the sde recipe. remcost-s0/s1 (sdehalfgrav+remcost) should get the same structural gait-gate repair before another acquisition spend; no further budget on this exact recipe until that lands.

