# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nodiscrete2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T15:04:49+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**hypothesis**: Plain English: the 3-arm single-axis DR knockout (bad_start alone, fault alone, push alone, each set to 0 with everything else at full strength) all FAILED to ignite fresh-init walking on the widen8 full-DR composite -- no ONE discrete/event axis explains the blocker. This tests whether the GROUP of all three catastrophic discrete-event axes together (bad_start+fault+ext_push+walk_push all zeroed simultaneously, but every continuous jitter/sensor-noise axis -- mass, friction, gains, encoder/tilt/gyro noise, com offset, link length, placement noise -- stays at FULL strength) is the actual blocker via an interaction the single-axis tests could not see. Companion arm nocontinuous2m (this cycle's other arm) tests the complementary split: discrete axes at full strength, continuous axes zeroed. If nodiscrete2m ignites and nocontinuous2m does not, the discrete/catastrophic-event axes (not continuous jitter) are the real blocker for a policy that has never learned to stand. If neither ignites, that's further evidence for pure breadth/SUM regardless of category, matching the concurrent uniform-magnitude dose-ladder (halfdr2m/quarterdr2m) finding.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up confirming discrete-event axes as the primary blocker (continuous jitter alone is survivable for fresh-init). FAIL (still flat/thrashing, slip 8-142/m matching the closed single-axis-knockout fingerprint) rules out the discrete-axis GROUP as sufficient by itself, reinforcing that continuous jitter breadth alone (or the full breadth sum) is enough to block ignition.

