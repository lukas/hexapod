# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-offctrl10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - matched control, no efficacy (2nd independent replication, s0/RNG2)

**created**: 2026-09-08T02:11:53+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: pyrugqjw

**hypothesis**: Second already-registered scratch lineage/RNG paired acquisition, motivated by charge-on s1 improving21->22/24 at10M with0falls while its matched off-control evaluates. Two bounded10M arms start from the exact same corrected s0fresh2M checkpoint MD5 2156daae67933cd1bc1a66accf422edb, existing RNG2 (no new seed). They differ only in additive leg-duty-ratio charge150 versus0. Healthy s0source is21/24,0falls with verified active charge. This pair tests continued-charge benefit versus withdrawal after shared2M exposure on a second existing initialization; source was already trained, not random or naive. It runs independently of s1 evaluation and provides a cross-lineage check against a one-episode threshold fluctuation. Preserve pure prior-free/noBC/no gait clock,8wayheadings, DR,motorlimits and schedule. No assumption of causal efficacy or class-wide recovery. This is the charge=0 arm.

**gate**: Paired +10M acquisition only; same24episode det/sto walk/startjitter panel, seed0. Each arm must retain>=21/24 gait_valid,0newfalls,noNEWchronic leg sacrifice relative to corrected2Msource. Compare on/off paired per-leg duty, gait, commandprogress andslip bygroup. Claim benefit only from better held-out leguse/gait without newfalls or command/slip regression; equal outcomes mean no demonstrated continued-charge advantage at thisduration. Do not compare rawreturns across differingrewardscales. Use existingpruner/normalintermediateevals; retaincheckpoints onfailure. No automatic furtherbudget, newseed or finalwalking/joystickqualification.

**verdict**: Matched +10M charge=0 continuation from the same corrected 2M s0/RNG2 legdutyratiofresh-guardfix1 source, only walk_leg_duty_ratio_charge 150->0. 24-ep det+sto walk/startjitter gate: gait_valid 21/24 (det 5/6, sto 6/6, sj/det 6/6, sj/sto 4/6), 0 falls -- the EXACT SAME 3 failing episodes/chronic legs as the pre-continuation 2M source (det/0 leg5, sj/sto ep2 leg5, sj/sto ep3 leg0): flat retention, no new chronic sacrifice, no regression from withdrawing the charge. Paired vs the matched charge-on sibling on10m (same source/RNG2/panel): ON is gait_valid 22/24 (+1, exactly the det/0 episode) but mean slip_per_m is HIGHER for ON in ALL 4 groups (det 11.26 vs 10.07, sto 8.00 vs 7.67, sj/det 9.87 vs 9.49, sj/sto 12.84 vs 12.78) and mean progress_ratio is LOWER for ON in 3/4 groups (det 0.817 vs 0.863, sto 1.107 vs 1.118, sj/det 0.995 vs 1.013; only sj/sto ticks up 0.707 vs 0.668). This is the IDENTICAL shape already found on the s1/RNG3 twin (offctrl10m PASS, 02:35) -- the +1 gait_valid flip is noise, not causal repair, replicated across two independent RNG lineages. CLOSES the s0/RNG2 continued-charge study: NO demonstrated efficacy for walk_leg_duty_ratio_charge past the shared 2M exposure at 10M depth, on EITHER of the two lineages tested. No further budget from this arm (per its own gate).

