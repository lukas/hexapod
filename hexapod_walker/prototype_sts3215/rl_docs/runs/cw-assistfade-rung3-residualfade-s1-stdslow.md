# cw-assistfade-rung3-residualfade-s1-stdslow

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T19:09:44+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: zogkl69o

**hypothesis**: Same as -s0-stdslow (see its own hypothesis): rung 3's 2/2 CANARY FAIL-MECHANISM traced to a schedule collision between the residual-blend anneal (0.05->1.0 over 0->1.4M/2M steps) and --log-std-anneal-frac=1.0 (log_std anneal on the SAME clock) squeezing exploration to std~0.05 exactly when the policy must adapt to losing reference authority. Single-lever fix: --log-std-anneal-frac=3.0 (std only ~1/3 annealed by 2M steps, ~0.19 vs ~0.05) leaving the blend schedule and every other lever unchanged. Seed 1, paired with -s0-stdslow for the same 2/2-seed read this track has used at every rung so far.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same text as the parent canary): ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal before concluding std-vs-schedule.

**verdict**: CANARY FAIL - MECHANISM: ignition gate NOT MET, std-anneal-frac lever did not rescue rung-3 residual-fade on seed 1 -- FAILED WORSE than the parent, not better. Evidence: logs/ckpt_eval/cw_assistfade_rung3_residualfade_s1_stdslow_gate/report.json (dr=0.0, held-out det+sto, DR-0): walk/det med progress 0.03 (bar 0.35, ~12x short), fwd 0.01m, slip/m 8.95, gait_valid nominally 6/6 BUT every single one of the 24 eval episodes across all 4 modes (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) terminates over_current -- the parent (non-stdslow) run only had over_current in a subset (4-7/12) of the startjitter panel, so widening --log-std-anneal-frac 1.0->3.0 turned a partial over_current fingerprint into a universal one. walk_startjitter gait_valid collapses to 1/6 det, 1/6 sto with chronic 1-3-leg sacrifice (sac [5],[5],[2,5],[1,3,5],[4] across det episodes). W&B (zogkl69o): reward quarters [101.1, 163.6, 172.3, 123.6] -- same Q3->Q4 decline shape as the parent's schedule-collision fingerprint despite the wider std floor, so the anneal-frac widening did not change the qualitative failure mode, only its severity. Contact sheets (walk_det_0..5) show the robot essentially frozen near its start pose for the full 10s episode -- no sustained forward translation, consistent with the 0.01m median displacement. Why: this is exactly the STATUS.md ~19:3x entry's own pre-registered FAIL-if branch ('if this ALSO fails the same way, the compounding is not std-related') -- the single-lever std-anneal-frac fix is REFUTED for seed 1 (and by the same-day sibling report, seed 0 shows the identical <0.35 progress / 0/6 gait_valid pattern too, though that file is left for its own claim, not verdicted here to avoid a duplicate). Not a mechanism kill -- the residual-blend action mechanism itself stays bank-proven; this is a schedule-parameter miss, now on its second lever. What's next: per the pre-registered fallback, do NOT repeat the log-std-anneal-frac lever a second time -- the next retreat is either a later/slower blend t1_steps (push the handover further past 1.4M so more of the run's budget is genuinely unassisted-and-learning before eval) or a longer total step budget for the same schedule.

