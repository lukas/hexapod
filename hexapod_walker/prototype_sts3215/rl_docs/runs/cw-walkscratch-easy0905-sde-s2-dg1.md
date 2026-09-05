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

**verdict**: CORRECTED (provenance): a respec-clone gotcha (banked in CURRENT_TRUTHS by a concurrent cycle after my first pass) means this run actually warm-started from `sde_s2.zip` -- the ORIGINAL 2M canary checkpoint that TERMINATES tilt_pitch (falls) in EVERY SINGLE eval episode, det AND sto -- not from the 40M `sde_s2_c2.zip` mature LEGPARK exploiter its own hypothesis/parent field claimed. Re-reading with the correct ancestor: MECHANISM-HEALTH CANARY FAIL, but the story is 'made real progress from an early falling checkpoint, did not yet reach real walking' rather than 'a converged exploiter destabilized'. env/walk_duty_gate_factor declined 1.0->0.69 (penalizing, not saturated/gamed). Det-mode gait_valid True/sac=[] all 6 episodes AND no TERM (stopped falling in det, an improvement over the falls-every-episode ancestor) -- genuine progress. But video/HUD shows the policy still hasn't reached directed six-leg walking: the det episode ends having yawed ~174deg from start heading, current 0.30A->1.40A, h_err -13mm (spin/destabilize, not forward travel). walk/sto: gait_valid 1/6, 5/6 TERM tilt_pitch. slip_per_m med 4.13 (det) up to 9.4-100 (sto) vs ~2.9 teacher band. Reward flat ~17-27 the whole 2M. Verdict unchanged (still not a walking gate PASS) but do NOT cite this as evidence about warm-starting off a converged exploiter -- it wasn't one. CLOSES the tested '\''walk_duty_gate=1.0 on the early sde_s2 2M checkpoint'\'' arm; does not fund a 40M acquisition off this checkpoint. From-scratch isolation twin (cw-walkscratch-easy0905-sde-dgfresh-s0, duty_gate=1.0 from step 0, no init-from at all) launched this cycle to read the mechanism without ANY inherited checkpoint quirks.

