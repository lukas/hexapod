# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1-torque1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T08:08:13+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1

**hypothesis**: Plain English: does the fresh-scratch Cartesian-foot walker keep walking when the 3x torque training-wheels are removed, or does it need the extra torque to stand and step? 2M warm continuation of the FROZEN 40M parent cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1 (ckpt sha256 569dfa7f5851307839559b53f636754d9c599432979707198a061597ceb78579, mesh_mjx twin 0-mesh/91-geom 4.806kg), changing ONLY dr.torque_scale 3,3->1,1; seed 7, rewards/PPO/motor limits/cart extents .06/.035/.04 unchanged; matched OFF sibling launched same cycle. Frozen protocol: artifacts/rl_watchdog/cartfoot_fresh_torque_guidance_20260908/PLAN.md (operator-authorized 4M total). Prediction-if-true: zero terminations, movement floor held, gait_valid >= own 3x source count 23/24 at 1x. Prediction-if-false: terminations or movement-floor loss at 1x (differential Cartesian torque sensitivity if OFF retains health). Strongest alternative: the frozen parent already passes 1x zero-shot (matched no-training parent-1x baseline eval runs alongside; child==zero-shot is NOT a training gain).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. FROZEN (PLAN.md 2026-09-08 08:02): 4 panels walk det/sto + walk_startjitter det/sto, 6 eps each, seed 0, unchanged evaluator flags, dr.torque_scale=1,1. HEALTH RETAINED = 0 terminations in 24/24 AND median net forward >=0.03 m/s in >=1 ordinary walk panel AND gait_valid >= own 3x source count ON 23/24 (per-panel source 6/6/5/6) AND no NEW recurring sacrificed-leg pattern (leg sacrificed >=3/6 in a panel where source had <3/6; report every leg/panel count incl. chronic deficits). PARTIAL = movement+no-term hold but gait/leg retention fails -> record exact episodes, no promotion, no extension. SEPARATE slip read (not pass/fail): mean slip/m all 4 panels for source3x vs zero-shot parent1x vs trained child1x; trained ON/OFF ratio <=1.2 in >=3/4 panels supports slip parity. Compare vs frozen-parent zero-shot 1x baseline before any adaptation claim; audit realized randomization/reset summaries. No automatic 40M continuation, extra seeds, or dose grid.

**refused_reason**: hexapod-mjx-train-1 already runs cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1-cont10m — GPU pods host exactly one run; pick a free GPU pod.

