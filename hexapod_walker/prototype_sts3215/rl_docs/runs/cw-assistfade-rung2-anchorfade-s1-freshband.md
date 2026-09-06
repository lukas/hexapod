# cw-assistfade-rung2-anchorfade-s1-freshband

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - COLLAPSE

**created**: 2026-09-06T17:05:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 12000000

**parent**: cw-assistfade-rung2-anchorfade-s1

**wandb_id**: 4voybsdm

**hypothesis**: Plain English: does the rung-2 anchor-fade ignition itself, run from TRUE random actor weights with the widened 0.04-0.08 m/s speed band baked in from step 0, escape the achieved-speed-ignoring pathology that all three hardening-stage escalations (-v2 no boost, -lsd2 std~0.135, -explore2 std~0.27, the last one a confirmed FAIL-COLLAPSE with 21/24 falls) failed to fix? Every prior hardening arm warm-started from a checkpoint that had already spent 8-10M steps habituating a SINGLE fixed 0.06 m/s cadence during ignition before ever seeing a varying command -- this arm tests whether that habituation, not the hardening recipe itself, is the structural cause. Byte-identical to the working seed-1 ignition recipe (cw-assistfade-rung2-anchorfade-s1 -> -reseed8m-gatefix, the 2-seed CONFIRMED rung-2 mechanism: bc_anchor_coef=3.0, bc_anchor_anneal_gate=1, bc_anchor_anneal_assay_reseed=1 fix already applied from step 0) except goal.walk_speed_min_m_s/max_m_s=0.04/0.08 (was fixed 0.06/0.06) and NO --init-from (fresh random actor, not warm-started from any checkpoint) with a 12M combined budget (>= the 2M+8M=10M cumulative that passed the fixed-band version, +2M cushion since a harder-to-satisfy widened-band ignition bar may take longer to latch).

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches and train/bc_coef ramps 3->0 within the 12M budget, AND (b) the post-anneal held-out det+sto gate (4 modes) clears gait_valid majority/0 falls/progress_ratio>=0.35, AND (c) per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across the widened band (not clustered within ~0.005 m/s across a >=0.02 m/s commanded spread, the exact -v2/-lsd2/-explore2 fingerprint). FAIL - HABITUATION-NOT-THE-CAUSE if the gate latches, gait is clean, but achieved speed STILL ignores the band -- closes the ignition-order hypothesis, escalates to an explicit stride-amplitude reward term next. FAIL - MECHANISM if the anchor never latches or gait collapses under the wider band before/after the anneal (would mean the widened band itself destabilizes ignition, a new finding). FAIL - COLLAPSE if gait/falls are worse than the working fixed-band ignition recipe at the matched budget.

**verdict**: Result: gait destroyed by budget, the 3rd corner of the habituation-dose grid to do so. Held-out gate: gait_valid FALSE in all 12 walk/det+walk/sto episodes, legs [4,5] (or [4] alone) chronically sacrificed every single episode, slip_per_m 4.5-8.8 (vs 2.9 teacher band), speed_mean_m_s flat 0.030-0.032 regardless of the 0.035-0.066 commanded band (also fails criterion c). bc_anchor_anneal/gate_pass DID latch cleanly at 1.52M and bc_coef ramped 3->0 by ~7M as designed (mechanism itself healthy) -- but rollout/ep_rew_mean shows a clear late-training DECLINE (climbs to a peak ~1195 around 9M then falls to 425 by the 12M finish), i.e. reward degrading in lockstep with the gait destruction, not the 08-21 rising-reward continuation case. Why: TRUE-random-init (0 habituation, matching sibling s0-freshband) but this seed's basin collapses under the full 12M budget after the anchor fully anneals away -- same budget-driven leg-sacrifice entrenchment already logged for rung 1's 3/3 seed failures and several unrelated crossgrav/sde lineages this week. Next: this closes the last cell of the 4-arm habituation-dose grid (s0-freshband FAIL-HABITUATION-NOT-THE-CAUSE clean-gait/flat-speed, s1-freshband FAIL-COLLAPSE gait-destroyed, s0-ignitewiden pending same-cycle verdict, s1-ignitewiden FAIL-STILL-IGNORES clean-gait/flat-speed) -- do not fund a 5th same-mechanism seed; per STATUS Next#0 escalate to an explicit stride-amplitude/speed-tracking reward term (semantics-bank first).

