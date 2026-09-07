# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T15:33:35+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: lanhu3s9

**hypothesis**: The frozen champion walks at 1.6-2.1x its commanded speed and pays nothing for the surplus; if we charge that surplus (and only it), the gait should slow to the commanded speed -- and if its ~4.5/m contact-point skating is financed by the surplus speed (09-07 audit: measurement honest, frames/rolling/chatter/transients all falsified), slip should drop with it. New opt-in reward.walk_freeprog_overspeed_charge=1.0 charges k_free*(along/cap-1) above the cap only, stride-EMA along, below-cap income bit-exact; bank-proven (4 WALKCURR_OVERSPEED tests). Warm from the champion, seed 2, otherwise identical recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism canary vs frozen parent's own gate (walk det med: slip/m 4.98, prog 1.87, gv 22/24, 0 falls): MECHANISM WORKS if prog_ratio med drops toward <=1.35 with gv >=18/24 and 0 falls. Then: slip/m med <=3.9 = overspeed-financed slip CONFIRMED (acq continuation licensed); prog<=1.35 but slip/m >=4.5 = hypothesis FALSIFIED, records a genuine gait-style slip floor (close axis, next lever is contact-model fidelity). MECHANISM FAIL if gv <12/24, any fall where parent had none, or prog collapses <0.75 (charge re-opened the stall basin).

