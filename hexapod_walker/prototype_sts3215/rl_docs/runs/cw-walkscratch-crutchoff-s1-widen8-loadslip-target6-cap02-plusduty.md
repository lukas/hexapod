# cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-cap02-plusduty

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T19:23:13+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-cap02-alone

**hypothesis**: Plain English: the loadslip-ratio-charge (excess-cap) isolation test just closed 2/2 seeds with mechanism-healthy/no-efficacy results -- but a fresh read of this exact eval's own per-leg telemetry shows the dominant visible pathology in these episodes (walk/det leg5 duty 0.04-0.09, occasionally leg0 too) is the LOW-duty 'flag leg' (airborne) type, which walk_leg_loadslip_ratio_charge does NOT target (it only prices the opposite HIGH-duty/high-slip dragged-anchor type) -- and this isolation lineage deliberately runs with walk_leg_duty_ratio_charge=0.0 (turned off to isolate loadslip cleanly), i.e. the one charge in this whole family that DOES directly target the observed flag-leg shortfall was never active in the arm being scored for efficacy. This arm restores walk_leg_duty_ratio_charge=150.0 (target=0.30, the already-mechanism-proven dose from the guardfix1 lineage; its own dose-escalation FAILs were about EFFICACY not mechanism health) ALONGSIDE the now excess-capped loadslip charge, on the SAME clean widen8-acq1 init the isolation canaries used -- the first time both charge types run together WITH the collapse-fixing cap present (every prior combined-charge run predates the cap and showed the uncapped reward collapse this cap was built to fix). Root-cause chain: behavior (leg5 airborne, duty 0.04-0.09) <- incentive gap (no charge prices this leg's shortfall in the isolation arm) <- pricing choice (duty-ratio-charge=0 for isolation cleanliness) -- this arm restores the missing incentive.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS-worth-CONTINUE if (a) reward stays bounded, no order-of-magnitude collapse vs this seed's own capped-loadslip-alone quarters AND (b) >=3/4 of the 4 held-out groups jointly improve slip+progress vs the widen8-acq1 baseline (same bar as every sibling in this family) AND (c) walk/det's specific leg5 sacrifice clears (duty_cycle[5] rises out of the <0.10 sacrificed band in the majority of walk/det episodes) -- clause (c) is this arm's own specific mechanism claim, over and above the family's generic efficacy bar. FAIL if reward collapses the same uncapped way as the pre-cap combined-charge lineage, or efficacy stays <3/4 groups, or leg5 stays sacrificed despite the restored duty-ratio charge -- closes the 'isolation removed the wrong charge' hypothesis and confirms the flag-leg pathology needs a structurally different fix than any additive peer-ratio charge tried so far. Read together with its seed twin before drawing a final PASS/FAIL.

**refused_reason**: hexapod-mjx-train-1 code marker 6cd5f7b44f204048fbb96fe181298dd0ca6be020-dirty != local HEAD 6cd5f7b44f204048fbb96fe181298dd0ca6be020 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-1 (and snapshot/commit before that if the tree is dirty).

