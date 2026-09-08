# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-on10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T02:10:38+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: tojgpbb4

**hypothesis**: Second already-registered scratch lineage/RNG paired acquisition, motivated by charge-on s1 improving21->22/24 at10M with0falls while its matched off-control evaluates. Two bounded10M arms start from the exact same corrected s0fresh2M checkpoint MD5 2156daae67933cd1bc1a66accf422edb, existing RNG2 (no new seed). They differ only in additive leg-duty-ratio charge150 versus0. Healthy s0source is21/24,0falls with verified active charge. This pair tests continued-charge benefit versus withdrawal after shared2M exposure on a second existing initialization; source was already trained, not random or naive. It runs independently of s1 evaluation and provides a cross-lineage check against a one-episode threshold fluctuation. Preserve pure prior-free/noBC/no gait clock,8wayheadings, DR,motorlimits and schedule. No assumption of causal efficacy or class-wide recovery. This is the charge=150 arm.

**gate**: Paired +10M acquisition only; same24episode det/sto walk/startjitter panel, seed0. Each arm must retain>=21/24 gait_valid,0newfalls,noNEWchronic leg sacrifice relative to corrected2Msource. Compare on/off paired per-leg duty, gait, commandprogress andslip bygroup. Claim benefit only from better held-out leguse/gait without newfalls or command/slip regression; equal outcomes mean no demonstrated continued-charge advantage at thisduration. Do not compare rawreturns across differingrewardscales. Use existingpruner/normalintermediateevals; retaincheckpoints onfailure. No automatic furtherbudget, newseed or finalwalking/joystickqualification.

**verdict**: CANARY PASS (acquisition-duration/retention scope, per its own pre-registered gate): +10M continuation of the charge-on (150) leg-duty-ratio-charge recipe from the corrected 2M s0/RNG2 guardfix1 source (fwd 2156daae...). Held-out 24-ep det+sto walk/startjitter panel: gait_valid 22/24 (walk/det 6/6, walk/sto 6/6, sj/det 6/6, sj/sto 4/6), 0 falls/terminations in every mode -- flat-or-BETTER than the source's own 21/24 (source's sole det/0 sacrifice [leg5] flips to gv=True here; the same 2 startjitter/sto episodes [leg5 ep2, leg0 ep3] remain the only fails -- no NEW chronic leg). Peer-excluded duty ratio for the formerly-weak legs (0,5) clears >=0.22 in 23/24 episodes each, same magnitude as source, no regression. ep_rew_mean falling to -32008 (quarters monotonically more negative) is explained by rollout/ep_len_mean rising 108->1235->1999->2000/2048 (episodes surviving to full length under a persistent ~0.10-0.15 per-tick charge shortfall that never fully zeroes, unlike the s0 rung3-assistfade sibling) -- not behavioral collapse. This is the exact same retention pattern already read on the s1 twin (guardfix-acq10m, PASS): the charge-on recipe survives a 5x-longer acquisition without new falls or new chronic sacrifice. It does NOT by itself prove charge is the active ingredient of the 21->22/24 delta (could be duration alone) -- that requires the matched offctrl10m control, which is still mid-gate-eval on train-1 (root-owned by another cycle, untouched here). Next: read offctrl10m against this same panel before claiming s0-specific charge efficacy; s1's own on/off pair already read 'no demonstrated advantage' at this duration, so the prior is that s0 will match unless proven otherwise.

