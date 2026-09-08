# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T08:37:23+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**hypothesis**: Matched fresh-init joint-space control for the cart_foot-freshinit-c1 canary above (same run, same 2M budget, IDENTICAL seed/DR/heading recipe, only the 3 walk_cart_foot_box_* keys removed). Isolates whether ignition/gait health on the harder widen8 8-way-heading + full crutch-off DR composite depends on the action-space swap or is just ordinary fresh-init-on-hard-DR difficulty -- every existing PASS/FAIL reference point for this composite (widen8-acq1 3/3 ACQ FAIL, all 19 reward-mechanism attempts) was a WARM START off a 5-way-heading base, never a fresh-init on the full 8-way+DR composite directly, so this control also tells us whether joint-space itself can even ignite from scratch at this difficulty.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: read together with the matched cart_foot-freshinit-c1 ON arm at the same budget. Same PASS/FAIL clauses as the ON arm (gait_valid majority + 0 falls + reward rising = PASS; chronic front-pair/single-leg sacrifice majority = FAIL regardless of reward trend). If this control ALSO fails to ignite (no majority gait_valid on any mode), the read is INCONCLUSIVE for the action-space question -- it would mean fresh-init-on-full-hard-DR is the harder variable, not the mechanism/action-space this pair was designed to isolate, and a milder fresh-init entry point would be needed before re-testing cart_foot.

