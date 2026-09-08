# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1-torque1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T08:14:09+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

**wandb_id**: c4inur4k

**hypothesis**: Plain English: matched joint-space control for the Cartesian torque-removal canary — does the fresh-scratch JOINT-space walker keep walking when the 3x torque training-wheels are removed? 2M warm continuation of the FROZEN 40M parent cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1 (ckpt sha256 f4b962c1a851b2b413625d631969b9d63e509633f2f64629733c2141982d014e, mesh_mjx twin 0-mesh/91-geom 4.806kg), changing ONLY dr.torque_scale 3,3->1,1; seed 7, rewards/PPO/motor limits unchanged, no cart_foot keys; matched ON sibling launched same cycle. Frozen protocol: artifacts/rl_watchdog/cartfoot_fresh_torque_guidance_20260908/PLAN.md (operator-authorized 4M total). Prediction-if-true: zero terminations, movement floor held, gait_valid >= own 3x source count 19/24 at 1x. Prediction-if-false: terminations or movement-floor loss at 1x. Strongest alternative: the frozen parent already passes 1x zero-shot (matched no-training parent-1x baseline eval runs alongside; child==zero-shot is NOT a training gain). If only ON fails while OFF retains health, that supports differential Cartesian torque sensitivity in this seed/recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. FROZEN (PLAN.md 2026-09-08 08:02): 4 panels walk det/sto + walk_startjitter det/sto, 6 eps each, seed 0, unchanged evaluator flags, dr.torque_scale=1,1. HEALTH RETAINED = 0 terminations in 24/24 AND median net forward >=0.03 m/s in >=1 ordinary walk panel AND gait_valid >= own 3x source count OFF 19/24 (per-panel source 6/6/1/6; chronic leg-4 sacrifice in walk_startjitter/det 5/6 is a PRE-EXISTING deficit, report it, it does not newly fail retention) AND no NEW recurring sacrificed-leg pattern (leg sacrificed >=3/6 in a panel where source had <3/6; report every leg/panel count). PARTIAL = movement+no-term hold but gait/leg retention fails -> record exact episodes, no promotion, no extension. SEPARATE slip read (not pass/fail): mean slip/m all 4 panels for source3x vs zero-shot parent1x vs trained child1x; trained ON/OFF ratio <=1.2 in >=3/4 panels supports slip parity. Compare vs frozen-parent zero-shot 1x baseline before any adaptation claim; audit realized randomization/reset summaries. No automatic 40M continuation, extra seeds, or dose grid.

