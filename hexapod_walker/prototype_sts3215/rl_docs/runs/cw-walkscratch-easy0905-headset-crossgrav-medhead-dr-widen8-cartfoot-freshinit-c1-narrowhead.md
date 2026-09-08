# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-narrowhead

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:36:37+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: pr966vo3

**hypothesis**: Plain English: the torqueretain bisection (just verdicted, both arms FAIL) ruled OUT torque-crutch removal as the widen8-cartfoot-freshinit ignition blocker. This test isolates the OTHER named suspect: heading breadth itself. Same seed40 fresh-init recipe, same full crossgrav/medhead DR matrix, same cart_foot action space, same torque_scale=1,1 (crutch off) -- the ONLY change is goal.walk_heading_set shrunk from widen8's 8-way set back to the original medhead 5-way set (drops the three backward/diagonal-backward headings 135,-135,180 that widen8 added). This exact 5-way medhead-dr-crutchoff composite already ignites fine when WARM-STARTED (cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0/1/2 -> acq1 lineage), but was never tested fresh-init. If ignition appears now (reward_walk rising, v_along turning positive, walk_speed rising -- unlike the flat/declining widen8 fresh-init and torqueretain arms), the widen8 backward-heading extension specifically is the fresh-init blocker, not DR/crossgrav breadth. If it still fails to ignite with the same flat/declining fingerprint, then full crossgrav+medhead DR breadth alone (independent of heading count) is too hard for a fresh random init, and this composite\'s only proven ignition path is warm-start/curriculum -- closing the fresh-init route for the whole DR-hardened composite family, not just widen8.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41/torqueretain arms: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up across quarters, env/v_along_cmd_m_s turning positive, env/walk_speed rising -- not the flat/declining shape all 4 prior widen8-freshinit arms showed); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched offctrl-narrowhead sibling (launched together) -- two arms agreeing is sufficient for a canary-level mechanism verdict.

