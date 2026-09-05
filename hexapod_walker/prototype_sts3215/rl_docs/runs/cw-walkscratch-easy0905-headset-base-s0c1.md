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

**verdict**: CANARY PASS, now CORROBORATED by the full harness gate (synced after the initial W&B-scope verdict, per the headset-halfgrav-c2 precedent -- re-verdicting with the real numbers, no change to the PASS call). 24 episodes (walk det+sto, walk_startjitter det+sto), 0/24 falls/terminations. walk/det+sto: 12/12 gait_valid=True, 0 sacrificed legs, forward_dist_m 1.95-2.84m/20s (0.10-0.14 m/s), slip_per_m 3.6-5.2 (above the 2.9 teacher band -- paddle/skate quality at this tiny 2M budget, not gate-blocking for a canary). walk_startjitter/det: 6/6 sacrifice leg [4] (gait_valid False) -- a single-leg favoritism specific to the perturbed-start deterministic scenario, NOT the gSDE LEGPARK-SKATE fingerprint (no near-zero-stride paddling, no reward-vs-speed divergence, this is plain Gaussian/no --use-sde); walk_startjitter/sto mostly recovers (5/6 valid, only 1 sacrifices leg 4). Net: real six-leg locomotion in 19/24 episodes at just 2M steps, a narrower single-scenario weak spot to watch as the just-launched 40M acquisition continuation (headset-base-s0c1-acq1, VERIFIED RUNNING train-3) trains further. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_gate/report.json.

