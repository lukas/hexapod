# cw-walkscratch-easy0905-headset-base-irr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T13:59:12+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: 0zs57vwc

**hypothesis**: Plain English: headset-base-acq1 already walks cleanly (1g) under a heading SET that changes on a fixed 6s clock -- this canary is the 1g sibling of headset-halfgrav-irr-c1, testing the same next rung (IRREGULAR direction-change timing via goal.walk_cmd_resample_jitter=0.5 added on top of the identical resample_s=6.0/heading-set recipe, no other change), warm-started from acq1's own 40M checkpoint. Pairs with the halfgrav arm for an n=2 gravity-cell read of the irregular-timing rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Canary/mechanism-health at OWN physics (1g): env/walk_speed stays alive (not decaying toward 0 vs acq1's live trend), ep_rew_mean/ep_len_mean not collapsing early, no blowup. Per 08-21: healthy canary funds a 40M acquisition follow-up with the real gate (20s held-out panel with jittered heading changes, >=0.03 m/s median net forward per heading, 0 falls/12 det eps, gait_valid majority, six-leg lift/place on video); flat reward + collapsed speed = FAIL, no continuation.

**verdict**: CANARY PASS (mechanism-health, 2M) — the 1g base-family irregular-direction-change-timing canary (goal.walk_cmd_resample_jitter=0.5, warm-started from headset_base_acq1's 40M checkpoint) is healthy: env/walk_speed alive 0.155/0.170/0.168/0.165 m/s across 4 quarters (not decaying), ep_rew_mean monotonic 42.4->87.5->134.3->191.2, ep_len_mean climbing 108->488 (fewer early falls), wrong_way stable ~8%. Beyond the canary's own bar, the harness's own 24-episode gate panel already synced (prestage ran the full acquisition-style panel, not just a light check): 0/24 falls, fwd med 2.2-3.2m/20s (0.11-0.16 m/s, clears the 0.03 floor by 4-5x), gait_valid 21/24 -- 6/6 walk/det, 6/6 walk/sto, 6/6 walk_startjitter/sto, only walk_startjitter/det weak at 3/6 (sac leg [1] x2, [4] x1) which is the SAME known perturbed-start-only favoritism every other base-family PASS this campaign shares (headset-base-acq1, -s1c1-acq1), not a new pathology. slip med 3.5-4.6, in the established (elevated but non-blocking) base-family band. Per 08-21/gate text this funds the 40M acquisition follow-up. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_c1_gate/report.json, W&B 0zs57vwc. Next: launched cw-walkscratch-easy0905-headset-base-irr-acq1 (40M, own-checkpoint warm start, VERIFIED RUNNING train-3), mirroring the halfgrav sibling's identical canary->acq1 decision this cycle.

