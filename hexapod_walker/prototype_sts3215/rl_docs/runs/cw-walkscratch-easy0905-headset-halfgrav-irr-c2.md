# cw-walkscratch-easy0905-headset-halfgrav-irr-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T14:41:59+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c1

**wandb_id**: 73esx971

**hypothesis**: headset-halfgrav-irr-c1 tests whether irregular direction-change timing (goal.walk_cmd_resample_jitter=0.5) preserves the six-leg heading gait at 0.5g, warm-started from the flagship headset-halfgrav-acq1 checkpoint; this is the SAME jitter mechanism on the OTHER just-PASSed halfgrav seed (headset-halfgrav-s1acq, this cycle's cleanest-yet ACQ PASS: 24/24 gait_valid, zero sacrificed legs) to check the irr result isn't specific to one checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as headset-halfgrav-irr-c1: 2M canary, 0 falls, six-leg gait_valid on video across the 3-heading set under jittered resample timing; continue/realign per 08-21 if still climbing.

**verdict**: CANARY PASS -- the 0.5g irregular-direction-change-timing canary (2nd seed, cross-checkpoint warm-start from headset-halfgrav-s1acq -- the sibling clean champion, not the same source as -c1) is healthy AND its own 24-ep harness gate already landed clean. Evidence: env/walk_speed alive+rising all 4 quarters (0.169/0.190/0.188/0.188 m/s), rollout/ep_rew_mean monotonic 31.1->56.1->93.7->124.0, ep_len_mean tripling 98->483, wrong_way falling 3.3%->2.1%. Harness gate (logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_irr_c2_gate/report.json): 0/24 falls, gait_valid 24/24 across ALL FOUR scenarios (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) with zero sacrificed legs anywhere -- cleanest irr-timing canary of the campaign, better than both c1 and the base-family c1/c2 siblings (which show marginal leg-1/4 favoritism under walk_startjitter/det). slip med 2.16-2.96 (tight), fwd med 2.8-3.5m/20s. Per 08-21 this funds continuation; halfgrav-irr-acq1 (40M, off s1acq) is already running so no new acquisition launched off this checkpoint specifically -- this is the 3rd/last planned halfgrav irr canary (mirrors base's c1/c2 pair) and closes the halfgrav-cell irr-canary sub-question at 3/3 clean (c1/c2/c3 all healthy-or-PASS, c3 alone still mid-eval on train-1). Next: read halfgrav-irr-acq1's gate (now genuinely computing, registered evalpending) before deciding on a 2nd halfgrav-irr acquisition seed.

