# cw-walkscratch-easy0905-sde-s0-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T10:54:05+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1 (ACQ CONTINUE this cycle: ep_len dipped then recovered to 239, reward ended positive +17.1, v_along holds ~0.15-0.17 m/s — same still-learning fingerprint as sde-s1/s2/s3). Plain English: give the sde-s0 lineage another 40M to see if survival duration keeps compounding like sde-s1-c2/sde-s2-c2 are already testing.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery.

**failed_reason**: run never appeared as 'running' in W&B within 240s

