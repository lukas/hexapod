# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T22:50:36+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

**hypothesis**: Plain English: does the already-bank-proved heading-widen curriculum (medhead->fullhead, validated 2/2 seeds this cycle as widen2-c1/c2b: gait stays valid, reversal-heading tracking measurably tightens vs a cold jump) ALSO work starting from a champion that is mature on IRREGULAR direction-change TIMING instead of plain fixed-interval commands? headset-halfgrav-irr-acq1 is the ACQ-PASS 40M champion trained on jittered resample timing (goal.walk_cmd_resample_jitter=0.5) at the narrow 3-way heading set (0,+-45deg). This arm adds ONLY the widen2 heading-set change (same 8-way compass, same mechanism, no new reward keys) on top of that champion, keeping the timing jitter live. If gait_valid/falls stay clean and reversal-heading tracking looks like widen2's own numbers (not the cold fullhead-c1 baseline's degradation), this produces a champion validated on BOTH widened heading breadth AND irregular timing simultaneously -- the actual composite shape of the track's DONE-gate contextual panel (heading set + irregular direction changes together), not just one axis at a time. If it instead degrades (new leg sacrifice, falls, or reversal tracking as bad as the cold jump), the two curriculum axes don't compose cleanly and need to be trained together from an earlier stage instead of sequentially.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking, does not by itself close the composite-panel question. PASS/INFORMATIVE if: gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating irr-acq1's own clean numbers, AND direction_err/course_err at the new reversal headings (+-135,180) come in tighter than the cold-jump fullhead-c1 baseline's per-episode spread (28-161deg). FAIL if gait_valid collapses (new leg sacrifice vs irr-acq1's own baseline) or falls appear (widening broke something that was working).

