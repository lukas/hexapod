# cw-walkscratch-easy0905-sde-s2-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:12:38+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: dn49lthl

**hypothesis**: Plain English: same as sde-s1-dg1 but the SECOND bare-sde LEGPARK-SKATE seed (sde-s2-c2) -- n=2 duty-gate canary confirmation on the bare-sde recipe before spending a 40M acquisition. Single lever (reward.walk_duty_gate=1.0), k_step_event/walk_gait_gate left at 0.

**gate**: MECHANISM-HEALTH CANARY: same as sde-s1-dg1 -- env/walk_duty_gate_factor should climb toward 1.0, not saturate; reward/speed not collapsing; 0 blowups. PASS funds 40M acquisition; FAIL closes the lever for bare-sde too.

