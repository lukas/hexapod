# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T21:19:08+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

**wandb_id**: hbbj4uco

**hypothesis**: Plain English: does the anchor14coef1 unified-policy RL fine-tune keep improving the dualbc4_walkteach (all-heading/turn-capable teacher-adoption) canary with an 8M-step acquisition budget, the same promote-on-PASS convention already validated twice on the dualbc3-dagger lineage (canary->acq8m PASS, progress_ratio 0.28->0.429, slip 3.39->2.55)? Canary cleared its mechanism-health gate (det walk gait_valid 6/6, prog_med 0.46, course_err_1s_med ~6deg inside walkteach-acq12m's 0.31-0.46 band, 0 sac/terms, wiring check PASS) -- straight continuation from the canary's own checkpoint, no cfg change.

**gate**: ACQUISITION (own-scope): det walk gait_valid stays >=5/6, sacrificed legs stay 0, progress_ratio improves or holds vs the canary's 0.43-0.46 (not regresses), slip/m stays inside teacher band (<=2.9), course_err_1s_med does not regress below walkteach-acq12m's own band, zero new walk terminations. Full DONE-gate mixedsession read follows per dualbc3 convention before any further unified-policy budget.

**verdict**: FAIL, joint with the already-FAILed -s1 twin -- the 8M unified-policy continuation regressed pure-walk progress on seed0 too, matching -s1's finding closely. Own pure-walk det read (mode_seq=0 forced override, gate cfg, n=8, launched last cycle on train-6, pulled back this cycle): progress_ratio med 0.362 (range 0.345-0.396), below the canary parent's 0.43-0.46 hold-or-improve bar (a real regression, not noise) and close to -s1's 0.373/0.379 read. slip_per_m med 4.15 (2.75-4.71), well over the walkheavy sibling's already-failing band. gait_valid 8/8, sacrificed_legs 0/8, zero terminations -- own contact-sheet reviewed, clean tripod gait, no flag leg. Root cause: same pooled-reward-masks-a-walk<->stance-trade mechanism already root-caused on the -s1 verdict (rising pooled reward from the 70% non-walk goal mix, walk-specific channels flat/declining) -- this seed0 read closes the joint gate the same way. No further budget on this specific lineage's plain acq8m recipe; the walk-heavy remix (walkheavy-acq8m{,-s1}) was the fix attempt and it ALSO failed both seeds (see its own joint verdict) -- diet-share is exonerated, optimization dynamics is the shared open suspect. Hardware-ready: no.

