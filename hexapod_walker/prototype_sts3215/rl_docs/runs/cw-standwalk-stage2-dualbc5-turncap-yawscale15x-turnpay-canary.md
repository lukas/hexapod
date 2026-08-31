# cw-standwalk-stage2-dualbc5-turncap-yawscale15x-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-31T09:00:16+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: vhgpzma8

**hypothesis**: Sibling dose to yawscale5x on the SAME reward-salience lever (see yawscale5x hypothesis for full text): raises k_walk_yaw and k_yaw_prog to 15.0 (vs the base 1.0, and 5x on the sibling) in case a modest 5x raise still leaves the turn income too small relative to the dominant walk reward channels (k_walk_prog=2.0/tick, anchor supervision, k_drag_stance=8000) to move PPOs advantage estimate, but a much larger raise finally does -- or, if the higher dose instead destabilizes/farms the base gait, that itself bounds how far this lever can go before causing more harm than good. Same dualbc5_turncap-turnpay-canary base/init-from, same bank-proven turn reward mechanism, same untouched stance-core log_std cooling, isolating ONLY the dose on the yaw-income weight target.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered): PASS if wz_med clears 0.03 in the commanded direction both signs; joint with the -yawscale5x sibling as a 2-point salience-response read. Also check env/reward_walk_yaw / env/walk_yaw_kernel_factor scale up roughly proportionally to the 15x weight (confirms the cfg multiplied through) and walk_det frame-strip for gait collapse -- a PASS requires 6-leg cycling and forward progress preserved, not a farmed/destabilized gait.

**verdict**: CANARY FAIL - MECHANISM: 15x salience dose (k_walk_yaw/k_yaw_prog 1.0->15.0) still produces ZERO real turn-in-place authority -- 8th mechanism class's high-dose arm FAILs the same as every prior class. Evidence: probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1, logs/ckpt_eval/turn_probe_yawscale15x.json) reads wz_med in [-0.0068,-0.0046] for wz_cmd=+0.25 (wrong sign, ~0) and [-0.029,-0.015] for wz_cmd=-0.25 -- both signs stay under the 0.03 floor, med|wz_err|=0.245 vs frozen-body prediction 0.25 -> the tool's own verdict is FROZEN-BODY. Mechanism check the gate demanded: env/reward_walk_yaw scaled proportionally with the weight (0.114 base -> 1.94 at 15x, ~17x, confirms the cfg multiplied through cleanly -- not a wiring bug), yet env/walk_yaw_kernel_factor stayed flat 0.07-0.09 (same band as base 0.088 and the 5x sibling 0.059) and env/yaw_prog_wz_avg stayed ~0 (-0.0018, no larger in magnitude than base/5x) -- more reward income bought zero behavior change. No falls in any probe (fell=false x4), so this is not a toppling-into-yaw confound. Why: matches the same-wave probe_yaw_credit finding (the critic's forward value barely reacts to toward/away wz noise) -- raising the reward's SIZE cannot fix a credit-assignment gap the critic itself does not propagate. What's next: per the STATUS 08-31 meta priority reorder, no 9th actor/critic-side RL mechanism class funds on this non-turning base -- the top-priority next step is auditing/fixing the dual-distill turn path itself (teacher wz~0.23 both signs -> dualbc5 pre-RL base ~0), started this cycle.

