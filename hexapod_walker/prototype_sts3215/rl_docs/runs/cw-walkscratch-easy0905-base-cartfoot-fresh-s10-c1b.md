# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS - PARITY (BAND-MATCH, non-blocking det quirk)

**created**: 2026-09-08T06:47:32+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10

**wandb_id**: d9xbrnil

**hypothesis**: Corrected relaunch of s10-c1 (crashed <1s on the documented --activation-fn+--init-from SystemExit gotcha, zero steps logged). Own-checkpoint continuation of the fresh-init cart-foot canary (fork b, seed 10): does the same +38M budget that took base-s0..s4 from 2M cold start to their established PASS band (six-leg walking, zero falls) also get the fresh cart-foot ON arm there, and if so does its MATURE slip/m beat or lose to that established band -- the fork(b) question fork(a)'s warm-start retrofit could not answer cleanly.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0..s4) on the same fixed-forward walk panel -- report slip/m specifically vs that band. FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could. Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.

**verdict**: Result: fork(b) fresh-init cart_foot ON, seed10, 40M cumulative -- matches the base family's own established PASS band on falls/distance/slip: 0/24 falls, fwd_dist_m med 3.00-3.72m/20s (0.13-0.19 m/s), slip_per_m med 2.61-3.70 (det 2.61-2.71 inside the 2.6-3.4 band; sto 3.21-3.70 at/slightly above it), reward rising every quarter (-496.8->634.6->1386.8->1660.9, no plateau). Evidence: det mode identically sacrifices leg[1] (walk/det) or [1]/[4]/[1,4] (walk_startjitter/det) every episode -- duty_cycle 0.07-0.12 vs siblings' 0.51-0.58 -- gait_valid 0/6 both det scenarios; but this vanishes completely under stochastic action noise (gait_valid 6/6, all legs duty>=0.13 in both sto scenarios), and swing_count for the 'sacrificed' legs is 72-100 (still cycling, not frozen at 0 like the gSDE chronic-park class). Why: this is the SAME fingerprint STATUS.md already recorded as a non-gate-blocking base/halfgrav-family quirk (halfgrav-s0-c1: 'repeatable leg-1 underuse -- duty 0.09 vs 0.3+ siblings -- vanishes under sto/jitter'), not a new cart_foot-specific pathology -- reinforces (does not contradict) fork(b)'s parity finding from seed7. Frame strips (walk_det_0, walk_sto_0) show steady forward body translation both modes, no drag/flag-leg visible on video. What's next: this is the 3rd fresh-init seed (after seed7 PASS-parity, seed11 pending); the matched OFF control for THIS seed (cartfoot-freshoffctrl-s10-c1) is still training on another pod -- read it before drawing a seed10-specific ON-vs-OFF slip-ratio conclusion; until then this stands as an absolute-band match, not yet a ratio comparison.

