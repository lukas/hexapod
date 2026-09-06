# cw-assistfade-rung3-residualfade-s1-latehandover

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T19:38:45+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**hypothesis**: Same as -s0-latehandover (see its own hypothesis): rung 3's schedule-collision FAIL reproduced worse on the std-anneal-frac lever (both -s0-stdslow and -s1-stdslow read <0.35 progress with over_current in every eval mode); per the pre-registered fallback, this arm changes ONLY sched.t1_steps (1.4M->1.7M, gentler/later blend handover within the 2M canary-phase cap) and reverts log-std-anneal-frac to the original 1.0. Seed 1, paired with -s0-latehandover for the same 2/2-seed read this track has used at every rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Identical ignition text to every rung-3 canary: sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes (det+sto, walk + walk_startjitter, DR-0, held-out). MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal before concluding schedule-shape-vs-mechanism.

**verdict**: CANARY FAIL - MECHANISM: the later-handover schedule fix (sched.t1_steps 1.4M->1.7M, single lever vs the failed parent) does NOT rescue rung 3 on seed 1 -- held-out DR-0 gate (dr=0.0, det+sto x walk/walk_startjitter, n=24): progress_ratio med 0.01 (walk/det), 0.05 (walk/sto), 0.04/0.06 (startjitter det/sto) -- ALL ~6-35x short of the 0.35 ignition bar, essentially UNCHANGED from (if anything slightly worse than) the un-fixed parent's own 0.03-0.06 med. walk/det+sto read gait_valid True (no chronically-parked leg) but forward_dist_m is only 0.03-0.06m/10s with slip/m 15-21 -- video (walk_det_0_sheet.png) confirms the body stays essentially in place across all 6 sampled frames while legs shuffle/slip, not real translation. walk_startjitter shows the same chronic 1-3-leg sacrifice + over_current safety terminations as the parent (4/6 det, 3/6 sto terminate). Reward quarters [100.9,180.6,244.7,249.7] are RISING (unlike stdslow's decline) -- checked per the 08-21 ruling before concluding: this is NOT a case of 'reward rising, eval just needs longer', because the sibling budget lever (-longbudget, 3x the steps) on the SAME schedule-collision root cause already shows this exact axis is budget-sensitive (s0-longbudget hit prog 0.27 at 6M) while this 2M later-handover fix shows literally zero measurable gain over the already-failed 2M parent -- the schedule tweak itself is not converting rising reward into any held-out progress, so the specific lever (t1_steps 1.7M) is refuted regardless of reward shape. Matches the pre-registered gate text's fail branch (progress<0.35 + over_current reappearing in startjitter). Not a kill of the residual-blend mechanism itself (stays bank-proven); closes 'later handover' as a repair lever for THIS seed (2/2 with s0-latehandover, see its own verdict) -- the surviving open fork is budget (longbudget, DIG-IN in progress on s0, s1 still computing).

