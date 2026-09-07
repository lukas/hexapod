# cw-assistfade-rung1-mesh-noanchor-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-07T11:21:48+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: n6ytiz4r

**hypothesis**: Plain English: is rung 1 of the assistance-removal ladder (BC init, then TASK-ONLY PPO with zero ongoing BC/anchor/imitation) provable on the mesh/100Hz family, closing the one named gap the track's own ledger audit flags as still UNPROVEN (rung0's persistent-anchor RL is proven; primitive-family rung1 evidence from 08-22 doesn't transfer across model families; rungs 2-4 were tried without this baseline ever landing)? Single-lever change vs the proven rung0 canary (cw-walkteach-scripted-allhead-canary-r1, CANARY PASS): same BC-cloned scripted-tripod init, same task/reward diet, bc_anchor_coef/walk_coef/phase_lock all forced to 0.0 from step 0 (no anchor at any point, not even at init) -- does PPO retain the BC clone's already-working gait under pure task reward, or does it revert to the static-stand basin the way rung2's earliest (no-anneal-safety) attempts did before the anchor mechanism was built?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Doc's own rung ignition gate (both this canary depth as a first read, not the full bar): held-out det+sto panel, PASS if: sustained forward translation the whole episode (progress_ratio>=0.35 per the doc, recorded as diagnostic at this 2M canary depth), all six legs participating (no permanently planted leg), zero falls/terminations. CANARY (2M) reads as PASS if reward does not collapse (no NaN/entropy blowup) and the held-out gait panel does not immediately revert to a static stand (progress_ratio clearly above ~0 in det mode); FAIL - MECHANISM if it reverts to the static/near-zero-progress basin within 2M, matching rung2's own early anchor-less failure shape (informative: closes 'skip the anchor entirely' as a rung1 shortcut, motivates why rung0's persistent anchor and rung2's anneal-gated anchor exist).

**verdict**: CANARY PASS -- Rung 1 on mesh/100Hz (BC init, then task-only PPO with ZERO ongoing anchor) retains the scripted-tripod BC clone's gait at 2M canary depth -- the first exact mesh-family rung-1 data point the track's own ledger audit flagged UNPROVEN. Evidence: held-out gate gait_valid 23/24 across walk+walk_startjitter det+sto (only one sto ep sacrifices legs [0,1,5] under an over_current term), progress_ratio med 0.16-0.24 (clearly above the static-basin floor, not yet the mature 0.35 ignition bar), duty_cycle/swing_count nonzero on all six legs every episode, video (walk_det_2) shows genuine forward translation with alternating support, not a static pose. 4/24 episodes hit an over_current safety termination and slip/m runs 5-11 (well over the 2.9 mature band) -- expected/not-gated at this canary tier per the run's own pre-registered text ('slip and current recorded but not held to the mature band at ignition'). Reward quarters [69.6,64.2,55.0,75.8], non-collapsing. This refutes 'skipping the anchor entirely reverts immediately to the static basin' as a rung-1 shortcut failure. Next: same-seed 12M acquisition depth read + a second seed for the doc's required both-seeds read -- both launched this cycle (cw-assistfade-rung1-mesh-noanchor-s0-acq12m, -s1).

