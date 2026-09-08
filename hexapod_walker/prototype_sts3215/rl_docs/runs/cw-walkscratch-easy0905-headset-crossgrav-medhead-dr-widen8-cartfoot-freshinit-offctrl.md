# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T08:37:23+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**wandb_id**: xpuzkq3h

**hypothesis**: Matched fresh-init joint-space control for the cart_foot-freshinit-c1 canary above (same run, same 2M budget, IDENTICAL seed/DR/heading recipe, only the 3 walk_cart_foot_box_* keys removed). Isolates whether ignition/gait health on the harder widen8 8-way-heading + full crutch-off DR composite depends on the action-space swap or is just ordinary fresh-init-on-hard-DR difficulty -- every existing PASS/FAIL reference point for this composite (widen8-acq1 3/3 ACQ FAIL, all 19 reward-mechanism attempts) was a WARM START off a 5-way-heading base, never a fresh-init on the full 8-way+DR composite directly, so this control also tells us whether joint-space itself can even ignite from scratch at this difficulty.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: read together with the matched cart_foot-freshinit-c1 ON arm at the same budget. Same PASS/FAIL clauses as the ON arm (gait_valid majority + 0 falls + reward rising = PASS; chronic front-pair/single-leg sacrifice majority = FAIL regardless of reward trend). If this control ALSO fails to ignite (no majority gait_valid on any mode), the read is INCONCLUSIVE for the action-space question -- it would mean fresh-init-on-full-hard-DR is the harder variable, not the mechanism/action-space this pair was designed to isolate, and a milder fresh-init entry point would be needed before re-testing cart_foot.

**verdict**: CANARY FAIL - MECHANISM: matched joint-space (OFF) control for the widen8-cartfoot-freshinit-c1 pair. Machinery healthy (finite/decreasing losses 444->313, value_loss 948->679, std anneals on schedule, no blowup), 0 falls/terminations in all 24 episodes, gait_valid majority every mode (5/6,6/6,6/6,4/6), no chronic single-leg-sacrifice fingerprint (duty spread 0.29-1.0 across legs, leg0 does most of the cycling in every episode). But shows the SAME unproductive high-frequency buzz as its cart_foot (ON) sibling at nearly identical magnitude: slip/m 61-84 det / 93-291 sto, stride_m_mean 0.001, forward_dist 0.01-0.03m, per-tick env/reward_walk flat/noisy (0.174-0.192, no trend), env/v_along_cmd_m_s pinned near zero the whole run, env/walk_speed DECLINING (0.093->0.082) -- none of the clearly-rising reward_walk/v_along signal the healthy halfgrav/1g fork(b) pairs showed at the same budget. Confirms (see the ON arm's own verdict, same cycle) that this is a composite-difficulty failure to ignite forward progress from fresh random-weight init, common to BOTH action spaces, not a cart_foot-specific effect -- the pair's isolation question is answered (no differential effect), and the widen8+crossgrav+medhead-DR composite needs a milder fresh-init entry point before either action space is retested on it.

