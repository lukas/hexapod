# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nopush2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T14:09:54+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: btx1r1u3

**hypothesis**: Plain English: does removing external body pushes (dr.ext_push_prob + dr.walk_push_prob, both 30% per-episode disturbance probability) let the fresh-init joint-space widen8/full-crutch-off-DR composite ignite? Pushes are a known driver of a DIFFERENT pathology (push-recovery fragility on already-walking champions, 09-07 crutch finding) -- this tests whether the same axis also blocks a policy that hasn't learned to walk at all yet. Single lever vs the matched offctrl 2M canary: both push probabilities 0.3->0.0, everything else unchanged.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: majority gait_valid + net forward speed >=0.03 m/s + 0 new falls vs the offctrl baseline = PASS (pushes are a real ignition blocker); still flat/thrashing = FAIL (rules out pushes as the sole culprit).

