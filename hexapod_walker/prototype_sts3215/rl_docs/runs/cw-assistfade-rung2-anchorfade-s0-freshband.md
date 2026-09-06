# cw-assistfade-rung2-anchorfade-s0-freshband

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T17:04:40+00:00

**pod**: hexapod-mjx-train-1

**steps**: 12000000

**parent**: cw-assistfade-rung2-anchorfade-s0

**wandb_id**: x8h2ftwk

**hypothesis**: Plain English: does the rung-2 anchor-fade ignition itself, run from TRUE random actor weights with the widened 0.04-0.08 m/s speed band baked in from step 0, escape the achieved-speed-ignoring pathology that all three hardening-stage escalations (-v2 no boost, -lsd2 std~0.135, -explore2 std~0.27, the last one a confirmed FAIL-COLLAPSE with 21/24 falls) failed to fix? Every prior hardening arm warm-started from a checkpoint that had already spent 8-10M steps habituating a SINGLE fixed 0.06 m/s cadence during ignition before ever seeing a varying command -- this arm tests whether that habituation, not the hardening recipe itself, is the structural cause. Byte-identical to the working seed-0 ignition recipe (cw-assistfade-rung2-anchorfade-s0 -> -reseed8m-gatefix, the 2-seed CONFIRMED rung-2 mechanism: bc_anchor_coef=3.0, bc_anchor_anneal_gate=1, bc_anchor_anneal_assay_reseed=1 fix already applied from step 0) except goal.walk_speed_min_m_s/max_m_s=0.04/0.08 (was fixed 0.06/0.06) and NO --init-from (fresh random actor, not warm-started from any checkpoint) with a 12M combined budget (>= the 2M+8M=10M cumulative that passed the fixed-band version, +2M cushion since a harder-to-satisfy widened-band ignition bar may take longer to latch).

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches and train/bc_coef ramps 3->0 within the 12M budget, AND (b) the post-anneal held-out det+sto gate (4 modes) clears gait_valid majority/0 falls/progress_ratio>=0.35, AND (c) per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across the widened band (not clustered within ~0.005 m/s across a >=0.02 m/s commanded spread, the exact -v2/-lsd2/-explore2 fingerprint). FAIL - HABITUATION-NOT-THE-CAUSE if the gate latches, gait is clean, but achieved speed STILL ignores the band -- closes the ignition-order hypothesis, escalates to an explicit stride-amplitude reward term next. FAIL - MECHANISM if the anchor never latches or gait collapses under the wider band before/after the anneal (would mean the widened band itself destabilizes ignition, a new finding). FAIL - COLLAPSE if gait/falls are worse than the working fixed-band ignition recipe at the matched budget.

