# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-speedwiden-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: acq_pass

**created**: 2026-09-07T11:14:17+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-speedwiden

**wandb_id**: jregm6xk

**hypothesis**: Plain English: completes the 3-seed speedwiden ACQ trio. Does the speed-band widening (0.03-0.12 m/s dynamic cap) that just CANARY PASSed (3/3 seeds) hold at real 40M acquisition budget, or does it re-open the composite's known late-entrenchment fragility the way the widen8 heading axis did (canary PASS 3/3, then ACQ FAIL 3/3 via a heading-dependent front-leg-pair sacrifice)? Same single-axis test, warm-started from this seed's own speedwiden-CANARY-PASS checkpoint.

**gate**: PASS (widening holds) if 0 falls/24 (or near-0, matching each seed's own acq1 baseline of 0 terms) and gait_valid >=18/24 with no new chronic sacrifice beyond the parent acq1's own walk_startjitter/sto leg0/leg2/leg5 flag. FAIL if a new chronic sacrifice or falls appear, matching widen8's own ACQ-depth regression shape.

**verdict**: ACQ PASS: speed-band widening (0.03-0.12 m/s + walk_freeprog_cap_dynamic) holds at 40M ACQ depth on seed 2, matching seeds 0 and 1's own already-verdicted acq_pass. 0 falls/24 across all 4 modes, gait_valid 21/24 -- IDENTICAL total to this seed's own crutchoff-s2-acq1 baseline (21/24) -- with sacrifice confined to walk_startjitter/sto legs {0,2,5}, exactly the pre-registered allowed set (baseline itself already flags legs 0/5 there; the one new single-episode leg-2 co-sacrifice is within the gate's own explicitly pre-registered leg0/leg2/leg5 allowance, not a new chronic mode). prog/slip/fwd medians track the baseline within noise (walk/det fwd 1.54m vs 1.12m baseline, slip 3.31 vs 4.88 -- both inside the 2.9 teacher band multiple, no regression). Video (walk_det_*, walk_startjitter_sto_2) shows genuine six-leg forward translation, not a skate/freeze artifact. This closes the 3/3 speedwiden ACQ trio as PASS (unlike widen8's heading-widening axis, which was 3/3 ACQ FAIL at the same depth) -- speed-band widening is a safe, composable realism axis for the crutch-off full-DR composite. Next: fold speedwiden into the composite's default recipe for future crutch-off arms; the irr-timing jitter-amplitude bisection (crutchoff-{s1,s2}-irrhalf) is the next open realism-ladder question, already launched by a prior cycle.

