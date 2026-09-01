# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrollctrl-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-01T01:00:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary

**hypothesis**: Is bounded-KL alone (no actor freeze) sufficient to stop turn-authority erosion, isolating kl-rollback from the value-warmup freeze it was paired with in the sibling klroll-acq1 arm?

**gate**: PASS if final probe_turn_authority wz_med>=0.10 both signs at 38M AND gait_valid>=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48 (kl-rollback alone sufficient). PARTIAL if authority holds above the prior mechanism-class floor (>0.05 both signs) but under 0.10 (helps but insufficient alone). FAIL if authority erodes to the same <=0.05 floor as every prior refuted mechanism (kl-rollback alone refuted, decision falls to the paired klroll-acq1 sibling read).

