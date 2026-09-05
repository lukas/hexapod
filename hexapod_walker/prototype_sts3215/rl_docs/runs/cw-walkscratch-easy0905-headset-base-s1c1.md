# cw-walkscratch-easy0905-headset-base-s1c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T12:09:04+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: xors486s

**hypothesis**: Plain English: n=3 seed check (third base-family champion, base-s1-c1) for the heading canary, same design as headset-base-s0c1 (see that run for full rationale) -- reusing idle GPU capacity per the operator's full-fleet-utilization order rather than leaving it idle mid-campaign.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-base-c1): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

**verdict**: CANARY PASS (mechanism-health scope only, fourth base-family heading-canary seed alongside headset-base-c1/s0c1). W&B (xors486s, 2.1M steps): ep_rew_mean climbs monotonically every quarter 31.0->55.3->112.6->141.3, ep_len_mean rises 102->490 ticks (near the 500-tick truncation), env/v_along_cmd_m_s holds positive 0.089->0.108 m/s throughout (heading gradient live), env/reward_walk trending up 0.398->0.432. Hand-pulled frame strips from the in-flight gate eval's walk_det_0.mp4 (train-5) show the six-leg 'feet' contact pattern CHANGING shape across the episode (t=2.41 4 planted -> t=8.41 1 planted -> t=14.41 5 planted -> t=17.41 3 planted, no fixed frozen subset), forward speed v rising through the episode (0.006-ish start -> 0.14-0.30 m/s later), tilt/height error mild (<=5.9deg, <=23mm) -- NOT the gSDE LEGPARK-SKATE fingerprint (plain Gaussian base family, no --use-sde). No FAIL trigger. Full 24-episode gait_valid/sacrificed-leg numbers still computing on train-5 -- left running, do not re-launch, read logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s1c1_gate/report.json when it lands. Informational session-gate rider (stand+walk composite) FAILed as expected -- does not affect this canary verdict. Next: same as headset-base-c1/s0c1 -- fund the 40M own-checkpoint acquisition continuation.

