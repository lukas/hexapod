# standwalk STATUS journal archive — 2026-09-03a (VERBATIM trim)

Moved out of STATUS.md 2026-09-03 ~03:1x to keep the live file under
its line budget. This is the 2026-09-03 ~01:5x update entry, verbatim.

Earlier update, 2026-09-03 ~01:5x (idle-kick, item 0's read still
mid-flight):
**Found + fixed a THIRD instance of the joint-frame-v2 stale-plant-
literal bug — this time inside `test_task_semantics.py` itself**, the
one file the 09-02 ~23:5x audit had cleared ("every ~16 TripodGait
import uses `sim_gait_compat` consistently"). That audit was right
about the TripodGait path but missed 12 helpers that ALSO build a RAW
plant pose (`plant_rad`/`stork_rad`/`topple_rad`/`bellysit_rad`/
`_stopcurrent_rollout`'s own literal) fed straight to `q_rad_to_action`,
bypassing `sim_gait_compat` — same bug, same fix shape: added
`RAW_PLANT = (20.0, 100.0)` (robot_abs equivalent of `WALK_PLANT`'s
sim-relative 80) for the bypass literals only; `WALK_PLANT` itself is
unchanged (still correct for the TripodGait path). Decisive zero-
training A/B on `_stopcurrent_rollout`'s still/brace twins: at the
stale literal "still" drew MORE current (0.439A) than "brace" (0.322A,
BACKWARDS) and the isometric-fight charge barely fired (0.97 vs the
1.0 bar); at the fix, "still" settles to 0.160A and "brace" separates
cleanly at 0.268A with a 16.1-pt margin. Verified: `test_stopcurrent_
reprices_the_isometric_fight` now PASSES (was one of the 09-02 ~23:5x
"10 plant-literal-cascade" reds); the other 9 in that set (4 walkcurr_
pf-family, low-priority/retired-track, + 5 with confirmed DIFFERENT
root causes) correctly stay red, not papered over. A full whole-file
regression is running in the background (`/tmp/full_after_fix.log`,
not finished at cycle end) to confirm zero regressions beyond the
targeted 10-test check; the manual per-site code audit (all 12 touched
call sites individually read) already gives high confidence. **Found
but NOT fixed:** a related, likely LARGER bug where several helpers
(`_hold_rollout`, `_lower_rollout`, `_getup_rollout`'s freeze/stilt)
feed raw `env.data.qpos` (MuJoCo-native, i.e. mujoco_rel) straight to
`q_rad_to_action` without the `mujoco_rel_rad_to_robot_abs_rad()`
conversion — measured on `_hold_rollout`'s "quiet" policy: un-fixed it
drifts 4.12mm off its settled height over 15s; converting q0 first
drops that to 0.44mm. Flagged for a dedicated next dig-in (full
derivation: `OPERATOR_QUESTIONS.md` 2026-09-03 ~01:2x-01:5x entry) —
touches more helpers than one cycle should rush. No training-default
cfg touched. Snapshotted+pushed. Item 0 (`cap29-stdwalklohi-acq1{,
-s1}` flat-only session read) confirmed still progressing live on
train-6/7 throughout (dr0 sto sub-pass ~20-25/32, normal pace).

