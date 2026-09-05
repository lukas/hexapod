# cw-walkscratch-easy0905-base-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:57:59+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0

**hypothesis**: Plain English: independent seed 2 of the validated easy-physics base family, launched straight at acquisition budget because the recipe's mechanism health is already proven by the base-s0/base-s1 2M CANARY PASSes (operator 09-05: identical-except-seed inherits mechanism evidence; do not re-pay 2M startup). From-scratch 40M, identical vector to base-s0 except --seed 2. Question: does teacher-free stepping on easy physics emerge robustly across seeds, and at what step count?

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence (finite losses, real actions, bank-consistent reward, motor contract 360 deg/s) is inherited from the family's 2M CANARY PASS 09-05 — spot-check it in W&B at ~2M but do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**refused_reason**: hexapod-mjx-train-11 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-11 (and snapshot/commit before that if the tree is dirty).

