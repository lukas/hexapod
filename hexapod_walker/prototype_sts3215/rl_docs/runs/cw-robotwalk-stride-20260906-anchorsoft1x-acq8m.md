# cw-robotwalk-stride-20260906-anchorsoft1x-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T21:15:03+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-robotwalk-stride-20260906-anchorsoft1x

**hypothesis**: Plain English: the softer anchor dose (bc_anchor_coef=1.0) cleared its 2M-step mechanism-health canary clean (0 falls, no duty-lock, gait_valid 24/24) with a real if modest progress gain over Candidate B in 3/4 held-out modes (+9 to +22%, one mode flat). This continues the SAME lineage (warm from the canary's own 2M checkpoint, not restarting from Candidate B) to the full 8M ACQ budget the campaign always intended, to see whether the gain compounds with more training or plateaus at the canary's level. Prediction-if-true: det h000 prog_m rises further above the 0.31-0.33 Candidate B band (toward the original 0.40 stretch target) while gait/slip/fall gates stay clean. Prediction-if-false: progress plateaus near the canary's ~0.34-0.35 reading with reward still rising (closes the anchor-dose axis at this coef, matching FAIL-NO-GAIN at full budget) or the gait degrades under more steps (destabilizes late, a different failure mode than arm A's early collapse).

**gate**: ACQUISITION gate (8M budget): PASS needs 0 falls, gait_valid>=22/24 all 4 modes, slip/m<=2.9, AND det h000 prog_m measurably above (not another ~5% wiggle) the canary's own 0.343 reading and above Candidate B's 0.31-0.33 band -- read together with the anchorsoft2x-acq8m sibling as a matched dose pair, not independent seeds. FAIL-PLATEAU if gait stays clean but prog_m sits flat at the canary's ~0.34 level (closes the anchor-dose axis at full budget, hands the lever to the hypothesis's own named alternative -- a faster motion source / cadence-CPG harvest). FAIL-LATE-COLLAPSE if duty-lock/falls/slip degrade with more steps despite a clean 2M canary (implicates the log-std final anneal target or extended-budget over-optimization of the loadslip/sway gates, not anchor dose).

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

