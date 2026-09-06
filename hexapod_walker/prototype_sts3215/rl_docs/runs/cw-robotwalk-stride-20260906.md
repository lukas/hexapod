# cw-robotwalk-stride-20260906

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:16:58+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-walkteach-scripted-allhead-acq12m

**wandb_id**: catovl0h

**hypothesis**: Plain English: the robot walks exactly as slowly as the scripted teacher it clones because training keeps pulling it toward the teacher's own stride -- turn that pull off and let the task reward alone push it to cover more commanded distance, keeping every cleanliness gate. Operator campaign robotwalk-smooth-20260906 (fb_20260906T030030_28f422, arm A stride). Candidate B cw-walkteach-scripted-allhead-acq12m PASSed but pinned at the scripted teacher's ~0.38 completion band (its own verdict: 12M extra budget + tighter std did NOT exceed the band; the record names walk BC coef=1 and yaw_zero_frac=1 as suspects). This arm tests the first suspect: warm from Candidate B's checkpoint (local zip sha256 30ed068e4356d5f42caba2a427f2845a230d7289a06467684731ec94a1f6f250; operator-deployed actor sha256 a813c4a692081978359042f825aaf5c4b43b58f91ffcd6db365a80d6827f4167), train.bc_anchor_coef=0.0 (anchor exactly off -- target emission and loss both gate on coef>0), log-std reopened to -3.0 and re-annealed to -4.0 over the 8M, everything else identical: mesh/100Hz, fixed 0.08 m/s command, slew cap 0.375 deg/tick and safety limits UNTOUCHED per operator order, loadslip/anchor/height/sway gates keep pricing dirty gaits. Prediction-if-true: det cmdsuite prog_m rises clearly above Candidate B's 0.31-0.33 m/12s band (target >=0.40 m at h000) with zero falls, slip/m<=2.9, all six legs cycling. Prediction-if-false: completion stays pinned ~0.33 with reward rising, or the gait degrades into drag/skate/rocking caught by slip+video -- then the ceiling is the physical slew/cadence envelope, not the anchor, and the next mechanism inside this arm is a faster motion source (cadence/CPG harvest), not more budget on this recipe. Strongest alternative: anchor-free PPO slowly forgets the clean gait shape -- caught by eval-every-1M, video-every-2M, and the loadslip income gate.

**gate**: ACQ 8M, campaign robotwalk-smooth-20260906: PASS if det+sto every-heading cmdsuite (12s holds, own cfg): zero falls, prog_m>0 at all 8 headings, slip/m<=2.9, no sacrificed leg on video, AND det forward h000 prog_m >= 0.40 m/12s (>=+20% over Candidate B's 0.3248 baseline, outside its 0.31-0.33 spread) with no heading below Candidate B's own 0.29 floor. Also record joygate stress_mix AND the SAME short forward/reverse/release/left+right arc script as Candidate B (100Hz policy, controller-compatible settings) for the hardware comparison. Below +10% at 8M with reward plateaued = anchor-ceiling hypothesis REFUTED (physical envelope becomes prime suspect); do NOT clone seeds. On PASS with clean video: completion cycle exports the controller-compatible artifact (exact run/checkpoint/export SHA, policy/config path, eval/video locations in ledger/story) for the local RobotLab watchdog; cloud never operates the robot or enqueues Lab jobs.

