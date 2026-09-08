# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T06:29:51+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**wandb_id**: b3piakh6

**hypothesis**: 3rd-seed replicate (n=3 with s7 + the concurrent base-cartfoot-fresh-s10) of the cartfoot fresh-init fork (b) question: does the Cartesian foot-space decode bootstrap walking from a random policy as cleanly as the joint-space decode on the proven-from-scratch easy0905 base recipe? Same predictions as s7's hypothesis (this cycle, ~06:2x): TRUE = finite losses/real excursion/bank agreement matching base-s0..s4; FALSE = statue/degenerate at 2M while the matched offctrl-s11 ignites normally; alternative = neither ignites (matches base-s0's own 2M history), inconclusive for cold-start comparison.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as base-s0/s1/s7 used, NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond settled stance on eval video/telemetry; motor contract sane; reward agrees with the WALKSCRATCH_EASY semantics bank. Read the seed7/seed10/seed11 ON arms TOGETHER for an n=3 ignition-health seed-pass-rate read, each against its own matched OFF control where available (s7, s11): HEALTHY-PARITY if all/most ON arms show finite losses + real excursion + bank agreement matching their OFF controls/base-s0..s4; HEALTHY-BUT-INCONCLUSIVE if none show excursion (matches base-s0 itself at 2M); FAIL-MECHANISM-SPECIFIC if ON arms systematically stay statue/degenerate while OFF controls ignite normally. No walking-quality claim at this depth.

**verdict**: CANARY PASS - HEALTHY-PARITY (mechanism-health tier): 2nd seed of the ON (cart_foot-space) fork (b) pair ignites like its matched OFF control (offctrl-s11, verdicted this cycle) and the base-s0/s1/seed-7 pair. rollout/ep_len_mean rises 104->236->357->493 ticks while per-tick env/reward_walk RISES 0.178->0.200->0.229->0.250 and env/v_along_cmd_m_s crosses zero upward the whole run (+0.0051->+0.0037->+0.0094->+0.0125). env/walk_speed holds 0.12-0.15 m/s throughout; walk_sto_2 frame strip shows real leg lift/place, not a statue. Total ep_rew_mean decline (-133->-570) is the same ep_len-growth artifact. HEALTHY-PARITY for seed 11 completes n=2 (s7+s11) matched-pair ignition coverage for fork (b), both showing NO cold-start disadvantage for the cart_foot decode vs joint-space. No walking-quality claim at 2M: walk/det 0/6 gait_valid, sac=[0,3] every episode, expected/non-blocking.

