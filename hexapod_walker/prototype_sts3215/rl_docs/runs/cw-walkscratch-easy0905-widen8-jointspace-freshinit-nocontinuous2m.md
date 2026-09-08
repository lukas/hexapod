# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nocontinuous2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:06:50+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: uevepjck

**hypothesis**: Plain English: companion split to nodiscrete2m (this cycle's other arm). The 3-arm single-axis DR knockout showed no ONE discrete/event axis (bad_start/fault/push) alone explains the fresh-init ignition failure. This arm tests the COMPLEMENTARY group: zero every CONTINUOUS jitter/sensor-noise axis (mass_scale, leg_mass_jitter, link length, com offset, friction, contact stiffness, ground tilt, gain scale, velocity scale, cmd-drop, placement noise, encoder/tilt/gyro noise+bias, imu bias/mount/position, action noise) down to nominal/zero, while keeping the three catastrophic discrete-event axes (bad_start_prob=0.25, fault_prob=0.3, ext_push_prob=0.3, walk_push_prob=0.3) at FULL strength. If this ignites and nodiscrete2m does not, continuous jitter (not discrete events) is the real blocker. If neither ignites, that reinforces pure DR-breadth/SUM as the blocker regardless of category, matching the concurrent uniform-magnitude dose-ladder (halfdr2m/quarterdr2m).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up confirming continuous jitter as the primary blocker (discrete events alone are survivable for fresh-init). FAIL (still flat/thrashing, slip 8-142/m matching the closed single-axis-knockout fingerprint) rules out the continuous-axis GROUP as sufficient by itself.

**verdict**: CANARY FAIL - MECHANISM: zeroing the CONTINUOUS-jitter/sensor-noise DR group (mass/link/com jitter, friction, contact stiffness, gain scale, sensor noise/bias, cmd-drop, placement/action noise) while leaving the 3 discrete-event axes (bad_start/fault/push) at full strength also fails to ignite fresh-init walking. Evidence: walk/det + walk_startjitter/det both collapse to gait_valid 0/6 with 5-6 of 6 legs flagged 'sacrificed' per episode and fwd med 0.00-0.01m (robot essentially frozen standing, not stepping) -- contact sheet confirms static pose across all 10 frames; walk/sto + walk_startjitter/sto show high slip (166-203/m, matches the closed thrashing fingerprint) with still-negligible net fwd (0.06-0.10m over the episode). Different failure texture than nodiscrete2m (frozen-standing vs thrashing-in-place) but the same bottom line: no net locomotion, gate FAIL on both speed and majority-gait_valid criteria. Combined with the sibling nodiscrete2m FAIL (same cycle), this CLOSES the group-axis split as a productive lever: neither the discrete-event group alone nor the continuous-jitter group alone explains fresh-init ignition failure on the widen8 full-DR composite -- consistent with (not proof of, but consistent with) DR breadth/SUM being the blocker regardless of category, matching the 3 single-axis knockouts and the concurrent uniform-magnitude halfdr2m/quarterdr2m ladder. Next licensed moves unchanged: narrow the DR composite magnitude for a fresh-init-specific ladder (partially underway via halfdr2m/quarterdr2m), or a genuinely new per-leg mechanism.

