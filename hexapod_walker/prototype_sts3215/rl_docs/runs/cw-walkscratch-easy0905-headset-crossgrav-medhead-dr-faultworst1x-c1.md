# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-faultworst1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T06:33:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: arb3yxjo

**hypothesis**: Worst-case dose of the fault axis: the in-flight fault1x-c1 canary uses the DEFAULT fault_mix (45% weak-joint / 25% frozen-joint / 30% whole-leg-disabled) at fault_prob=0.3, so most episodes never see the hardest sub-case. This arm forces fault_prob=1.0 with fault_mix=(0,0,1) so EVERY episode gets a full leg (all 3 joints) permanently disabled (scale=0.0) from a random point onward -- the single hardest real-hardware failure mode (a dead leg), tested in isolation and at guaranteed (not probabilistic) exposure so the read is not diluted by lucky no-fault episodes.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) EXCLUDING the disabled leg itself from the sacrifice count (a disabled leg is an expected/forced sacrifice, not a policy pathology) and 0 falls -- shows the champion can still walk on 5 legs when one is truly dead. FAIL/INFORMATIVE-NEGATIVE if it falls or the other 5 legs also degrade (a 2nd chronic sacrificed leg beyond the forced-dead one, or falls) -- shows the champion cannot gracefully degrade to single-leg-loss and fault-tolerance needs a real hardening-rung training budget, not just isolated single-episode fault exposure.

