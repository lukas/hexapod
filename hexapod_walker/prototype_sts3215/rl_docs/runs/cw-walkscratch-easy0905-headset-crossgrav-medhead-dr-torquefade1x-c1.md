# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:50:42+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**wandb_id**: 1flk48ly

**hypothesis**: Dose-response follow-up to torquefade2x-c1's PERFECT 24/24 PASS: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean) survive with the torque/battery-assist crutch removed ENTIRELY (dr.torque_scale 3->1, i.e. actuator forcerange back to the real unassisted servo spec) with zero retraining? This is the hardest single point on the torque-fade dose axis -- if it holds, the whole 3x assist crutch was unnecessary for THIS champion's margin; if it fails, it bounds exactly how much assist the gait actually depends on.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- the champion does not need the torque-assist crutch at all. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- locates the torque-assist floor a real hardening-rung must respect.

**verdict**: PASS/INFORMATIVE-POSITIVE (torque-fade dose axis CLOSED at the floor). Removing the 3x torque/battery-assist crutch ENTIRELY (dr.torque_scale 3->1, real unassisted servo forcerange) on the campaign's cleanest champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) gives a PERFECT 24/24 gait_valid, 0 falls, sac=[] every one of 24 episodes across all 4 panels (walk det/sto, startjitter det/sto). Video (walk_det_0..5) shows clean upright six-leg cycling, level body, correct heading, no flag leg. slip/m 4.6-7.9 -- elevated vs the 2.9 teacher band but in the SAME range every DR-restore sibling in this sweep reads (not specific to torque removal). Evidence: this is the hardest point on the dose axis (1x/1.5x/2x/3x now all tried) -- torquefade2x-c1 PASSED perfect earlier, torquefade1x-c1 (this run) is equally perfect, so the whole 3x idealized torque-assist crutch was NEVER load-bearing for this champion's margin at any dose. Closes the torque-fade axis for good; no further dose point needed. What's next: ACQ-scale (40M) durability of this and other single-axis DR-restore canaries is the still-open question (per the campaign's own composition-axis finding that canary-clean does not guarantee ACQ-clean) -- this cycle launched the first two such continuations (friction1x-c1-acq1, mass1x-c1-acq1 by a concurrent cycle).

