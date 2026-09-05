# cw-walkscratch-easy0905-sdehalfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:58:14+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**hypothesis**: Plain English: backlog spare — second seed of the sde+halfgrav factorial cell so the 2x2 grid has n=2 in every cell (operator 09-05: keep a ready batch in backlog for the drain). From-scratch 40M, identical to sdehalfgrav-s0 except --seed 1.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family's 2M CANARY PASS 09-05; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**refused_reason**: hexapod-mjx-train-5 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-5 (and snapshot/commit before that if the tree is dirty).

