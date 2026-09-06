# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-06T11:02:27+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1

**wandb_id**: bidomeob

**hypothesis**: Plain English: does the full ~30-axis realism composite, with kick at its proven-safe half dose (0.15) AND the 3x torque crutch fully removed (the real unassisted servo spec), hold up at real acquisition budget (40M) -- this is QUEUE AIM item (3)'s second composite-ACQ funding step, a DIFFERENT recipe from the parallel allaxis-nokick-c1-acq1 (which keeps the crutch ON and disables kick entirely). Single lever vs the canary: budget 2M->40M, otherwise byte-identical.

**gate**: ACQ gate (40M): aggregate gait_valid majority (>=18/24) sustained at ACQ scale (matching or improving the 21/24 canary), 0 falls/terminations, no NEW chronic single-leg sacrifice, slip/m recorded (expected higher than the crutch-ON composites, ~7-17/m at canary scale) but not itself gating. PASS -> confirms the full-realism-without-crutch composite is durable at acquisition scale, a stronger realism claim than allaxis-nokick-c1-acq1 alone (keeps the crutch). FAIL/entrenches -> the composite needs the torque crutch after all once trained longer, even though the 2M canary showed no such need.

**verdict**: Full ~30-axis realism composite WITHOUT the torque crutch (dr.torque_scale dropped 3->1, the true unassisted servo spec) holds at 40M acquisition scale, clearing its own pre-registered bar. Held-out mesh gate: gait_valid 22/24 (walk/det 6/6, walk/sto 5/6, startjitter/det 5/6, startjitter/sto 6/6), matching/improving the 21/24 canary; 0 falls/terminations across all 24 episodes; the 2 sacrificed-leg episodes (sto/4: leg2, startjitter/det/1: legs0+2) are scattered/non-chronic (varies episode to episode, no single leg out every time) -- video-confirmed upright six-leg cycling throughout, no collapse. Slip elevated as expected without the crutch (5-13/m vs the crutch-ON composite's 3-5/m) but this gate does not gate slip, only records it -- per this doc's own launch notes, higher slip here is the price of dropping the crutch, to be addressed by future hardening, not a gate failure. Reward monotonic (412.9/849.8/1065.2/1200.4). Confirms the full-realism-without-crutch composite is durable at acquisition scale -- a stronger realism claim than the crutch-ON allaxis-nokick-c1-acq1 sibling (found this cycle, separately flagged DIG-IN for its own 2-fall read). Closes QUEUE AIM item (3)'s cont40m-scale confirmation and half of item (4)'s precondition.

