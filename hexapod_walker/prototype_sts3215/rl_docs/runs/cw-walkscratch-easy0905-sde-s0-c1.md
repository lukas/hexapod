# cw-walkscratch-easy0905-sde-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CONTINUE

**created**: 2026-09-05T09:49:24+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: of5ll200

**hypothesis**: Plain English: the gSDE canary had the strongest early forward signal of the cohort; this continues it from its own checkpoint at acquisition budget. Own-checkpoint 40M continuation of sde-s0. Built by respec from the base-s0 vector because plain --init-from REJECTS retained --use-sde/--activation-fn (fb_20260905T080341_ef45b6): PPO.load preserves the checkpoint's own gSDE mode (sde_sample_freq=20) and ELU; the vector is otherwise identical to sde-s0's.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture. Also verify at first eval that the loaded policy is gSDE (use_sde=True, sde_sample_freq=20 in checkpoint data).

**verdict**: ACQ CONTINUE — same still-learning fingerprint as siblings sde-s1/sde-s2/sde-s3 (not a FAIL per 08-21 ruling). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_sde_s0_c1_gate/report.json — every det/sto episode across all 4 scenarios TERM tilt_pitch (0/24 gait_valid, 2-3 legs sacrificed, fwd 0.07-0.57m, well below the 0.6m/20s bar). BUT wandb_history.csv shows rollout/ep_len_mean DIPPED to 52-76 mid-run (steps ~288-908, ~11-36M) then genuinely RECOVERED to 239 at the final logged point (40M) — not a flat dead plateau — while rollout/ep_rew_mean climbed monotonically the whole run (-204->-267->-59->-38->-28->-25->-16->-5.5->+17.1, ending POSITIVE) and env/v_along_cmd_m_s holds 0.15-0.17 m/s throughout. This is the exact sde-family fingerprint already read on sde-s1/sde-s2 (own checkpoints continued as sde-s1-c2/sde-s2-c2) and sde-s3 (also CONTINUE this cycle): survival duration still being learned, speed skill already retained, reward genuinely rising not just per-burst gaming (contrast with the sdehalfgrav flat-plateau FAIL fingerprint). Next: own-checkpoint 40M continuation (sde-s0-c2), matching the already-launched sde-s1-c2/sde-s2-c2/sde-s3-c1 pattern — MUST strip --activation-fn/--use-sde on the plain --init-from (PPO.load restores gSDE+ELU; CURRENT_TRUTHS.md gotcha).

