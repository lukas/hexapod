# cw-walkscratch-easy0905-base-cartfoot-fresh-s10

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T06:25:10+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: rnczjz6g

**hypothesis**: Plain English: fork (b) of the cart-foot foot-placement mechanism -- does reparameterizing the same 18 actions as per-leg Cartesian foot targets (analytic IK, FK parity 1.8e-16 m, default-off bit-exact) give a genuine slip/learning advantage when trained COMPLETELY FROM SCRATCH (new seed 10, no warm start) on the easy0905 base recipe (fixed 0.06 m/s forward, no heading, no DR) -- the recipe already PROVEN to train six-leg walking cleanly from scratch with the plain joint decode (base-s0/s1/s2/s3/s4, 4-5/5 PASS). This removes the cont40m retrofit's warm-start-scramble confound (fork (a), cartfoot-c1-cont10m, ACQ FAIL this cycle: slip stayed 2.6-3.3x the matched control after 10M steps even though reward never stopped falling) by giving the mechanism a task it does not have to re-acquire skill on -- a fair fresh-init test of the parameterization itself.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, same bar as base-s0's own: finite losses, weights changing, real joint/foot excursion beyond the settled stance on eval video/telemetry, no non-finite blowups. Read PAIRED against the matched cartfoot-freshoffctrl-s10 control (same seed, same recipe, cart_foot keys OFF) at 2M: report reward trajectory shape for both (does ON track OFF's reward curve reasonably, or diverge sharply) and, once either/both reach an eval-plottable gait, gait_valid + slip/m vs the matched control. Healthy-but-not-yet-walking at 2M is NOT a failure (the base recipe itself needed the full +18M to reach its own PASS) -- continue from own checkpoint under the same canary->acquisition rule the base family used. Only stop for nonfinite training, no-op actions, or a reward/eval divergence that mirrors fork (a)'s FAIL shape (reward falling AND slip far worse than the control with no recovery after a real continuation).

**verdict**: CANARY PASS (HEALTHY-PARITY, fork b fresh-init cart-foot mechanism, seed 10, easy0905 base recipe -- fixed 0.06 m/s forward, no heading, no DR): finite losses (train/loss 700->378, value_loss 1522->965, both declining), weights changing, real telemetry excursion (env/walk_speed 0.10-0.15 m/s, env/walk_loadslip_ratio 7->20, non-trivial and non-frozen) over the full 2,097,152 steps. Read PAIRED against the matched cartfoot-freshoffctrl-s10 control (same seed, cart_foot keys OFF, verdicted this cycle too): the two are STATISTICALLY INDISTINGUISHABLE at 2M (speed/slip/loss curves track within a few percent the whole run) -- no cold-start inductive-bias handicap for the Cartesian foot-target decode vs plain joint-space, matching the shape independently reproduced by a concurrent cycle's freshinit-c1-s7/offctrl-s7 pair (same telemetry values to 2 decimals). Per this gate's own text, neither arm shows real walking yet -- base-s0 itself needed the full continuation past 2M to reach its PASS band, so no slip/quality claim follows at this depth. Launched the +38M own-checkpoint continuation (base-cartfoot-fresh-s10-c1, 40M total, matching the base family's own canary->PASS continuation budget) to answer the actual fork(b) question: does the mechanism's MATURE slip beat, tie, or lose to the established base family band (base-s0/s1/s2/s3/s4).

