# cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-stagedr20m-b40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:50:26+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: toz7pjgv

**hypothesis**: Plain English: the ONE changed curriculum recipe of the pre-registered staged-DR fresh-acquisition test — does ramping DR exposure from the nominal sim to the full explicit dr.* override matrix over the first 20M steps (env.dr_stage_ramp_steps=20000000, mechanism canary-PASSed as stagedr2m) let the exact seed40 widen8 cart_foot crutch-off fresh-init recipe (fresh random init, no BC/teacher/gait clock, full gravity, 1x torque, source motor limits) ignite forward progress where full-DR-from-step-0 failed at 2M twice (seed40+seed41) and torque restoration did not rescue it? Motivation is a wiring fact, not just the finite FAILs: the recipe's dr.* overrides are ABSOLUTE (applied after --dr-scale), so every prior arm trained at the full DR matrix from step 0 with no possible ramp — gradual exposure is the genuinely-new design the narrowhead/torqueretain closures called for. Read TOGETHER with the equal-budget matched control cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-b40m-ctrl (full DR from step 0, 40M, same seed 40, launched same cycle) on the UNCHANGED full-DR held-out evaluation. Pre-registered joint reading: staged-ignites+control-flat => gradual DR exposure enables fresh acquisition (one seed, this recipe, no generalization claim); both-flat => this linear-20M schedule does not rescue ignition and DR-breadth-at-start is not confirmed as the blocker at 40M; both-ignite => budget, not DR schedule, was the blocker; control-ignites+staged-flat => staging harmful. Honest-exposure note: this arm trains its first 20M under milder-than-full DR by design — the differing exposure IS the intervention; both arms get identical full-DR gates. Prediction-if-true: env/reward_walk rising and env/v_along_cmd_m_s sustained >=+0.01 emerging during the low-DR phase and SURVIVING the ramp to full DR + the 20M full-DR tail. Prediction-if-false: progress appears early then collapses as the ramp passes ~0.5, or never appears. Strongest alternative: any ignition is explained by budget alone — controlled by b40m-ctrl. No unplanned seeds/grid, no automatic extension: continuation only by an explicit future-cycle 08-21 decision reading the final full-DR gate and reward slope.

**gate**: ACQ movement gate on the UNCHANGED full-DR held-out panel (identical to the halfgrav/1g cohort practice; the armed-but-unbroadcast eval env sits at the FULL override ranges by construction, unit-tested): PASS if >=0.03 m/s median net forward in >=1 of walk/{det,sto} with 0 falls in det and gait_valid majority (>=4/6) in the passing mode; chronic single-leg/front-pair sacrifice majority in det = FAIL regardless of speed. MUST be verdicted jointly with the matched equal-budget control b40m-ctrl per the pre-registered 4-outcome reading in the hypothesis; a staged-arm PASS with a control PASS is credited to budget, not staging. dr_stage_ramp/frac telemetry must show the 0->1 ramp over the first 20M (machinery regression check only). No continuation or extension without an explicit future-cycle decision.

