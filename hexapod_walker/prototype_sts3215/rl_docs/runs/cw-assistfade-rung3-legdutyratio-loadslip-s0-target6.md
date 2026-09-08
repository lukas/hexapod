# cw-assistfade-rung3-legdutyratio-loadslip-s0-target6

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T13:48:46+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-loadslip-s0

**wandb_id**: uey1ws97

**hypothesis**: Companion to the walkcurr target-calibration respec: does the load-slip charge stop making rung3's held-out walk/det+sto panel outright WORSE once its target is calibrated from real data? A zero-training diagnostic (rl_move/sim/calibrate_loadslip_target.py, replays the matched bare-duty legdutyratio-s0 checkpoint's own deterministic walk with goal.walk_contact_diagnostics=1, blend=1.0 post-anneal) measured this rung3 lineage's own worst-leg peer-ratio distribution: p10=1.0, p50=1.40, p90=5.60, p95=8.09 (n=2000 walk ticks -- only 2/6 episodes registered walk ticks on this residual-gated recipe, a smaller/noisier corpus than the walkcurr read but the SAME direction and similar magnitude). The assumed target=1.5 sits at roughly this population's own p25-p50, not a tail threshold, so the excess-above-target charge fires on the majority of ticks for a normal gait rather than singling out a genuinely bad leg -- plausibly why even a tiny measured excess (0.02-0.08 the whole run) still tracked with a real held-out slip regression. Single-lever change vs the closed loadslip-s0 sibling: target 1.5->6.0 only, same charge=150/seed/lineage/budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: (a) telemetry finite. (b) zero new falls/terminations vs the matched legdutyratio-s0 (bare duty-charge) sibling. (c) same per-leg slip/duty comparison the original loadslip-s0 gate used: PASS-if the held-out walk/det+sto panel's slip narrows or at minimum stops being outright worse than the bare-duty baseline (12.67/16.71 det/sto slip med) -- FAIL-MECHANISM again if still indistinguishable or worse, in which case the calibration fix alone does not rescue this lever on rung3 and a genuinely different mechanism is owed.

