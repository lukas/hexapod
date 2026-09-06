# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gains1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SUPERSEDED

**created**: 2026-09-06T07:39:22+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gains1x-c1

**wandb_id**: fflp4yb9

**hypothesis**: Plain English: does the nominal per-servo PD-gain spread (+-20% kp/+-25% kv) stay a clean walk with a real 40M training budget, not just a 2M canary glance? gains1x-c1's own 2M canary was 23/24 (0 falls, one non-chronic leg-4 flag) -- this is its first ACQ-scale confirmation, joining the sibling encnoise1x/friction1x/mass1x/latency1x/push1x/torquefade2x/torquefade15x/zerobias1x/kick1x individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the gains-spread axis needs real training exposure before being called safe.

**verdict**: Mislabeled-budget duplicate, not a real ACQ read: same respec-steps-inheritance footgun -- landed at 2M not 40M. Same information as the already-PASSed gains1x-c1 2M canary (23/24 gait_valid, one non-chronic leg-4 flag, 0 falls) -- no new evidence. Why: closing the ledger cleanly. What's next: the correctly-budgeted 40M read is running as gains1x-c1-acq1-r2 (a concurrent cycle's own assignment this window) -- read and verdict that one, not this.

