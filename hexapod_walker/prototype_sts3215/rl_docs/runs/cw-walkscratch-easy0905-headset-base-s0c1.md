# cw-walkscratch-easy0905-headset-base-s0c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T12:10:23+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: tm703vax

**hypothesis**: Plain English: n=3 seed check for the base-family heading canary (headset-base-c1, from base-s2, already CANARY PASSed: reward+v_along_cmd+ep_len all healthy). Does a SECOND base-family champion (base-s0-c1) also keep walking under the small discrete heading set {0,+45,-45} using the same unchanged freeprog reward? Same bank-proven recipe (test_walkscratch_easy_pilot.py EASY_HEADING, 22/22 green), same boundaries (no new reward keys, own-track warm start, not teacher/BC/motion-prior). Cheap 2M canary reusing idle GPU capacity while the base-c1/halfgrav-c1 40M acquisitions train.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-base-c1/headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live (env/v_along_cmd and/or reward_walk trending up across the 2M budget). FAIL only on flat reward/v_along or an immediate park recapture.

**verdict**: CANARY PASS (mechanism-health scope only, third base-family heading-canary seed alongside headset-base-c1/s1c1). W&B (tm703vax, 2.1M steps): ep_rew_mean climbs monotonically every quarter 9.9->47.7->82.8->117.3, ep_len_mean rises 100->486 ticks (near the 500-tick truncation, almost no early falls by the end), env/v_along_cmd_m_s holds positive 0.098->0.105 m/s throughout (heading gradient genuinely live, not marching in place), env/reward_walk trending up 0.397->0.425. Hand-pulled frame strips from the in-flight gate eval's walk_det_0.mp4 (train-3, per-leg contact overlay) show the six-leg 'feet' pattern genuinely CHANGING shape across the episode (t=0.01 all six planted at reset -> t=2.41 3 planted -> t=8.41 2 planted -> t=14.41 1 planted -> t=19.81 2 planted, no fixed frozen subset), forward speed v rising through the episode (0.006->0.174 m/s), tilt/height error mild (<=4.1deg, <=23mm) -- NOT the gSDE LEGPARK-SKATE fingerprint (this is the plain Gaussian base family, no --use-sde). No FAIL trigger (no flat reward, no immediate park recapture). Full 24-episode det+sto+startjitter gait_valid/sacrificed-leg numbers still computing on train-3 (video-every=1 is slow) -- left running, do not re-launch, read logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_gate/report.json when it lands. Informational session-gate rider (stand+walk composite) FAILed as expected (that skill isn't this run's job) -- does not affect this canary verdict. Next: same as headset-base-c1 -- fund the 40M own-checkpoint acquisition continuation.

