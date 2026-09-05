# cw-walkscratch-easy0905-headset-halfgrav-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T11:31:49+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-halfgrav-s2

**hypothesis**: Plain English: does the clean fixed-forward 0.5g walking skill halfgrav-s2 already learned keep walking (now toward a small set of commanded headings: straight, +45deg, -45deg, resampled every 6s within the 20s episode) instead of just marching straight, using the SAME reward it already trained under (no new keys -- k_walk_freeprog's existing along/cross decomposition already prices live heading-tracking correctly, bank-proven this cycle in test_walkscratch_easy_pilot.py's EASY_HEADING section, 22/22 green). Matching sibling to the concurrently-launched cw-walkscratch-easy0905-headset-base-c1 (1g): STATUS.md's own next-rung note says base+halfgrav answer the fixed-forward milestone identically and gravity 'doesn't look like the deciding lever' for THAT rung -- this checks whether that holds for heading generalization too, warm-started from halfgrav-s2 (own-track checkpoint, not a teacher/BC/motion-prior, same boundary as every other -c1 continuation this campaign).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS at 2M (mechanism-health scope, NOT the acquisition bar): finite losses, real motion, motor-contract compliance (360 deg/s in-log), and evidence the heading-tracking gradient is live -- env/v_along_cmd and/or reward_walk trending up across the 2M budget, ideally with gait_valid>0 on at least one non-zero heading in a spot-check pod eval. FAIL only on flat reward/v_along or an immediate park recapture; genuine acquisition budget (40M) is a separate follow-up decision after this + the base-c1 sibling both read healthy, mirroring the original base/halfgrav canary-then-acquisition pattern.

