# cw-assistfade-rung1-mesh-noanchor-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T12:14:19+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-assistfade-rung1-mesh-noanchor-s0

**wandb_id**: ifih9o5t

**hypothesis**: Plain English: does rung 1 (BC init, then task-only PPO with zero ongoing anchor) hold on a SECOND seed, or was s0's clean six-leg retention a seed-specific fluke? Byte-identical recipe to cw-assistfade-rung1-mesh-noanchor-s0 (same BC-cloned scripted-tripod init, bc_anchor_coef/walk_coef/phase_lock=0.0 from step 0), only --seed changes 0->1. s0 landed CANARY PASS at mechanism-health tier (gait_valid 23/24 across walk/walk_startjitter det+sto, progress_ratio med 0.16-0.24, six legs cycling on video, only 4/24 episodes hit a safety termination) but the doc's own ignition gate requires BOTH seeds before advancing the rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same mechanism-health CANARY-tier bar as s0: PASS if reward does not collapse (no NaN/entropy blowup) and the held-out walk panel does not immediately revert to a static stand (progress_ratio clearly above ~0 in det mode, most episodes gait_valid with no permanently-sacrificed leg); FAIL - MECHANISM if it reverts to the static/near-zero-progress basin within 2M matching rung2's own early anchor-less failure shape. This is diagnostic only -- the FULL ignition bar (progress_ratio>=0.35, zero falls/terminations, both seeds) needs the longer acquisition follow-up, not this 2M read.

