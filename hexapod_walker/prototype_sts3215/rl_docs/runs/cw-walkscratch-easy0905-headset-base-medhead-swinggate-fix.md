# cw-walkscratch-easy0905-headset-base-medhead-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T21:41:42+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-acq1

**wandb_id**: 2j266hc8

**hypothesis**: Batch member 2/3 of the entrenched-checkpoint swing_gate retrofit question (sibling: swinggate-fix on s0c1_acq1): does reward.walk_swing_gate (bank-proved this cycle, 4/4 green) cure the base(1g)-family leg-1/4 favoritism on a DIFFERENT entrenched 40M champion (headset-base-medhead-acq1, ACQ FAIL, gait_valid only 10/24, leg 1/4 chronically sacrificed under the 5-way medium-heading set)? Broadens the entrenched-retrofit read beyond one checkpoint before concluding swing_gate does/doesn't repair already-entrenched exploiters on this family.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): repair-signal if the chronically-sacrificed leg's duty in walk/det and walk_startjitter/det majority-clears the harness's gait_valid duty>0.10 bar (matching this family's own accepted-PASS range) with 0 new falls. FAIL - MECHANISM if the same leg stays chronically parked in a majority of episodes regardless of whether walk_swing_gate_factor shows real decline. Read as part of the n=3 entrenched-checkpoint batch (s0c1, medhead, irr) before concluding swing_gate cures/doesn't-cure entrenched leg-favoritism on this family.

**verdict**: CANARY FAIL - MECHANISM (engaged, no repair; entrenched-checkpoint retrofit on medhead_acq1): the retrofit's per-mode gait_valid tally (walk/det 2/6, walk/sto 6/6, walk_startjitter/det 1/6, walk_startjitter/sto 2/6 = 11/24) is statistically indistinguishable from the undosed medhead_acq1 twin's own baseline (1/6, 6/6, 1/6, 2/6 = 10/24) -- both stay MAJORITY-PARKED on both det modes (the gate's own explicit FAIL bar), with the sacrificed leg still alternating between leg1 and leg4 episode-to-episode in both runs (twin sac pattern [[1],[],[4],[4],[1],[1]] on walk/det vs retrofit [[1],[],[4],[],[1],[1]] -- same two legs, same rough frequency). 2M of walk_swing_gate=1.0 produced no majority-clearing repair signal on either flagged leg. 0 new falls (terms 0 all modes, matching twin). env/walk_swing_gate_factor logged saturated at 1.0 at all 4 sparse sampled points (same weak-evidence caveat as the other two swing_gate arms this cycle -- likely an eval-instant snapshot not a trailing average). 3rd of 4 swing_gate arms to FAIL this cycle (2 INERT-clean on s0c1 lineage, this one marginal/noise-level on the medhead lineage) -- no arm in the batch shows a repair signal. Evidence: ops.sh report logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_medhead_swinggate_fix_gate/report.json vs logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_medhead_acq1_gate/report.json, W&B 2j266hc8.

