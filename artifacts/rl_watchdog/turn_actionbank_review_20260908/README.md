# Reviewed action-response bank copy

Completed reviewed controller replay: see `RESULT.md` and `review_summary.json`. All 296 original trajectories match exactly, all 288 pulses retain progress/contact slip/health under the corrected screen, and none reaches the unchanged 5 mrad primary threshold. No core source or live owner runner was changed.

The completed owner bank found 0/288 pulses reaching the preregistered 0.005 rad commanded-direction observed-yaw gain (maximum about 0.0041 rad). Preserve that finite pulse-class negative result; it does not falsify coordinated, longer, closed-loop or learned steering mechanisms and does not justify a PPO canary.

## Source reconciliation

`owner_runner_snapshot.py` is the initial 06:27 snapshot (0b94ca3f...). The later completed owner source is `owner_completed_runner.py` (ed15d1c609381f954e239577d13879d633791e221db88df5df4d064abe82a15a). Before its full bank, the owner switched the absent pitch_rel_deg lookup to absolute pitch_deg and added baseline final-qpos equality. Thus neither a pitch-zero assertion nor a missing-final-qpos assertion applies to the completed bank. Absolute-angle extrema do not generally cancel a reset reference under a baseline-relative comparison. Missing values still silently defaulted to zero in the owner runner.

The used `_build_cfg`, `make_env`, `_load_model`, `rollout`, and `_ContactAudit` helper callpaths were independently found identical between the owner's old worktree and current source at review. Worktree age alone was not a causal defect. Parent must use the validated helper source and retained frozen full-mesh assets; never regenerate XML/assets. Runtime source hashes are saved with the reviewed bank.

## Review protocol amendment

The copy preserves the exact 64-key config, seed 0 / DR 0, checkpoint 61f9c20f..., XML 7efb8e8a..., command hold/ramp, branch selection, doses and original 0.005 rad primary threshold. Pulse injection remains AFTER SB3 predict action-space clipping, then single-component bound clipping, before unchanged environment safety and servo dynamics. It is not a pre-clipping policy-logit perturbation. A 1.333333 Hz phase clock has period 0.7500001875 s; 75 followup ticks are its nearest 100 Hz representation. Half-cycle branches remain selected by actual phase (638 vs 600 expected); actual phase error is output.

Additional zero controls check full endpoint qpos, MuJoCo integration state, registered episode/controller history, policy recurrent state and observation, plus trace equality. They run before pulse branches. Every pulse also checks its full prefix state. Absent state or gate measurements abort rather than masquerading as a healthy zero.

The original primary `d_yaw_rad` deliberately retains the owner's live last-solve xmat timing, so direct comparison remains possible. `endpoint_d_yaw_rad` is additional. Private MjData is used for endpoint computations; live solver buffers are never refreshed.

Corrected retention is explicitly a POST-REVIEW measurement screen, not a retroactive reinterpretation of preregistration. In the new metrics, `fwd_disp_m` integrates actual body-frame forward velocity at physics substeps. `loaded_slip_m` sums substep, normal-load-weighted pad MATERIAL contact-point displacement on stationary ground, with the same >0.5 N numeric foot-load cutoff (actual summed normal force, not the old touch sensor proxy). Dividing by loaded foot-seconds gives `loaded_material_mean_speed_m_s`. This finite-step material-point displacement accounts for pad rotation; it is not body-center translation. It is Euler-only and fails for moving external bodies. Distances are already integrated per substep and receive no extra dt factor.

The old initial-heading chord and touch-weighted pad-center displacement remain under `legacy_initial_heading_fwd_disp_m` and `legacy_pad_center_touch_slip_m`. When --original-bank is supplied, each branch additionally retains all `owner_original_metrics`, and exact original observed yaw / legacy trace hash / final-qpos comparisons must pass. The original proxy retention screen retains its original semantics; any corrected screen uses the same numerical 0.9 forward / 1.25 slip / +3 degree tilt / no-term / all-walk thresholds but must be labeled post-review. No threshold was changed to obtain a pass. Window scoring is 80 post-pulse ticks, with 81 state samples including the initial state.

## Focused local validation

Six tests pass (0.11 s): real emitted pitch plus fail-closed missing/nonfinite values; no-slip rotation of a loaded material point despite moving pad center and correct distance units; changing-heading body progress versus initial-heading chord; state parity detecting changed qvel/controller history while qpos is equal; and real MuJoCo direct-versus-audited step equality for qpos/qvel/warmstart/derived solver fields. The sixth regression covers ordered deque history and its capacity. The full checkpoint bank subsequently completed; the result is recorded separately.

## Executed controller command

This directory was copied to `/workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908`. Copy hashes and the five helper ASTs matched current main and the original owner worktree. The command below executed in the parent's retained validated full-mesh worktree without regeneration. It pins spec, cfg, checkpoint and XML hashes; output records all source/asset hashes. No optimizer, checkpoint creation, W&B, physical robot or training launch is involved.

```sh
cd /workspace/hexapod_hybrid_fullmesh_20260908/hexapod_walker/prototype_sts3215
HEXAPOD_PROTOTYPE_ROOT="$PWD" timeout 600 uv run python /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908/reviewed_probe_action_response_bank.py \
  --spec /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908/owner_prereg_spec.json \
  --cfg-json /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908/cfg_set.json \
  --checkpoint rl_move/sim/policies/ppo_goal_cw_robotwalk_turns_20260907_yawref_cigate8m.zip \
  --original-bank /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_20260908/bank.json \
  --out /workspace/hexapod/artifacts/rl_watchdog/turn_actionbank_review_20260908/full \
  --workers 12
```

Expected 4 baselines, 8 zero branches, 288 pulse branches. The output must report zero/prefix parity, full original trajectory parity and unchanged original yaw responses before interpreting the corrected retention metrics. No duplicate smoke/full run is needed. On failure, preserve the failure artifact/trace and repair only the concrete cause; do not lower a gate.
