# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-02T15:41:14+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1

**wandb_id**: rym79pju

**hypothesis**: Plain English: on the identical cap29-acq1{,+s1} DONE-gate session read, STO-mode walk segments reach only 5-8% of commanded progress (slip 10.6-28.5) vs DET's 32-38% (slip 2.8-3.6) -- a bigger gap than the ~2x windowed-course-err steering overshoot. Config archaeology on this exact run's own launch args found the cause candidate: only the stance core's log_std is annealed down (to -4.0 via --log-std-anneal-core stance); the walk core's log_std is untouched by the anneal and its train/std metric sits flat around 0.222 (log_std~-1.5) for the entire 38M-step run. The already-closed stdwalk-mild/hi canary (08-31, dualbc5 lineage) tested RAISING walk log_std for turn authority and found achieved body-yaw noise completely insensitive to it (a different question, already refuted in that direction) -- this is the untested opposite lever: does annealing walk log_std DOWN (mild -2.0 vs aggressive -3.5, paired with stance's existing -4.0) close the sto/det walk-progress gap without degrading det walk quality, given turn authority is already known not to be std-sensitive so should be safe to reduce?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Cheap canary read (2M steps, no acquisition spend yet): (1) probe_turn_authority (wz_cmd=+-0.25, seeds 0/1) wz_med must stay >=0.07 rad/s (this lineage's established ceiling band, e.g. gradclip0p15-acq1 0.188/-0.224) -- a collapse below that would mean the std cut ate into the (small) turn authority after all. (2) det+sto eval_checkpoint.py walk-mode read (--task joint_walk --modes walk --episode-seconds 30, plain + --stochastic) must show sto progress_ratio_med rise materially above the cap29-acq1 session baseline (0.045-0.085) toward det (0.32-0.38) with det progress_ratio staying in 0.28-0.40 (no big det regression) and slip not rising outside noise. PASS-for-acquisition if sto clears ~0.15+ with det healthy; PARTIAL if sto improves some but not close to det, or det pays a real cost; FAIL if sto stays in the 0.05-0.09 band (std was not the driver) or turn authority collapses.

**verdict**: CANARY PASS (PASS-for-acquisition, strongest of the 4-way grid). Evidence: probe_turn_authority wz_med 0.191-0.209 (both seeds/signs) >> the 0.07 floor -- turn authority untouched. purewalk_checkpoint det vs sto walk-mode progress_ratio_med: det 0.32, sto 0.32 (walk_startjitter det 0.32/sto 0.37) -- sto essentially MATCHES det, closing the cap29-acq1 session baseline's sto/det gap (0.045-0.085 sto vs 0.32-0.38 det) almost completely, far past the ~0.15 PASS bar. Slip stayed flat-to-better in sto (walk det 3.39 vs sto 3.05; startjitter det 4.03 vs sto 4.54). Zero falls across both purewalk sets (16/16). Why: annealing the WALK core's log_std down to -3.5 (paired with stance's existing -4.0 via --log-std-anneal-core walk,stance) removes the action-sampling noise that was making stochastic rollouts fail to track the deterministic policy's own trajectory -- confirms the config-archaeology hypothesis (walk log_std sat flat at std~0.222 the whole 38M cap29-acq1 run while only stance was annealed), and shows the lever is independent of the already-closed 08-31 stdwalk-mild/hi canary (raising walk std for turn authority -- std-insensitive there; lowering it here for sto/det convergence -- clearly sensitive). Next: fund a full acquisition-scale pair on this exact dose to see if the fix compounds into the DONE-gate session read's steering/slip numbers, not just the canary-scale walk-mode probe (queued this cycle).

