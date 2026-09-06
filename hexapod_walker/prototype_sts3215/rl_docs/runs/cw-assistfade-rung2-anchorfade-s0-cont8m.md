# cw-assistfade-rung2-anchorfade-s0-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T11:24:55+00:00

**pod**: hexapod-mjx-train-8

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0

**hypothesis**: Rung-2 anchor-fade-from-random-weights (seed 0) already clears the ignition bar at 2M under the strong anchor (prog 0.36-0.52, gv 24/24, 0 falls) but the in-training anneal-gate assay never latched (early_term_rate 0.25 in n=8 samples). More steps give the periodic assay (every 500k) many more chances to hit a clean batch, latch ignition_gate_pass, and drive bc_anchor_coef through its 4M-step anneal to 0 -- the doc's real downstream gate is deterministic held-out behavior WITH the anchor at/near zero, not under it.

**gate**: ACQUISITION continuation (8M new steps, 10M cumulative), not a fresh canary. PASS/CONTINUE if: (a) bc_anchor_anneal/gate_pass latches at least once and bc_anchor_anneal/coef visibly ramps down in wandb_history, AND (b) the held-out det+sto gate eval post-anneal still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. CONTINUE (not fail) if the anchor has still not annealed by 10M cumulative but reward/progress keep climbing and gait stays intact (rung1's own bcinit-taskonly canary needed +8M just to close its speed shortfall). FAIL - MECHANISM only if the anchor loss diverges/NaNs, or the held-out gait collapses (sacrificed leg, falls) at this budget.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

