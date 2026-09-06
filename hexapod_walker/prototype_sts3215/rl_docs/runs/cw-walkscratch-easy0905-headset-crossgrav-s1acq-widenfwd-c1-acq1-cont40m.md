# cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:11:41+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1

**wandb_id**: o4p4pjkr

**hypothesis**: Plain English: does the campaign's cleanest source (s1acq, native 0.5g gait_valid 24/24) still hold its widenfwd (8-way heading) composition after a SECOND 40M helping (80M cumulative), matching the endurance-margin rule already confirmed on medhead/s1acq-abrupt/s3acq-abrupt (cleanliness AT the first 40M read, not total budget, predicts whether more training helps or hurts)? s1acq-widenfwd-c1-acq1's own first 40M ACQ read was a clean 21/24 (0 falls, only a lateral non-worsening leg-shift vs its 22/24 2M canary) -- exactly the 'already clean at 40M' profile the rule predicts should HOLD, not entrench, at 80M.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 21/24 40M read) at 80M cumulative, no NEW chronic single-leg sacrifice, 0 falls. FAIL/WORSENS if it drops further (a new or spreading chronic leg pattern, gait_valid materially below 21/24) -- would be the first clean-at-40M source to worsen with more budget, overturning the endurance-margin rule.

**verdict**: HARDENING PASS/HOLDS (5th cont40m endurance confirmation of the cleanliness-margin rule, on the noisiest composition line so far). 80M cumulative gate: gait_valid 20/24 (4/6 det, 6/6 sto, 6/6 startjitter/det, 4/6 startjitter/sto) vs the 40M parent's 21/24 (5/6/6/4) -- within noise, not a materially-below-21 drop. The parent's own chronic sac pattern (det ep4 legs[0,3]; startjitter/sto ep1+ep5 leg[0]) reproduces EXACTLY at 80M; only one new non-chronic single-episode flag appeared (det ep1 leg[4], singleton, no 2nd occurrence anywhere in the panel) -- not a spreading/new-chronic leg. 0 falls/24 both reads. slip_per_m actually IMPROVED vs parent (sto med 10.09->6.83, startjitter/sto med 8.39->5.80; det/startjitter-det roughly flat 5.6-7.4 range both reads) despite this arm's already-noisy widenfwd baseline (8-way heading composition inherently carries higher slip than plain headset, flagged at the 40M read too). Contact sheet shows a normal six-leg walking gait, no new pathology. Confirms the endurance-margin rule (clean-at-40M predicts cont40m holds) on its noisiest tested composition, joining widen2c1-irrfwd (exact hold), widenirr-c3 (narrow dip), medhead-irrfwd (improves), halfgrav-widenirr-c3 (mild degrade but still majority). Tooling note: the gate eval had actually finished on-pod (train-3) at 09:35 with nobody watching -- reaped via 'pod_eval.py <run>' (copy-back only, no relaunch) rather than waiting/re-running; the pod was concurrently claimed for a new training launch (torquefade2x-c1-acq1-cont40m) by another cycle in the same window, which is why the orphaned result needed a manual reap instead of the normal prestage sync. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s1acq_widenfwd_c1_acq1_cont40m_gate/report.json (this cycle's reap), W&B o4p4pjkr.

