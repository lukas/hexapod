# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-08T06:35:58+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10

**wandb_id**: 1fk8b959

**hypothesis**: Own-checkpoint continuation of the fresh-init cart-foot canary (fork b): the 2M cold-start read (this run + the concurrent cycle's matched freshinit-c1/offctrl-s7 pair) found HEALTHY-PARITY -- ON and OFF are statistically indistinguishable at 2M (walk_speed ~0.10-0.15 m/s, loadslip_ratio ~19-22, freeprog_score ~-0.44 to -0.65, nearly identical across both mechanisms AND both seeds 7/10) -- i.e. no cold-start inductive-bias handicap for the Cartesian foot-target decode, but also too early for any slip/quality claim (matches base-s0's own history, which needed the full continuation to actually walk). This run asks whether the SAME +38M budget that took base-s0/s1/s2/s3/s4 from 2M cold start to their established PASS band (six-leg walking, zero falls) also gets the fresh cart-foot arm there, and if so whether its MATURE slip/m beats or loses to that established band -- the actual fork(b) question fork(a)'s warm-start retrofit could not answer cleanly.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0/s1/s2/s3/s4) on the same fixed-forward walk panel -- then report its slip/m specifically vs that band (does foot-space parameterization help, hurt, or tie, learned fully from scratch with no warm-start confound). FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could (mechanism-specific from-scratch handicap). Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.

**failed_reason**: W&B global_step not advancing (0 -> 0) after 210s (n_steps=128, cpu-time flat for 2 polls)

