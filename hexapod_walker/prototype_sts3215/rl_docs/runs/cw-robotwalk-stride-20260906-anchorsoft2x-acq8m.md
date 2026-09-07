# cw-robotwalk-stride-20260906-anchorsoft2x-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T21:18:24+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-robotwalk-stride-20260906-anchorsoft2x

**hypothesis**: Plain English: the softer anchor dose (bc_anchor_coef=1.5) cleared its 2M-step mechanism-health canary clean (0 falls, no duty-lock, gait_valid 24/24) with a real if modest progress gain over Candidate B in 3/4 held-out modes (+12 to +16%, one mode flat) -- reading essentially identically to its coef=1.0 sibling. This continues the SAME lineage (warm from the canary's own 2M checkpoint, not restarting from Candidate B) to the full 8M ACQ budget, matched with the anchorsoft1x-acq8m sibling to see whether the two dose points diverge with more training or both plateau/gain identically. Prediction-if-true: det h000 prog_m rises further above the 0.31-0.33 Candidate B band while gait/slip/fall gates stay clean, tracking or exceeding its coef=1.0 sibling. Prediction-if-false: progress plateaus near the canary's ~0.35 reading with reward still rising, or the gait degrades under more steps (a late failure mode distinct from arm A's early collapse).

**gate**: ACQUISITION gate (8M budget): PASS needs 0 falls, gait_valid>=22/24 all 4 modes, slip/m<=2.9, AND det h000 prog_m measurably above (not another ~5% wiggle) the canary's own 0.354 reading and above Candidate B's 0.31-0.33 band -- read together with the anchorsoft1x-acq8m sibling as a matched dose pair, not independent seeds. FAIL-PLATEAU if gait stays clean but prog_m sits flat at the canary's ~0.35 level (closes the anchor-dose axis at full budget for this coef too). FAIL-LATE-COLLAPSE if duty-lock/falls/slip degrade with more steps despite a clean 2M canary.

**refused_reason**: a process for cw-robotwalk-stride-20260906-anchorsoft2x-acq8m already exists on hexapod-mjx-train-1

