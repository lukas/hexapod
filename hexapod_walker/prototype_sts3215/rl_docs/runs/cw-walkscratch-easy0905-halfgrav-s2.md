# cw-walkscratch-easy0905-halfgrav-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:57:44+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**hypothesis**: Plain English: independent seed 2 of the validated half-gravity easy family, at acquisition budget (mechanism evidence inherited from halfgrav-s0's 2M CANARY PASS; operator 09-05 matched-seed directive). From-scratch 40M, identical to halfgrav-s0 except --seed 2; seed MATCHED to base-s2 for a paired base-vs-halfgravity comparison at 1g vs 0.5g. Question: does halving gravity systematically accelerate/enable teacher-free stepping across matched seeds?

**gate**: Acquisition milestone at OWN physics (halfgrav arms at their own 0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence inherited from the family's 2M CANARY PASS 09-05 — spot-check at ~2M in W&B, do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**refused_reason**: hexapod-mjx-train-3 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-3 (and snapshot/commit before that if the tree is dirty).

