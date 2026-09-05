# cw-walkscratch-easy0905-headset-base-s0c1-noiseonly-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T19:32:05+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgfresh

**wandb_id**: xyz4gzvh

**hypothesis**: Isolation control for headset-base-s0c1-dgnoise-c1 (this cycle, still training): that arm changes TWO things vs the plain undosed s0c1 2M canary at once if read naively (walk_duty_gate ON + a much higher --log-std-final). This arm isolates the noise variable alone: identical seed=0/--init-from base_s0_c1.zip as every sibling in this family, --log-std-final raised -2.0->-1.2 (same as dgnoise-c1) but NO walk_duty_gate (reward.walk_duty_gate left at its default 0.0, matching the plain undosed s0c1 canary otherwise). If leg-4 duty in walk_startjitter/det climbs on ITS OWN (no pricing needed), raising exploration noise alone is the fix and duty_gate was never necessary; if leg-4 stays parked exactly like the undosed twin, duty_gate (or some other explicit price) is a necessary ingredient and dgnoise-c1's result (if it improves) is a genuine interaction effect, not a noise-alone artifact.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition at this checkpoint. Compare walk_startjitter/det leg-4 duty directly against the undosed s0c1 twin's own report (logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_gate/report.json: duty 0.02-0.05, gait_valid 0/6) and against dgnoise-c1's own report once it lands. Read as: leg-4 duty climbs here (noise alone helps) vs stays flat (duty_gate pricing is the necessary ingredient, not just noise) vs both climb similarly (noise is the whole story, duty_gate was a red herring). walk/det+sto must stay >=10/12 valid with no new falls for any reading to be informative (a collapse here would just mean the noise dose is too hot, not a mechanism finding).

