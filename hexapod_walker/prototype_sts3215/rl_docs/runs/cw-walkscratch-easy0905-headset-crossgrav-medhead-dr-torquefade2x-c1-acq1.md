# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:46:05+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**wandb_id**: n838t060

**hypothesis**: Plain English: does removing HALF the torque/battery-assist crutch (3x->2x) stay a clean walk once trained for real, not just at a 2M canary glance? torquefade2x-c1's own 2M canary was a PERFECT 24/24 (0 falls, no sacrificed leg) on the campaign's cleanest champion -- this is its first ACQ-scale (40M) confirmation, the same durability question already asked of every irr/widen composition axis but never yet asked of a bare single-axis DR-realism restore.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 24/24 canary) across the full 4-panel harness at 40M, no NEW chronic single-leg sacrifice, 0 falls -- confirms simple single-axis DR canaries durability-check the same way composition axes do. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- shows even a currently-idealized torque-crutch axis needs real training exposure, not a bare canary read, before it can be called safe; would flag the whole single-axis-restore sweep's canary-only PASSes as provisional pending their own ACQ checks.

**verdict**: ACQ PASS/HOLDS -- the 2x torque-fade dose (dr.torque_scale=2,2, halfway off the idealized 3x crutch) holds cleanly at 40M on the medhead crossgrav champion. Evidence: harness gait_valid PERFECT 24/24 across all 4 panels (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), sac=[] every single episode, 0 terminations anywhere, slip/m 3.7-6.0 (in-band), forward progress 0.4-2.3m/20s every episode; det frame strip (walk_det_0.png) shows a clean six-leg cycling gait, no dragging/paddle-creep. Reward rose every quarter (874->1551->1637->1709). Why: this is the same recipe/champion family (medhead-abrupt-c1-acq1-cont40m parent) that has now passed every single-axis ACQ read tried (friction/mass/latency/etc) -- torque-crutch removal at the 2x dose composes cleanly too, same as the campaign's other clean single-axis confirmations. This entry was an orphan recovery: training finished (W&B state=finished, 40.37M steps) and the gate harness had already produced a complete report.json+videos, but the ledger was stuck at status=RUNNING with the pod since reassigned -- found and read directly per the campaign's own orphan-recovery pattern, not re-run. Next: the 15x (near torque-crutch-off) sibling ACQ read is the harder end of this dose ladder -- read it next (also found finished this cycle).

