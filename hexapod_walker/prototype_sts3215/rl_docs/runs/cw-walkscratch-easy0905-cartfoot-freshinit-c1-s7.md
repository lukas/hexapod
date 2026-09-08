# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T06:23:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: 7poujbfm

**hypothesis**: Does the Cartesian foot-space action decode bootstrap walking from a random policy as well as the joint-space decode does, on the one recipe in this campaign proven to learn walking from scratch (easy0905 base pilot), avoiding the mature-composite cold-start confound flagged 09-08 ~06:1x. If TRUE: this fresh cart_foot arm reaches the same 2M WALKSCRATCH_EASY mechanism-health bar (finite losses, real joint/foot excursion beyond settled stance, reward-bank agreement) as base-s0/s1 did -- foot-space parameterization is not a cold-start handicap. If FALSE: this arm stays a statue / produces degenerate excursion or nonfinite output at 2M while the matched offctrl-s7 (same seed, joint-space) ignites normally -- showing joint-space carries an inductive-bias advantage that specifically matters at COLD START, not only at retrofit depth. Strongest alternative: NEITHER arm ignites at 2M (matching base-s0/s1's own history, which needed continuation past 2M to actually walk) -- inconclusive for a cold-start comparison; both would need the same further continuation before any comparative claim.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as base-s0/s1 used, NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond settled stance on eval video/telemetry; motor contract sane (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY semantics bank (park~0, movement income positive, no opening-stop windfall). Read the ON/OFF pair TOGETHER: HEALTHY-PARITY if both show finite losses + real excursion + bank agreement (foot-space cold-starts as cleanly as joint-space); HEALTHY-BUT-INCONCLUSIVE if NEITHER shows excursion (matches base-s0 itself at 2M, needs continuation before any comparative claim); FAIL-MECHANISM-SPECIFIC if ON stays statue/degenerate while OFF ignites normally (joint-space cold-start advantage). No walking-quality claim at this depth either way.

