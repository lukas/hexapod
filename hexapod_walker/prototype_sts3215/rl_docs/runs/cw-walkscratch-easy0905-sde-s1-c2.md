# cw-walkscratch-easy0905-sde-s1-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T10:38:48+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1

**hypothesis**: Plain English: sde-s1 was ruled ACQ CONTINUE (ep_len 111->231 ticks rising, reward 2.8->38.7, no plateau at 40M cutoff). CORRECTED relaunch of sde-s1-c1 (a concurrent cycle's launch, FAILED in ~2s: --activation-fn elu passed alongside a plain --init-from triggers train_ppo_mjx.py's own SystemExit guard for non-transplant warm-starts -- PPO.load already restores the checkpoint's saved activation/gSDE). This respec blanks --activation-fn and only adds --init-from, mirroring the working base-s0-c1/base-s1-c1/halfgrav-s0-c1/sde-s2-c2 pattern (all confirmed complete/training with this exact fix).

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True, sde_sample_freq=20) via PPO.load's restored state. Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0/s1 fingerprint) or park recaptures.

**refused_reason**: a process for cw-walkscratch-easy0905-sde-s1-c2 already exists on hexapod-mjx-train-4

