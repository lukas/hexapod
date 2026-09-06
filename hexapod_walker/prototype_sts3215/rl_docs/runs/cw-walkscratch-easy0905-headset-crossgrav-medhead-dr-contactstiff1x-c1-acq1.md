# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:58:55+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1

**wandb_id**: vy3mdsxv

**hypothesis**: Plain English: does the ground-contact-stiffness/compliance-spread axis (dr.contact_stiff_scale 0.7-2.0x, previously pinned identical every episode) stay a clean walk with real training budget, not just a 2M canary glance? contactstiff1x-c1's own 2M canary was 23/24 (one non-chronic leg-4 flag, 0 falls) -- joining the individual-axis ACQ-durability batch alongside friction1x/mass1x/encnoise1x/torquefade-dose/zerobias1x/latency1x/push1x-acq1.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls (a repeat of the same non-chronic leg-4 blip is fine). FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: ACQ PASS/HOLDS: 40M gait_valid 23/24 (walk/det 6/6, sto 6/6, startjitter/det 5/6, startjitter/sto 6/6), 0 falls/terms. Same class as the 2M canary (also 23/24, single non-chronic startjitter/det flag) though the specific flagged episode/leg shifted (canary: ep5 leg4; ACQ: ep1 leg5) -- still exactly one isolated episode in one mode, no chronic single-leg pattern, no new fall. slip/m flat to slightly improved (det med 3.74 vs canary 3.68, sto/startjitter bands unchanged). Reward rising. 7th individual-axis DR-restore ACQ confirmation to hold (contact-stiffness/compliance axis). Per STATUS QUEUE AIM this is another already-clean axis confirmed at ACQ scale -- no further per-axis spend justified for this axis.

