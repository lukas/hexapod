# cw-walkscratch-easy0905-headset-base-irr-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T14:38:21+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-c1

**wandb_id**: lp4katkf

**hypothesis**: headset-base-irr-c1 tests whether irregular direction-change timing (goal.walk_cmd_resample_jitter=0.5) preserves the six-leg heading gait, warm-started from the flagship headset-base-acq1 checkpoint; this is the SAME jitter mechanism on the OTHER already-PASSed base seed (headset-base-s1c1-acq1) to check the irr result isn't specific to one checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as headset-base-irr-c1: 2M canary, 0 falls, six-leg gait_valid on video across the 3-heading set under jittered resample timing; continue/realign per 08-21 if still climbing.

**verdict**: CANARY PASS (mechanism-health, 2M) -- the 1g base-family irregular-direction-change-timing canary warm-started from headset-base-s1c1-acq1 (the OTHER passed base seed, cross-checkpoint check on headset-base-irr-c1's result). env/walk_speed alive across all 4 quarters (0.140/0.149/0.151/0.147 m/s, not decaying), rollout/ep_rew_mean monotonic 42.0->88.3->150.5->198.5, ep_len_mean tripling 98->483 (fewer early falls), wrong_way falling 3.6%->1.6%. Per 08-21 this funds continuation; the harness's own 24-ep gate panel already synced too: 0/24 falls, fwd med 2.5-2.8m/20s (0.12-0.14 m/s, clears the floor), gait_valid 17/24 (walk/sto 6/6, walk_startjitter/sto 6/6, walk/det softer at 4/6 -- legs[4] duty 0.08 in 2/6 episodes, marginal not chronic-park: swing_count still 80-143/20s and video (walk_det_0.png) shows all six legs visibly cycling, no frozen leg -- and walk_startjitter/det weakest at 1/6, legs [1]/[4] alternating marginal duty 0.03-0.23, same known base-family perturbed-start favoritism every prior base PASS shares, just harder here than sibling c1 (21/24) or the flagship acq1/s1c1-acq1 champions. slip med 3.9-4.7, in the established base-family band. CAVEAT for next-cycle triage: this canary is weaker than c1's on the harness panel (17/24 vs 21/24, and unlike c1 the softening now touches primary walk/det, not just startjitter) -- the s0c1-acq1 precedent showed an even milder marginal-duty canary harden into a full ACQ FAIL over 40M budget, so do NOT auto-launch a base-irr-acq2 from this checkpoint copying the c1->acq1 pattern without first reading how base-irr-acq1 (already running, from c1) actually lands; if acq1 passes cleanly, revisit whether a second base-irr acquisition is worth the spend given this weaker canary, or whether the single acq1 confirmation satisfies the irr-timing question for the 1g cell (mirrors the halfgrav cell's own irr-c2 sibling, also not yet given its own acq2). No refill launched off this run this cycle (launch budget already spent on the walk_duty_gate canary batch, see STATUS.md ~15:2x). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_c2_gate/report.json, W&B lp4katkf.

