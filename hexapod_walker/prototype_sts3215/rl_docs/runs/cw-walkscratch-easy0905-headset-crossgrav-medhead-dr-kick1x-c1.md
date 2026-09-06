# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T05:18:09+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: ngh1u2od

**hypothesis**: Turn on the project's mid-walk roll-kick perturbation (a torso roll impulse, distinct from the base-torque push tested by the sibling push1x arm), currently OFF (dr.walk_kick_prob=0.0, zero kick events all campaign). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive a real chance (30%/episode, nominal dose 8-18deg peak roll over 0.5-1.2s) of a mid-walk lateral kick without retraining collapse? Isolated single-axis diagnostic, same template as the sibling push/mass/friction/latency/deadband/torque/noise DR-restoration arms; the 2nd half of the ladder's named 'DR/push hardening' rung.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from an occasional roll kick with zero retraining. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows kick recovery needs its own real training-budget hardening rung, not a free zero-shot add.

**verdict**: CANARY FAIL - INFORMATIVE-NEGATIVE: restoring the mid-walk roll-kick perturbation (dr.walk_kick_prob=0.3, 8-18deg peak roll over 0.5-1.2s, previously OFF the whole campaign) on the champion produces a real FALL: aggregate gait_valid 20/24 (walk/det 5/6 sac[2], walk/sto 6/6, walk_startjitter/det 4/6 sac[0]/sac[4] on two different episodes, walk_startjitter/sto 5/6) stays above the 18/24 majority floor and no single leg is chronically sacrificed (flags spread across legs 0/2/4, not entrenched), BUT walk_startjitter/sto episode 4 TERMINATES via tilt_roll (prog 2.71, fwd only 0.09m before the episode ends) -- a genuine roll-over, confirmed on video (contact sheet shows progressive body roll across the clip ending fully tipped, not an instant start-jitter stumble). The gate text pre-registered ANY fall as a FAIL trigger regardless of aggregate majority, and this arm produces one. This matches the gate's own predicted failure mode: kick recovery is not a free zero-shot add on top of the existing champion -- it needs its own real training-budget hardening rung (a dedicated kick-hardening continuation with dr.walk_kick_prob active during training), not a bare DR-restore canary. No same-recipe retry; the next step is a real hardening arm (train ON the kick, not just eval under it), which should be prioritized alongside the campaign's other confirmed-binding axes (none so far -- this is the FIRST DR axis in the whole restoration sweep to produce an actual fall). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_kick1x_c1_gate/report.json + walk_startjitter_sto_4.mp4 (frame strip reviewed), W&B ngh1u2od.

