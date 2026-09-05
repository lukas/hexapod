# cw-walkscratch-easy0905-sde-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T08:59:12+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**hypothesis**: Plain English: the gSDE canary showed the strongest early forward signal of the cohort (v_along +0.017 m/s at 2M) with much larger realized exploration than Gaussian noise at the same log_std; this continuation gives it the acquisition budget from its own checkpoint. Own-checkpoint 40M continuation of sde-s0 (operator 09-05 full-fleet order). Built by respec from the base-s0 vector (NOT sde-s0) because the trainer's plain --init-from REJECTS retained --use-sde/--activation-fn (fb_20260905T080341_ef45b6 item 2): PPO.load preserves the checkpoint's own gSDE mode (sde_sample_freq=20) and ELU activation; the arg vector is otherwise identical to sde-s0's (base-s0 and sde-s0 differ only by --use-sde/--sde-sample-freq).

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Also verify at first eval that the loaded policy is gSDE (use_sde=True, sde_sample_freq=20 in checkpoint data) — a silent exploration-mode change invalidates the arm. Not met with signals rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at budget or park recapture.

**refused_reason**: hexapod-mjx-train-2 code marker 72fec1b5129da81c47a83093e10d53189e651e69-dirty != local HEAD 72fec1b5129da81c47a83093e10d53189e651e69 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-2 (and snapshot/commit before that if the tree is dirty).

