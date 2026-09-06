# cw-robotwalk-stride-20260906-anchorsoft2x-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-06T21:17:02+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-robotwalk-stride-20260906-anchorsoft2x

**wandb_id**: jymcz68k

**hypothesis**: Plain English: the softer anchor dose (bc_anchor_coef=1.5, half of Candidate B's 3.0) cleared its 2M-step mechanism-health canary clean (0 falls, no duty-lock, gait_valid 24/24) with a real if modest progress gain over Candidate B in 3/4 held-out modes (+12 to +16%, one mode flat), reading essentially identically to its anchorsoft1x (coef=1.0) sibling at canary scale. This continues the SAME lineage (warm from the canary's own 2M checkpoint, not restarting from Candidate B) to the full 8M ACQ budget, launched together with the anchorsoft1x-acq8m sibling as a matched dose pair to see whether the two doses resolve differently at full budget or stay indistinguishable. Prediction-if-true: det h000 prog_m rises further above the 0.31-0.33 Candidate B band, and/or separates from the anchorsoft1x-acq8m sibling's full-budget reading (revealing a real dose-response). Prediction-if-false: progress plateaus near the canary's ~0.35-0.41 reading with reward still rising (FAIL-PLATEAU, closing the anchor-dose axis at this coef) or the gait degrades late (FAIL-LATE-COLLAPSE) despite the clean canary.

**gate**: ACQUISITION gate (8M budget): PASS needs 0 falls, gait_valid>=22/24 all 4 modes, slip/m<=2.9, AND det h000 prog_m measurably above (not another ~5% wiggle) the canary's own 0.354 reading and above Candidate B's 0.31-0.33 band -- read together with the anchorsoft1x-acq8m sibling as a matched dose pair, not an independent seed. FAIL-PLATEAU if gait stays clean but prog_m sits flat at the canary's ~0.35-0.41 level (closes the anchor-dose axis at full budget for this coef; if the anchorsoft1x-acq8m sibling ALSO reads FAIL-PLATEAU, the whole anchor-dose axis is closed and the next lever is the hypothesis's own named alternative -- a faster motion source / cadence-CPG harvest). FAIL-LATE-COLLAPSE if duty-lock/falls/slip degrade with more steps despite a clean 2M canary.

