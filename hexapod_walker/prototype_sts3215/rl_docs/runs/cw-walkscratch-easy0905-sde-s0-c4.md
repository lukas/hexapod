# cw-walkscratch-easy0905-sde-s0-c4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T11:12:50+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0-c1

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1's lineage (ACQ CONTINUE verdict this cycle: ep_len/reward still climbing at the 40M cutoff, same fingerprint as sde-s1/sde-s2). CORRECTING sde-s0-c3: that respec cloned base-s0 (the ORIGINAL 2M-canary config, not base-s0-c1's 40M acquisition config) and I forgot an explicit --steps override, so it silently trained only 2M steps (FINISHED_BEFORE_CHECKUP, no crash, just the wrong budget -- caught by a concurrent cycle's checkup). This respec is from base-s0-c1 (confirmed 40M) PLUS an explicit --steps 40000000 belt-and-braces, blank --activation-fn, --init-from targeting sde-s0-c3's checkpoint (which DID get a valid extra 2M of on-lineage training, so nothing is wasted).

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**refused_reason**: hexapod-mjx-train-8 already runs cw-walkscratch-easy0905-sde-s0-c4 — GPU pods host exactly one run; pick a free GPU pod.

