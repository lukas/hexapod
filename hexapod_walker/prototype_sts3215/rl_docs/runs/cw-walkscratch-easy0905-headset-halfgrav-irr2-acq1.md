# cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T23:36:48+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c2

**wandb_id**: 1tqy50b7

**hypothesis**: Does the halfgrav irregular-direction-change-timing (goal.walk_cmd_resample_jitter=0.5) acquisition rung generalize across seeds, matching the n=2 seed-confirmation discipline already applied to medhead/widen2? headset-halfgrav-irr-c2 (seed 3, warm-started from the independently-passed headset-halfgrav-s1acq champion, not c1's own halfgrav-acq1) is one of 3 healthy 2M irr-timing canaries (irr-c1/c2/c3 all CANARY PASS) but only c1 was ever continued to a full 40M acquisition (irr_acq1, itself ACQ PASS: 22/24 gait_valid, 0 falls, slip at/under the 2.9 band). This is the SAME already-bank-proved recipe (no new reward keys, no new mechanism) on a DIFFERENT seed/parent-champion lineage (s1acq not acq1), giving the irr-timing rung its own n=2 confirmation before any further composition arm (widenirr/irrwiden, already in flight off irr_acq1 alone) draws a recipe-level conclusion resting on a single seed.

**gate**: ACQ PASS if walk/det gait_valid >=4/6 AND walk_startjitter/det >=4/6 (matching the adopted s0c1-acq1 rule), 0 falls, slip/m at/under the 2.9 teacher band, no chronically sacrificed leg (duty>0.10 on all six) in a majority of episodes. CONTINUE if walk/det clears >=4/6 but walk_startjitter/det is borderline (duty 0.06-0.11, not chronic 0.0-0.02) with reward still climbing, matching medhead2-acq1's own accepted CONTINUE precedent. ACQ FAIL if either primary mode stays <4/6 with a chronic (duty<=0.05) sacrificed leg regardless of reward trend.

**verdict**: ACQ PASS: 2nd seed of the halfgrav irr-timing-jitter rung (respec of irr-c2, seed3) at full 40M budget. Harness gait_valid 19/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 4/6, walk_startjitter/sto 5/6) -- both primary modes clear the >=4/6 bar exactly, 0 falls in all 24 episodes, slip_per_m tightly banded 2.1-2.9 across every episode (at/under the 2.9 teacher band, no outlier spikes unlike the widen2 family this cycle). Leg4 is the recurring weak point (duty 0.04-0.27 across episodes, dips below the 0.10 sacrificed-threshold in 5/24 total, mostly walk_startjitter/det) but stays duty>0.10 (healthy) in 19/24 episodes overall -- not chronically sacrificed in a majority per the gate's own bar. Video (walk_det_0) shows genuine six-leg cycling with the commanded-direction arrow changing per the irregular resample timing, matching the mechanism's intent. Reward climbed monotonically every quarter (364->656->703->819), no plateau/misalignment signal. Closely matches sibling seed irr-acq1's own ACQ PASS numbers (20/24 gait_valid, slip 2.18-3.04, no chronic sacrifice) -- gives the halfgrav irr-timing rung its n=2 seed confirmation (2/2 PASS), same discipline already applied to medhead/widen2. SKILLS.md updated.

