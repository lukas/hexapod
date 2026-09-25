"""Reset-time episode setup of the balance env's _reset_begin: the
physics-easing gravity scale, the mode-sequence / goal-trajectory
sampling and the start-pose (spawn) selection; moved verbatim out of
sim_env.py.
"""
from __future__ import annotations

import math
import numpy as np

from hexapod_core.joint_frame import joint_index, leg_slice
from rl_move.body_ik import FixedFootBodyIK
from rl_move.config import cfg_get
from rl_move.env import start_kind_of
from rl_move.robot_state import DEG2RAD, N_JOINTS


# QUADWALK "quadstance" spawn (08-13, quad track): per-lift-leg
# (yaw, hip, knee) rad — the "tuck" claw from
# quadruped_feasibility.FRONT_POSES (kept literal here so env workers
# don't import that mujoco-loading probe module; c57 static sweep GO,
# within joint limits yaw ±0.61 / hip −1.40..0.52 / knee −0.35..2.62).
_QUAD_TUCK_ROBOT_RAD = (0.0, -1.10, 1.30)


def spawn_pose_q_start(env, start_at):
    """Start-pose (spawn) selection by start kind; moved verbatim from
    SimHexapodBalanceEnv._reset_begin.
    """
    if start_at == "zero":
        q_start = np.zeros(N_JOINTS, dtype=float)
        # Bridge start (rise reverse-curriculum): blend the start
        # joints toward the crouch pose. Zero pose is exactly q=0,
        # so the blend is a plain scale of the crouch solution.
        f = float(getattr(env._goal_traj, "start_curl", 0.0))
        if f > 0.0:
            from rl_move.body_ik import BodyOffset
            bridge_ik = FixedFootBodyIK()
            bridge_ik.reset(env._plant_deg * DEG2RAD)
            res = bridge_ik.solve(BodyOffset(
                height=-float(env._goal_traj.crouch_dz)))
            if res.ok:
                q_start = f * res.q_rad
        if env._ep_rand is not None:
            q_start = env._clip_to_joint_limits(
                q_start + env._ep_rand.start_offset_rad)
    elif start_at == "crouch":
        # Feet at the plant footprint, body crouch_dz lower: solve
        # the same fixed-foot IK the policy uses.
        from rl_move.body_ik import BodyOffset
        crouch_ik = FixedFootBodyIK()
        crouch_ik.reset(env._plant_deg * DEG2RAD)
        res = crouch_ik.solve(
            BodyOffset(height=-float(env._goal_traj.crouch_dz)))
        q_start = (env._clip_to_joint_limits(res.q_rad) if res.ok
                   else env._start_pose_rad())
        if env._ep_rand is not None:
            q_start = env._clip_to_joint_limits(
                q_start + env._ep_rand.start_offset_rad)
    elif start_at == "rise_bank":
        # Post-lower rise start (08-14): a harvested settled
        # lower-endpoint pose of the policy's OWN lower skill
        # (goal.rise_start_bank, built by harvest_lower_endpoints).
        # SESSION_BULK_GATE named this the single trainable
        # boundary: ALL 10 det session failures + the weakest sto
        # stratum (0.801, over_current-dominated) were post-lower
        # rises, while synthetic-start first rises were 300/300.
        # +-2 deg jitter, same as the walk park bank.
        bank = env._rise_start_bank()
        if bank is None:
            raise RuntimeError(
                "start_at='rise_bank' requires goal.rise_start_bank")
        bi = int(env.rng.integers(len(bank)))
        q_start = bank[bi].copy()
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
    elif start_at == "lower_bank":
        # Composed-session LOWER entry start (2026-09-23, goal.
        # lower_start_bank — goal_task.sample()'s "lower" branch
        # analogue of the rise_bank branch above, same harvested-
        # pose/jitter contract).
        bank = env._lower_start_bank()
        if bank is None:
            raise RuntimeError(
                "start_at='lower_bank' requires goal.lower_start_bank")
        bi = int(env.rng.integers(len(bank)))
        q_start = bank[bi].copy()
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
        # Momentum-restore companion (goal.bank_qvel_restore, 2026-
        # 09-23 ~19:5x — see sim_env._apply_bank_qvel_handoff): stash
        # THIS row's harvested qvel (None on a v1/qvel-less bank) so
        # the post-settle hook can restore it later in reset(); a
        # plain attribute set, not a behavior change by itself (the
        # hook is separately gated off by default).
        qvel_bank = env._lower_start_bank_qvel()
        env._pending_bank_qvel_mj = (
            None if qvel_bank is None else qvel_bank[bi].copy())
    elif start_at == "hold_bank":
        # Composed-session HOLD entry start (2026-09-25, goal.
        # hold_start_bank -- goal_task.sample()'s "hold" branch
        # analogue of the lower_bank branch above, same harvested-
        # pose/jitter/qvel-restore contract). Harvested via
        # `eval_modeseq.py --dump-seg-qpos` (`hold_entry` tag) off a
        # real post-rise composed session, not a bespoke rollout.
        bank = env._hold_start_bank()
        if bank is None:
            raise RuntimeError(
                "start_at='hold_bank' requires goal.hold_start_bank")
        bi = int(env.rng.integers(len(bank)))
        q_start = bank[bi].copy()
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
        qvel_bank = env._hold_start_bank_qvel()
        env._pending_bank_qvel_mj = (
            None if qvel_bank is None else qvel_bank[bi].copy())
    elif start_at == "walk_entry_bank":
        # Composed-session WALK entry start (2026-09-23 ~19:5x,
        # walk_task._sample_walk's own analogue of the lower_bank
        # branch above -- reintroduces the walk-side mechanism the
        # position-only v1 (goal.walk_entry_bank_frac) closed the
        # same day, this time always carrying the matching harvested
        # qvel row alongside the position).
        bank = env._walk_entry_bank()
        if bank is None:
            raise RuntimeError(
                "start_at='walk_entry_bank' requires "
                "goal.walk_entry_bank")
        bi = int(env.rng.integers(len(bank)))
        q_start = bank[bi].copy()
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
        qvel_bank = env._walk_entry_bank_qvel()
        env._pending_bank_qvel_mj = (
            None if qvel_bank is None else qvel_bank[bi].copy())
    elif start_at == "gait":
        # Mid-stride TALL spawn (TALL LADDER T6: RSI-for-walk, see
        # walk_task._sample_walk). Scripted tripod-gait pose at a
        # random phase, generated at the episode's own commanded
        # velocity so swing/stance geometry matches the command the
        # policy wakes up under. The gait is rolled forward ~1 s
        # plus a uniform slice of one period so its internal
        # command smoothing is engaged and every phase is sampled.
        from hexapod_core.tripod_gait import TripodGait
        traj = env._goal_traj
        i_ss = min(int(round(0.5 / env.dt)), len(traj.vx) - 1)
        g = TripodGait()
        g.sync_plant_stance(float(env._plant_deg[1]),
                            float(env._plant_deg[2]))
        g.set_velocity(vx=float(traj.vx[i_ss]),
                       vy=float(traj.vy[i_ss]))
        # Turn-state reset densification (08-23, turnlib3 FAIL
        # branch): goal.walk_gait_spawn_wz (default 0 = off,
        # bit-exact: omega is simply never passed) additionally
        # feeds the episode's own commanded yaw rate into the
        # scripted-gait pose generator, so turn / turn-in-place
        # episodes SPAWN mid-rotation instead of always entering
        # the turn from a standstill. Pricing (k_yaw_prog 1-3x),
        # demo range (teacher_v3) and style ablation (-noamp1)
        # were all measured unable to move tip tracking; the
        # policy never VISITS fast-turning states — same
        # densify-at-reset shape as park_start/gait_start.
        spawn_wz = float(cfg_get(env.cfg, "goal",
                                 "walk_gait_spawn_wz", default=0.0))
        wz_arr = getattr(traj, "wz", None)
        if spawn_wz > 0.0 and wz_arr is not None:
            g.set_velocity(omega=float(wz_arr[i_ss]) * spawn_wz)
        g.reset_phase()
        warm = 1.0 + float(env.rng.uniform(0.0, g.period))
        t, q_deg = 0.0, g.neutral_pose_deg()
        while t < warm:
            q_deg = g.desired_deg(t)
            t += env.dt
        q_start = np.asarray(q_deg, dtype=float) * DEG2RAD
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
    elif start_at == "any":
        # GETUP-mode start diversity (operator 08-11: "from any
        # position: recover -> stand -> walk"). The recovery task's
        # curriculum IS its start distribution — episodes spawn all
        # along the pipeline (random legal tangle that settles
        # however it lands incl. tipped, belly-zero, partial curl,
        # crouch, plant, tripod park) so backward-chaining needs no
        # reference trajectory or RSI. The KIND was drawn by
        # _sample_getup (goal side, where the force hook lives) and
        # rides on the trajectory.
        kind = getattr(env._goal_traj, "start_kind", "tangle")
        tangle_blends = {
            "tangle_mild": 0.25,
            "tangle_mid": 0.50,
            "tangle_60": 0.60,
            "tangle_70": 0.70,
            # Legacy forced-eval alias retained for old probes.
            "tangle_deep": 0.75,
            "tangle_80": 0.80,
            "tangle_90": 0.90,
            "tangle": 1.0,
        }
        if kind in tangle_blends:
            from rl_move.safety import AXIS_LIMITS_DEG
            q_random = np.array(
                [env.rng.uniform(*AXIS_LIMITS_DEG[j % 3])
                 for j in range(N_JOINTS)], dtype=float) * DEG2RAD
            q_start = tangle_blends[kind] * q_random
        elif kind == "zero":
            q_start = env.rng.uniform(
                -2.0, 2.0, N_JOINTS) * DEG2RAD
        elif kind in ("partial", "crouch", "crouch_shallow",
                      "crouch_mid", "crouch_deep", "partial_high",
                      "partial_mid", "partial_low"):
            from rl_move.body_ik import BodyOffset
            crouch_ranges = {
                "crouch_shallow": (0.010, 0.025),
                "crouch_mid": (0.025, 0.045),
                "crouch_deep": (0.045, 0.070),
            }
            depth = (float(env.rng.uniform(*crouch_ranges[kind]))
                     if kind in crouch_ranges
                     else float(env.rng.uniform(0.03, 0.07)))
            any_ik = FixedFootBodyIK()
            any_ik.reset(env._plant_deg * DEG2RAD)
            res = any_ik.solve(BodyOffset(
                height=-depth))
            q_c = (res.q_rad if res.ok
                   else env._plant_deg * DEG2RAD)
            partial_ranges = {
                "partial_high": (0.70, 0.95),
                "partial_mid": (0.40, 0.70),
                "partial_low": (0.15, 0.40),
            }
            f = (1.0 if kind in ("crouch", "crouch_shallow",
                                 "crouch_mid", "crouch_deep")
                 else float(env.rng.uniform(
                     *partial_ranges.get(kind, (0.10, 0.90)))))
            # Zero pose is exactly q=0, so the belly->crouch blend
            # is a plain scale (same construction as rise bridge).
            q_start = f * np.asarray(q_c, dtype=float)
        elif kind == "plant_catch":
            # First backward-curriculum rung: already at the goal
            # neighborhood, but the controller must catch and hold
            # plant for the full success dwell instead of receiving
            # a free terminal reward at reset.
            q_start = (env._plant_deg * DEG2RAD).copy()
            q_start += env.rng.uniform(
                -2.0, 2.0, N_JOINTS) * DEG2RAD
        elif kind == "park":
            q_start = (env._plant_deg * DEG2RAD).copy()
            tripod = ((1, 3, 5) if env.rng.random() < 0.5
                      else (0, 2, 4))
            for leg in tripod:
                q_start[joint_index(leg, "hip")] -= float(
                    env.rng.uniform(10.0, 25.0)) * DEG2RAD
                q_start[joint_index(leg, "knee")] += float(
                    env.rng.uniform(-5.0, 10.0)) * DEG2RAD
        elif kind in ("onefoot_micro", "onefoot_mid", "onefoot"):
            # Progressive one-foot correction rungs.  They use the
            # same construction and differ only in disturbance
            # magnitude, so promotion measures a real expansion of
            # the solved basin instead of a task-definition switch.
            q_start = (env._plant_deg * DEG2RAD).copy()
            leg = int(env.rng.integers(6))
            if kind == "onefoot_micro":
                hip_deg = env.rng.uniform(3.0, 8.0)
                knee_deg = env.rng.uniform(-1.0, 3.0)
            elif kind == "onefoot_mid":
                hip_deg = env.rng.uniform(8.0, 15.0)
                knee_deg = env.rng.uniform(-3.0, 6.0)
            else:
                hip_deg = env.rng.uniform(15.0, 30.0)
                knee_deg = env.rng.uniform(-5.0, 12.0)
            q_start[joint_index(leg, "hip")] -= float(
                hip_deg) * DEG2RAD
            q_start[joint_index(leg, "knee")] += float(knee_deg) * DEG2RAD
        elif kind in ("repair_one", "repair_two"):
            # Terminal contact-repair rungs. Keep the chassis on a
            # plant support polygon while one/two legs begin folded
            # and laterally misplaced. Unlike the early one-foot
            # rungs, yaw is wrong too: merely lowering the hip cannot
            # satisfy footprint + six-load success, so the policy must
            # identify and deliberately re-place the missing foot.
            q_start = (env._plant_deg * DEG2RAD).copy()
            n_bad = 1 if kind == "repair_one" else 2
            first = int(env.rng.integers(6))
            if n_bad == 1:
                legs = (first,)
            else:
                # Adjacent lifted pairs put the four remaining feet
                # on one side and collapse the chassis during limp
                # settle. Non-adjacent pairs retain a true four-foot
                # support polygon, matching the quiet B14 failures.
                candidates = [leg for leg in range(6)
                              if leg != first
                              and (leg - first) % 6 not in (1, 5)]
                legs = (first, int(env.rng.choice(candidates)))
            for leg in np.asarray(legs, dtype=int):
                sign = -1.0 if env.rng.random() < 0.5 else 1.0
                q_start[joint_index(leg, "yaw")] += sign * float(
                    env.rng.uniform(15.0, 35.0)) * DEG2RAD
                # The quadstance feasibility sweep's tucked claw is
                # known to stay clear while the other four feet form
                # a support polygon. Small jitter keeps this a family,
                # not one memorized target.
                q_start[joint_index(leg, "hip")] = (
                    _QUAD_TUCK_ROBOT_RAD[1]
                    + env.rng.uniform(-3.0, 3.0) * DEG2RAD)
                q_start[joint_index(leg, "knee")] = (
                    _QUAD_TUCK_ROBOT_RAD[2]
                    + env.rng.uniform(-4.0, 4.0) * DEG2RAD)
        elif kind == "bank":
            # RECOVER family 2: harvested post-lower/interrupted
            # poses (goal.recover_start_bank npz, key q_rad
            # (K,18)). Placement + slip/limp settle produce a
            # physically consistent start; the exact-qvel restore
            # is CPU-only (family-5 falling velocities are the
            # pre-registered next rung).
            bank = env._recover_start_bank()
            if bank is None:
                raise ValueError("start_kind 'bank' requires "
                                 "goal.recover_start_bank")
            q_start = bank[int(env.rng.integers(len(bank)))].copy()
            q_start += env.rng.uniform(
                -2.0, 2.0, N_JOINTS) * DEG2RAD
        elif kind == "flip":
            # Final recovery rung: random legal joints plus a base
            # rotation about a
            # random horizontal axis, applied by _place_at_plant
            # (consume-once pending quat, both C and MJX paths go
            # through place_env -> _place_at_plant), then the
            # slip/limp settle drops it however it lands. Runs
            # enabling this kind must widen safety.max_roll/
            # pitch_deg to ~179 (a fall is a recoverable state).
            from rl_move.safety import AXIS_LIMITS_DEG
            q_start = np.array(
                [env.rng.uniform(*AXIS_LIMITS_DEG[j % 3])
                 for j in range(N_JOINTS)], dtype=float) * DEG2RAD
            ax_ang = float(env.rng.uniform(0.0, 2.0 * math.pi))
            ang = float(env.rng.uniform(90.0, 180.0)) * DEG2RAD
            ax = (math.cos(ax_ang), math.sin(ax_ang), 0.0)
            half = ang / 2.0
            s = math.sin(half)
            env._flip_spawn_pending = (
                math.cos(half), ax[0] * s, ax[1] * s, ax[2] * s)
        else:  # "plant"
            q_start = (env._plant_deg * DEG2RAD).copy()
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._clip_to_joint_limits(q_start)
        # Recovery episodes anchor tilt obs/trip/reward to LEVEL
        # (gravity truth), like tipped starts: the task is to
        # level out from wherever the spawn settled, never to hold
        # the spawn lean. Runs enabling this mode must widen
        # safety.max_roll/pitch_deg — a fall is a recoverable
        # state here, not a termination.
        env._tipped_applied = True
    elif start_at == "park":
        # Tripod-park start (walk reset diversity, cycle 24): plant
        # pose with one alternating tripod's hips lifted 10-25 deg
        # (feet hover ~15-45 mm — the park attractor observed on
        # camera, duty ~[0.9,0.1,0.9,0.1,0.9,0.1]) plus small knee
        # jitter. The policy must step OUT of the park to earn; see
        # walk_task._sample_walk for the rationale.
        q_start = (env._plant_deg * DEG2RAD).copy()
        tripod = (1, 3, 5) if env.rng.random() < 0.5 else (0, 2, 4)
        for leg in tripod:
            q_start[joint_index(leg, "hip")] -= float(
                env.rng.uniform(10.0, 25.0)) * DEG2RAD
            q_start[joint_index(leg, "knee")] += float(
                env.rng.uniform(-5.0, 10.0)) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._apply_tipped_start(q_start)
        q_start = env._clip_to_joint_limits(q_start)
    elif start_at == "quadstance":
        # QUADWALK four-leg spawn (08-13, quad track; opt-in via
        # cfg goal.quadwalk_start="quad", see
        # walk_task._sample_quadwalk). Mid feet splayed forward
        # (0.06 m — the bare
        # plant+tuck stance pitch-trips in <1 s, CoM ahead of the
        # 4-foot polygon front edge; the splayed form is the
        # QUADWALK bank's own statically-surviving freeze stance),
        # commanded lift legs pre-folded into the feasibility
        # sweep's "tuck" claw. Episodes begin INSIDE the fronts-up
        # stance the policy already knows from quad-hold, so
        # rear-four stepping is the reachable behavior and six-leg
        # walking requires actively planting the charged fronts.
        # +-2 deg jitter matches the gait/park spawn convention.
        # Reached only from quadwalk trajectories, so no legacy
        # rng stream can be perturbed.
        from hexapod_core.tripod_gait import TripodGait
        g = TripodGait()
        g.sync_plant_stance(float(env._plant_deg[1]),
                            float(env._plant_deg[2]))
        _orig = g._foot_target_in_body

        def _splayed(i, vx, vy, om, _o=_orig, _s=0.06):
            dx, dy, dz = _o(i, vx, vy, om)
            if i in (1, 4):
                dx += _s
            return (dx, dy, dz)
        g._foot_target_in_body = _splayed
        g.set_velocity(vx=0.0, vy=0.0)
        g.reset_phase()
        q_start = np.asarray(g.desired_deg(0.0), dtype=float) * DEG2RAD
        lift = tuple(getattr(env._goal_traj, "lift_legs", None)
                     or (0, 5))
        for leg in lift:
            q_start[leg_slice(leg)] = _QUAD_TUCK_ROBOT_RAD
        q_start += env.rng.uniform(-2.0, 2.0, N_JOINTS) * DEG2RAD
        if env._ep_rand is not None:
            q_start = q_start + env._ep_rand.start_offset_rad
        q_start = env._apply_tipped_start(q_start)
        q_start = env._clip_to_joint_limits(q_start)
        # The limp-settle stage passively pitches this front-back-
        # asymmetric stance nose-down onto the tucked claws (~15-17
        # deg) before the servos engage; anchoring the tilt ref at
        # that sagged attitude would (a) train the policy to HOLD
        # the sag and (b) trip tilt_pitch the moment it LEVELS by
        # more than the envelope (measured: recovery to 6 deg
        # tripped at |6-16.6|>10). Keep the reference LEVEL like
        # tipped starts / "any" recovery spawns, so the attitude
        # terms pay leveling out. Runs enabling this spawn must
        # widen safety.max_roll/pitch_deg past the sag transient
        # (the deployment-contract 25 deg envelope covers it),
        # same contract as the getup "any" starts.
        env._tipped_applied = True
    else:
        q_start = env._clip_to_joint_limits(
            env._apply_tipped_start(env._start_pose_rad()))
    return q_start


def reset_gravity_ease(env):
    """Physics easing: this episode's gravity scale (ease.gravity_scale and
    its DR band); moved verbatim from SimHexapodBalanceEnv._reset_begin.
    """
    # Physics easing (see __init__): scale this episode's gravity
    # by the CURRENT cfg value, so an active sched.* ramp moves the
    # physics episode-by-episode.
    # Batched-pool note: pooled resets restore entries minted at
    # choreography time, so under an active schedule an episode's
    # eased physics can lag the schedule by up to the pool depth
    # (a few episodes) — end easing schedules at v1=1.0 (nominal)
    # and judge scheduled runs on measured behavior metrics.
    env._ease_g = 1.0
    # Saved pre-easing originals (only populated when the _ep_rand
    # mutation branch below actually runs) so the new
    # ease.rise_flat_only gate (see the _is_rise block further
    # down, once start_kind is known) can UNDO the easing on
    # episodes that don't qualify, without re-deriving the
    # unscaled values from scratch.
    env._ease_orig_gravity_vec = None
    # ease.gravity_scale_dr_{lo,hi} (2026-09-14, walkcurr flat-start-
    # rise gravity-ANNEAL grid closure): the pre-existing
    # sched.*-driven ease.gravity_scale ramp is a single GLOBAL
    # value shared by every one of the run's parallel envs at a
    # given tick (sched.n_envs converts local ticks to one process-
    # wide "global step" clock) -- a sequential curriculum that
    # only ever contains the easy end early and the hard end late.
    # The 3-arm anneal grid (anneal4m/anneal8m/anneal8m-lowlr, all
    # warm-started off the eased-gravity flat-start-rise PASS
    # snapshot s1048576) closed 3/3 at TRUE nominal gravity this
    # cycle: anneal4m stagnated (SEED-PRUNED), anneal8m forgot the
    # skill by 2M steps of ramp, anneal8m-lowlr merely forgot more
    # slowly (retained the 0.4g behavior through all 11M steps) but
    # its own explicit nominal-gravity probe (ease/sched stripped,
    # true g, n=12 det+sto) still reads 0/12, identical over_current
    # fingerprint to the un-annealed baseline -- despite the
    # schedule having reached v1=1.0 by step 8.5M, 2.5M steps
    # before the run ended. A synchronized global ramp forgets the
    # easy end wholesale once it passes, whether slowly (low LR) or
    # quickly (default LR); it never actually verified the policy
    # could do the flat-start task at nominal gravity DURING
    # training, only that it could recite the eased-gravity
    # solution. This is a genuinely different mechanism, not
    # another anneal dose: each EPISODE independently samples its
    # OWN gravity scale uniform in [lo, hi] (via the same per-env
    # self.rng already used for every other DR axis), so the batch
    # trains on a persistent MIXTURE of easy and hard gravity every
    # single step throughout the run -- the easy end is never fully
    # retired, and the policy is directly, continuously evaluated
    # (via its own reward) at the hard end the whole time instead of
    # only after a ramp completes. Default OFF (both keys unset) is
    # bit-exact: falls through to the existing single-value
    # ease.gravity_scale/sched.* path below, completely untouched.
    # Setting only one of the pair or a non-positive/inverted range
    # raises loudly (mirrors the existing ease.* validation below,
    # which fires unconditionally on whatever _e_g this block
    # produces). Composes with ease.rise_flat_only exactly like the
    # single-value case: the scoping gate downstream (once
    # start_kind is known) undoes today's episode's draw uniformly,
    # same as it already undoes a scheduled value.
    _e_g_dr_lo = cfg_get(env.cfg, "ease", "gravity_scale_dr_lo",
                         default=None)
    _e_g_dr_hi = cfg_get(env.cfg, "ease", "gravity_scale_dr_hi",
                         default=None)
    if _e_g_dr_lo is not None or _e_g_dr_hi is not None:
        if _e_g_dr_lo is None or _e_g_dr_hi is None:
            raise ValueError(
                "ease.gravity_scale_dr_lo/hi must both be set "
                f"(got lo={_e_g_dr_lo!r} hi={_e_g_dr_hi!r})")
        _e_g_dr_lo = float(_e_g_dr_lo)
        _e_g_dr_hi = float(_e_g_dr_hi)
        if not (0.0 < _e_g_dr_lo <= _e_g_dr_hi):
            raise ValueError(
                "ease.gravity_scale_dr_lo/hi must satisfy "
                f"0 < lo <= hi, got lo={_e_g_dr_lo} hi={_e_g_dr_hi}")
        _e_g = (float(env.rng.uniform(_e_g_dr_lo, _e_g_dr_hi))
                if _e_g_dr_lo < _e_g_dr_hi else _e_g_dr_lo)
    else:
        _e_g = float(cfg_get(env.cfg, "ease", "gravity_scale",
                             default=1.0))
    if _e_g != 1.0:
        if _e_g <= 0.0:
            raise ValueError("ease.* scales must be > 0, got "
                             f"gravity={_e_g}")
        if env._ep_rand is not None:
            env._ease_orig_gravity_vec = np.asarray(
                env._ep_rand.gravity_vec, float).copy()
            env._ep_rand.gravity_vec = (
                env._ease_orig_gravity_vec * _e_g)
        elif env._owns_model:
            # randomize=False private-model env (eval harness at
            # DR-0, viewers): reset() applies the same scale
            # directly to the model.
            env._ease_g = _e_g
        else:
            raise ValueError(
                "ease.* on a shared-model shim env needs "
                "randomize=True (dr_scale may be 0): the batched "
                "path can only ease gravity through per-world "
                "model-DR fields")


def reset_mode_seq_and_goal(env):
    """Mode-sequence episode state, goal-trajectory sampling, start kind
    and the ease.rise_flat_only undo; moved verbatim from
    SimHexapodBalanceEnv._reset_begin.
    """
    # Mode-sequencing episode state (goal.mode_seq, TRANSITIONS_
    # DIRECTIVE CODE item 1). Cleared BEFORE _sample_goal so the
    # planner (walk_task._sample_mode_seq) can repopulate it; all
    # five ride mjx_host.SNAP_ATTRS (pool-restore lesson). None/0
    # defaults = legacy bit-exact (the switch hook is a single
    # attr check per tick and no rng is ever drawn).
    env._seq_plan = None          # [{mode, tick, blend}, ...]
    env._seq_idx = 0              # index of the ACTIVE segment
    env._seq_stand_z = None       # abs z of the last commanded stand
    env._seq_seg_end = None       # active segment's end tick
    env._seq_pose_anchor = None   # hold/lower BC base pose mid-seq
    # Active segment's own start tick (manual-drive-session-s1
    # dig-in, 08-28: the *_grace_s windows below were all gated on
    # the EPISODE-absolute clock `self._step_i * self.dt`, so any
    # mid-sequence segment starting after its own grace window had
    # already elapsed on the episode clock got ZERO grace — a
    # mode_seq session's mid-episode hold entry tripped
    # hold_min_load in ~1.4s (operator manual-drive REPORT.md
    # finding #3), reproduced live: episode-relative t already
    # exceeds hold_height_grace_s/hold_min_load_terminate_grace_s
    # (~1s) the moment a later segment starts. Fixed by measuring
    # grace against SEGMENT-relative elapsed time instead (below).
    # Stays 0 for the whole episode when goal.mode_seq is off (no
    # switches ever happen), so every non-mode_seq config/recipe
    # is bit-exact — this is a bugfix to the existing grace
    # mechanism's intent, not a new one.
    env._seg_entry_step = 0

    # Goal first: it decides the reset pose. Rise episodes start at
    # the ZERO pose — legs straight out, belly resting on the yaw
    # servos, exactly how the operator places the robot — and must
    # curl the legs in and stand. Everything else starts at the plant.
    env._goal_traj = env._sample_goal()
    start_at = ("plant" if env._goal_traj is None
                else getattr(env._goal_traj, "start_at", "plant"))
    # ease.rise_flat_only (2026-09-14, walkcurr flat-start-rise
    # 22/22-closed-lever escalation): scope the pre-existing
    # generic ease.gravity_scale physics-easing
    # mechanism (08-13, GAIT.md P3 lever 3, built for a different
    # track's early-training ignition and used so far only as a
    # STATIC whole-run setting) to ONLY the hardest, still-unsolved
    # start_kind='flat' rise episodes -- a genuinely new mechanism
    # FAMILY on this residual (dynamics-parameter easing), distinct
    # from every already-closed cap/reward-pricing/reset-timing/
    # leg-order/batch-composition lever (22/22 null, STATUS
    # 2026-09-14 ~08:3x). Rationale: the 03:1x root-cause read
    # showed a mesh-native OPEN-LOOP tuck-then-press clears rise at
    # 2.21A (11% margin under the 2.5A trip) -- over_current is an
    # RL sequencing/exploration problem, not a physics ceiling, so
    # temporarily easing gravity (lower effective weight to push
    # against during exploration) may let PPO discover the correct
    # low-current curl-then-lift KINEMATIC sequence without
    # tripping the cap, while non-flat episodes (bridge/crouch/
    # walk/hold/lower -- all already solved) keep training at
    # nominal physics so the fix can't be a free lunch that quietly
    # trades away already-closed behavior. Default OFF (key unset
    # or 0.0) is bit-exact: the pre-existing unconditional
    # ease.gravity_scale behavior above is
    # completely untouched. When ON and this episode does NOT
    # qualify (not rise, or rise but not a flat start), UNDOES any
    # easing the block above already applied, restoring the exact
    # pre-easing values so those episodes are bit-exact nominal.
    #
    # MUST run HERE (inside _reset_begin, right after the goal is
    # known) and NOT later in _reset_finalize (where self._is_rise
    # is normally set): this method's caller (reset()) calls
    # self._ep_rand.apply_to_model(...), which is what actually
    # copies _ep_rand.gravity_vec onto model.opt.gravity, almost
    # immediately after _reset_begin returns and LONG before
    # _reset_finalize ever runs. A first version of this gate lived
    # in _reset_finalize and correctly reverted _ep_rand.gravity_vec
    # on paper, but apply_to_model had already baked the EASED
    # value into model.opt.gravity by then, so gravity easing
    # silently leaked into every non-flat-rise episode (hold/
    # bridge/crouch/walk/lower) despite the field-level revert
    # looking right in isolation -- found this cycle via a direct
    # model.opt.gravity vs _ep_rand.gravity_vec comparison after
    # the mod/strict canaries both showed an unexplained hold-
    # canary regression vs their own parent. _goal_traj.mode/
    # start_kind_of are used directly (self._is_rise doesn't exist
    # yet at this point in _reset_begin).
    if float(cfg_get(env.cfg, "ease", "rise_flat_only",
                      default=0.0)) == 1.0 and not (
            env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") == "rise"
            and start_kind_of(env._goal_traj) == "flat"):
        env._ease_g = 1.0
        if env._ep_rand is not None:
            if env._ease_orig_gravity_vec is not None:
                env._ep_rand.gravity_vec = (
                    env._ease_orig_gravity_vec)
    return start_at
