# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T05:29:44+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: wf7nj28x

**hypothesis**: Plain English: completes the 3-seed crutch isolation. The crutchoff-{s1,s2} single-lever ablation (torque_scale 3x->1x, same seeds/init-from as the already-FAILED c1-s1/c1-s2 2M canaries) came back CANARY PASS 2/2 (0 falls/24 eps, gait_valid 20/24 both) -- crutch is a real driver of push-recovery fragility. This seed (s0/seed=2) is the ONE of the original 3 that PASSED its own 2M canary with crutch ON and only fell at 40M ACQ (2/24 tilt_roll). Same single-lever ablation on this seed: does removing the crutch also help the seed whose failure only showed up at scale, or is s0's ACQ-only failure a different (budget-entrenchment) mechanism the 2M canary can't see either way?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY. PASS if 0 falls/terminations across all 24 episodes AND gait_valid stays majority (>=18/24) -- matches the crutchoff-s1/s2 bar. This alone does not confirm ACQ-scale robustness (s0's own failure only appeared at 40M) -- a clean canary here licenses a matched 40M ACQ continuation next, mirroring crutchoff-s1/s2's own now-licensed acq1 follow-up.

