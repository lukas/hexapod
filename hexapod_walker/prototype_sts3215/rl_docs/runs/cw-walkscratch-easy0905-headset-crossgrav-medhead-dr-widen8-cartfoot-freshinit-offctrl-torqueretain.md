# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl-torqueretain

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T09:11:03+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: ammkxcg3

**hypothesis**: Plain English: matched joint-space (OFF) control for the c1-torqueretain arm launched alongside it. Same isolation: does restoring the 3x torque crutch (removed in the widen8 fresh-init recipe, dr.torque_scale 1,1->3,3) let a from-scratch joint-space policy ignite where the crutchoff recipe just failed twice (seed40+seed41, both CANARY FAIL - MECHANISM)? Byte-identical to the seed40 offctrl fresh-init recipe otherwise (same seed 40, same 8-way heading set, same full DR matrix, joint-space action decode).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41 pair: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up, env/v_along_cmd_m_s turning positive, env/walk_speed rising); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched c1-torqueretain sibling -- two arms agreeing is sufficient for a canary-level mechanism verdict, disagreement flags DIG-IN.

**verdict**: CANARY FAIL - MECHANISM, matched joint-space (OFF) sibling of c1-torqueretain, same read: restoring the 3x torque crutch does not ignite this composite either. Machinery healthy (finite/decreasing loss, std anneal on schedule, gait_valid majority every mode 6/6,6/6,5/6,5/6, no chronic single-leg-sacrifice majority; 1 safety termination out of 24 episodes, tilt_roll in walk/sto/4). env/reward_walk flat/noisy (0.177/0.191/0.188/0.192), env/v_along_cmd_m_s pinned near zero (0.0032->0.0004, no clear positive trend), env/walk_speed DECLINES (0.135->0.131->0.120->0.105) -- same shape as the crutch-off seed40/41 pair and its ON torqueretain sibling. Gate: slip/m med 73-168, fwd progress near-zero. Two arms agreeing (this + c1-torqueretain) is sufficient per the pre-registered gate: torque-crutch restoration does not rescue ignition on the widen8 8-way-heading+full-DR fresh-init composite at either action space. This closes the torque-crutch hypothesis; do not relaunch a torque-scale variant of this exact composite. Next candidate bisection (heading-only or DR-only) is a genuinely new question, not a filler retry.

