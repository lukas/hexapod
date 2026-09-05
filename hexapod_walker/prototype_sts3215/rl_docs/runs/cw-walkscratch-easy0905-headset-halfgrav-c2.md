# cw-walkscratch-easy0905-headset-halfgrav-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T11:34:41+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-halfgrav-s2

**wandb_id**: r82tqlzx

**hypothesis**: Plain English: does the clean fixed-forward 0.5g walking skill halfgrav-s2 already learned keep walking toward a small set of commanded headings (straight/+45/-45deg, resampled every 6s in the 20s episode) instead of just marching straight, under the SAME reward it already trained under (bank-proven this cycle, test_walkscratch_easy_pilot.py EASY_HEADING, 22/22 green). Re-launch of headset-halfgrav-c1 (w6xs0zav), which died in ~2s with the documented SystemExit ('--activation-fn only applies to from-scratch/transplant builds; a plain --init-from warm start keeps the checkpoint's own activation') because the concurrent cycle that launched it forgot to blank --activation-fn on a plain --init-from continuation (CURRENT_TRUTHS.md Known Tooling Gotchas) -- fixed here. Matching sibling to headset-base-c1 (1g, train-1, confirmed running past 2M steps).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS at 2M (mechanism-health scope, NOT the acquisition bar): finite losses, real motion, motor-contract compliance (360 deg/s in-log), and evidence the heading-tracking gradient is live -- env/v_along_cmd and/or reward_walk trending up, ideally gait_valid>0 on a non-zero heading in a spot-check pod eval. FAIL only on flat reward/v_along or immediate park recapture; 40M acquisition budget is a separate follow-up after this + headset-base-c1 both read healthy.

**verdict**: CANARY PASS corroborated by the full gate eval (was pending at first verdict): 24/24 walk+walk_startjitter det+sto episodes gait_valid=True, 0 sacrificed legs, 0 terminations, fwd_dist_m med 3.32-3.58m/20s (0.17-0.18 m/s net, far above the 0.03 m/s bar), slip_per_m med 2.22-2.41 (inside/near the teacher's <=2.9 band, tightest of the heading rung so far). This is already acquisition-grade quality at just 2M steps, not just mechanism-health -- strong leading signal for the in-flight 40M headset-halfgrav-acq1 follow-up (train-0, do not re-launch). No corrective action needed; original CANARY PASS verdict stands, corroborated.

