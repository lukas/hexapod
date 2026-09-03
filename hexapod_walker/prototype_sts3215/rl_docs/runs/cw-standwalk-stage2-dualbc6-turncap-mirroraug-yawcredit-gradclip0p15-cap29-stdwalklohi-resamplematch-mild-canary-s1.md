# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-mild-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-03T10:45:56+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-canary

**wandb_id**: 7c7vxb9i

**hypothesis**: Seed replicate of resamplematch-mild-canary (seed0, train-1, RUNNING): same milder single-lever retry (resample_s 4.0->5.0, jitter 0.5->0.35, walk_cmd_mode=stress_mix kept) off the resamplematch-canary CANARY-FAIL-MECHANISM finding (steering unchanged/worse + new immediate own-DR tilt-roll falls at the full-stress dose). Second seed closes the pass-rate question before any acquisition-scale commitment.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as resamplematch-mild-canary seed0's gate (probe_turn_authority + det/sto walk-mode eval_checkpoint.py read under stress_mix, dr0+owndr): PASS if BOTH seeds clear >=20% steering improvement with zero new own-DR falls; FAIL if either seed reproduces the immediate-tilt own-DR falls or turn authority regression.

**verdict**: CANARY FAIL - MECHANISM (seed-1 companion to resamplematch-mild-canary; same conclusion, cross-seed replicated -- see that runs verdict for full numbers). Falls/turn-authority sub-criteria resolved clean: probe_turn_authority wz_med 0.190/0.212 rad/s (well above 0.07 floor, zero probe falls); own-DR walk-only read (eval_checkpoint.py --modes walk --per-mode 16, dr-scale 0.0/0.5 x det/sto, no-video) shows 0/16 immediate-tilt terms (the harder-dose fall mode does not reproduce), only a benign late (t~22.4s, hold-segment) hold_min_load termination at the same 1/16 baseline-noise rate seen in seed0 and in the unrelated stdwalklohi-acq1 fastwalkcheck baseline. Steering/slip sub-criteria do NOT clear the gates PASS bar: dir_err_med 38.6-39.5deg (flat vs the harder-dose resamplematch-canary FAIL band 38-41deg, no >=20% drop); course_err_1s_med 7.3-11.4deg (roughly flat vs that runs 9.6-12.6deg FAIL band, one subgroup marginally better but not a clean win); slip_per_m_med 3.19-4.30, still breaching ~3.8 in the own-DR-det subgroup (3.98) that matters most. Conclusion matches seed0 number-for-number in kind: PARTIAL-shaped per the gates own pre-registered branch (falls gone + authority holds + steering doesnt move), recorded as FAIL-MECHANISM per the ledgers canary-scope status vocabulary. Diet-rate lever CLOSED (both doses, both seeds); pivoting to the structural forward+turn co-occurrence lever (walk_yaw_zero_frac/walk_turn_in_place_frac) per track STATUS Next. Artifacts: logs/ckpt_eval/standwalk_resamplematch_mild_canary_s1_walkcheck/{s1dr0det,s1dr0sto,s1owndrdet,s1owndrsto}/report.json, logs/ckpt_eval/probe_turn_authority_resamplematch_mild_canary_s1.json.

