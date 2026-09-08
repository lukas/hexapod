# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nopush2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T14:09:54+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: btx1r1u3

**hypothesis**: Plain English: does removing external body pushes (dr.ext_push_prob + dr.walk_push_prob, both 30% per-episode disturbance probability) let the fresh-init joint-space widen8/full-crutch-off-DR composite ignite? Pushes are a known driver of a DIFFERENT pathology (push-recovery fragility on already-walking champions, 09-07 crutch finding) -- this tests whether the same axis also blocks a policy that hasn't learned to walk at all yet. Single lever vs the matched offctrl 2M canary: both push probabilities 0.3->0.0, everything else unchanged.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: majority gait_valid + net forward speed >=0.03 m/s + 0 new falls vs the offctrl baseline = PASS (pushes are a real ignition blocker); still flat/thrashing = FAIL (rules out pushes as the sole culprit).

**verdict**: CANARY FAIL - MECHANISM: removing dr.ext_push_prob+dr.walk_push_prob (0.3,0.3->0.0,0.0) alone does NOT ignite fresh-init walking on the widen8 full-DR composite. walk/det fwd med 0.02m/20s episode (~0.001 m/s, misses 0.03 m/s PASS floor by ~30x), slip med 74/m (matches closed-4/4 thrash fingerprint). gait_valid 6/6 det is leg-cycling without translation -- contact sheet shows the robot stationary across all 10 frames. Rules out external pushes as the SOLE ignition blocker (pushes were already known to hurt push-recovery on an ALREADY-WALKING champion per the 09-07 crutch finding; this shows they are also not uniquely responsible for blocking ignition of a never-walked policy). 3 of 3 single-lever isolation arms now FAIL: no single named DR axis alone explains the widen8 fresh-init ignition failure -- confirms DR breadth itself (the SUM of many small-disruption axes) as the blocker, closing single-axis knockout as a productive lever on this composite without a genuinely combinatorial design or a narrowed composite / new per-leg mechanism.

