# cw-assistfade-rung1-bcinit-taskonly-s2-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:18:50+00:00

**pod**: hexapod-mjx-train-8

**steps**: 8000000

**parent**: cw-assistfade-rung1-bcinit-taskonly-s2

**hypothesis**: Plain English: the second mechanism-healthy rung-1 seed also walks cleanly but at ~65% of the required forward progress after its 2M canary -- give the same policy 5x more budget and see if speed alone rises to the ignition bar without wrecking the gait, giving n=2 on the continuation question alongside s1-cont8m. Continuation of cw-assistfade-rung1-bcinit-taskonly-s2 from its own 2M final checkpoint (md5 951bd04390264e9b9ed0c93361d483d2), byte-identical rung-1 recipe (EASIER_WALKING_CURRICULUM: BC init, task-only PPO, no anchor, fixed forward 0.06 m/s, 10s eps, mesh/100Hz). Canary evidence: gait_valid 23/24, 0 falls, all six legs cycling on the det strip, det prog med 0.23 vs 0.35 bar, reward not flat (quarters 83/79/121/100). 08-21 ruling: continue-not-fail. Prediction-if-true: det prog med >= 0.35 by 10M total with gait_valid intact (jointly with s1-cont8m this makes rung-1 ignition a 2-seed result). Prediction-if-false: prog plateaus <0.30 with reward flat => rung-1 budget-ceiling evidence with n=2, retreat per doc (rung-2 slower fade / rung-3 residuals), NOT a reward-dose/architecture retry. Strongest alternative: seed s1's continuation alone passes and s2's does not => ignition is seed-lottery, panel-level selection needed.

**gate**: IGNITION at 10M total (EASIER_WALKING_CURRICULUM.md bar, own-cfg det panel, video first): sustained forward translation full episode, repeated alternating support transitions, all six legs participating, ZERO falls and ZERO safety terminations (over_current reported separately per the 09-04 uncalibrated-current ruling; corroborated stalls only), progress_ratio >= 0.35 det med (canary baseline 0.23). Slip/current recorded, not gated at ignition. PASS => rung-1 ignition met on this seed (joint read with s1-cont8m); FAIL gait-clean-but-plateaued or gait-destroyed => rung-1 ceiling evidence, retreat one rung per doc. Never a reward-dose or architecture retry on this rung (doc-binding).

