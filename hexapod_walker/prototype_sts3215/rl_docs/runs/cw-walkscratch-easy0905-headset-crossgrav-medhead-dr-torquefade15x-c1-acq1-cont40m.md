# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T09:39:00+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1

**wandb_id**: xw4dkuk9

**hypothesis**: Plain English: does the 1.5x torque-fade axis (dr.torque_scale=1.5,1.5, the harder end of the torque-crutch-removal dose ladder) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of friction1x/mass1x/torquefade2x. Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, reward rising every quarter 937->1675->1790->1912).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 24/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: 1.5x torque-fade axis holds at 80M cumulative (2nd 40M block on top of the clean torquefade15x-c1-acq1 40M parent). Evidence: gate PERFECT 24/24 gait_valid across all 4 panels (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), 0 falls/terms, sac=[] every one of 24 episodes -- identical to the parent's own 24/24, 0-falls read at 40M. Slip/m stays in the same band (walk/det 4.21 vs parent 4.23, walk/sto 5.04 vs 5.25; startjitter panels 5.83/6.19 vs parent's 5.06/5.69, a modest but non-disqualifying rise, no chronic single-leg pattern). Reward still climbing every quarter (1240->2143->2246->2328). Contact sheet confirms clean six-leg cycling, no flag/drag/skate. Why: per the gate's own PASS/HOLDS criterion (gait_valid majority + no new chronic single-leg sacrifice + 0 falls) this is a clean HARDENING confirmation, matching the sibling torquefade2x-c1-acq1-cont40m pattern verdicted this same session. Next: closes the torque-fade dose axis's endurance question for good (1x/1.5x/2x all now clean at ACQ+cont40m scale); per QUEUE AIM no further per-axis cont40m spend follows -- remaining frontier is the two in-flight composite ACQs (allaxis-nokick-c1-acq1, allaxiskickhalf-nocrutch1x-c1-acq1) and the kickhalf1x-c1-acq1 kick-dose read.

