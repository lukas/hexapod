# cw-walkscratch-easy0905-sde-s1-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T10:37:22+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1

**hypothesis**: Plain English: sde-s1 was ruled ACQ CONTINUE, not FAIL, at its 40M cutoff (ep_len_mean still rising 111->231 ticks, reward rising 2.8->38.7 with no plateau, v_along_cmd holding ~0.15-0.17 m/s) -- give it the same own-checkpoint 40M continuation budget sde-s0 got. CORRECTED relaunch of sde-s1-c1 (crashed in <1s, confirmed via pod log /tmp/train_cw-walkscratch-easy0905-sde-s1-c1.log: '--activation-fn only applies to from-scratch/transplant builds; a plain --init-from warm start keeps the checkpoint's own activation' -- base-s1's vector carries --activation-fn elu (non-blank, unlike base-s0's blank), and train_ppo_mjx.py's guard raises SystemExit whenever --activation-fn is truthy alongside a plain --init-from since PPO.load already restores the checkpoint's saved activation/gSDE state). This respec blanks --activation-fn explicitly and only adds --init-from, mirroring the working base-s0-c1/halfgrav-s0-c1 pattern.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True, sde_sample_freq=20) via PPO.load's restored state, not the CLI flag. Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

