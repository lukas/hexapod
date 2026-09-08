# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T06:22:39+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: xlzhnck1

**hypothesis**: Matched joint-space fresh-init control for cartfoot-freshinit-c1-s7 (same seed 7, byte-identical base-pilot recipe, no cart_foot keys) -- isolates whether any ignition-health difference is caused by the action decode rather than seed/recipe drift; also serves as an independent-seed replicate of the already-proven base-s0/s1 fresh-init arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as base-s0/s1 used, NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond settled stance on eval video/telemetry; motor contract sane (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY semantics bank (park~0, movement income positive, no opening-stop windfall). Read the ON/OFF pair TOGETHER: HEALTHY-PARITY if both show finite losses + real excursion + bank agreement (foot-space cold-starts as cleanly as joint-space); HEALTHY-BUT-INCONCLUSIVE if NEITHER shows excursion (matches base-s0 itself at 2M, needs continuation before any comparative claim); FAIL-MECHANISM-SPECIFIC if ON stays statue/degenerate while OFF ignites normally (joint-space cold-start advantage). No walking-quality claim at this depth either way.

**verdict**: CANARY PASS (mechanism-health tier): matches the base-s0/base-s1 reference pattern this bar was built on. rollout/ep_len_mean rises 101->223->353->488 ticks across the 4 quarters while per-tick env/reward_walk RISES 0.167->0.195->0.216->0.236 and env/v_along_cmd_m_s crosses zero (-0.0002->+0.0042->+0.0069->+0.0089) -- the total ep_rew_mean decline (-140->-551) is the SAME ep_len-growth artifact the 09-05 ~08:5x base-s0/s1 canaries showed, not reward regression. env/walk_speed holds 0.11-0.14 m/s throughout (real motion, not settled stance) and the walk_sto_1 frame strip shows genuine leg excursion/pose change frame-to-frame, not a statue. This is the joint-space (OFF, no cart_foot keys) fresh-init control for seed 7, byte-identical easy0905 base-pilot recipe -- it ignites exactly like the already-proven base family, confirming seed 7 itself is not unlucky. Next: the comparative ON-vs-OFF PARITY/FAIL-MECHANISM-SPECIFIC read for this exact seed needs the ON sibling cartfoot-freshinit-c1-s7 (still training this cycle, untouched) -- next reader pairs them once c1-s7 finishes. No walking-quality claim at this 2M depth (gate scope): walk/det shows 0/6 gait_valid, sac=[2] every episode, fwd~0.01m, expected/non-blocking per the gate's own no-walk-at-2M clause.

