# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T05:29:44+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: wf7nj28x

**hypothesis**: Plain English: completes the 3-seed crutch isolation. The crutchoff-{s1,s2} single-lever ablation (torque_scale 3x->1x, same seeds/init-from as the already-FAILED c1-s1/c1-s2 2M canaries) came back CANARY PASS 2/2 (0 falls/24 eps, gait_valid 20/24 both) -- crutch is a real driver of push-recovery fragility. This seed (s0/seed=2) is the ONE of the original 3 that PASSED its own 2M canary with crutch ON and only fell at 40M ACQ (2/24 tilt_roll). Same single-lever ablation on this seed: does removing the crutch also help the seed whose failure only showed up at scale, or is s0's ACQ-only failure a different (budget-entrenchment) mechanism the 2M canary can't see either way?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY. PASS if 0 falls/terminations across all 24 episodes AND gait_valid stays majority (>=18/24) -- matches the crutchoff-s1/s2 bar. This alone does not confirm ACQ-scale robustness (s0's own failure only appeared at 40M) -- a clean canary here licenses a matched 40M ACQ continuation next, mirroring crutchoff-s1/s2's own now-licensed acq1 follow-up.

**verdict**: CANARY PASS (mechanism-health scope): removing the 3x torque crutch (dr.torque_scale 3,3->1,1) clears this seed's 2M canary bar too, completing the 3-seed crutch-isolation set 3/3. 0 falls/terminations across all 24 held-out episodes (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 6/6 -- no term_reason on any episode), gait_valid 19/24 (walk/det 6/6, walk/sto 4/6, startjitter/det 6/6, startjitter/sto 3/6 -- 2-3 episodes per sto submode flag a single transient sacrificed leg, not chronic, matching the s1/s2 pattern's own sto softening). Frame strips (walk_det_0, walk_startjitter_sto_3) confirm a level, upright body walking cleanly through push-perturbation markers with no topple. This is notable because s0 is the ONE original seed whose crutch-ON failure only appeared at 40M ACQ, not its own 2M canary -- so this clean canary does not yet prove the fix holds at scale (exactly the open question the s1/s2 acq1 continuations are already testing). Next: matched 40M ACQ continuation (crutchoff-s0-acq1), completing the 3-seed ACQ picture alongside the already-running s1/s2-acq1.

