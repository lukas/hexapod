# cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T07:55:46+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stance-mesh2-stage2-dualbc1-anchor14-walkretaincoef1-rescue-s1

**wandb_id**: 5bwe8jbl

**hypothesis**: Plain English: seed1 companion of cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary (same recipe question: does the anchor14 walk-retain-coef1 in-loss BC-anchor recipe transfer from the OLD stotight45-seed13 teacher to the BRAND NEW dualbc2_allheadwalk mesh/100Hz all-heading LEARNED walk teacher) -- run jointly since the whole track convention on this recipe (anchor11/anchor14) has been a paired seed0/seed1 call, and seed1 was historically the catastrophe-prone seed on the OLD teacher lineage; this checks whether that seed-dependence carries over to the new teacher or was specific to the old BC clone's own basin.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY gate as the seed0 twin, read jointly: WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero. PASS/promote if gait_valid>=5/6 zero-sac and progress_ratio clears the 0.10-0.18 band; PARTIAL if gait_valid holds but progress flat (still fund 8M per precedent); FAIL if anchor4-class catastrophe (gait_valid 0-1/6, sacrificed legs) or probe pathologies worsen under RL.

**verdict**: CANARY FAIL - MECHANISM (gate's own 'probe pathologies worsen under RL' clause). Evidence: fresh no-video harness probe of THIS checkpoint (det walk n=6, DR-0, run on hexapod-mjx-train-2, logs/ckpt_eval/cw_standwalk_stage2_dualbc2_allheadwalk_anchor14coef1_canary_s1_gate_fast/report.json): progress_ratio median -0.05 (NEGATIVE net motion vs command), slip_per_m 34.9-55.9 (huge), direction_err_mean_deg 128.8-132.9 (near-opposite the single commanded heading), gait_valid True / sacrificed_legs=[] on all 6 (NOT the literal old anchor4 leg-sacrifice signature -- a different, worse pathology). Root-caused to the BASE checkpoint (ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip, this run's --init-from): an independent probe of that checkpoint alone (same method, before any RL) already shows det walk progress_ratio ~0.000, forward_dist_m 0.018-0.026m over a full 30s episode (in-place quiver, not walking), slip/m 27-38, direction_err 27-47deg det / ~90deg sto. The distillation's OWN quick_probe smoke test ('probe walk: ep returns [260,-1111]') only checks episode RETURN, never displacement, so it looked unremarkable and this defect went uncaught before 2 GPU RL canaries (this run + its seed0 twin) were funded on top of it. 2M RL under anchor14coef1 did not fix this -- it made the pathology WORSE (near-zero/incoherent direction -> a confident ~130deg-off-command walk, MORE distance covered but the wrong way, slip up). WIRING CHECK passes clean (train/bc_anchor_loss_walk falls to a 0.004 plateau, fill_walk nonzero every rollout) -- this is a distillation-quality finding, not an anchor14coef1 dose/mechanism defect. Next: (1) do not fund further RL on ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip as-is; (2) closed the tooling gap this exposed -- distill_gru.py quick_probe now also prints net planar walk-mode displacement and WARNS under 0.05m (2 new tests, test_distill_transitions.py, snapshot exp/quick-probe-net-displacement-check) so the next distillation catches this pre-RL; (3) whoever verdicts the seed0 twin (cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary, a concurrent cycle's own run) should read this -- same broken base likely explains its own numbers too; (4) the real fix is in the Stage-2 distillation recipe (mix/epochs/teacher quality), not a new RL dose on this lineage.

