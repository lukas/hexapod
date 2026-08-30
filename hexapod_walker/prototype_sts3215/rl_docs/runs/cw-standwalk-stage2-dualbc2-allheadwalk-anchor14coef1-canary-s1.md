# cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T07:55:46+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stance-mesh2-stage2-dualbc1-anchor14-walkretaincoef1-rescue-s1

**wandb_id**: 5bwe8jbl

**hypothesis**: Plain English: seed1 companion of cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary (same recipe question: does the anchor14 walk-retain-coef1 in-loss BC-anchor recipe transfer from the OLD stotight45-seed13 teacher to the BRAND NEW dualbc2_allheadwalk mesh/100Hz all-heading LEARNED walk teacher) -- run jointly since the whole track convention on this recipe (anchor11/anchor14) has been a paired seed0/seed1 call, and seed1 was historically the catastrophe-prone seed on the OLD teacher lineage; this checks whether that seed-dependence carries over to the new teacher or was specific to the old BC clone's own basin.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY gate as the seed0 twin, read jointly: WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero. PASS/promote if gait_valid>=5/6 zero-sac and progress_ratio clears the 0.10-0.18 band; PARTIAL if gait_valid holds but progress flat (still fund 8M per precedent); FAIL if anchor4-class catastrophe (gait_valid 0-1/6, sacrificed legs) or probe pathologies worsen under RL.

