# Cartesian foot-placement action decode — build notes (2026-09-08)

Mechanism: `goal.walk_cart_foot_box_{x,y,z}_m` (all default 0.0 = OFF,
bit-exact legacy) — reinterprets the 18 joint actions per leg as a
Cartesian foot target in the leg-root frame, analytic model-derived
yaw + planar-2R IK -> logical joint targets -> unchanged SafetyLayer/
servo/reward. Code: `rl_move/sim/cart_foot_decode.py` + the branch in
`rl_move/sim/joint_task.py`. Banks:
`rl_move/tests/test_cart_foot_decode.py` (8) +
`rl_move/tests/test_cart_foot_frame.py` (4, root's independent frame
bank) = 12/12 green on controller.

## Correction history (same cycle)

The first decoder draft derived the leg frame's radial axis from the
zero-pose FOOT direction; the foot's constant lateral offset (~1.5 mm)
made an exact planar chain look ~0.35 deg tilted, and the draft
recorded a false "irreducible CAD tilt" with a 2.08 mm FK error and a
false primitive-family geometric rejection. Root's copy-only review
(`artifacts/rl_watchdog/cart_foot_frame_review_20260908/`) identified
the bug and surgically applied the pitch-plane frame fix. With the
corrected frame the analytic FK matches MuJoCo site FK to 1.77e-16 m
on mesh_mjx (and fits the primitive family too); the old geometric
rejection is replaced by a genuine nonparallel-pitch-axis guard.

## Measured facts (mesh_mjx twin, lineage bias/box cfg, corrected frame)

- Leg constants (leg-root frame, all legs identical): hip anchor
  (hx,hz) = (0.01250, 0.03840) m, F = 0.09000 m, T = 0.14550 m,
  foot lateral offset y = -0.0015 m. FK exact to 1.8e-16 m.
- Zero-action parity with the source joint-box decode's a=0 pose
  (yaw 0, hip 20 deg, knee 100 deg logical): ~4e-16 rad. Decode
  self-consistency on unclipped targets: < 1e-9 m (exact).
- Source stance foot point (leg-root frame): (0.0718, -0.0015, -0.1357) m.
- Joint-box foot-space image around it (4000-sample bound, lineage box
  yaw15/hip20/knee25 deg): x [-0.071,+0.068], y [+/-0.034],
  z [-0.029,+0.052] m -> launch box (0.06, 0.035, 0.04) m
  (comparable exploration scale to the source's own action box).
- Cartesian box corners partially exceed the yaw cone / outer annulus:
  targets project to the closest reachable point; decode is total.
- Warp/GPU integration: root's environment bank
  (`artifacts/rl_watchdog/cart_foot_gpu_bank_20260908/`, status PASS,
  cuda:0, MjxShardedVecEnv impl=warp, source hashes == this tree)
  exercised the real worker `_act_to_q` with the exact cont40m recipe
  + the three box overrides: decode parity 0.0 rad at constructor /
  after model DR / after pool pops; resets/pool refill clean; decoder
  cost ~72 us/call.
- Pre-existing clean-HEAD test failures, unrelated (worktree-verified):
  `test_joint_frame.py::test_joint_policy_surface_...` (plant knee
  100 vs 80) and the recorded `test_sim_env.py::test_drag_charges_...`.

## Bank-integrity record (post-launch, same cycle)

Full `test_task_semantics.py` run on BOTH the mechanism tree and a
clean-HEAD worktree: 35 failed / 353 passed each, with IDENTICAL
35-name failure sets (diff empty) — the mechanism diff introduces
ZERO bank regressions; all 35 are pre-existing (retired-mechanism
walkcurr/sv/assistfade semantics families plus the two already-known
clean-HEAD failures).

## Outcome record (same cycle)

- cartfoot-c1 (2M retrofit): CANARY PASS mechanism-viable (19/24 gv,
  0 falls through fully reinterpreted actions) but NOT promising —
  slip 3-10x the matched off control in 4/4 groups.
- cartfoot-offctrl (+2M control): CANARY PASS, source band retained.
- cartfoot-c1-cont10m (fork a): ACQ FAIL per its pre-registered rule —
  slip converges (worst group 68->16/m) but plateaus at 2.6-3.3x the
  matched control at 10M more steps with reward never rising; RETROFIT
  form CLOSED (verdicted by the concurrent triage cycle, consistent
  with this cycle's read).
- cartfoot-offctrl-cont10m: PASS, band stable (5.1-5.8/m).
- Scoped next candidate (not launched, per-cycle cap reached and it
  needs its own pre-registration): FRESH-INIT equal-footing test —
  cartfoot vs joint decode from init, matched budgets/seeds, so
  neither arm carries the semantics-scramble handicap.
