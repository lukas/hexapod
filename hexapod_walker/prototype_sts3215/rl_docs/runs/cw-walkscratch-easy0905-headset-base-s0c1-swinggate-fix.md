# cw-walkscratch-easy0905-headset-base-s0c1-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T21:34:31+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgate2-c1

**wandb_id**: 2vlzxnoh

**hypothesis**: Entrenched-checkpoint retrofit twin of swinggate-fresh: does the new reward.walk_swing_gate mechanism (MIN-over-legs trailing-window COUNT of qualifying real swings, bank-proved this cycle 4/4 green) cure the leg-4 marginal-underuse habit AFTER it has already entrenched over a full 40M acquisition (headset-base-s0c1-acq1), the same way walk_duty_gate's entrenched-checkpoint retrofit (dgate2-c1/dgatefix batch) was tried and found genuinely-pricing-but-too-late on this family? Warm-starts from the same headset_base_s0c1_acq1.zip 40M champion dgate2-c1 used.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): PASS/repair-signal if walk_startjitter/det leg duty on the chronically-parked leg moves meaningfully off its 0.02-0.07 baseline (matching or beating the first-seed medhead champion's accepted-PASS 0.08-0.09 range) in a majority of episodes, with 0 new falls. FAIL - MECHANISM if the same leg stays chronically <=0.07 in a majority of episodes despite walk_swing_gate_factor showing real (non-saturated) decline -- the 'genuinely pricing but too late against an entrenched checkpoint' pattern the duty_gate retrofit batch already established, this time for a different mechanism. Read together with swinggate-fresh: if fresh cures it but this retrofit doesn't, budget the fresh recipe as the winning provenance; if both fail, swing_gate needs a longer acquisition budget or a genuinely new lever.

