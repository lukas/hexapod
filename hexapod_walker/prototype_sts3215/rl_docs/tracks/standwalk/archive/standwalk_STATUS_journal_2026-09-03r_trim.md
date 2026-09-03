# standwalk STATUS journal archive — 2026-09-03r (VERBATIM)

Prior "Update" banner text, superseded by the 09-03 ~23:0x
banner (candidate (i)-v2 yaw-arm-scale lever built, zero-
training gate PASSED, 4-cell RL canary launched). Moved here
verbatim, unedited.

---

Update, 2026-09-03 ~22:1x (**Candidate (i) harness BUILT + first read:
the scripted teacher's YAW joint saturates the SafetyLayer slew clip
on combined ticks but almost NEVER on pure-turn ticks at the SAME
|wz_cmd| — hypothesis (a) CONFIRMED on the open-loop reference.**)

Built `rl_move/sim/probe_joint_tracking.py` (+ 3 tests, all green) per
Next item 2's own prescription: drives the LIVE mesh/100Hz sim with
the scripted `TripodGait` teacher and records, every walk-mode tick,
`desired` (open-loop IK target) vs `cmd` (env's post-SafetyLayer-clip
target, `env._cmd`) vs `actual` (physics-settled `joint_position`),
split per axis (yaw/hip/knee) and PURE-TURN (vx=0) vs COMBINED
(vx=0.08) at the identical `wz_cmd=+-0.25`. Result (15s episodes,
det. scripted policy, seeds 0/1 identical since no DR):
**yaw-axis clip saturation frac (fraction of walk ticks where the raw
per-tick yaw delta alone exceeds `max_delta_q_deg`): pure-turn 0.0%,
combined 47.7%** — every cell, both wz signs, both seeds, exactly
reproduced (symmetric, deterministic). p90 accumulated yaw
desired-vs-commanded gap: pure-turn ~0deg, combined 8.3deg. The
downstream actuator/physics tracking gap (`cmd` vs `actual`) does NOT
show the same asymmetry — if anything it is SMALLER on combined for
yaw specifically (2.4deg med) than pure-turn (4.3deg med), i.e. once
the SafetyLayer has already truncated the target, physics has an
easier (smaller) residual to chase. **This answers Next item 2's own
question: the combined-tick turn-authority loss lives in the
SafetyLayer clip stage, specifically on the yaw joint, not in
downstream stance-leg slip/contact-force competition** — no falls in
any probe cell. Root mechanism (not yet fixed): `_foot_target_in_body`
sums `vx` and `omega*r*sin/cos(leg_angle)` into one raw per-leg
velocity vector before the yaw-angle IK solve; adding a nonzero `vx`
term changes the per-tick yaw-angle swing enough to blow the slew
budget that a rotate-only command never touches — exactly the
"vx+omega superposition formula" candidate (i) named, now measured
rather than inferred. Evidence:
`logs/ckpt_eval/joint_tracking_cap29_scripted_09-03.json`. Prior
banner (candidate (ii) 4/4 FAIL close) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03q_trim.md`.

