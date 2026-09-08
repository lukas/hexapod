# Independent result audit — PASS

The delegated reviewer `fresh_cartesian_frontier/template_norm_review` audited the completed result independently using only saved JSON/NPZ records and NumPy. No runner, rollout helper or simulator was imported or executed by this audit. The review found no mismatch.

- Exact six-cell inventory: 6,020 control/action rows, 6,020 actual writes, 30,100 profile ticks and 30,100 physics steps. Each control tick has five 0.002-second profile/physics steps.
- All 78 prior body/current arrays match shape, dtype and bytes.
- All 34 historical state boundaries match saved qpos and the three state hashes. The four arc endpoints at 755 remain explicitly new captures.
- Runner file and execution-manifest SHA256 both match `761c19669895a3ac57bf3aca835cc819cadb088a446d5ba44c94f963c2693bf9`.
- No safety holds, failed statuses, terminations or decoder failures. Entry slew ramps were inactive.

The following eight per-joint aggregate fields were independently recomputed from raw NPZ arrays across both registered windows (all ticks and [200,N)) for all six cells; maximum discrepancy was exactly zero:

1. `decoded_safe_mean_abs_rad`
2. `requested_increment_mean_abs_rad`
3. `safe_increment_mean_abs_rad`
4. `requested_slew_exceed_fraction`
5. `profile_goal_target_mean_abs_rad`
6. `effective_profile_mean_abs_rad`
7. `profile_actual_post_mean_abs_rad`
8. `profile_velocity_cap_max_ratio`

This is the exact independent recomputation scope, not a claim that every aggregate or interpretation received a second implementation. The audit specifically preserves the meaning of `requested_slew_exceed_fraction`: requested increments exceeding the nominal/entry slew allowance. It does not measure recoverable yaw loss or establish a controller mechanism. Sixty static tests and root's independent pre-execution implementation review are separate checks described in README.md.
