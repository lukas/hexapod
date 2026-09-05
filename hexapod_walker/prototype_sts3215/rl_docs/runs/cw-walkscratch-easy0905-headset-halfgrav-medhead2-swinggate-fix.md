# cw-walkscratch-easy0905-headset-halfgrav-medhead2-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T21:57:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1-cont40m

**wandb_id**: jkh3xzb5

**hypothesis**: This cycle's own verdict on headset-halfgrav-medhead2-acq1-cont40m found ACQ FAIL specifically on walk_startjitter/det (stuck 2/6 gait_valid through 80M) with borderline-low duty (0.05-0.08) on legs that vary episode-to-episode -- a milder version of the same per-leg-utilization underuse the base(1g) family's swing_gate batch is targeting, just not yet hard-parked. Does reward.walk_swing_gate (bank-proved 4/4 green this cycle, already retrofitting 3 base-family entrenched checkpoints in parallel) also lift the flagged legs' duty above the gait_valid bar on this halfgrav/medhead2 lineage's exact FAILED checkpoint, without breaking its already-clean walk/det (5/6) or introducing falls?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if walk_startjitter/det's previously-flagged legs majority-clear duty>0.10 (matching this family's own accepted-PASS 0.08-0.09+ range) with 0 new falls and walk/det stays >=4/6 gait_valid (no regression from the 5/6 baseline). FAIL - MECHANISM if the same legs stay <0.10 in a majority of episodes regardless of whether walk_swing_gate_factor shows real decline, or if walk/det regresses below 4/6. Read alongside the base-family n=3 swing_gate batch (s0c1/medhead/irr) before concluding swing_gate's effect on this family.

