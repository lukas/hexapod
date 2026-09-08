# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-acq10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T05:58:16+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1

**hypothesis**: Plain English: cartfoot-c1's 2M canary showed the Cartesian foot-space action decode re-acquires zero-fall six-leg walking from a fully scrambled joint-space warm start, but training reward kept declining and slip ran 3-10x worse than the matched joint-space control at equal steps -- this arm mirrors the campaign's own duty-charge 10M-continuation protocol to test whether that gap is a closing re-acquisition transient or a real asymptotic cost of the foot-space parameterization. Same recipe/RNG2, warm-started from cartfoot-c1's own 2M checkpoint, +10M steps (12M cumulative).

**gate**: Standard 24-ep walk/walk_startjitter det+sto gate read AGAINST the matched cartfoot-offctrl-acq10m continuation at the SAME cumulative budget. IMPROVING if slip_per_m median moves toward (or into) the offctrl band in >=3/4 groups AND gait_valid holds >=18/24 with 0 falls: fund a further continuation. PLATEAU/WORSE if slip stays >=2x the matched offctrl-acq10m in >=3/4 groups with 0 falls: reads as a structural parameterization cost, not a warm-start transient -- closes the retrofit-continuation path for this mechanism. FAIL if walking regresses (new falls, or gait_valid<12/24 with reward flat).

**refused_reason**: hexapod-mjx-train-0 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont10m — GPU pods host exactly one run; pick a free GPU pod.

