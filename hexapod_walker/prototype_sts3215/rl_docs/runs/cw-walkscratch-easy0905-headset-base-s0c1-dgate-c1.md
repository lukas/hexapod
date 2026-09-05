# cw-walkscratch-easy0905-headset-base-s0c1-dgate-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:06:32+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-acq1

**wandb_id**: wlon6s9r

**hypothesis**: Plain English: the s0c1-acq1 dig-in showed this seed walks fast with zero falls but chronically parks leg 4 (duty 0.03-0.07 in every det episode) because nothing in the diet prices a parked leg the income can't outbid; this canary warm-starts the SAME failed 40M checkpoint with the new bank-proven contact-duty income gate (reward.walk_duty_gate=0.9: transport income x [(1-g)+g*MIN over legs of clip(trailing-3s duty/0.15,0,1)] -- combines walk_gait_gate's proven income-collapse structure with k_park's proven duty signal, un-dodgeable by token swings, 27/27 bank incl. 5 new duty-gate tests at exp/walk-duty-gate-mechanism-0905). Prediction-if-true: env/walk_duty_min climbs toward 1.0 and the det-mode leg-4 duty recovers above 0.10-0.15 within 2M with no fall regression (the policy demonstrably knows six-leg walking -- its own 2M canary was walk/det 6/6 gait_valid). Prediction-if-false: duty stays <0.10 with the gate factor pinned low but paid, or a DIFFERENT leg parks (MIN-over-legs should prevent), or income collapse destabilizes into falls. Strongest alternative: contact-chatter hover just above the 0.15 floor without real load -- check slip/stride at the gate eval.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Canary (mechanism health, 2M): env/walk_duty_min and walk_duty_gate_factor rise toward 1.0 (not pinned at the floor); gate eval shows leg-4 walk/det duty >0.10 in a majority of episodes with 0 falls (parent baseline 0/24 falls, leg-4 duty 0.03-0.07); reward may drop at switch-on but must not collapse to termination-dominated.

