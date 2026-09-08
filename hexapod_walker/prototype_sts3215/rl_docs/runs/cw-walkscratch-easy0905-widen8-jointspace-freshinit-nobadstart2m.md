# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nobadstart2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T14:09:39+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: ap9nlkj0

**hypothesis**: Plain English: does removing the up-to-35deg random bad-start joint perturbation at reset (the most violent single DR axis for a policy that starts as random noise and has not yet learned to stand) let the fresh-init joint-space widen8/full-crutch-off-DR composite ignite forward walking, where the full composite (4/4 cells: joint-space and cart_foot, immediate and staged DR) failed to ignite at both 2M and 40M? Single lever vs the matched offctrl 2M canary: dr.bad_start_prob 0.25->0.0 only, dr.bad_start_max_joints/dr.bad_start_deg left in the vector but inert at prob=0. Same seed 40, same 8-way heading set, same full remaining DR matrix (mass/friction/gains/sensor noise/faults/pushes all still on).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: majority (>=3/4 modes or >=13/24 pooled) gait_valid with net forward displacement >=0.03 m/s median and 0 new falls vs the offctrl baseline = PASS (bad_start is a real ignition blocker, worth a 40M follow-up); still flat/thrashing (slip 8-142/m, near-zero net speed, matching the closed 4/4 fingerprint) = FAIL (bad_start is not the culprit, narrows to another axis or confirms breadth itself, not one specific axis).

**verdict**: CANARY FAIL - MECHANISM: removing dr.bad_start_prob (0.25->0.0) alone does NOT ignite fresh-init walking on the widen8 full-DR composite. walk/det fwd med 0.01m over a 20s episode (~0.0005 m/s, misses the 0.03 m/s PASS floor by ~60x), slip med 69/m (matches the closed-4/4 thrash fingerprint, not the healthy <=2.9 band). gait_valid superficially high (5-6/6) because legs cycle in place without net translation -- contact sheet confirms in-place trembling, zero body displacement across all 10 frames, not gaited walking. Rules out bad_start as the SOLE ignition blocker; consistent with DR breadth itself (many small-disruption axes summing) rather than one named axis. Single-lever isolation branch: 1 of 3 arms closed.

