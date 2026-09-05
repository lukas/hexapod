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

**verdict**: CANARY PASS, now CORROBORATED by the full harness gate (synced after the initial W&B-scope verdict, per the headset-halfgrav-c2 precedent). 24 episodes (walk det+sto, walk_startjitter det+sto), 0/24 falls/terminations. walk/det+sto: 12/12 gait_valid=True, 0 sacrificed legs, forward_dist_m 2.77-3.82m/20s (0.14-0.19 m/s, the fastest of the two new seeds), slip_per_m 2.8-4.9 (near/above the 2.9 teacher band). walk_startjitter/sto: 6/6 gait_valid=True, 0 sacrificed legs -- clean. walk_startjitter/det: 5/6 sacrifice leg [1] or [1,4] (gait_valid False), 1/6 fully valid -- narrower single/dual-leg favoritism specific to the perturbed-start deterministic scenario only, same shape as headset-base-s0c1's leg-4 favoritism (not the gSDE LEGPARK-SKATE fingerprint -- plain Gaussian, no --use-sde, no near-zero-stride paddling). Net: 19/24 episodes real six-leg locomotion at just 2M steps, best forward progress of the new seed pair. 40M acquisition continuation already launched (headset-base-s1c1-acq1, VERIFIED RUNNING train-5). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s1c1_gate/report.json.

