# cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T06:28:34+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: w31jriiu

**hypothesis**: Matched control for cw-walkscratch-easy0905-base-cartfoot-fresh-s10: byte-identical fresh-init easy0905 base recipe (fixed 0.06 m/s forward, no heading, no DR), same seed 10, but cart_foot keys left at their bit-exact-off default (plain joint-space decode). Isolates whatever the ON arm shows to the cart_foot mechanism itself rather than seed variance.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Should reproduce the base family's own established shape (finite losses, real gait emerging over the canary->acquisition arc, eventual PASS-band gait_valid/slip/no-falls matching base-s0/s1/s2/s3/s4). Any large unexplained deviation from that established band at matched seed would itself be a finding (seed-10 anomaly) separate from the cart_foot comparison. This is the required control for the fresh-init cart-foot mechanism read; do not verdict the ON arm without it.

**verdict**: CANARY PASS (matched control for base-cartfoot-fresh-s10, fork b): byte-identical easy0905 base recipe, seed 10, cart_foot keys at their bit-exact-off default. Finite losses (train/loss 655->347, value_loss 1420->845, declining), real telemetry excursion (walk_speed 0.11-0.14 m/s, loadslip_ratio 8->23) over the full 2,097,152 steps -- same shape as base-s0's own 2M history, no seed-10 anomaly. Tracks the ON arm within a few percent on every telemetry channel (HEALTHY-PARITY, recorded on the ON arm's own verdict). Valid, undrifted control.

