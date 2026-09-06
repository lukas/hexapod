# cw-assistfade-rung2-anchorfade-s1-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL - INFORMATIVE

**created**: 2026-09-06T11:28:53+00:00

**pod**: hexapod-mjx-train-9

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1

**wandb_id**: al3k8stz

**hypothesis**: Rung-2 anchor-fade-from-random-weights (seed 1) already clears the ignition bar at 2M under the strong anchor but the in-training anneal-gate assay never latched (early_term_rate 0.25 in n=8 samples, same pattern as -s0). More steps give the periodic assay (every 500k) many more chances to hit a clean batch, latch ignition_gate_pass, and drive bc_anchor_coef through its 4M-step anneal to 0 -- the doc's real downstream gate is deterministic held-out behavior WITH the anchor at/near zero, not under it.

**gate**: ACQUISITION continuation (8M new steps, 10M cumulative), not a fresh canary. PASS/CONTINUE if: (a) bc_anchor_anneal/gate_pass latches at least once and bc_anchor_anneal/coef visibly ramps down in wandb_history, AND (b) the held-out det+sto gate eval post-anneal still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. CONTINUE (not fail) if the anchor has still not annealed by 10M cumulative but reward/progress keep climbing and gait stays intact. FAIL - MECHANISM only if the anchor loss diverges/NaNs, or the held-out gait collapses (sacrificed leg, falls) at this budget.

**verdict**: Same fingerprint as sibling -s0-cont8m (already root-caused this cycle by another triage pass, rl_docs/tracks/assistfade/STATUS.md 09-06 ~12:0x): held-out mesh gate eval shows NO gait collapse -- gait_valid 6/6 all 4 modes (walk/walk_startjitter x det/sto), 0 falls/terms, sac=[] everywhere, six-leg cycling (duty 0.61-0.64) on video -- so the pre-registered FAIL-MECHANISM text is not met. But det progress_ratio fell to 0.33 (parent 2M canary: 0.35-0.52, bar 0.35) while sto held 0.35-0.39; slip 3.1-4.2/m, above the 2.9 teacher band. wandb_history confirms the same root cause: the pinned single-seed anneal assay (env.seed(828282) every round, desync off) never latched ignition_gate_pass across all 15 checks over the 8M new steps (bc_anchor_anneal/gate_pass=0 throughout), so bc_anchor_coef never annealed off 3.0 -- the SAME hard init the anchored policy can't fix. The fixed-seed canary regression guard fired identically: canary/walk_fwd_{a,b} pass 1-3M new steps, then fail 0/0 from 5M through the final check at 7.87M, AUTO-STOP at cumulative step 7,870,464 (~130k short of the full 8M budget) while ep_rew_mean kept climbing every quarter (302/1047/1290/1319) -- reward<->eval divergence from the stuck anchor degrading the deterministic mean, not a training collapse. Per 08-21: misalignment to repair, not a lineage kill. The repair (train.bc_anchor_anneal_assay_reseed, default OFF, bit-exact, 9 tests green) is already built+snapshotted and both seeds already relaunched from the PARENT 2M checkpoints as cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m (currently training per this cycle's roster) -- no further action needed on this exact lineage; that pair is the next real read.

