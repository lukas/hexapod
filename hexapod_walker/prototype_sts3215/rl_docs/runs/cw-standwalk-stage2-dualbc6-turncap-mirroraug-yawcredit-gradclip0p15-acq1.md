# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T12:09:32+00:00

**pod**: hexapod-mjx-train-7

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: tsuqyk9w

**hypothesis**: Plain English: the gradclip0p15 canary at 2M didn't just recover turn authority, it OVERSHOT the plain-continuation control (wz_med 0.198/-0.200 vs 0.083/-0.138) while ALSO fixing the walk-quality collapse (prog/slip back to control levels) that the unclipped dose and the looser 2.0 clip both showed -- does that hold or erode over an acquisition-scale 38M budget (matching the turnpay-acq1 precedent), the way turn authority has eroded on every longer-budget arm in this campaign so far?

**gate**: PASS/PROMOTE (new campaign best) if final (38M) probe_turn_authority wz_med stays >=0.15 both signs (allowing some erosion off the 2M 0.198/-0.200 seed but nowhere near the ~0.03-0.09 erosion floor every prior longer-budget arm settled to) AND own purewalk det gait_valid>=5/6 zero falls AND progress_ratio in/above the 0.40-0.48 wave-1 band AND slip/m <=2.9. PARTIAL if wz_med lands 0.05-0.15 (real retention, quantify) or progress/slip regress mildly. FAIL if wz_med erodes back under 0.05 both signs (matching every prior acquisition-scale erosion in this campaign) or gait/progress collapses back to the rr1/gradclip2p0 pattern (prog<0.25, slip>4).

