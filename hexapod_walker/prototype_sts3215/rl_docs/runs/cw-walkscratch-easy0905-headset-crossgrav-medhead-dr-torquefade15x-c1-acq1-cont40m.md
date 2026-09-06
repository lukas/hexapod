# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T09:39:00+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1

**wandb_id**: xw4dkuk9

**hypothesis**: Plain English: does the 1.5x torque-fade axis (dr.torque_scale=1.5,1.5, the harder end of the torque-crutch-removal dose ladder) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of friction1x/mass1x/torquefade2x. Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, reward rising every quarter 937->1675->1790->1912).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 24/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops (<12/24), a chronic single-leg pattern emerges, or a fall appears.

