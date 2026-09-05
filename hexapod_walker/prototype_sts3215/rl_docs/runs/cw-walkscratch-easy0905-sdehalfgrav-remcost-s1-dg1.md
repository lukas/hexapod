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

**verdict**: MECHANISM-HEALTH CANARY FAIL, same fingerprint as the s0-dg1 sibling verdicted this cycle (read together). env/walk_duty_gate_factor declined 1.0->0.91 (not saturated/gamed). Det-mode gait_valid True/sac=[] in all 6 episodes (no parked leg -- the sacrifice exploit is broken) but progress essentially zero (prog -0.00, fwd 0.00m every det episode) with enormous slip (0.90-72.3, up to 25x the ~2.9 teacher band on walk_startjitter/det) -- a frozen/near-static stance, not a walk. walk/sto: gait_valid 0/6, all 6 TERM tilt_roll/tilt_pitch (falls), sac sets of 2-4 legs. Reward trajectory (-672/-776/-846/-900 at matched absolute env steps) tracks the UN-gated parent's own trajectory over the identical range (-656/-809/-857/-888) -- not a NEW collapse, this recipe's reward is already this negative from term_cost pricing. Same root cause as s0-dg1: the remcost recipe's own launch hypothesis named 'retreat to the ~0-income park basin' as its predicted failure mode if term_cost over-corrects toward fall-aversion; once duty_gate closes the shuffle income route, that is exactly what both seeds do. CLOSES the instant-full-dose walk_duty_gate warm-start repair on remcost at 2/2 seeds -- does NOT fund a 40M acquisition off either checkpoint. Next: cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0 (from-scratch, duty_gate=1.0 from step 0, no remcost pricing, launched this cycle) isolates the mechanism from remcost's fall-aversion and the warm-start shock.

