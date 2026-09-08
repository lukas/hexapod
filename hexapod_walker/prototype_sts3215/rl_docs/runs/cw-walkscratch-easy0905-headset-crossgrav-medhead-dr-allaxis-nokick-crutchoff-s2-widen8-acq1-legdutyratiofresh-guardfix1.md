# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyratiofresh-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T12:12:47+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyfresh

**wandb_id**: qp8ae93g

**hypothesis**: 3rd-seed (s2) BUG-FIX RELAUNCH matching the s0/s1 guardfix1 pattern: s2's own legdutyratiofresh attempt (2026-09-07 22:00) predates the ebad6d0d activation-guard fix (2026-09-08 00:27 UTC), so its charge=150 was silently inert like the original s0/s1 attempts -- this is INVALID, not evidence either way. Fresh 2M rerun on the fixed code, same seed4/init-from-s2_widen8/heading/DR/motor cfg as the s0(seed2)/s1(seed3) guardfix1 relaunches, tests whether the 0.30-target duty-ratio charge stops the chronic front-pair/leg sacrifice on this 3rd seed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the s0/s1 guardfix1 gate: PASS if the chronic leg's duty recovers (peer-relative ratio >=0.22 majority of episodes) and gait_valid >=18/24 with 0 new falls; CONTINUE if reward+gait_valid both trending up but short; FAIL if the same sacrifice persists regardless. This run ALSO doubles as the matched 0.30-dose baseline for the s2 swing-floor tie-break launched alongside it.

