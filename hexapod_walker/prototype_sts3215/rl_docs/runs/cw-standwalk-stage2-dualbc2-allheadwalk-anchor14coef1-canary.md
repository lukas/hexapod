# cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T07:51:30+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stance-mesh2-stage2-dualbc1-anchor14-walkretaincoef1-rescue

**wandb_id**: 9hocbxso

**hypothesis**: Plain English: does the anchor14 walk-retain-coef1 in-loss BC-anchor recipe -- already proven on the OLD stotight45-seed13 scripted-teacher BC clone to rescue walk-catastrophe seeds and keep compounding cleanly with budget through an 8M acquisition (see cw-standwalk-stance-mesh2-stage2-dualbc1-anchor14-walkretaincoef1-rescue{,-s1,-acq8m,-s1-acq8m}, all PASS) -- transfer the same way when RL-fine-tuning the BRAND NEW cw-standwalk-stage2-dualbc2-allheadwalk BC checkpoint instead? That checkpoint is the first mesh/100Hz all-heading LEARNED walk teacher (distilled this cycle from cw-walk-allheading-mlp-singleframe-acq1-stdanneal + stancemix_bcchain3_stdanneal, --transitions dropped per its own seq-verify abort) composed with the same stance teacher family; its own quick_probe/probe_seq smoke numbers (walk ep returns [260,-1111], rise [-814,-1444], hold [537,72], actor RMS 0.037) are a plausible-but-imperfect raw BC clone, matching the anchor1-era precedent for what a pre-RL clone looks like before the walk-anchor recipe cleans it up.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY at 2M (paired seed0/seed1 call, not a skill-acquisition read): WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update, reward trend per 08-21 read first. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6 with zero/near-zero sacrificed legs and progress_ratio clears the same 0.10-0.18 band anchor14's own 2M canary showed on the old teacher (not required to already look like the finished skill). PARTIAL if gait_valid holds but progress_ratio stays near-zero/flat -- fund the 8M continuation anyway per the anchor14 precedent (its own early-window numbers were modest too and matured with budget). FAIL if either seed shows the anchor4-class catastrophe (gait_valid 0-1/6, sacrificed legs) or the BC checkpoint's own probe pathologies (rise/hold catastrophic falls) get WORSE under RL instead of recovering -- that would mean the new teacher's compat gap (flat-rise-in-composition / imperfect isolated-mode probes) isn't rescued by this exact recipe and needs its own dig-in before a second recipe attempt.

**verdict**: CANARY FAIL - MECHANISM (gate's own 'probe pathologies worsen under RL' clause) -- seed0 twin of the already-diagnosed -s1 (prior cycle), same root cause, now 2/2. Evidence: this run's own gate/owncfg harness (n=6 each, DR-0 + own-DR): walk/det progress_ratio med -0.05 to -0.06, slip_per_m med 32-49 (cap 3.0), direction_err_mean_deg 100-175deg (near-opposite of commanded heading), wrong_direction_frac up to 0.69, gait_valid True/6-6 (certifies six-leg cycling only, not net displacement). Video (walk_det_0_sheet.png) confirms: legs cycle the whole clip but the body stays essentially in place -- a stationary high-slip shuffle, not forward walking. Root-caused (prior cycle, shared with -s1) to the Stage-2 distillation BASE checkpoint (ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip, this run's --init-from): an independent pre-RL probe of that checkpoint already showed near-zero net displacement (forward_dist 0.018-0.026m/30s). 2M of anchor14coef1 RL made the pathology WORSE (near-zero/incoherent direction -> confident ~100-175deg-off-command walk with high slip), matching the gate's explicit FAIL disjunct. Reward quarters [38.2, 2.9, -313.9, -101.0] match -s1's shape. CONSEQUENCE: do not fund further RL on this Stage-2 zip as-is; defect is upstream in the distillation recipe. Closes the anchor14coef1-canary pair at 2/2 FAIL, both attributable to the shared base-checkpoint defect, not an anchor-dose finding.

