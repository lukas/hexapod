# cw-walkscratch-easy0905-halfgrav-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:59:26+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**hypothesis**: Plain English: the half-gravity canary was healthy; this gives it the acquisition budget from its own checkpoint to test whether stepping emerges earlier when the robot weighs half as much. Own-checkpoint 40M continuation of halfgrav-s0 (operator 09-05 full-fleet order), zero recipe changes (ease.gravity_scale=0.5 retained in cfg); --activation-fn stripped per plain --init-from restriction. Evaluated at ITS OWN 0.5g; full-gravity is a later diagnostic, never automatic promotion.

**gate**: Acquisition milestone at OWN 0.5g physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Not met with signals still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at budget or park recapture.

**refused_reason**: hexapod-mjx-train-3 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-3 (and snapshot/commit before that if the tree is dirty).

