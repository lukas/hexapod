# cw-walkscratch-easy0905-sde-s2-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-05T15:12:38+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: dn49lthl

**hypothesis**: Plain English: same as sde-s1-dg1 but the SECOND bare-sde LEGPARK-SKATE seed (sde-s2-c2) -- n=2 duty-gate canary confirmation on the bare-sde recipe before spending a 40M acquisition. Single lever (reward.walk_duty_gate=1.0), k_step_event/walk_gait_gate left at 0.

**gate**: MECHANISM-HEALTH CANARY: same as sde-s1-dg1 -- env/walk_duty_gate_factor should climb toward 1.0, not saturate; reward/speed not collapsing; 0 blowups. PASS funds 40M acquisition; FAIL closes the lever for bare-sde too.

**verdict**: MECHANISM-HEALTH CANARY FAIL. env/walk_duty_gate_factor did NOT saturate (dropped 1.0->0.69 over the 2M steps, i.e. correctly penalizing, not gamed) and det-mode gait_valid read True/sac=[] in all 6 episodes (no chronically-parked leg -- the specific LEGPARK-SKATE exploit this warm start (from the 40M sde-s2-c2 exploiter) was showing IS broken). But video/HUD readout shows the policy substituted a DIFFERENT non-walking failure within the 2M retrain budget rather than real six-leg locomotion: walk_det frame strip shows the robot ending the 20s episode having yawed ~174 deg from its start heading (R=+0.0 -> R=+174.5) with mean current spiking 0.30A->1.40A and h_err -13mm (sunk/tipped), not directed forward progress -- a spin/destabilize pattern, not walking. walk/sto is worse: gait_valid 1/6, 5/6 episodes end in TERM tilt_pitch (falls). slip_per_m med 4.13 (det), 9.4-100 (sto) vs the ~2.9 teacher band. Training reward flatlined ~17-27 for the whole 2M vs the SAME un-gated checkpoint's own early-training trajectory (9->31->43->55 at the same absolute step count) and vs its full 40M climb to 2003 -- expected since the gate deliberately collapses the previously-exploited income, but nothing replaced it with real progress inside this budget. Root cause read (walk_task.py ~3945-3980): duty_gate multiplies transport/progress income by a MIN-over-legs floor factor but has no penalty for a leg's duty being TOO HIGH (never swinging) — a warm-started policy under an abrupt full-strength (dose 1.0) income shock can retreat toward instability/low-effort responses rather than relearn a gait in 2M steps; this does not yet prove the mechanism itself is unsound (see the from-scratch isolation twin launched this cycle). CLOSES this specific 'instant full-dose walk_duty_gate warm-start off a mature 40M sde LEGPARK exploiter' repair recipe -- does NOT fund a 40M acquisition off this checkpoint. Next: cw-walkscratch-easy0905-sde-dgfresh-s0 (from-scratch, duty_gate=1.0 from step 0, launched this cycle) isolates whether the mechanism itself is sound without the warm-start confound.

