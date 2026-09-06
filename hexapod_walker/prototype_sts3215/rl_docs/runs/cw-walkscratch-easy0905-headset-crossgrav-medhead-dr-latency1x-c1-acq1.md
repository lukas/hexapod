# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:25:08+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1

**wandb_id**: np2kt3bf

**hypothesis**: Plain English: does the real actuator command-latency spread (previously OFF) stay a clean walk with real training, not just a 2M canary glance? latency1x-c1's own 2M canary was a PERFECT 24/24 (0 falls) on the campaign's cleanest champion -- a 3rd ACQ durability confirmation for a bare DR-realism axis (after torquefade2x-c1-acq1, mass1x-c1-acq1), picking the single most hardware-timing-critical axis in the sweep.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally near its own 24/24 canary) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: Real actuator command-latency spread (dr.latency_scale=1,1, previously only 2M-canary-clean) holds at a REAL 40M acquisition budget: PERFECT 24/24 gait_valid across all 4 modes (walk/walk_startjitter x det/sto), sac=[] every episode, 0 terminations/falls, matching (actually tightening) its own 2M canary. Reward monotonic no plateau (quarters 432/839/926/1048). slip_per_m 3.0-4.6, consistent with sibling DR-restore ACQ continuations. contact_sheet.png video-confirmed clean six-leg tripod cycling, no flag leg/drag/skate. 3rd ACQ-scale durability confirmation for a bare DR-realism axis (after torquefade2x-c1-acq1, mass1x-c1-acq1), and the single most hardware-timing-critical axis in the sweep -- closes it.

