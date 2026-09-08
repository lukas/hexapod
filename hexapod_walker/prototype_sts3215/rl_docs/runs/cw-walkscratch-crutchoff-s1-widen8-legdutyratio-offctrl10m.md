# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-offctrl10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T01:47:09+00:00

**pod**: hexapod-mjx-train-8

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: 0gfv9tv8

**hypothesis**: Matched charge-off control for the completed +10M active leg-duty-ratio acquisition. The 2M corrected s1 canary is healthy (21/24 gait,0 falls) but did not improve over its actual init, and comparison to an older40M undosed run confounds dose and duration. This new bounded +10M control starts from the EXACT SAME corrected2M checkpoint MD5edfa283302954b40103334227eb3db1c, RNG3, schedule/8wayheading/DR/motor limits and all other args as cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m; ONLY reward.walk_leg_duty_ratio_charge changes150 to0. It tests continued-charge benefit versus removal after a shared2M exposure, not never-exposed training or seed robustness. This is one planned comparison arm, not a new seed or a duplicate charge-on continuation. Prior-free/noBC/no gait clock retained. Reward-scale values across arms are not evidence of behavioral improvement.

**gate**: Matched +10M control comparison only. Use exact same24episode walk/startjitter det+sto panel, evalseed0 and normal cadence. Require0newfalls, gait_valid>=21/24 and noNEWchronic single-leg sacrifice relative to shared corrected2M source; report per-leg relative duty, command progress, slip bygroup and paired episode changes for charge-on/off. If health regresses, preserve checkpoint and follow existing pruner rules; do not accept worsening gait because return rises. Credit the continued-charge hypothesis only if on beats off on held-out leg usage/gait without newfalls or command/slip regression; equality means no demonstrated benefit at this duration. No automatic additional budget or final walking/joystick qualification.

