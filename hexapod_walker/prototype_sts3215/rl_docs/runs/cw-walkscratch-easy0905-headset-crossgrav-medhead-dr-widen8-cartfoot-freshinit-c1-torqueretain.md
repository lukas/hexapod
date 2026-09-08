# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-torqueretain

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:08:57+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: lqeww3mi

**hypothesis**: Plain English: does restoring the 3x torque training-wheels crutch (removed in the widen8 fresh-init recipe) let a from-scratch policy ignite forward progress on the same 8-way-heading+full-DR composite that just FAILED to ignite twice (seed40+seed41, both CANARY FAIL - MECHANISM: flat reward_walk, declining walk_speed, near-zero v_along, all with crutchoff torque_scale=1,1)? Isolates ONE variable: dr.torque_scale 1,1->3,3, everything else byte-identical to the seed40 fresh-init recipe (same seed 40, same 8-way heading set, same full DR matrix, same cart_foot action space). If ignition appears (reward_walk trending up, v_along turning positive, walk_speed rising instead of falling), the torque crutch removal -- not heading/DR breadth -- was the ignition blocker, matching the known mature-checkpoint finding that torque1x alone creates new chronic-leg pathology. If it still fails to ignite, the blocker is heading/DR breadth instead and a heading-only or DR-only bisection is the next rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41 pair: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up across quarters, env/v_along_cmd_m_s turning positive, env/walk_speed rising, not the flat/declining shape both failed arms showed); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched offctrl-torqueretain sibling (launched together) -- two arms agreeing is sufficient for a canary-level mechanism verdict, disagreement flags DIG-IN.

