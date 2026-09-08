# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-footgeom0135-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:05:41+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: axdsdiru

**hypothesis**: Plain English: does a policy trained WITH a bigger (13.5mm vs the default 4.5mm point-like) foot contact sphere walk with genuinely lower slip, not just look better in a zero-shot eval on a policy that never saw the new geometry? This is the matched training-side follow-up to this cycle's frozen-checkpoint probe, which found slip improving 15-26% in all 4 gate groups (own-DR panel) on the SAME unmodified champion evaluated with the bigger foot, but with one new startjitter/sto fall the baseline didn't have. Prediction if true: training with the bigger foot from the champion checkpoint holds or improves the same slip win (>=10% in >=3/4 groups) without adding a new chronic single-leg sacrifice or a net increase in fall count past the zero-shot read's own +1. Prediction if false: slip is flat/worse once the policy can adapt to the new contact geometry (the zero-shot win was an artifact of freezing the policy, not a real structural gain), or falls increase further -- closing this lever the same way torsional friction (03:5x) already closed, joining it as REFUTED. Strongest alternative: the effect is a rolling-friction-torque-arm artifact of MuJoCo's sphere-plane contact model at this specific dose, not a physically generalizable claim -- this canary tests the CHAMPION'S behavior under the model change, not a claim about the real robot's foot pad.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health + directional canary (own-DR panel, det+sto x nominal+startjitter, 24 episodes, same protocol as the champion's own cont40m gate). PASS if slip/m improves >=10% in >=3/4 of the 4 groups vs the champion's own cont40m baseline (det 4.98, sto 5.17, sj/det 5.10, sj/sto 5.42) with 0 NEW chronic single-leg sacrifice (a leg sacrificed in >=4/6 episodes of any one mode that wasn't already a baseline pattern) and total falls across all 24 episodes <= 1 (matching or beating this cycle's own zero-shot read, which saw exactly 1 new fall). FAIL if slip is flat or worse in >=3/4 groups (closes this lever, same bar the torsion-friction probe was held to), OR falls exceed 1, OR a new chronic sacrifice appears. Read together with the frozen-checkpoint zero-shot probe (logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_footgeom0135_probe/report.json) -- this run answers whether the win survives adaptation, not just eval-time freezing.

