# Support-conditioned geometric yaw assay: completed STOP

The preregistered analytic law failed the original steering authority gate: **0/16 states reached 5 mrad command-aligned positive-branch gain**, so neither yaw sign qualified at either fixed target. Maximum G+ was **1.4662 mrad**; mean/median were **0.3351/0.3933 mrad**. Corrected behavioral retention passed **32/32** signed pulse branches. This is a valid negative result for this exact finite law, not evidence for increasing its dose, repeating it as a controller, fitting another template or launching PPO. The earlier coordinated-screen STOP and learned-policy continuous-arc qualification failures remain unchanged.

## Provenance and actual execution

- Preregistered before any rollout on GitHub main: c0cb4ae02, 2026-09-08 08:54:05.233368 UTC. Exact prepared source copied unchanged to [PROPOSAL_SOURCE.md](PROPOSAL_SOURCE.md); [PREREGISTRATION.json](PREREGISTRATION.json) changes its status only. Protocol SHA256: 93d328352ef4fe3dc5d323a86f22110ba7b2bb0aa49fd1b1744fe27964d20abc.
- Ownership was checked and root assigned the unowned CPU diagnostic under standing simulation authority: [ownership_audit.md](ownership_audit.md). No physical robot actions, GPU training, architecture/reward search or additional scheduling.
- Initial runner was published at d94a3ee54. First attempt began 08:59:18 UTC, produced the eight frozen continuous baselines and sixteen selected states, and failed during zero-control observation before nonzero pulses. The runner incorrectly required a diagonal logical-to-MuJoCo derivative. Actual robot-absolute mapping has knee-relative = knee-absolute − hip-absolute, with per-leg derivative [[1,0,0],[0,1,0],[0,-1,1]].
- Faithful implementation repair published at bfc8f431ef2199afc440fe3925fa40eae5f75588, before corrected pulse execution. The full derivative was already present in the Jacobian chain; the incorrect assertion was repaired. Seven tests pass, including the real joint-frame function and an actual MuJoCo kinematic Jacobian finite-difference comparison. No response-derived change to the controller or criteria.
- [initial_attempt/](initial_attempt/) preserves the failure, all eight baseline traces, selected states and complete-state hashes. [recovery_pins.json](recovery_pins.json) freezes every initial evidence file and actual joint-frame SHA. The corrected runner **reused these eight baselines without rerunning them**, asserted the exact sixteen selections and setup, and verified all zero controls before pulses.
- Corrected execution started **2026-09-08 09:04:22 UTC** on the existing controller CPU with eight workers and completed in **26.652 seconds**, exit 0. It used isolated source /workspace/hexapod_hybrid_fullmesh_20260908/hexapod_walker/prototype_sts3215, reviewed helper /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908/reviewed_probe_action_response_bank.py, and output /workspace/hexapod_support_yaw_20260908/full_recovered. No current shared-source simulation overrides were inherited.
- [execution_manifest.json](full_recovered/execution_manifest.json), [pins.json](pins.json) and [cfg_set.json](cfg_set.json) retain exact source, asset, runtime and 64-key assisted configuration provenance. The manifest embeds the original registration's historical NOT_STARTED value; actual terminal status is [summary.json](full_recovered/summary.json), **COMPLETE / STOP**.

Frozen policy ppo_goal_cw_robotwalk_turns_20260907_yawref_cigate8m.zip SHA256: 61f9c20f0f72d89217a22b47037e33c8dad2f50bfaca0a3d5517f714dd0eeb10; full XML SHA256: 7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837. Every rollout reports full mesh: **34 meshes, 159 geoms, 4.80573 kg**, motor **400 write speed / 20 acceleration / 0.375° per tick / 350 counts/s resolved velocity / 100 Hz**. **350 is a velocity ceiling, not current.** The frozen current/safety configuration is preserved; this is simulation evidence, not physical validation.

## Exact fixed experiment and checks

Two held-out reset draws × two initial phases × two command signs × two target phases yielded 16 states. There were eight 755-tick continuous baselines, **48/48 zero/positive/negative branch slots**, and four 15-second straight cells, each with untouched and exact-zero-off rollouts. All states were available; none was replaced. Pulses were one frozen geometry-derived vector for five ticks, followed by 75 unchanged-policy ticks. The requested maximum coordinate dose was 0.05, with float64 roundoff at 1e-17; maximum applied float32 increment was 0.05000000447, ordinary float rounding. There were zero action clipping events.

- All sixteen zero branches matched continuous baseline prefix, endpoint full integration/controller state, and scoring-window trace.
- All thirty-two pulse prefixes and frozen vectors matched their paired zero branches. All forty-eight support-observation paths preserved live integration/cached state.
- All four straight zero-off pairs matched full trace and endpoint state through 1,500 ticks; this is parity, not newly learned straight walking evidence.
- All 64 recorded rollouts completed without termination. All 32 pulse windows were complete and entirely in walking mode.
- Every selected state had exactly three supporting feet (>0.5 N), horizontal support rank 2, and each selected action Jacobian rank 3 at the preregistered cutoff. Tripod supports [0,2,4] and [1,3,5] occurred eight times each. No unavailable/no-op substitution occurred.
- Source/asset/checkpoint/helper hashes, exact reset offsets and original state selections are retained. [audit_frozen_results.py](audit_frozen_results.py) independently recomputes evidence checks and retention without launching simulation or fitting a controller.

## Every held-out result

Positive means adding the fixed sign(command)-aligned analytic vector; negative reverses that vector while preserving the command. The primary outcome remains the original last-solve world yaw. All numbers below are measured against the corresponding untouched baseline. A gain of at least +5 mrad, positive odd response, and both-branch retention were all required.

| Reset | Initial phase | wz | Target | Tick | G+ (mrad) | G− (mrad) | Odd (mrad) | ± retention |
|---|---|---:|---|---:|---:|---:|---:|---|
| 1 | π/2 | +0.15 | 5π/6 | 638 | 1.4662 | 0.2670 | 0.5996 | pass/pass |
| 1 | π/2 | +0.15 | 11π/6 | 600 | -0.1926 | -2.0153 | 0.9113 | pass/pass |
| 1 | π/2 | -0.15 | 5π/6 | 638 | -0.2759 | -4.1889 | 1.9565 | pass/pass |
| 1 | π/2 | -0.15 | 11π/6 | 600 | 1.2773 | -0.2371 | 0.7572 | pass/pass |
| 1 | 3π/2 | +0.15 | 5π/6 | 600 | 1.1445 | 0.5816 | 0.2814 | pass/pass |
| 1 | 3π/2 | +0.15 | 11π/6 | 638 | 0.3764 | -2.4174 | 1.3969 | pass/pass |
| 1 | 3π/2 | -0.15 | 5π/6 | 600 | 0.4102 | -3.8711 | 2.1407 | pass/pass |
| 1 | 3π/2 | -0.15 | 11π/6 | 638 | 0.3116 | -0.0419 | 0.1767 | pass/pass |
| 2 | π/2 | +0.15 | 5π/6 | 638 | -0.6212 | 0.6631 | -0.6422 | pass/pass |
| 2 | π/2 | +0.15 | 11π/6 | 600 | -0.0337 | -5.5792 | 2.7727 | pass/pass |
| 2 | π/2 | -0.15 | 5π/6 | 638 | -0.6785 | -0.6652 | -0.0067 | pass/pass |
| 2 | π/2 | -0.15 | 11π/6 | 600 | 1.1633 | 0.6566 | 0.2533 | pass/pass |
| 2 | 3π/2 | +0.15 | 5π/6 | 600 | 0.9017 | 0.7853 | 0.0582 | pass/pass |
| 2 | 3π/2 | +0.15 | 11π/6 | 638 | 0.4329 | -5.1774 | 2.8051 | pass/pass |
| 2 | 3π/2 | -0.15 | 5π/6 | 600 | -0.7465 | -0.5779 | -0.0843 | pass/pass |
| 2 | 3π/2 | -0.15 | 11π/6 | 638 | 0.4256 | -0.8992 | 0.6624 | pass/pass |

All sixteen positive gains fail the fixed 5 mrad threshold. Odd response is positive in 13/16 states, range −0.6422 to +2.8051 mrad; this smaller directional response cannot substitute for the absolute gain gate. Negative-branch G− reaches −5.5792 mrad, which is steering against the command and does not qualify. No target/sign regrouping or response fit was performed.

Retention is healthy within the original 80-tick windows: forward-distance ratios range **0.9873–1.0337** (minimum required 0.9); loaded material slip ratios **0.9707–1.0194** (maximum allowed 1.25); maximum increases in absolute roll and pitch are **0.0704° / 0.0714°** (allowed 3°). Every leg has positive loaded duration in every branch; per-leg minima across the pulse windows are [0.418, 0.380, 0.394, 0.388, 0.384, 0.334] seconds. Per-leg material displacement and loaded time are descriptive, with no new chronic-leg threshold. Vector L1 norms are 0.14037–0.15009 and L2 norms 0.08065–0.08603.

## Evidence and limits

[Full state results](full_recovered/state_results.json), [all signed branches](full_recovered/pulse_branches.json), [zero controls](full_recovered/zero_controls_frozen.json), [straight pairs](full_recovered/straight_zero_off.json), [post-execution audit](full_recovered/post_execution_audit.json), and [64 trace files](full_recovered/traces/) retain all held-out outcomes, normal loads, Jacobians, action increments, clipping, per-leg metrics and parity evidence. The exact immutable baseline and selected-state JSON files are byte-identical to the first attempt.

One descriptive reporting item is unavailable: **the frozen helper did not export a motor-current time series**. Current configuration remains pinned (2.5 A, 2 s sustained trip), but no measured current-health claim is made. Existing complete-state hashes do not recover that missing series. No response rerun was made to fill it. This omission cannot turn the sub-threshold steering result into a pass.

The geometric Jacobian test uses private kinematic operations only; force observation uses stored solved contact wrenches with no solver refresh. The fixed law has no learned response coefficients. The experiment closes this exact law as specified. Even a pass would not have isolated a causal benefit of support conditioning, validated recurring steering or authorized PPO; the observed STOP provides none of those claims.
