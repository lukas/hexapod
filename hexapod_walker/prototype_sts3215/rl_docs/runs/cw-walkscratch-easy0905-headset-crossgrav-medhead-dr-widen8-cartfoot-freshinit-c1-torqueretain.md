# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-torqueretain

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T09:08:57+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: lqeww3mi

**hypothesis**: Plain English: does restoring the 3x torque training-wheels crutch (removed in the widen8 fresh-init recipe) let a from-scratch policy ignite forward progress on the same 8-way-heading+full-DR composite that just FAILED to ignite twice (seed40+seed41, both CANARY FAIL - MECHANISM: flat reward_walk, declining walk_speed, near-zero v_along, all with crutchoff torque_scale=1,1)? Isolates ONE variable: dr.torque_scale 1,1->3,3, everything else byte-identical to the seed40 fresh-init recipe (same seed 40, same 8-way heading set, same full DR matrix, same cart_foot action space). If ignition appears (reward_walk trending up, v_along turning positive, walk_speed rising instead of falling), the torque crutch removal -- not heading/DR breadth -- was the ignition blocker, matching the known mature-checkpoint finding that torque1x alone creates new chronic-leg pathology. If it still fails to ignite, the blocker is heading/DR breadth instead and a heading-only or DR-only bisection is the next rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41 pair: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up across quarters, env/v_along_cmd_m_s turning positive, env/walk_speed rising, not the flat/declining shape both failed arms showed); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched offctrl-torqueretain sibling (launched together) -- two arms agreeing is sufficient for a canary-level mechanism verdict, disagreement flags DIG-IN.

**verdict**: CANARY FAIL - MECHANISM per the pre-registered bisection gate: restoring the 3x torque training-wheels crutch (dr.torque_scale 1,1->3,3, byte-identical seed40 widen8-cartfoot-freshinit ON recipe otherwise) does NOT ignite forward progress. Machinery healthy (finite/decreasing loss, std anneal on schedule, 0 falls in all 24 gate episodes, gait_valid majority every mode 6/6,6/6,6/6,5/6, no chronic single-leg sacrifice). But env/reward_walk stays flat/noisy across quarters (0.185/0.171/0.173/0.179), env/v_along_cmd_m_s stays pinned near zero and ends slightly negative (0.0036->-0.0002), env/walk_speed actively DECLINES (0.148->0.145->0.130->0.120) -- the same flat/declining fingerprint as the crutch-off seed40/41 pair, not the rising signal that would indicate the torque crutch was the blocker. Gate: slip/m med 97-160 (3-10x the easy-rung band), fwd progress near-zero per 20s episode, contact-sheet strip shows the body essentially stationary. Read together with the matched offctrl-torqueretain sibling (also FAIL, same cycle) -- two arms agreeing closes this rung: torque-crutch removal is NOT the ignition blocker for this composite. The blocker is heading/DR breadth itself; the next rung (if pursued) is a heading-only or DR-only bisection of the widen8 composite, not another torque-scale variant.

