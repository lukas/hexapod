# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-offctrl10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - matched control, no efficacy

**created**: 2026-09-08T01:47:09+00:00

**pod**: hexapod-mjx-train-8

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: 0gfv9tv8

**hypothesis**: Matched charge-off control for the completed +10M active leg-duty-ratio acquisition. The 2M corrected s1 canary is healthy (21/24 gait,0 falls) but did not improve over its actual init, and comparison to an older40M undosed run confounds dose and duration. This new bounded +10M control starts from the EXACT SAME corrected2M checkpoint MD5edfa283302954b40103334227eb3db1c, RNG3, schedule/8wayheading/DR/motor limits and all other args as cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m; ONLY reward.walk_leg_duty_ratio_charge changes150 to0. It tests continued-charge benefit versus removal after a shared2M exposure, not never-exposed training or seed robustness. This is one planned comparison arm, not a new seed or a duplicate charge-on continuation. Prior-free/noBC/no gait clock retained. Reward-scale values across arms are not evidence of behavioral improvement.

**gate**: Matched +10M control comparison only. Use exact same24episode walk/startjitter det+sto panel, evalseed0 and normal cadence. Require0newfalls, gait_valid>=21/24 and noNEWchronic single-leg sacrifice relative to shared corrected2M source; report per-leg relative duty, command progress, slip bygroup and paired episode changes for charge-on/off. If health regresses, preserve checkpoint and follow existing pruner rules; do not accept worsening gait because return rises. Credit the continued-charge hypothesis only if on beats off on held-out leg usage/gait without newfalls or command/slip regression; equality means no demonstrated benefit at this duration. No automatic additional budget or final walking/joystick qualification.

**verdict**: CANARY PASS - matched control, no charge efficacy shown (per its own pre-registered gate). Matched +10M charge=0 continuation from the same corrected 2M s1 source/RNG3/8-way panel as the charge-on sibling guardfix-acq10m. Own health: gait_valid 21/24 (det 5/6, sto 6/6, sj/det 6/6, sj/sto 4/6), 0 falls/terminations in all 24 episodes -- EXACT SAME 3 failing episodes/chronic legs as the pre-continuation 2M source (det/0 leg5, sj/sto ep2 leg5, sj/sto ep3 leg0): flat retention, no new chronic sacrifice, no regression from removing the charge. Comparative read vs the matched charge-on sibling (same source, only walk_leg_duty_ratio_charge 150 vs 0): ON gait_valid is 22/24 (+1, exactly the det/0 episode that stays failed here) but that is NOT a clean win -- mean slip_per_m is HIGHER for ON in ALL 4 groups (nominal-det 11.34 vs 10.02, nominal-sto 7.60 vs 6.89, jitter-det 9.04 vs 8.65, jitter-sto 12.79 vs 12.18) and mean progress_ratio is LOWER for ON in 3/4 groups (nominal-sto 1.159 vs 1.248, jitter-det 1.064 vs 1.099, jitter-sto 0.691 vs 0.725; only nominal-det ticks up 0.898 vs 0.888). The gate credits the continued-charge hypothesis "only if on beats off ... without command/slip regression" -- ON fails that bar (broad slip regression, mixed progress). VERDICT: no demonstrated efficacy for continuing walk_leg_duty_ratio_charge past the shared 2M exposure at this 10M depth; the 21->22 gait_valid flip is better read as noise than as a charge-causal recovery. Study on the s1/RNG3 pair is CLOSED; no further budget from this arm. The independent s0/RNG2 on10m/offctrl10m pair (root-owned) is the cross-lineage replication check, not yet evaluable (no gate artifacts synced). Evidence: logs/ckpt_eval/cw_walkscratch_crutchoff_s1_widen8_legdutyratio_offctrl10m_gate/report.json vs .../_guardfix_acq10m_gate/report.json vs .../legdutyratiofresh_guardfix1_gate/report.json (source). W&B 0gfv9tv8.

