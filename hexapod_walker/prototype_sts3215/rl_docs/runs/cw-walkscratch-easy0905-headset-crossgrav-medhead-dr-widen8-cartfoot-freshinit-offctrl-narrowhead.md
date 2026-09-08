# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl-narrowhead

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T09:38:38+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: cihv6dse

**hypothesis**: Plain English: matched joint-space (OFF) control for the c1-narrowhead arm launched alongside it. Same isolation: does shrinking the heading set from widen8's 8-way back to the original medhead 5-way (dropping the 135/-135/180 backward directions), with everything else byte-identical to the seed40 offctrl fresh-init recipe (full crossgrav/medhead DR, torque_scale=1,1, joint-space action decode), let a fresh-init policy ignite where the 8-way version just failed twice (seed40+seed41) and torque-crutch restoration also failed?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the seed40/41/torqueretain arms: PASS if gait_valid majority + 0 falls + reward RISING (env/reward_walk trending up, env/v_along_cmd_m_s turning positive, env/walk_speed rising); chronic single-leg-sacrifice majority = FAIL regardless of reward. Read together with its matched c1-narrowhead sibling -- two arms agreeing is sufficient for a canary-level mechanism verdict.

**verdict**: CANARY FAIL - MECHANISM. Matches its c1-narrowhead sibling (verdicted together this cycle) almost exactly: env/reward_walk flat/noisy (0.162/0.201/0.183/0.182), env/v_along_cmd_m_s pinned near zero (-0.0019 to +0.0033), env/walk_speed DECLINES (0.092->0.082) -- the same flat/declining shape all 4 prior widen8-freshinit arms showed, not the rising signal this canary's gate required. Gate: gait_valid nominally majority (6/6,6/6,6/6,4/6) but fwd med is 0.02/0.07/0.02/0.12m over 20s (no net translation) while slip/m med is 74.3-213.9 -- legs cycling in place, not walking; 0 falls in all 24 episodes. This is the pre-registered narrowhead bisection's OFF arm, testing whether shrinking widen8's 8-way heading set back to the pre-widen8 5-way medhead set rescues fresh-init ignition of the full crossgrav+medhead-DR composite. It does not, on either action space (both this arm and c1-narrowhead fail identically). Two arms agreeing meets this pair's own mechanism-verdict bar. CONCLUSION (shared with c1-narrowhead): the widen8 backward-heading extension is NOT the fresh-init blocker; the full crossgrav+medhead DR breadth itself is too hard for this composite to bootstrap from a random-weight fresh init regardless of heading-set width. This closes the fresh-init bisection line for this DR-hardened composite family -- its only proven ignition path remains warm-start/curriculum (cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s{0,1,2} -> acq1). Do not relaunch this composite fresh-init at any heading-set width or torque setting without a genuinely new mechanism (e.g. a staged DR-breadth curriculum).

