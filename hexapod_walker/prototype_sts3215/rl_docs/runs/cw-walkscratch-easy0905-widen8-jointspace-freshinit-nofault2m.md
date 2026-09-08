# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nofault2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T14:09:23+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: v06yxt9u

**hypothesis**: Plain English: does removing simulated actuator-fault injection (dr.fault_prob, 30% chance per episode of a degraded/stuck joint) let the fresh-init joint-space widen8/full-crutch-off-DR composite ignite, isolating the 'faulty actuator' axis from the rest of the already-closed 4/4 full-DR ignition failure? Single lever vs the matched offctrl 2M canary: dr.fault_prob 0.3->0.0 only, everything else (bad_start, pushes, sensor noise, mass/friction/gain DR) unchanged.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: majority gait_valid + net forward speed >=0.03 m/s + 0 new falls vs the offctrl baseline = PASS (fault injection is a real ignition blocker); still flat/thrashing = FAIL (rules out fault_prob as the sole culprit).

**verdict**: CANARY FAIL - MECHANISM: removing dr.fault_prob (0.3->0.0) alone does NOT ignite fresh-init walking on the widen8 full-DR composite. walk/det fwd med 0.01m/20s episode (~0.0005 m/s, misses 0.03 m/s PASS floor by ~60x), slip med 68.6/m (matches closed-4/4 thrash fingerprint). gait_valid 6/6 det but that's leg-cycling pattern validity, not translation -- contact sheet shows the robot stationary in place across all 10 frames. Rules out simulated actuator faults as the SOLE ignition blocker. Single-lever isolation branch: 2 of 3 arms closed.

