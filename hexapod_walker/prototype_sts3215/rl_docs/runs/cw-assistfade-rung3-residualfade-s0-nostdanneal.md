# cw-assistfade-rung3-residualfade-s0-nostdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T14:26:59+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: gp7oxefj

**hypothesis**: Rung 3's residual-fade mechanism failed 6/6 arms (bare, stdslow denom-3.0, latehandover t1=1.7M, longbudget 6M) via one consistent root cause: the blend anneal (ref->raw authority handover, 0.05->1.0 over 1.4M/2M steps) races the log_std anneal (--log-std-final -3.0 --log-std-anneal-frac 1.0, same 2M-step clock) to their floors together, so by the time the policy must stand on its own it also has almost no exploration noise left to adapt with (train/std ~0.37->0.09->0.05 in lockstep with blend->1.0). Every named fallback so far only SLOWED the std decay (stdslow: denom 6M vs 2M, ~1/3 of the way to floor) or moved the BLEND schedule (latehandover/longbudget) -- none has tried fully DISABLING the forced std anneal (drop --log-std-final/--log-std-anneal-frac entirely, reverting to PPO's own natural per-step-learned log_std with no external schedule at all), which removes the collision's second half completely rather than just slowing it. Single lever vs the ORIGINAL failed rung3-residualfade-s0/s1 canary: --log-std-anneal-frac/--log-std-final dropped, every other byte (blend schedule t1=1.4M, reward stack, random-weight init, 2M budget) identical.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, same ignition bar as every rung3 sibling (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating, zero falls/safety terminations, progress_ratio>=0.35 on all modes. Must override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from eval cfg-set) at eval time. PASS-IF-TRUE: ignition clears AND wandb_history.csv shows reward NOT declining through the last ~0.6M settling-window steps (the exact shape that flagged every prior FAIL) -- confirms the std-anneal collision was the true blocker, not the phase-sv-contact reward diet itself, and reopens rung 3 as a viable ladder rung. FAIL-if: same declining-reward-through-settling-window shape and/or same ignition miss as the 6 prior arms -- closes the std-anneal axis too, leaving the diet itself (per rung4's own closure) as the shared blocker across rungs 2-4 and licensing a track-level DONE-NEGATIVE writeup (walkcurr-style) rather than a 7th schedule variant.

**verdict**: CANARY FAIL - MECHANISM: dropping the forced log_std anneal (--log-std-final/--log-std-anneal-frac entirely absent, PPO's own per-step log_std only) does NOT rescue rung 3. Ignition bar missed on every axis: walk/det gait_valid 0/6 (all 6 sac legs [0,3], all 6 TERM over_current) despite a deceptively high prog med 0.57 (2-leg-sacrifice high-raw-progress shuffle, not six-leg gait); walk/sto gait_valid 3/6, startjitter modes 2/6. wandb_history.csv shows the SAME pre-registered FAIL shape: reward peaks ep~200 (~180-220) then declines through the back half to 45 final (quarters [101.9,176.8,158.0,114.5]), in lockstep with env/walk_loadslip_ratio climbing 0.2->5.0 and terminations/over_current climbing 0->15/round -- policy drifts into a high-slip, high-current, leg-sacrificing regime exactly like every prior rung-3 arm, just without the std-anneal collision. This was the last genuinely untried rung-3 lever (schedule-collision root-cause fully ruled out); see s1-nostdanneal for the seed-pair replicate.

