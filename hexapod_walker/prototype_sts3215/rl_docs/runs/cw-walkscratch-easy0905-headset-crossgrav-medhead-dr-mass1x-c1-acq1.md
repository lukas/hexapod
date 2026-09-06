# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:47:24+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1

**wandb_id**: rllle5x4

**hypothesis**: Plain English: does the real hardware's mass-manufacturing tolerance (0.85-1.20x global mass_scale + 0.10 per-leg jitter) stay a clean walk with real training, not just a 2M canary glance? mass1x-c1's own 2M canary was 23/24 (one non-chronic leg-4 flag) on the campaign's cleanest champion -- unlike the PERFECT-canary axes, this is a near-clean-but-imperfect canary, a second useful data point (after torquefade2x-c1-acq1) on whether canary cleanliness predicts ACQ-scale durability for bare DR-realism axes the way it does for irr/widen composition axes.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice (a repeat of the same non-chronic leg-4 blip is fine) and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears -- would show mass tolerance is a real hardening-rung item, not a free axis.

**verdict**: ACQ PASS (40M): the mass-restore axis (dr.mass_scale=0.85-1.20, leg_mass_jitter_pct=0.10) holds at full training budget, IMPROVING on its own 2M canary. Gate report: 24/24 gait_valid=True across all 4 modes, sacrificed_legs=[] in EVERY episode, 0 terminations/falls -- the canary's single non-chronic leg-4 flag (23/24) does NOT recur at 40M. slip_per_m med 3.56-4.70 across submodes, comparable band to sibling axes (friction1x-acq1 3.4-4.3, encnoise1x canary 3.4-5.6). Contact sheet confirms clean six-leg tripod cycling, no drag/skate/paddle-creep. Reward climbed monotonically (quarters 585->1065->1156->1234, no plateau). Evidence: gate stayed genuinely computing on its pod (train-7, kubectl exec confirmed alive 745% CPU) past the prompt's claimed prestage-sync point -- waited it out via backgrounded ops.sh pollreap. Closes: single-axis mass/leg-mass-jitter realism is durable at ACQ scale, joining friction1x/encnoise1x/torquefade2x/gains1x/geom1x/fault1x in the individual-axis durability batch.

