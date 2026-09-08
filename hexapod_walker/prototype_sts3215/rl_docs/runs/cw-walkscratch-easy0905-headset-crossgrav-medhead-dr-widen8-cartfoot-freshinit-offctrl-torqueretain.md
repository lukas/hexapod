# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl-torqueretain

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:11:03+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: ammkxcg3

**hypothesis**: Plain English: matched joint-space (OFF) control for the c1-torqueretain arm launched alongside it. Same isolation: does restoring the 3x torque crutch (removed in the widen8 fresh-init recipe, dr.torque_scale 1,1->3,3) let a from-scratch joint-space policy ignite where the crutchoff recipe just failed twice (seed40+seed41, both CANARY FAIL - MECHANISM)? Byte-identical to the seed40 offctrl fresh-init recipe otherwise (same seed 40, same 8-way heading set, same full DR matrix, joint-space action decode).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41 pair: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up, env/v_along_cmd_m_s turning positive, env/walk_speed rising); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched c1-torqueretain sibling -- two arms agreeing is sufficient for a canary-level mechanism verdict, disagreement flags DIG-IN.

