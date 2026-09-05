# cw-walkscratch-easy0905-sde-idleterm-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:34:44+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: wb5pll75

**hypothesis**: The sde family's bare easy0905 recipe converges to a STATIC-FROZEN absorbing pose (>=3 seeds confirmed this cycle+prior: sde-s0-c4/s1-c2/s2-c2 all reach near-full ep_len survival with walk_speed/v_along_cmd DECLINING and slip RISING over 40M, video shows an unchanging tilted pose 11s apart) -- the exact 'static-quiver' class the walkcurr track's own WALKCURR_PF_IDLE_TERM bank (test_task_semantics.py, 2026-08-24) already diagnosed and fixed on the older pf_fwd lineage: soft anti-park PRICES alone (k_park_duty, k_walk_idle_charge) leave the frozen stand as PPO's cheapest optimum (an absorbing state prices alone cannot evict), so the validated fix pairs those prices WITH a qvel-based safety.walk_idle_terminate_s TERMINATION (ends the episode + a small dedicated penalty once mean |joint velocity| across all 18 actuated joints sits under 2 deg/s for 3s past a 3s grace -- bank-proven surgical: only cuts the truly-frozen twin, leaves gait/stall/skate/topple untouched, test_walkcurr_idle_term_only_cuts_the_frozen_twin/test_walkcurr_idle_term_matches_unarmed_bank_off_the_frozen_twin both green just re-ran). This arm ports that EXACT already-bank-proven mechanism+dose (k_park_duty=4.0, k_walk_idle_charge=2.0 idle_speed=0.025/tau=1.0, k_loadslip_excess=4.5 with its gate/ok/max/floor, safety.walk_idle_terminate_s=3.0/grace=3.0/qvel=2deg_s, walk_idle_terminate_penalty=150) onto the EASY_BASE sde recipe (freeprog income mechanism unchanged) fresh from scratch (continuing off the converged frozen checkpoint was shown ineffective for the analogous gaitgate-cont1 case, 08-25 RL_LOG -- from-scratch is the decisive test). NOT using reward.walk_gait_gate/k_walk_move_current: those target a DIFFERENT exploit (rare-token-swing rigid-tripod-lock under DR) already CLOSED-unfixable at every dose on the joystick track's harder full-DR curriculum (RL_LOG 08-25); this video shows a near-fully-static pose (unchanged 11s apart), matching the static-quiver class idle-terminate targets, not the token-swing class. Seed 0 of 2.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY mechanism-health scope (2M budget, matches sde-s0's own scale): finite losses, optimizer actually stepping, some learnable signal. Read alongside seed 1: does rollout/ep_len_mean show the walk_idle_terminate reason firing early-episode (policy initially frozen, as expected) with reward/ep_len RECOVERING over the 2M budget (the escape signature) rather than plateauing at the terminate-boundary tick count? Video: any six-leg motion attempt visible vs sde-s0-c4's unchanging pose. Not a full ACQ verdict at 2M -- decides whether to fund a 40M continuation of this recipe or close the sde family per the base-family comparison.

