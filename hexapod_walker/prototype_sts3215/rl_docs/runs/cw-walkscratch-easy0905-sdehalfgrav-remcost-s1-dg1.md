# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-05T15:09:06+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**wandb_id**: l0ttyyw1

**hypothesis**: Plain English: same as sdehalfgrav-remcost-s0-dg1 but the SECOND remcost LEGPARK-SKATE seed -- n=2 duty-gate canary confirmation on the remcost recipe before spending a 40M acquisition. Single lever (reward.walk_duty_gate=1.0), k_step_event/walk_gait_gate left at 0.

**gate**: MECHANISM-HEALTH CANARY: same as sdehalfgrav-remcost-s0-dg1 -- factor should climb not saturate, reward/speed not collapsing, 0 blowups. PASS funds 40M acquisition; FAIL closes the lever for remcost too (6/6 closure counting the bare-sde pair).

**verdict**: CORRECTED (provenance): same gotcha as the s0-dg1 sibling -- this run also carried NO --init-from, fully FROM SCRATCH with reward.walk_duty_gate=1.0 from step 0 on the sdehalfgrav-remcost recipe, not a warm-start. Read together with s0-dg1 (2/2 same fingerprint): env/walk_duty_gate_factor declined 1.0->0.91 (penalizing, not gamed). Det-mode gait_valid True/sac=[] but progress essentially zero (prog -0.00, fwd 0.00m every det episode) with enormous slip (0.90-72.3, up to 25x band on walk_startjitter/det) -- frozen/near-static, not walking. walk/sto: gait_valid 0/6, all 6 TERM tilt_roll/pitch (falls). Reward (-672/-776/-846/-900 at matched steps) matches the UN-gated parent's own from-scratch trajectory (-656/-809/-857/-888) almost exactly -- not a new collapse. Confirms, from scratch (no warm-start confound), that duty_gate+remcost's term_cost pricing together collapse to the ~0-income park basin remcost's own hypothesis predicted as its failure mode. CLOSES 'walk_duty_gate=1.0 + remcost term_cost, from scratch' at 2/2 seeds -- does not fund a 40M acquisition off either checkpoint. Isolation follow-up (cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0, no remcost pricing) launched this cycle.

