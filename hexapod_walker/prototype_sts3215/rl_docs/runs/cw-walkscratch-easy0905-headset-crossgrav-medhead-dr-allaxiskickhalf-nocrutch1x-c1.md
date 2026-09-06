# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T10:20:25+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf1x-c1-r2

**wandb_id**: i5bvlxvc

**hypothesis**: Plain English: does the full ~30-axis kick-safe realism composite (allaxiskickhalf1x-c1-r2, gate still computing) ALSO survive with the torque/battery-assist crutch removed entirely (dr.torque_scale 3->1, the real unassisted servo spec), given that dose is already individually clean at both canary AND acquisition scale (torquefade1x-c1-acq1 ACQ PASS 24/24) and the smaller 2-axis kick+no-crutch probe (kickhalf-notorquecrutch-c1) is separately mid-gate? This is the full-composite half of item 3's 'composite WITHOUT the 3x crutch' step -- an independent read from the isolated 2-axis pair, since the other ~28 axes (mass/friction/latency/imu/etc) could interact with a de-crutched actuator even if kick+no-crutch alone does not. If true (PASS): the 3x torque crutch was never load-bearing for full-realism composite tolerance either, simplifying the eventual champion recipe. If false (FAIL): the crutch is specifically protecting against a torque-limited actuator's interaction with the OTHER realism axes (mass/friction/stiffness), not just kick recovery, and the composite ACQ (once allaxiskickhalf1x-c1-r2 gate PASSes) must keep the 3x crutch.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- the full composite tolerates a de-crutched actuator with no other adjustment. FAIL/INFORMATIVE-NEGATIVE if a fall appears or gait_valid collapses (<12/24) -- the 3x torque crutch is load-bearing for full-realism composite tolerance specifically (not just kick recovery), and the eventual composite ACQ recipe must keep it.

**verdict**: CANARY PASS (mechanism-health) -- the full ~30-axis realism composite (kick at its proven-safe half dose 0.15, torque crutch REMOVED, torque_scale 3.0->1.0) reaches 0 falls/24 across all 4 panels (walk/det 6/6, walk/sto 5/6, walk_startjitter/det 4/6, walk_startjitter/sto 6/6 = 21/24 aggregate gait_valid), no chronic single-leg sacrifice (3 flagged episodes hit 3 DIFFERENT legs/leg-pairs: [2], [0,2], [3] -- scattered, not repeating). Counterintuitive but decisive result vs the gate's own stated FAIL hypothesis ('the crutch is load-bearing for composite tolerance'): removing the crutch does NOT reproduce or worsen the crutch-ON kick-half-dose composite's 7/24-fall FAIL () -- it clears cleanly. The cost is real though: slip/m runs 7-17/m (vs 3-6/m for the crutch-ON composites), matching torquefade1x's own standalone finding that de-crutching raises slip without hurting validity. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_gate/report.json (21/24, 0 terms) vs allaxiskickhalf1x_c1_r2_gate/ (7 terms), W&B i5bvlxvc. Why: closes QUEUE AIM item (3)'s remaining half (composite-without-crutch, kick-safe dose) -- crutch removal does not destabilize the composite; if anything the two together look independent, not compounding. What's next: licenses a SECOND composite ACQ (40M) on this exact no-crutch+kick-safe recipe, alongside the already-funded allaxis-nokick-c1-acq1 (kick-fully-off, crutch-ON) -- these are two genuinely different recipes both clearing the composite canary bar, not a duplicate; both deserve their own ACQ read since they answer different downstream questions (does the campaign need the crutch at all vs does it need kick recovery at all).

