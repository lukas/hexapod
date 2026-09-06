# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-faultworst1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:33:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: arb3yxjo

**hypothesis**: Worst-case dose of the fault axis: the in-flight fault1x-c1 canary uses the DEFAULT fault_mix (45% weak-joint / 25% frozen-joint / 30% whole-leg-disabled) at fault_prob=0.3, so most episodes never see the hardest sub-case. This arm forces fault_prob=1.0 with fault_mix=(0,0,1) so EVERY episode gets a full leg (all 3 joints) permanently disabled (scale=0.0) from a random point onward -- the single hardest real-hardware failure mode (a dead leg), tested in isolation and at guaranteed (not probabilistic) exposure so the read is not diluted by lucky no-fault episodes.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) EXCLUDING the disabled leg itself from the sacrifice count (a disabled leg is an expected/forced sacrifice, not a policy pathology) and 0 falls -- shows the champion can still walk on 5 legs when one is truly dead. FAIL/INFORMATIVE-NEGATIVE if it falls or the other 5 legs also degrade (a 2nd chronic sacrificed leg beyond the forced-dead one, or falls) -- shows the champion cannot gracefully degrade to single-leg-loss and fault-tolerance needs a real hardening-rung training budget, not just isolated single-episode fault exposure.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE (worst-case fault dose, orphan recovery -- finished training+eval, no verdict recorded): fault_prob=1.0 + fault_mix=(0,0,1) guarantees a WHOLE-LEG DISABLE every single episode (vs fault1x-c1's probabilistic/mixed default dose). Harness gait_valid reads 0/24, but this is a harness-vs-injected-fault alignment artifact, not a policy pathology: in ALL 24/24 episodes the ONE flagged sacrificed leg exactly matches the injected fault's disabled leg (e.g. fault 'leg:j[3,4,5]@0.0' -> sac=[1], 'leg:j[15,16,17]@0.0' -> sac=[5], verified leg-by-leg across every episode/mode). 0 falls/terms in all 24 episodes, progress_ratio med 1.2-1.8, forward_dist 0.8-2.4m -- the champion walks cleanly on the remaining 5 legs with a guaranteed dead leg every episode. This is the strongest fault-tolerance result in the DR sweep (worse than fault1x-c1's own probabilistic dose) and closes the fault-axis dose ladder at its ceiling.

