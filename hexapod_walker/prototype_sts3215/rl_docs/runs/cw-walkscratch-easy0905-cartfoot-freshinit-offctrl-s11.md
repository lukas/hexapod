# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T06:31:10+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**wandb_id**: c2vthugj

**hypothesis**: Matched joint-space fresh-init control for cartfoot-freshinit-c1-s11 (same seed 11, no cart_foot keys) -- isolates the decode effect from seed/recipe drift; 3rd independent-seed replicate of the base-s0..s4 fresh-init family.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as base-s0/s1/s7 used, NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond settled stance on eval video/telemetry; motor contract sane; reward agrees with the WALKSCRATCH_EASY semantics bank. Read the seed7/seed10/seed11 ON arms TOGETHER for an n=3 ignition-health seed-pass-rate read, each against its own matched OFF control where available (s7, s11): HEALTHY-PARITY if all/most ON arms show finite losses + real excursion + bank agreement matching their OFF controls/base-s0..s4; HEALTHY-BUT-INCONCLUSIVE if none show excursion (matches base-s0 itself at 2M); FAIL-MECHANISM-SPECIFIC if ON arms systematically stay statue/degenerate while OFF controls ignite normally. No walking-quality claim at this depth.

