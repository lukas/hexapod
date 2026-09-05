# cw-walkscratch-easy0905-base-s1-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:59:42+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s1

**hypothesis**: Plain English: second-seed twin of the base continuation — the 2M canary was healthy and this gives the same recipe its acquisition budget from its own checkpoint. Own-checkpoint 40M continuation of base-s1 (operator 09-05 full-fleet order), zero recipe changes; --activation-fn stripped per plain --init-from restriction (PPO.load preserves ELU/log_std).

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Not met with signals still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**refused_reason**: hexapod-mjx-train-1 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-1 (and snapshot/commit before that if the tree is dirty).

