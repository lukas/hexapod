# cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-stagedr2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:42:16+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

**wandb_id**: yyywkp49

**hypothesis**: Plain English: machinery check for the brand-new staged-DR mechanism — does env.dr_stage_ramp_steps (built this cycle, commit bc8643f2: the trainer ramps the episode-reset DR distribution per rollout from the nominal sim up to this recipe's full explicit dr.* override matrix, flushing pooled resets on each stage change) run healthily end-to-end on the GPU/warp stack? Built because the failed fresh-init recipes carry their whole DR matrix as ABSOLUTE --cfg-set dr.* overrides (applied AFTER --dr-scale, sim_env.__init__), so neither --dr-scale nor the walkcurr bucket ladder could ramp them — they trained at full DR from step 0. Exact seed40 widen8-cartfoot-freshinit-c1 recipe otherwise (fresh random init, no BC/teacher/gait clock, full gravity, 1x torque, source motor limits), compressed ramp 0->1 over 1.5M so the 2M canary exercises the whole schedule including the bit-exact endpoint restore and a 0.5M full-DR tail. MECHANISM HEALTH ONLY: any early-ignition signal under milder early DR is noted, no acquisition claim. Prediction-if-true: dr_stage_ramp/frac rises 0->1 by 1.5M with interpolating range telemetry, training numerically healthy. Prediction-if-false: missing/flat stage telemetry, broadcast/flush errors, or numerical blowup. Strongest alternative: mechanism works but pool-flush cadence costs prohibitive wall clock (visible as fps collapse).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if dr_stage_ramp/frac reaches 1.0 by ~1.5M steps with logged ranges interpolating as designed (dr_stage_ramp/mass_scale_lo 1.0->0.85, bad_start_prob 0->0.25, fault_prob 0->0.3), losses finite, std anneal on schedule, no canary auto-stop, fps not collapsed (>=half the sibling c1 canary's throughput). FAIL only on machinery grounds. Pre-registered follow-up on PASS: launch cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-stagedr20m-b40m (this recipe, --steps 40000000, env.dr_stage_ramp_steps=20000000, seed 40, phase acquisition, fresh init) read against the matched equal-budget control cw-walkscratch-easy0905-widen8-cartfoot-freshinit-c1-b40m-ctrl (launched this cycle) on the UNCHANGED full-DR held-out gate: >=0.03 m/s median net forward in >=1 of walk/{det,sto}, 0 falls det, gait_valid majority. No unplanned seeds, no automatic extension.

