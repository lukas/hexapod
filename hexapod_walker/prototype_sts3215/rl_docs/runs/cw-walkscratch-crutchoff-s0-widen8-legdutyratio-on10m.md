# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-on10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T02:10:38+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: tojgpbb4

**hypothesis**: Second already-registered scratch lineage/RNG paired acquisition, motivated by charge-on s1 improving21->22/24 at10M with0falls while its matched off-control evaluates. Two bounded10M arms start from the exact same corrected s0fresh2M checkpoint MD5 2156daae67933cd1bc1a66accf422edb, existing RNG2 (no new seed). They differ only in additive leg-duty-ratio charge150 versus0. Healthy s0source is21/24,0falls with verified active charge. This pair tests continued-charge benefit versus withdrawal after shared2M exposure on a second existing initialization; source was already trained, not random or naive. It runs independently of s1 evaluation and provides a cross-lineage check against a one-episode threshold fluctuation. Preserve pure prior-free/noBC/no gait clock,8wayheadings, DR,motorlimits and schedule. No assumption of causal efficacy or class-wide recovery. This is the charge=150 arm.

**gate**: Paired +10M acquisition only; same24episode det/sto walk/startjitter panel, seed0. Each arm must retain>=21/24 gait_valid,0newfalls,noNEWchronic leg sacrifice relative to corrected2Msource. Compare on/off paired per-leg duty, gait, commandprogress andslip bygroup. Claim benefit only from better held-out leguse/gait without newfalls or command/slip regression; equal outcomes mean no demonstrated continued-charge advantage at thisduration. Do not compare rawreturns across differingrewardscales. Use existingpruner/normalintermediateevals; retaincheckpoints onfailure. No automatic furtherbudget, newseed or finalwalking/joystickqualification.

