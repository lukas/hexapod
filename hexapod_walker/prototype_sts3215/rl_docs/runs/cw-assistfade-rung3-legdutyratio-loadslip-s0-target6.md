# cw-assistfade-rung3-legdutyratio-loadslip-s0-target6

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T13:48:46+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-loadslip-s0

**wandb_id**: uey1ws97

**hypothesis**: Companion to the walkcurr target-calibration respec: does the load-slip charge stop making rung3's held-out walk/det+sto panel outright WORSE once its target is calibrated from real data? A zero-training diagnostic (rl_move/sim/calibrate_loadslip_target.py, replays the matched bare-duty legdutyratio-s0 checkpoint's own deterministic walk with goal.walk_contact_diagnostics=1, blend=1.0 post-anneal) measured this rung3 lineage's own worst-leg peer-ratio distribution: p10=1.0, p50=1.40, p90=5.60, p95=8.09 (n=2000 walk ticks -- only 2/6 episodes registered walk ticks on this residual-gated recipe, a smaller/noisier corpus than the walkcurr read but the SAME direction and similar magnitude). The assumed target=1.5 sits at roughly this population's own p25-p50, not a tail threshold, so the excess-above-target charge fires on the majority of ticks for a normal gait rather than singling out a genuinely bad leg -- plausibly why even a tiny measured excess (0.02-0.08 the whole run) still tracked with a real held-out slip regression. Single-lever change vs the closed loadslip-s0 sibling: target 1.5->6.0 only, same charge=150/seed/lineage/budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: (a) telemetry finite. (b) zero new falls/terminations vs the matched legdutyratio-s0 (bare duty-charge) sibling. (c) same per-leg slip/duty comparison the original loadslip-s0 gate used: PASS-if the held-out walk/det+sto panel's slip narrows or at minimum stops being outright worse than the bare-duty baseline (12.67/16.71 det/sto slip med) -- FAIL-MECHANISM again if still indistinguishable or worse, in which case the calibration fix alone does not rescue this lever on rung3 and a genuinely different mechanism is owed.

**verdict**: CANARY FAIL - MECHANISM per its own explicit gate: vs the matched bare-duty-charge legdutyratio-s0 sibling (slip 12.67 det / 16.71 sto), the recalibrated target=6.0 loadslip charge makes walk/det WORSE (15.80, +25%) and leaves walk/sto indistinguishable (17.17, +2.8%, within noise) -- the gate's own criterion (c) text says exactly this ('indistinguishable or worse') is a FAIL-MECHANISM. Falls/gait_valid did NOT regress (criterion b holds: walk_startjitter/det improves 2/6->5/6 gait_valid with 5->1 fewer over_current terms; walk_startjitter/sto holds flat at 4 terms, gv 1/6->2/6) so this is not a safety regression, just no slip benefit on the rung3 lineage. Reward trajectory is healthy (quarters 102/174/222/128, no collapse, unlike the widen8-crutchoff-s0 sibling of this same target6 recalibration -- the collapse there is lineage/reward-scale specific, not inherent to the mechanism). Recalibrating the target from p10 to p90 does not rescue this lever on rung3; a genuinely different mechanism is owed here per the gate's own pre-registered fallback, not a further loadslip-charge dose/target sweep on this lineage.

