# cw-assistfade-rung2-anchorfade-s1-cont8m-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-06T11:30:46+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1

**hypothesis**: Rung-2 anchor-fade-from-random-weights (seed 1) already clears the ignition bar at 2M under the strong anchor (prog 0.35-0.51, gv 24/24, 0 falls) but the in-training anneal-gate assay never latched (early_term_rate 0.25 in n=8 samples), matching seed 0's own read. More steps give the periodic assay many more chances to latch ignition_gate_pass and drive bc_anchor_coef through its 4M-step anneal to 0 -- pairs with the already-running s0-cont8m to give this rung its first n=2 anneal-to-completion read.

**gate**: ACQUISITION continuation (8M new steps, 10M cumulative), not a fresh canary. PASS/CONTINUE if: (a) bc_anchor_anneal/gate_pass latches at least once and bc_anchor_anneal/coef visibly ramps down in wandb_history, AND (b) the held-out det+sto gate eval post-anneal still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. CONTINUE (not fail) if the anchor has still not annealed by 10M cumulative but reward/progress keep climbing and gait stays intact. FAIL - MECHANISM only if the anchor loss diverges/NaNs, or the held-out gait collapses (sacrificed leg, falls) at this budget.

**verdict**: Accidental duplicate: an earlier respec invocation for cw-assistfade-rung2-anchorfade-s1-cont8m timed out client-side mid-launch and was retried, producing this -rr1 twin on a second pod (train-2) instead of confirming the original had already landed on train-9. Killed immediately on discovery (identical recipe/seed/parent to the healthy s1-cont8m already running) to free the GPU slot and avoid double-counting this cycle's launch/step budget. No information lost -- s1-cont8m (train-9) is the surviving run and is the one to read.

