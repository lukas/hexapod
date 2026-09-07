# cw-assistfade-rung1-mesh-noanchor-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T11:21:48+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: n6ytiz4r

**hypothesis**: Plain English: is rung 1 of the assistance-removal ladder (BC init, then TASK-ONLY PPO with zero ongoing BC/anchor/imitation) provable on the mesh/100Hz family, closing the one named gap the track's own ledger audit flags as still UNPROVEN (rung0's persistent-anchor RL is proven; primitive-family rung1 evidence from 08-22 doesn't transfer across model families; rungs 2-4 were tried without this baseline ever landing)? Single-lever change vs the proven rung0 canary (cw-walkteach-scripted-allhead-canary-r1, CANARY PASS): same BC-cloned scripted-tripod init, same task/reward diet, bc_anchor_coef/walk_coef/phase_lock all forced to 0.0 from step 0 (no anchor at any point, not even at init) -- does PPO retain the BC clone's already-working gait under pure task reward, or does it revert to the static-stand basin the way rung2's earliest (no-anneal-safety) attempts did before the anchor mechanism was built?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Doc's own rung ignition gate (both this canary depth as a first read, not the full bar): held-out det+sto panel, PASS if: sustained forward translation the whole episode (progress_ratio>=0.35 per the doc, recorded as diagnostic at this 2M canary depth), all six legs participating (no permanently planted leg), zero falls/terminations. CANARY (2M) reads as PASS if reward does not collapse (no NaN/entropy blowup) and the held-out gait panel does not immediately revert to a static stand (progress_ratio clearly above ~0 in det mode); FAIL - MECHANISM if it reverts to the static/near-zero-progress basin within 2M, matching rung2's own early anchor-less failure shape (informative: closes 'skip the anchor entirely' as a rung1 shortcut, motivates why rung0's persistent anchor and rung2's anneal-gated anchor exist).

