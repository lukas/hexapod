# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:44:45+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1

**wandb_id**: ub3dxkyb

**hypothesis**: Does the campaign's cleanest single-axis DR-restore canary (medhead-dr-friction1x-c1: nominal 0.6-1.4x foot/ground friction restored, PERFECT 24/24 gait_valid at 2M, 0 falls) hold up at a real acquisition-scale (40M) training budget on top of the 80M champion, the same canary-vs-ACQ durability question this campaign's crossgrav/widen/irr composition axes have repeatedly answered NO to (roughly half of healthy-source canary-clean compositions entrench a chronic sacrificed leg by 40M)? No individual DR-restore axis has yet been extended past its 2M canary -- this is the first.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls -- shows single-axis friction realism is durable, not just canary-clean. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows even a clean single-axis DR canary is not safe to assume durable, extending the composition-axis entrenchment risk to plain single-axis restoration too.

**verdict**: ACQ PASS (40M): the friction-restore axis (dr.friction_scale=0.6-1.4) holds at full training budget, not just canary-clean. Gate report: 24/24 gait_valid=True across all 4 modes (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), sacrificed_legs=[] in EVERY episode, 0 terminations/falls. slip_per_m med 3.44-4.26 across submodes -- inside/tighter than the axis's own 2M canary (slip/m 3.2-5.8, PERFECT 24/24). Contact sheet + walk_det_0 frame strip confirm clean six-leg tripod cycling, no drag/skate/paddle-creep. Reward climbed monotonically (quarters 562->1035->1136->1219, no plateau), matching the eval. Evidence: gate stayed genuinely computing on its pod (train-4, kubectl exec confirmed alive 771% CPU) past the prompt's claimed prestage-sync point -- waited it out via backgrounded ops.sh pollreap rather than trusting the stale sync claim. Closes: single-axis friction realism is durable at ACQ scale, joining encnoise1x/torquefade2x/mass1x/gains1x/geom1x/fault1x in the individual-axis durability batch.

