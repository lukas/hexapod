# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:34:07+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1

**wandb_id**: n8j96qsz

**hypothesis**: Plain English: does the halfway torque-assist dose (dr.torque_scale 3x->1.5x, midway between the already-ACQ-confirmed-in-progress 1x/2x points) stay a clean walk with real training budget, not just a 2M canary glance? torquefade15x-c1's own 2M canary was a PERFECT 24/24 (0 falls, sac=[] every episode) -- this is its first ACQ-scale (40M) confirmation, joining the sibling torquefade2x-c1-acq1/friction1x-c1-acq1/mass1x-c1-acq1/encnoise1x-c1-acq1 individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 24/24 canary) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show even the mid-point torque-fade dose needs real training exposure before being called safe.

**verdict**: ACQ PASS/HOLDS -- the 1.5x torque-fade dose (dr.torque_scale=1.5,1.5, most of the way off the idealized 3x crutch) holds cleanly at 40M on the medhead crossgrav champion. Evidence: harness gait_valid PERFECT 24/24 across all 4 panels, sac=[] every episode, 0 terminations anywhere, slip/m 4.1-6.5 (mildly higher than the 2x dose's 3.7-6.0 but still in-band), forward progress 0.6-2.2m/20s every episode; det frame strip (walk_det_0.png) shows a clean six-leg cycling gait, no dragging/flag-leg. Reward rose every quarter (937->1675->1790->1912). Why: this is the harder end of the torque-crutch-removal dose ladder (1x/2x/15x all now ACQ-read) -- even at 1.5x actuator torque (half the idealized 3x margin), the champion tolerates full 40M exposure with zero degradation vs its own 2M canary. Together with torquefade2x-c1-acq1 (also PASS, verdicted this same cycle) this closes 2/3 of the torque-crutch dose ladder at ACQ scale; the campaign's own torquefade1x-c1-acq1 (the least-faded/closest-to-crutch dose) is still mid-gate-eval as of this cycle -- read it before declaring the full ladder closed. This entry was an orphan recovery: training finished (W&B state=finished) and the gate harness had already produced a complete report.json+videos, but the ledger was stuck at status=RUNNING with the pod since reassigned -- found and read directly, not re-run.

