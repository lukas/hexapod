# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl-narrowhead

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:38:38+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: cihv6dse

**hypothesis**: Plain English: matched joint-space (OFF) control for the c1-narrowhead arm launched alongside it. Same isolation: does shrinking the heading set from widen8's 8-way back to the original medhead 5-way (dropping the 135/-135/180 backward directions), with everything else byte-identical to the seed40 offctrl fresh-init recipe (full crossgrav/medhead DR, torque_scale=1,1, joint-space action decode), let a fresh-init policy ignite where the 8-way version just failed twice (seed40+seed41) and torque-crutch restoration also failed?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41/torqueretain arms: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up, env/v_along_cmd_m_s turning positive, env/walk_speed rising); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched c1-narrowhead sibling -- two arms agreeing is sufficient for a canary-level mechanism verdict.

