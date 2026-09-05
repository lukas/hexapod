# cw-walkscratch-easy0905-sde-s2-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (misaligned)

**created**: 2026-09-05T10:34:29+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2

**wandb_id**: c7f152s7

**hypothesis**: Plain English: sde-s2 was ruled ACQ CONTINUE, not FAIL, at its 40M cutoff (ep_len_mean still rising 102->214 ticks, reward tracking up an order of magnitude off its mid-training trough, v_along_cmd holding ~0.15-0.17 m/s). Give it the same own-checkpoint 40M continuation budget sde-s0/sde-s1 got. CORRECTED relaunch of sde-s2-c1 (FAILED in ~2s: that launch used --init-from-source which cloned --use-sde/--sde-sample-freq/--activation-fn alongside a plain --init-from -- train_ppo_mjx.py's own guard raises SystemExit for --activation-fn+--init-from on a non-transplant warm-start, since PPO.load already restores the checkpoint's saved activation/gSDE state from the zip. This respec is built from the NON-sde base-s2 vector (matching seed) with --activation-fn explicitly blanked and only --init-from added, exactly mirroring the working base-s0-c1/base-s1-c1/halfgrav-s0-c1 pattern (verified: their logs show '--activation-fn ""' and completed full 40M training).

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True, sde_sample_freq=20) via PPO.load's restored state, not the CLI flag. Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

**verdict**: Result: same LEGPARK-SKATE fingerprint as sde-s1-c2, independent seed — the exploit is the sde cell's stable attractor under the easy0905 minimal diet, not seed noise. 0/24 falls, det fwd 1.57m/20s (0.078 m/s, clears the 0.03 bar), but gait_valid 0/24 with sacrificed legs [1] (det) / [3,4] (sto) / up to [1,3,4] under start-jitter+sto; slip_per_m 3.46-6.35. W&B: ep_rew_mean +2003 monotonic, ep_len 1956, env/walk_speed 0.23->0.15 and v_along_cmd 0.16->0.13 declining through the back half while per-tick reward_walk rises 0.71->1.24 — identical misalignment mechanics to s1-c2 (see that verdict for the full root-cause chain: freeprog cap + zero leg-participation pricing). Corroboration makes this a class verdict for the unmodified-diet sde continuations. Next: repair continuation cw-walkscratch-easy0905-sde-s2-c3gg from this checkpoint (walk_gait_gate=1.0 structural income gate + gait_gate_stride_mm=5 + k_step_event=1.0), second seed of the repair pair.

