# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf-notorquecrutch-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T09:50:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**hypothesis**: Plain English: do the campaign's two riskiest realism axes -- kick-safe dose (walk_kick_prob=0.15, already individually clean) and full torque-crutch removal (torque_scale 1.0 vs the idealized 3x, already individually clean at canary+ACQ for 1.5x/2x and awaiting its own 1x ACQ gate) -- still compose cleanly TOGETHER, isolated from the other ~28 benign axes already confirmed composable via alldrconf1x-c1? This is a sharper 2-axis interaction probe than jumping straight to the full ~30-axis composite (allaxis1x-c1 FAILED there, but confounded by full-dose kick at 0.3, not 0.15), and gives an early read on the torque-crutch x kick interaction while the single-axis torquefade1x-c1-acq1 gate is still computing.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- these two aggressive axes don't interact badly. FAIL/INFORMATIVE-NEGATIVE if a fall or gait_valid collapse appears -- pins the interaction specifically to kick x no-crutch, not the full composite's other ~28 axes.

