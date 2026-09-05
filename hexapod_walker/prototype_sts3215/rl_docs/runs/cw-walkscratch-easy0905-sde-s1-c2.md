# cw-walkscratch-easy0905-sde-s1-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (misaligned)

**created**: 2026-09-05T10:37:22+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1

**wandb_id**: iuxu4b7m

**hypothesis**: Plain English: sde-s1 was ruled ACQ CONTINUE, not FAIL, at its 40M cutoff (ep_len_mean still rising 111->231 ticks, reward rising 2.8->38.7 with no plateau, v_along_cmd holding ~0.15-0.17 m/s) -- give it the same own-checkpoint 40M continuation budget sde-s0 got. CORRECTED relaunch of sde-s1-c1 (crashed in <1s, confirmed via pod log /tmp/train_cw-walkscratch-easy0905-sde-s1-c1.log: '--activation-fn only applies to from-scratch/transplant builds; a plain --init-from warm start keeps the checkpoint's own activation' -- base-s1's vector carries --activation-fn elu (non-blank, unlike base-s0's blank), and train_ppo_mjx.py's guard raises SystemExit whenever --activation-fn is truthy alongside a plain --init-from since PPO.load already restores the checkpoint's saved activation/gSDE state). This respec blanks --activation-fn explicitly and only adds --init-from, mirroring the working base-s0-c1/halfgrav-s0-c1 pattern.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True, sde_sample_freq=20) via PPO.load's restored state, not the CLI flag. Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

**verdict**: Result: not walking per gate — new class-level exploit, naming it LEGPARK-SKATE. Real progress on survival (0/24 falls vs parent sde-s1 falling every det trial; ep_len ~1982/2000) and the det speed bar clears (0.94m/20s = 0.047 m/s >= 0.03), but gait_valid 0/24: legs [1,4] (det) / [4] (sto) permanently sacrificed — duty_cycle [0.96,0.04,0.87,0.95,0.00,0.97], swing_count [54,20,82,54,1,46] over 20s, stride_m_mean 6mm, slip_per_m 3.5-6.5 (teacher band <=2.9). Video walk_det_0_sheet: near-frozen splayed pose creeping forward, one leg held aloft the whole episode. W&B root cause: ep_rew_mean climbs monotonically to +2023 while env/walk_speed DECLINES 0.22->0.135 and v_along_cmd 0.16->0.115 through the back half; per-tick reward_walk RISES 0.77->1.25 as speed falls — the easy0905 minimal diet (freeprog cap 0.06, k_step_event/k_park_duty/k_walk_idle_charge/k_loadslip_excess all 0, term_penalty 24) pays nothing for speed above cap and prices nothing about a parked leg, so the reward optimum IS this exploit. Per 08-21 this is the MISALIGNED branch, not continue-blind: dug in, found the structural fix (reward.walk_gait_gate, 08-13 quadwalk lesson: additive k_park_duty reprices get paid, MIN-over-legs income gate does not) had its 3 semantics-bank tests red since the 09-02 merge (stale joint-frame-v2 bypass pose literals -> over_current actor deaths, + honest-gait stride calibration drift 10->7mm) — fixed all 3 this cycle (4/4 green, collateral checked, remaining slipwalk/fullcircle reds pre-date my edits). Next: repair continuation cw-walkscratch-easy0905-sde-s1-c3gg from this checkpoint with walk_gait_gate=1.0 + gait_gate_stride_mm=5 + k_step_event=1.0. Family read: Gaussian cells 8/8 ACQ PASS vs sde 0/4 valid gaits — gSDE exploration reliably finds the legpark basin under the minimal diet.

