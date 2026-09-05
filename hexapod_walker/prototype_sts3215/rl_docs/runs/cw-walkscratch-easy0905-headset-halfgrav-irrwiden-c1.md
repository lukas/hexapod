# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T22:50:36+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

**wandb_id**: odxtzpm6

**hypothesis**: Plain English: does the already-bank-proved heading-widen curriculum (medhead->fullhead, validated 2/2 seeds this cycle as widen2-c1/c2b: gait stays valid, reversal-heading tracking measurably tightens vs a cold jump) ALSO work starting from a champion that is mature on IRREGULAR direction-change TIMING instead of plain fixed-interval commands? headset-halfgrav-irr-acq1 is the ACQ-PASS 40M champion trained on jittered resample timing (goal.walk_cmd_resample_jitter=0.5) at the narrow 3-way heading set (0,+-45deg). This arm adds ONLY the widen2 heading-set change (same 8-way compass, same mechanism, no new reward keys) on top of that champion, keeping the timing jitter live. If gait_valid/falls stay clean and reversal-heading tracking looks like widen2's own numbers (not the cold fullhead-c1 baseline's degradation), this produces a champion validated on BOTH widened heading breadth AND irregular timing simultaneously -- the actual composite shape of the track's DONE-gate contextual panel (heading set + irregular direction changes together), not just one axis at a time. If it instead degrades (new leg sacrifice, falls, or reversal tracking as bad as the cold jump), the two curriculum axes don't compose cleanly and need to be trained together from an earlier stage instead of sequentially.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking, does not by itself close the composite-panel question. PASS/INFORMATIVE if: gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating irr-acq1's own clean numbers, AND direction_err/course_err at the new reversal headings (+-135,180) come in tighter than the cold-jump fullhead-c1 baseline's per-episode spread (28-161deg). FAIL if gait_valid collapses (new leg sacrifice vs irr-acq1's own baseline) or falls appear (widening broke something that was working).

**verdict**: CANARY PASS: composing the widen2 heading-set change (5-way medhead -> full 8-way compass incl. reversals) ON TOP OF the ACQ-PASS irr-timing-jitter champion (jitter-first order) produces the CLEANEST gait_valid read of the entire widen2 family so far. Evidence: harness gait_valid 23/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes -- only ONE episode flags a transient leg pair [2,4], no chronic single-leg pattern anywhere. This beats widen2-c1's own 2M canary (21/24) and widen2-c2b's (16/24). direction_err_mean_deg/slip in the det/walk mode (median ~68deg / ~6.4 per-m) sit in the same ballpark as widen2-c1's own numbers, not degraded toward the cold fullhead-c1 jump's catastrophic range (28-161deg, 0/24 success uniformly). Frame strip (walk_det_0) shows genuine six-leg cycling through a full command-resample cycle. Why: this is exactly this canary's own pre-registered PASS bar ("gait_valid/falls stay clean... reversal-heading tracking looks like widen2's own numbers, not the cold-jump baseline's degradation") -- met with margin; this is a mechanism-health canary only (2M), not a course-tracking bar clear. What's next: this validates that heading-breadth and timing-irregularity compose cleanly in the jitter-first order -- launch a 40M acquisition continuation to test whether this composite champion holds at full budget the way widen2-c1-acq1 (PASS) did, mirroring that template; read together with the concurrent cycle's mirror-order widenirr-c1/c2b (widen-first order, not yet landed) once available to see whether curriculum order matters.

