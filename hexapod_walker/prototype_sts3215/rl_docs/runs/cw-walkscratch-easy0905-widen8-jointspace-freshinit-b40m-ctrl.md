# cw-walkscratch-easy0905-widen8-jointspace-freshinit-b40m-ctrl

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:20:50+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: xr8rlhfh

**hypothesis**: Plain English: the joint-space half of the action-space x DR-schedule comparison — does the exact failed JOINT-SPACE fresh-init recipe (seed40 widen8 crutch-off offctrl: fresh random init, no BC/teacher/gait clock, full gravity, 1x torque, source motor limits, full explicit DR matrix from step 0) ignite forward progress at the full honest 40M budget instead of the 2M it failed at? Exact clone of the offctrl joint-space control at 40M, nothing else changed. Read TOGETHER with the staged sibling cw-walkscratch-easy0905-widen8-jointspace-freshinit-stagedr20m-b40m (env.dr_stage_ramp_steps=20000000, launched same cycle) and alongside the already-running cart-foot pair (b40m-ctrl / stagedr20m-b40m, same seed 40, equal 40M each) as a one-seed 2x2 factorial: does any staged-DR benefit depend on the action representation (cart_foot vs joint-space)? Preconditions met this cycle: staged-DR machinery canary PASS (stagedr2m) AND the bounded on-device Warp endpoint/reset-pool diagnostic PASS (artifacts/diag/diag_dr_stage_device_20260908T11Z.json + rl_move/sim/diag_dr_stage_device.py: per-world ModelDR/TickParams device rows bit-exact vs mint-time draws on startup AND pooled-injection paths, broadcast is reset-only for live worlds, pool flush verified, realized reset draws exactly nominal at frac 0, within scaled ranges at 0.5, spanning the full matrix at 1.0 with exact full-ranges object restore). Exposure honesty (fb_20260908T104404_58b3a5): dr_stage_ramp/frac is a REQUESTED fraction; realized per-world DR exposure lags it under reset-only semantics — never infer realized full-DR training time from target logs. Pre-registered joint reading for this pair: staged-ignites+control-flat => gradual DR exposure enables joint-space fresh acquisition (one seed, this recipe, no generalization claim); both-flat => staging does not rescue joint-space ignition at 40M; both-ignite => budget, not schedule, was the blocker; control-ignites+staged-flat => staging harmful. Cross-pair factorial read is DESCRIPTIVE only (one seed per cell): report which of the four cells ignite; no interaction claim without replication. Prediction-if-true(budget-suffices): env/reward_walk rising across quarters and env/v_along_cmd_m_s sustained >=+0.01. Prediction-if-false: flat as at 2M. Strongest alternative: ignition requires the cart_foot inductive bias — visible as cart-foot cells igniting while both joint-space cells stay flat. One-seed factorial comparison, NOT a robustness proof. No unplanned seeds/grid/extensions; continuation only by an explicit future-cycle 08-21 decision.

**gate**: ACQ movement gate on the UNCHANGED full-DR held-out panel (identical to the running cart-foot pair): PASS if >=0.03 m/s median net forward in >=1 of walk/{det,sto} with 0 falls in det and gait_valid majority (>=4/6) in the passing mode; chronic single-leg/front-pair sacrifice majority in det = FAIL regardless of speed. FIXED 40M acquisition budget — no early 2M skill closure. MUST be verdicted jointly with cw-walkscratch-easy0905-widen8-jointspace-freshinit-stagedr20m-b40m per the pre-registered 4-outcome reading, and reported alongside the cart-foot pair as the one-seed 2x2 action-space x DR-schedule table (descriptive, no robustness claim). No continuation or extension without an explicit future-cycle decision.

