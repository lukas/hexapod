# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T06:22:39+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: xlzhnck1

**hypothesis**: Matched joint-space fresh-init control for cartfoot-freshinit-c1-s7 (same seed 7, byte-identical base-pilot recipe, no cart_foot keys) -- isolates whether any ignition-health difference is caused by the action decode rather than seed/recipe drift; also serves as an independent-seed replicate of the already-proven base-s0/s1 fresh-init arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as base-s0/s1 used, NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond settled stance on eval video/telemetry; motor contract sane (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY semantics bank (park~0, movement income positive, no opening-stop windfall). Read the ON/OFF pair TOGETHER: HEALTHY-PARITY if both show finite losses + real excursion + bank agreement (foot-space cold-starts as cleanly as joint-space); HEALTHY-BUT-INCONCLUSIVE if NEITHER shows excursion (matches base-s0 itself at 2M, needs continuation before any comparative claim); FAIL-MECHANISM-SPECIFIC if ON stays statue/degenerate while OFF ignites normally (joint-space cold-start advantage). No walking-quality claim at this depth either way.

