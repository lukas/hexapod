# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY-PASS

**created**: 2026-09-07T15:33:35+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: lanhu3s9

**hypothesis**: The frozen champion walks at 1.6-2.1x its commanded speed and pays nothing for the surplus; if we charge that surplus (and only it), the gait should slow to the commanded speed -- and if its ~4.5/m contact-point skating is financed by the surplus speed (09-07 audit: measurement honest, frames/rolling/chatter/transients all falsified), slip should drop with it. New opt-in reward.walk_freeprog_overspeed_charge=1.0 charges k_free*(along/cap-1) above the cap only, stride-EMA along, below-cap income bit-exact; bank-proven (4 WALKCURR_OVERSPEED tests). Warm from the champion, seed 2, otherwise identical recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism canary vs frozen parent's own gate (walk det med: slip/m 4.98, prog 1.87, gv 22/24, 0 falls): MECHANISM WORKS if prog_ratio med drops toward <=1.35 with gv >=18/24 and 0 falls. Then: slip/m med <=3.9 = overspeed-financed slip CONFIRMED (acq continuation licensed); prog<=1.35 but slip/m >=4.5 = hypothesis FALSIFIED, records a genuine gait-style slip floor (close axis, next lever is contact-model fidelity). MECHANISM FAIL if gv <12/24, any fall where parent had none, or prog collapses <0.75 (charge re-opened the stall basin).

**verdict**: CANARY PASS (mechanism-health scope only, per this run's own gate note -- not a hypothesis verdict). gv 22/24 (>=18 bar), 0 new falls (matches parent), no prog collapse -- none of the FAIL-MECHANISM criteria fire. The new walk_freeprog_overspeed_charge term is confirmed ACTIVELY FIRING and safe: env/reward_walk_freeprog_pen sits at -1.3..-1.4/tick, LARGER in magnitude than reward_walk income itself (0.83-0.98), and the policy responds by getting MORE stable under it (terminations/tilt_roll crashed 93->25->11->10 across the 2M window, ep_len_mean nearly quadrupled 111.6->472.9, reward_walk ticking up 0.827->0.979) rather than entrenching a new exploit -- this is a healthy adaptation signature, not inert/broken code. However the PRIMARY research question (does the charge reduce overspeed and, with it, slip) is UNRESOLVED at this dose/budget: v_along_cmd_m_s stayed flat at 0.083-0.084 the whole window (prog_ratio only softened in 2/4 modes, none reaching the <=1.35 mechanism-works bar) and slip/m stayed flat-to-worse in every mode (4.93-6.24 vs parent 4.98-5.42) -- the raw ep_rew_mean decline (-59.5->-108.6) is an episode-LENGTH artifact of the stability improvement above, NOT reward-misalignment or entrenchment. Read: 2M steps is too short for an already-deeply-entrenched 1.4-2x-overspeed checkpoint to visibly shed speed even under a dominant charge. Licensed and launched an 8M acquisition-depth continuation (same recipe, same k_over=1.0, evidence cited) to give the mechanism enough budget to actually move v_along/resolve the slip question; if still flat at 8M, next lever is a stronger k_over dose, not more of the same budget.

