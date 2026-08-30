# cw-walkcurr-pf-terrain1-central-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T00:32:57+00:00

**pod**: hexapod-mjx-train-0

**steps**: 20000000

**wandb_id**: 82muplua

**hypothesis**: Plain English: does training on rough, varied terrain instead of a flat floor give the from-scratch centralized-MLP PPO+SV-diet policy the extra exploration push that flat ground could not, per Heess et al. 2017 (environment/terrain diversity as the exploration driver, registered literature item (3) in the 08-29 operator ruling)? This is fallback (b) of the operator-named ladder, opened after fallback (a) (the off-policy SAC probe: 7 SAC-SV arms across s0/s1/budget10m/tilt2/tilt5/tilt10/tilt10-r2/tilt5-settle1/tilt10-settle1, none passed the rung-1 gate) was exhausted this cycle. Identical SV diet/budget(20M)/seed(0)/centralized-128,64,32-tanh-MLP architecture to cw-walkcurr-pf-central-sv-s0 (pinned static-crouch basin, FAIL) and to this arm's own flat-ground control cw-walkcurr-pf-terrain0-central-s0 -- the ONLY lever is env.terrain_amp=1.0 (full 18mm indoor-bump hfield, MP.make_terrain_heightmap, flat within 0.32m of spawn then rough) plus the env.model_source=primitive needed to get hfield-in-Warp support at all (the checked-in mesh_mjx twin has no hfield asset; primitive's hfield-under-Warp path is independently precedented -- cw-walk-terrain10-payload/-deadband both reached PASS on the joystick track pre-08-24 with this exact terrain_amp=1.0+impl=warp combo, so this is proven machinery, not new code). If it escapes the static basin (walk_speed off floor, ep_len stable/rising, ideally clearing the rung-1 gate) while the terrain0 flat control stays pinned = terrain diversity is a real exploration lever, promote (retrofit onto decleg-sv, try higher doses, more seeds). If both terrain0 and terrain1 stay pinned identically = terrain doesn't help at this dose either, closing fallback (b) at amp=1.0 and forcing a dose escalation or the next item down the ladder.

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6, FLAT ground -- the gate/eval harness is unchanged; terrain is a training-time exploration driver only, not part of the held-out test surface): zero tilt terminations, cmd_prog_frac>=0.35, direction_err_deg<=30, slip/m<=3.0, gait_valid>=4/6 with all six legs cycling, real stepping on video. Discovery litmus corrected per the decleg-sv dig-in finding: require env/walk_speed clearly off its ~0.02 m/s static floor AND stable-or-rising rollout/ep_len_mean (NOT raw freeprog escape alone -- proven to correlate with an episode-shortening artifact, not real discovery). Read against BOTH cw-walkcurr-pf-central-sv-s0 (mesh flat baseline) and cw-walkcurr-pf-terrain0-central-s0 (primitive flat control): escape past either baseline with rising reward = terrain lever real, continue per 08-21 even short of the full gate; pinned static basin + flat/falling reward matching both baselines = aligned FAIL, terrain-at-this-dose closed.

