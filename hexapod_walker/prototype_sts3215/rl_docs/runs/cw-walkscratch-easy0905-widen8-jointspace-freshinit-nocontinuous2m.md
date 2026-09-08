# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nocontinuous2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T15:06:50+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: uevepjck

**hypothesis**: Plain English: companion split to nodiscrete2m (this cycle's other arm). The 3-arm single-axis DR knockout showed no ONE discrete/event axis (bad_start/fault/push) alone explains the fresh-init ignition failure. This arm tests the COMPLEMENTARY group: zero every CONTINUOUS jitter/sensor-noise axis (mass_scale, leg_mass_jitter, link length, com offset, friction, contact stiffness, ground tilt, gain scale, velocity scale, cmd-drop, placement noise, encoder/tilt/gyro noise+bias, imu bias/mount/position, action noise) down to nominal/zero, while keeping the three catastrophic discrete-event axes (bad_start_prob=0.25, fault_prob=0.3, ext_push_prob=0.3, walk_push_prob=0.3) at FULL strength. If this ignites and nodiscrete2m does not, continuous jitter (not discrete events) is the real blocker. If neither ignites, that reinforces pure DR-breadth/SUM as the blocker regardless of category, matching the concurrent uniform-magnitude dose-ladder (halfdr2m/quarterdr2m).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up confirming continuous jitter as the primary blocker (discrete events alone are survivable for fresh-init). FAIL (still flat/thrashing, slip 8-142/m matching the closed single-axis-knockout fingerprint) rules out the continuous-axis GROUP as sufficient by itself.

