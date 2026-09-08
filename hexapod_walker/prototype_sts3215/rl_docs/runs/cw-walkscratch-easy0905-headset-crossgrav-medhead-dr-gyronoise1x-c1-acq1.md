# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-06T08:06:35+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

**wandb_id**: mfxo6gt4

**hypothesis**: Plain English: does the IMU gyro-noise axis (dr.gyro_noise_deg_s=0.5, previously pinned at 0 the whole campaign) stay a clean walk with real training budget, not just a 2M canary glance? gyronoise1x-c1's own 2M canary was a PERFECT 24/24 (sac=[] every episode, 0 falls) -- joining the individual-axis ACQ-durability batch alongside friction1x/mass1x/encnoise1x/torquefade-dose/zerobias1x/latency1x/push1x-acq1.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: CANARY PASS: 40M ACQ read of the gyro-noise DR-restore axis (2M canary source, 09-06) on the medhead-crossgrav champion. gait_valid 23/24 (6/6,6/6,6/6, 5/6 -- 1 sacrifice, walk_startjitter/sto ep3 leg0, non-chronic singleton), 0 falls/terminations in all 24 episodes, slip/m med 3.88-4.55 (in-band, matches sibling axes), progress_ratio med 1.78-1.88. Reward quarters rise monotonically [791.2, 1386.1, 1448.9, 1531.2], still climbing at 40M. Contact-sheet + walk_det frame strip: body clearly translating, legs cycling, no flag-leg/skate. This eval was orphaned since 09-06 (checkpoint pulled twice, gate harness finished on-pod but was never copied back to the controller -- prestage gap); reaped via ops.sh podeval this cycle (found already finished on hexapod-mjx-train-8, copy-back only, no relaunch). Confirms the gyro-noise axis durable at ACQ depth, joining the already-closed single-axis DR-restore sweep (09-06 ~10:1x-10:24 closure) -- mop-up of a pending read, no new frontier action.

