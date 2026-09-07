# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widenbis135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T12:23:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

**wandb_id**: duvwg4h3

**hypothesis**: Plain English: does the +135deg-alone heading widen that EXONERATED seed 0 (base5+135, ACQ PASS, 21/24 gait_valid matching baseline) replicate on seed 1, or was s0 lucky? This campaign's own discipline requires 3-seed confirmation before calling any realism axis closed (every other axis here -- speedwiden, the original 5-way heading set, all named DR axes -- was seed-replicated before adoption); widenbis135 is s0-only so far. Same exact recipe as s0-widenbis135 (add ONLY +135deg to the 5-way heading set), warm-started from s1's OWN ACQ-passed crutchoff-s1-acq1 checkpoint instead of s0's, seed 3 to match s1's own convention. Prediction-if-true: gait_valid stays near s1-acq1's own 21/24 baseline, 0 falls, no new chronic sacrifice -- widenbis135 generalizes as safe. Prediction-if-false: a new chronic leg-pair sacrifice or fall appears -- s0's clean result was seed-specific, not a property of the +135 heading itself.

**gate**: PASS (heading exonerated, replicates s0) if 0 falls/24 AND gait_valid>=19/24 AND no chronic (<0.10 duty every flagged episode) single-leg or leg-pair sacrifice absent from s1-acq1's own clean panel. FAIL if a chronic sacrifice or fall appears that s1-acq1's own baseline does not show.

**verdict**: Heading exonerated, REPLICATES s0 (2/3 seeds now). gait_valid 21/24 total, IDENTICAL to s1-acq1's own clean baseline (21/24); 0 falls/24 in both. walk/sto and walk_startjitter/det both 6/6 clean (matching baseline). walk_startjitter/sto sac pattern (legs 0,5) is the SAME already-known flaky cell as baseline (baseline had 3 sac episodes there, this run has 2 -- narrower, not worse). One NEW single-episode low-duty leg0 flag in walk/det/1 (duty=0.09, baseline walk/det was 6/6 clean) -- not chronic per gate wording (appears once, not across multiple flagged episodes; every other walk/det episode is clean and video shows normal 6-leg cycling), so does not trip the FAIL condition. slip_per_m med 5.25-8.12 across modes, comparable to s1-acq1's own 4.67-8.33 range (no degradation). Video (contact sheet, walk_det_1) shows continuous forward translation with visible leg swing throughout, no stall/skate/drag pattern. Next: this is now 2/3 seeds ACQ PASS for widenbis135 (s0, s1); s2-widenbis135 still training (leave for its own reader) -- once s2 lands, widenbis135 closes 3/3 and item(1)'s validated heading set (base5+135) plus speedwiden are both candidates for the next full composite champion alongside the still-running widenbis135-speedwiden interaction test.

