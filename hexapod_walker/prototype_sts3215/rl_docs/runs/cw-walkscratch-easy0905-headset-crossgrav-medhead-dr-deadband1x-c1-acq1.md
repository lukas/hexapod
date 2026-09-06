# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:05:14+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**wandb_id**: neh736zk

**hypothesis**: Plain English: does the actuator-deadband axis (dr.deadband_scale=1,1, previously collapsed to 0 the whole campaign) stay a clean walk with real training budget, not just a 2M canary glance? deadband1x-c1's own 2M canary was 23/24 (one non-chronic leg-5 flag, 0 falls) -- joining the individual-axis ACQ-durability batch alongside friction1x/mass1x/encnoise1x/torquefade-dose/zerobias1x/latency1x/push1x-acq1.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls (a repeat of the same non-chronic leg-5 blip is fine). FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: ACQ PASS/HOLDS: 40M gait_valid 23/24 (walk/det 6/6, sto 6/6, startjitter/det 6/6, startjitter/sto 5/6), 0 falls/terms. Same class as the 2M canary (also 23/24, single non-chronic startjitter flag) though the specific flagged episode/leg/mode shifted (canary: startjitter/det ep1 leg5; ACQ: startjitter/sto ep3 leg0) -- still exactly one isolated episode, no chronic single-leg pattern, no new fall. slip/m flat (det med 4.84 vs canary 4.94, other panels unchanged band). Reward rising. 8th individual-axis DR-restore ACQ confirmation to hold (actuator-deadband axis). Per STATUS QUEUE AIM this is another already-clean axis confirmed at ACQ scale -- no further per-axis spend justified for this axis.

