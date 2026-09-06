# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-noise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:02:29+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-noise1x-c1

**hypothesis**: Plain English: does the COMBINED sensor-noise axis (encoder_noise_deg=0.09 + tilt_noise_deg=0.3 + gyro_noise_deg_s=0.5 together, the project's own domain_rand.py own-DR defaults, previously all pinned at 0) stay a clean walk with real training budget, not just a 2M canary glance? noise1x-c1's own 2M canary was 23/24 (one non-chronic leg-5 flag in startjitter/sto, 0 falls) -- the combined-axis complement to the single-axis encnoise1x/gyronoise1x/tiltnoise1x ACQ reads, testing whether stacking three individually-clean sensor axes together still holds at 40M.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls (a repeat of the same non-chronic leg-5 blip is fine). FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears -- would show combined sensor noise compounds where individual axes don't.

