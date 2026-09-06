# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-noise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:02:29+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-noise1x-c1

**wandb_id**: wwuo72of

**hypothesis**: Plain English: does the COMBINED sensor-noise axis (encoder_noise_deg=0.09 + tilt_noise_deg=0.3 + gyro_noise_deg_s=0.5 together, the project's own domain_rand.py own-DR defaults, previously all pinned at 0) stay a clean walk with real training budget, not just a 2M canary glance? noise1x-c1's own 2M canary was 23/24 (one non-chronic leg-5 flag in startjitter/sto, 0 falls) -- the combined-axis complement to the single-axis encnoise1x/gyronoise1x/tiltnoise1x ACQ reads, testing whether stacking three individually-clean sensor axes together still holds at 40M.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls (a repeat of the same non-chronic leg-5 blip is fine). FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears -- would show combined sensor noise compounds where individual axes don't.

**verdict**: ACQ PASS/HOLDS (found as an unverdicted orphan -- ledger stuck RUNNING, training+gate both finished). Combined encoder+gyro+tilt sensor-noise DR axis (dr.encoder_noise_deg/dr.gyro_noise_deg_s/dr.tilt_noise_deg all at 1x, per its own gate text testing whether combined sensor noise compounds where individual axes don't) holds at 40M: gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6), 0 falls/terminations across all 24 episodes, only 1 scattered non-chronic sacrificed-leg episode (leg0, walk_startjitter/sto/3 only). Answers the gate's own question: combined sensor noise does NOT compound into a worse failure than any individual noise axis already passed. slip/m med 3.8-4.8 (in-family with sibling per-axis PASSes). Per QUEUE AIM's own STOP on further per-axis spend, no cont40m continuation follows -- recorded for SKILLS.md/ledger hygiene only.

