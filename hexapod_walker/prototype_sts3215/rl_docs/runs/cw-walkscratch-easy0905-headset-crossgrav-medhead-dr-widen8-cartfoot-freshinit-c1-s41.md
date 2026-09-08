# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-s41

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T08:41:58+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**wandb_id**: gafez8n2

**hypothesis**: 2nd independent seed replicate of the cart_foot-freshinit-c1 canary (train-0, seed40, launched this cycle): tests whether the mechanism-viability read (does the Cartesian foot-target action space ignite/avoid the chronic-sacrifice pathology on the fresh-init widen8 8-way-heading + full crutch-off DR composite) reproduces across seeds, matching every other canary pair in this campaign (fork(b) itself used n=2-3 seeds before calling a track-level result). Same recipe, only --seed differs (41 vs 40).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: read together with its own matched offctrl-seed41 sibling AND the seed40 pair. Same PASS/FAIL clauses (gait_valid majority + 0 falls + reward rising = PASS; chronic sacrifice majority = FAIL regardless of reward). Two independent seeds agreeing (either direction) is sufficient for a canary-level mechanism verdict; disagreement flags a DIG-IN before funding acquisition.

**verdict**: CANARY FAIL - MECHANISM: 2nd independent seed (41 vs 40) of the widen8-cartfoot-freshinit-c1 (ON) canary: REPRODUCES the seed40 pair's fingerprint exactly, closing the pre-registered n=2-seed agreement bar. Machinery healthy (loss 498->378, value_loss 1057->810, std anneals 0.368->0.218 on schedule, no blowup). 0 falls across all 24 gate episodes (only 2 safety terms, both in walk_startjitter/sto), gait_valid majority every mode (6/6,6/6,6/6,4/6), no chronic single-leg-sacrifice fingerprint (duty spread 0.54-0.99 across all six legs every episode, leg0 does the most swinging just like seed40 -- sacrificed_legs=[] in 22/24 eps). But the anticipated PASS signal never appears: per-tick env/reward_walk stays flat/noisy across all 4 quarters (0.181/0.197/0.186/0.171, no trend), env/v_along_cmd_m_s hovers near zero all run and ends NEGATIVE (-0.00066), and env/walk_speed actively DECLINES (0.102->0.105->0.099->0.091) -- opposite of the rising signal the healthy halfgrav/1g canaries show at this budget. ep_rew_mean's apparent collapse (-115->-528) is fully explained by ep_len_mean growing 105->488 (surviving longer accumulates more of the same near-zero/negative per-tick total, not a new failure mode). Gate eval confirms: slip/m med 94.07 det / 156.51 sto (3-10x the easy-rung cart_foot band), forward_dist 0.02-0.11m, stride_m_mean ~0.001 -- video (walk_startjitter/sto contact sheet) shows the body essentially stationary while legs buzz. This is the SAME composite-too-hard-to-ignite-from-fresh-init signature as the seed40 c1/offctrl pair (both already CANARY FAIL - MECHANISM), now independently reproduced on a 2nd seed for the ON arm -- per this pair's own gate text, two seeds agreeing is sufficient for a canary-level mechanism verdict (no disagreement, no DIG-IN). Do not relaunch this exact fresh-init widen8 recipe at either action space without a milder fresh-init entry point first (per the seed40 pair's ruling, unchanged).

