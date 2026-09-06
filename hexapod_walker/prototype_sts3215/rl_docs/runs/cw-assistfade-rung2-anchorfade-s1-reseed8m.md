# cw-assistfade-rung2-anchorfade-s1-reseed8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - TOOLING (root-caused + fixed this cycle, not a policy failure)

**created**: 2026-09-06T12:07:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1

**wandb_id**: qsqewbb5

**hypothesis**: Twin seed of -s0-reseed8m (same one-cycle batch; seed pass-rate n=2). The anchor-fade mechanism was deadlocked only by its own pinned assay: s1-cont8m showed the identical signature (15/15 assay rounds fail at early_term_rate 0.125, coef stuck 3.0, canary walk_fwd 0/2 from 5M). With fresh assay seeds per round the 2M parent checkpoint (held-out ignition bar pass: prog 0.35-0.51, 24/24 gv, 0 falls) should latch, anneal bc_coef 3->0 over 4M, and keep walking without the anchor. Inits from the parent 2M checkpoint, not the degraded cont8m end.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches and bc_anchor_anneal/coef visibly ramps 3->0 in wandb_history, AND (b) the post-anneal held-out det+sto gate eval still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses (falls/sacrificed leg) as the anchor fades, or the anchor loss diverges/NaNs. FAIL - ASSAY-DISTRIBUTION if reseeded rounds STILL never latch across >=8 rounds with early_term persistently >0 (genuine high fall rate on the training distribution, contradicting the held-out 0/24 read). Canary walk_fwd auto-stop stays armed; a stop DURING the fade with reward rising is read per the 08-21 ruling against the coef value at stop time.

**verdict**: Result: held-out mesh gate eval clears the ignition bar on ALL 4 modes -- gait_valid 24/24, 0 falls/terms, sac=[] everywhere, six-leg cycling on video, progress_ratio 0.35/0.40/0.38/0.40 (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto respectively) -- clause (b) of the pre-registered gate is essentially MET even with the anchor still stuck at its full strength. But clause (a) (anneal-gate latch + coef ramp 3->0) never had a chance: bc_anchor_anneal/gate_pass=0 in all 15 in-training checks over the full 8M budget, coef pinned at 3.0 the whole run, reward still rising every quarter (302/1054/1300/1317, no plateau). Root cause (shared with the -s0 twin, verdicted this same cycle): train_ppo_mjx._BcAnchorAnnealGateCb._build() never isolated the in-training ignition assay's goal generator to pure walk (missing the same post-construction set_goal_mix call the main training venv gets, and missing goal.walk_pure's construction-time isolation) -- so ~50-60% of assay episodes silently drew a non-walk goal (config.yaml default mix: p_hold/p_lean/p_track/p_unload/p_raise/p_rise all nonzero) with no .vx trajectory, and a single such episode's resulting cmd_prog_frac=nan poisons aggregate_walk_probe's plain-mean for the WHOLE round regardless of the actual fall rate -- confirmed via a standalone GPU repro reproducing the exact nan pattern with a trivial zero-action policy, then eliminating it (0/8 nan across 3 reseeded rounds after the fix vs 5-6/8 before). This is NOT a policy failure: this seed's own held-out numbers already clear the ignition bar cleanly under the still-strong anchor, better than the -s0 twin. Fixed this cycle (train_ppo_mjx.py _BcAnchorAnnealGateCb._build, forces zero-every-p-mode then p_walk=1.0 via set_goal_mix, mirroring eval_checkpoint.py ALL_MODES isolation and goal.walk_pure), 2 new regression tests (test_walkcurr_mjx.py), 137+21 existing tests green, snapshot exp/bc-anchor-anneal-goalmix-fix. Next: relaunch the identical rung-2 recipe from the same 2M parent checkpoint with the fix in place (cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix) -- given this seed already clears the bar under the stuck anchor, expect the gate to latch within the first 1-2 checks this time.

