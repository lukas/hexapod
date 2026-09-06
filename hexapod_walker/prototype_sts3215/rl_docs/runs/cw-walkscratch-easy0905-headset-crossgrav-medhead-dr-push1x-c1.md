# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-push1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:15:40+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: zuuyfqmt

**hypothesis**: Turn on the project's mid-walk external base-torque push perturbation, currently OFF (dr.walk_push_prob=0.0, i.e. zero push events in every episode all campaign despite the walkcurr goal ladder explicitly naming 'DR/push hardening' as the rung after direction changes). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive a real chance (30%/episode, nominal dose 2.0-3.0 N*m peak base torque pulse over 0.8-1.5s) of a mid-walk shove without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms; the actual 'push' half of the ladder's named next rung.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from an occasional shove with zero retraining. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows push recovery needs its own real training-budget hardening rung, not a free zero-shot add.

**verdict**: Restoring nominal (30%/episode) mid-walk base-torque push perturbation on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean) costs a modest but majority-clearing amount: aggregate gait_valid 20/24 (walk/det 5/6 sac=[2,5], walk/sto 5/6 sac=[5], walk_startjitter/det 4/6 sac=[0]+sac=[4], walk_startjitter/sto 6/6 clean), 0 falls/terminations anywhere, reward rising every quarter (40.9/110.3/171.0/226.5, 2M canary). Sacrifice pattern is scattered across legs 0/2/4/5 with no leg repeating 3+ times -- no NEW chronic single-leg fingerprint, unlike the entrenchment cases seen elsewhere in this campaign. Frame strips (walk_det_4, walk_startjitter_det_4) show a clean upright six-leg cycling gait absorbing the shove, not a collapse. Meets the gate's PASS bar (majority >=18/24, no new chronic leg, 0 falls): mid-walk push-recovery is not a binding constraint at nominal dose for this champion, matching every other single-axis DR-restoration canary this campaign (latency/deadband/noise/tiltnoise/torquefade2x all clean-to-PASS). Closes the 'push' half of the DONE ladder's DR-hardening rung as a free zero-shot capability; no retraining budget needed for this axis at this dose.

