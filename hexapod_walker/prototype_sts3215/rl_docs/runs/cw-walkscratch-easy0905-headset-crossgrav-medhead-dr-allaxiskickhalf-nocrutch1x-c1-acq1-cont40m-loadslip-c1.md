# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T15:08:56+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 5y2te2vi

**hypothesis**: Plain English: does pricing loaded foot slip directly make this already-clean-walking champion (0 falls, six-leg gait_valid 24/24 across two fresh stress panels this cycle) actually SLIP LESS, without breaking its gait? The champion's own diagnostics (heading-stress + speed-pressure panels, this cycle) show slip/m 4.3-6.5x the 2.9 teacher-band cap, the ONLY named gap -- no leg sacrifice, no falls. Single lever vs the byte-identical bare recipe: reward.walk_loadslip_gate=1.0 + loadslip_ok=3.0/max=8.0 (widened from the WALKTEACH-proven 6.0 because this champion's own measured ratio already sits above 6.0, which would clip the gate factor to 0 from step 0) + k_loadslip_excess=10.0 (WALKTEACH's own proven dose). Bank-checked first (test_task_semantics.py WALKCURR_ITEM4_BARE/LOADSLIP_OVERRIDES, 4/4 new behavioral tests green): honest gait stays clearly positive (1082 vs bare 1181, -8%) and clearly ahead of every degenerate scripted twin (skate crushed -2312 vs bare +191, margin widens sharply); the from-scratch stall>park discovery-gradient ordering does NOT hold at this dose (documented, measured, scoped out -- this is a CONTINUATION-only candidate, never a from-scratch walkcurr rung, and the champion's own policy does not currently visit a permanent-zero-progress stall basin per its own eval panels).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary. PASS if: wandb_history env/walk_loadslip_ratio trends down (or env/walk_loadslip_factor trends up toward 1) while reward_walk/reward_walk_prog stay flat-to-rising (08-21-aligned, not collapsing), AND a fresh gate re-eval (own-pod, DR-0, walk+walk_startjitter det+sto, n>=12) still reads 0 falls / gait_valid all-clear / 0 sacrificed legs with slip/m median measurably lower than this cycle's 5.065 training-diet baseline. FAIL if slip barely moves, if falls/sacrificed-legs reappear, or if forward progress/along_dist_m collapses toward the documented stall-basin failure mode despite the continuation-only scoping -- any of those closes this lever and forces a fresh design (e.g. a windowed rather than episode-cumulative slip ratio) before another attempt.

