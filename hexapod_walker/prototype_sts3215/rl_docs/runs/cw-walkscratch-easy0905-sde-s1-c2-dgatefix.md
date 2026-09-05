# cw-walkscratch-easy0905-sde-s1-c2-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T15:57:12+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s1-c2

**wandb_id**: 8x8i8jt6

**hypothesis**: Plain English: sde-s1-c2 learned LEGPARK-SKATE (chronically parks 1-2 legs, rides income from the remaining legs' skate). The recency-based walk_gait_gate repair is closed 6/6 (gamed by rare token swings). The new walk_duty_gate mechanism (per-leg trailing-3s contact-DUTY income gate, un-dodgeable by a rare touch) already showed a real escape in walk/det when applied from an EARLY undifferentiated checkpoint (sde-s1-dg1, CANARY PASS) -- but that arm had a checkpoint-provenance bug and never actually continued c2's own entrenched-skate checkpoint. This arm fixes that: --init-from points at sde_s1_c2.zip itself (the real FAIL checkpoint), hand-built via backlog add to avoid the respec clone-without-init-from-source gotcha. Does the SAME mechanism bring an ALREADY-parked leg back down, not just prevent parking from never having started?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice, the exact walk_gait_gate failure signature) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg in those episodes. FAIL: factor saturates while a leg stays <0.10 duty, or reward/speed collapses -- closes walk_duty_gate on the entrenched-checkpoint case specifically.

**verdict**: CANARY FAIL - MECHANISM: completes the n=4 entrenched-checkpoint walk_duty_gate read (found this run's harness gate had already been silently reaped by an earlier cycle's pollreap; picked it up this cycle since capacity is fully idle and it was the last un-triaged arm of the batch). Harness: walk/det gait_valid 0/6, legs [1,4] sacrificed identically all 6 episodes (fwd/slip bit-identical to 2 decimals), walk_startjitter/det 0/6 same pair, walk/sto 1/6, walk_startjitter/sto 0/6 -- frame strip (walk_det_0_sheet.png) shows legs 1+4 tucked/dragging every sampled frame, unchanged pose across episodes. env/walk_duty_gate_factor genuinely DECLINES 1.0->0.54 (real pricing, not saturated) while ep_rew_mean quarters RISE (94->234->338->410) -- the same 08-21 rising-reward/declining-factor shape sibling sde-s2-c2-dgatefix showed before its own 40M continuation (sde-s2-c2-dgatefix-cont40m, already verdicted ACQ FAIL this campaign) re-saturated the factor to 0.94 with the sacrifice unchanged. Since that continuation already answers what happens when this exact shape is given more budget (re-saturation, no repair), funding a duplicate 40M continuation for this seed would be redundant, not exploratory -- no continuation launched. This closes the entrenched-checkpoint walk_duty_gate batch at n=4/4 CANARY FAIL (sde-s2-c2-dgatefix, sdehalfgrav-remcost-s0/s1-dgatefix, sde-s1-c2-dgatefix): retrofitting duty_gate onto an already-converged LEGPARK exploiter never repairs it within reachable budget regardless of whether training-time reward rises or falls. Combined with the from-scratch dgfresh closure (freeze) and the strong-floor dgate2 closure (inert-dose / engaged-no-repair) on the non-gSDE family, 'price the parked leg with walk_duty_gate' is now closed end-to-end for every checkpoint-provenance case tried on both the gSDE and non-gSDE families. Next: a genuinely new mechanism (harder floor + explicit per-leg exploration anneal, or structural init change) is needed before further duty_gate-class spend; no such mechanism is bank-proven yet this cycle so none is launched speculatively.

