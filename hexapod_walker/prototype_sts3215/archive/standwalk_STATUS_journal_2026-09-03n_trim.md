# standwalk STATUS journal archive — 2026-09-03n

Moved verbatim from `rl_docs/tracks/standwalk/STATUS.md` 2026-09-03
~19:1x when superseded by the 4-arm omega-boost canary batch's
complete (all-FAIL) read + the rise-stall replay closure. Points on
to `...-03m_trim.md` (noted gap, per that pointer's own note: this
file and several files it in turn points to do not exist on disk,
unrepaired here — matches the pre-existing gap policy already
recorded upstream).

---

Earlier update, 2026-09-03 ~17:5x (idle-kick, Next item 2, branch (a) —
**ROOT CAUSE FOUND (zero-training) + LEVER BUILT + 4-ARM CANARY BATCH
LAUNCHED**): diagnosed WHY the combined-tick wz collapse happens
before touching `tripod_gait.py`: per-leg IK never fails and coxa-yaw
excursion is LARGER under combined than pure-turn (ruling out an IK/
workspace-clipping bug), but `info["walk_loadslip_ratio"]` rises ~20%
combined vs pure-walk, and boosting the omega TERM in the teacher's
foot-target formula alone (independent of any clip) recovers wz
smoothly — this is a friction/thrust-ALLOCATION effect: vx (0.08 m/s)
numerically dominates the per-leg omega contribution (omega*r~0.018
m/s), so almost all of the shared ground-reaction budget goes to
forward thrust, starving yaw. Built the fix as a BC-anchor-teacher
lever (not a `tripod_gait.py` class edit — same effect, lower risk):
new `train.bc_anchor_teacher_omega_boost` (env-side, `sim_env.py`,
default 1.0 = bit-exact identity, gated to combined ticks only,
mirrors `bc_anchor_walk_combined_skip`'s gating) multiplies the omega
fed to the teacher's `TripodGait.set_velocity` only when vx_ref!=0 AND
wz_ref!=0. Proven zero-training on the SCRIPTED teacher itself via a
new `probe_turn_authority.py --scripted-omega-boost` flag: boost 1.0
-> 2.0 raises combined wz_med 0.072->0.160 rad/s (+122%) at vx_med
0.034->0.026 (-24%); boost 1.5 -> wz_med 0.117 (+62%) at vx_med 0.032
(-6%); pure-turn/pure-walk PROVEN bit-exact untouched (9 new tests in
`test_probe_turn_authority.py`, 4 new pinned-equality tests in
`test_bc_anchor.py`, 101/101 + 9/9 green; also fixed an unrelated
pre-existing stale-constant test failure caught incidentally). Batch-
launched the 2-dose x 2-seed matched grid (operator 08-22 batching
rule) against the SAME already-PASSED controls as branch (b)
(`cap29-stdwalklo-hi{,-s1}`, no duplicate control spend):
`cap29-stdwalklohi-omegaboost{1p5,2p0}{,-s1}`, all 4 RUNNING. Same
pre-registered gate shape as branch (b)'s canary (beat the
yawdensity_canary_s1 comparator both signs, <=10% pure-turn/straight-
walk regression vs control). Snapshot `d6f83ade`
(`exp/standwalk-combined-omega-boost-09-03`). One backlog item hit an
unrelated launcher infra snag (stale `linux_control/vision_ui` dir on
`hexapod-mjx-train-6` blocking its code-sync tar, left over from the
09-03 AprilTag-tracker submodule extraction) — cleaned the pod
directory and re-queued; all 4 now RUNNING. NEXT CYCLE: read all 4
combined-tick `probe_turn_authority.py --vx-cmds` results vs the gate.