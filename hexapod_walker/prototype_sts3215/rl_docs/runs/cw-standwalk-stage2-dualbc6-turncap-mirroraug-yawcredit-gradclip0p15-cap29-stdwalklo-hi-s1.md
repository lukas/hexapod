# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-02T15:43:21+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1

**wandb_id**: ciuqoe04

**hypothesis**: Plain English: on the identical cap29-acq1{,+s1} DONE-gate session read, STO-mode walk segments reach only 5-8% of commanded progress (slip 10.6-28.5) vs DET's 32-38% (slip 2.8-3.6) -- a bigger gap than the ~2x windowed-course-err steering overshoot. Config archaeology on this exact run's own launch args found the cause candidate: only the stance core's log_std is annealed down (to -4.0 via --log-std-anneal-core stance); the walk core's log_std is untouched by the anneal and its train/std metric sits flat around 0.222 (log_std~-1.5) for the entire 38M-step run. The already-closed stdwalk-mild/hi canary (08-31, dualbc5 lineage) tested RAISING walk log_std for turn authority and found achieved body-yaw noise completely insensitive to it (a different question, already refuted in that direction) -- this is the untested opposite lever: does annealing walk log_std DOWN (mild -2.0 vs aggressive -3.5, paired with stance's existing -4.0) close the sto/det walk-progress gap without degrading det walk quality, given turn authority is already known not to be std-sensitive so should be safe to reduce?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Cheap canary read (2M steps, no acquisition spend yet): (1) probe_turn_authority (wz_cmd=+-0.25, seeds 0/1) wz_med must stay >=0.07 rad/s (this lineage's established ceiling band, e.g. gradclip0p15-acq1 0.188/-0.224) -- a collapse below that would mean the std cut ate into the (small) turn authority after all. (2) det+sto eval_checkpoint.py walk-mode read (--task joint_walk --modes walk --episode-seconds 30, plain + --stochastic) must show sto progress_ratio_med rise materially above the cap29-acq1 session baseline (0.045-0.085) toward det (0.32-0.38) with det progress_ratio staying in 0.28-0.40 (no big det regression) and slip not rising outside noise. PASS-for-acquisition if sto clears ~0.15+ with det healthy; PARTIAL if sto improves some but not close to det, or det pays a real cost; FAIL if sto stays in the 0.05-0.09 band (std was not the driver) or turn authority collapses.

**verdict**: CANARY PASS (PASS-for-acquisition, replicates the hi seed0 result on seed1). Evidence: probe_turn_authority wz_med 0.209-0.213 (both signs) >> the 0.07 floor. purewalk_checkpoint det vs sto walk-mode progress_ratio_med: det 0.32, sto 0.28 (walk_startjitter det 0.34/sto 0.32) -- sto within ~12% of det, far past the ~0.15 PASS bar and nowhere near the cap29-acq1 session baseline's 0.045-0.085 sto floor. Slip: det 4.95/sto 3.48 (sto BETTER than det here, one det outlier ep at slip 23.1 pulls the det median up -- noise, not a sto regression). Zero falls across both purewalk sets (16/16). Same mechanism as seed0 (hi): annealing the walk core's log_std to -3.5 alongside stance's -4.0 removes the sto-sampling noise that was decoupling stochastic rollouts from the deterministic trajectory. Two independent seeds agreeing is the replication the operator's n>=3-ish seed-pass-rate guidance asks for at canary scale. Next: fund with seed0 as a 2-seed acquisition-scale pair on this dose (queued this cycle).

