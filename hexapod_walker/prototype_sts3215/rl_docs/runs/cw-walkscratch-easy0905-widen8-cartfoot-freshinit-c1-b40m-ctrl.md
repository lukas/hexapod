# cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-b40m-ctrl

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:45:36+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: ncyj9w33

**hypothesis**: Plain English: the necessary matched control for the staged-DR fresh-acquisition test — does the exact failed fresh-init recipe (seed40 widen8 cart_foot crutch-off: fresh random init, no BC/teacher/gait clock, full gravity, 1x torque, source motor limits, full explicit DR matrix from step 0) ignite forward progress when given the full honest 40M budget instead of the 2M it failed at? Its 2M canary (this run's source, freshinit-c1) was machinery-healthy but reward_walk-flat with near-zero v_along — a genuine 2M FAIL shape, but 2M is 5% of the standard acquisition budget, so 'just needs budget' is the strongest alternative to the staged-DR hypothesis and must be controlled. Read TOGETHER at equal 40M optimizer budget, same seed 40, same recipe, UNCHANGED full-DR held-out evaluation, with the staged arm cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-stagedr20m-b40m (env.dr_stage_ramp_steps=20000000; launches after its own 2M mechanism canary stagedr2m passes). Pre-registered joint reading: staged-ignites+control-flat => gradual DR exposure enables fresh acquisition (one seed, this recipe, no generalization claim); both-flat => this linear-20M staging schedule does not rescue ignition and DR-breadth-at-start is not confirmed as the blocker at 40M; both-ignite => budget, not DR schedule, was the blocker and staging is unnecessary; control-ignites+staged-flat => staging harmful. Honest-exposure note: the staged arm trains its first 20M under milder-than-full DR by design — the differing exposure IS the intervention; both arms get identical full-DR gates. No unplanned seeds/grid, no automatic extension: continuation only by an explicit future-cycle 08-21 decision reading the final full-DR gate and reward slope.

**gate**: ACQ movement gate on the UNCHANGED full-DR held-out panel (identical to the halfgrav/1g cohort practice): PASS if >=0.03 m/s median net forward in >=1 of walk/{det,sto} with 0 falls in det and gait_valid majority (>=4/6) in the passing mode; chronic single-leg/front-pair sacrifice majority in det = FAIL regardless of speed. Ignition telemetry read alongside: env/reward_walk rising across quarters and env/v_along_cmd_m_s sustained >=+0.01, vs the flat/declining 2M-canary fingerprint. One half of the pre-registered 2-arm staged-DR comparison — verdict must be written jointly with stagedr20m-b40m at equal budget; no continuation or extension without an explicit future-cycle decision.

