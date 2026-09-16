"""BC-anchor target emission of the balance env's _step_finish (rise
reference, getup, recover, hold/track and lower branches), moved
verbatim out of sim_env.py.
"""
from __future__ import annotations

import math
import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import DEG2RAD, N_JOINTS

from .balance_helpers import load_rise_ref


def bc_anchor_target(env, info):
    """info["bc_target"/"bc_mode"/...] emission; moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # BC-anchor target (rl_move/sim/bc_anchor.py; RL_PLAN queue 2a,
    # operator 08-11 — the rise lever AFTER all reward-side levers
    # closed). For every rise tick with a live reference clock,
    # emit the normalized action whose joint target is the
    # reference pose one ref-tick ahead; the trainer's aux loss
    # pulls pi_mean(obs) toward it. NOT a reward term — reward
    # above is untouched and the rise semantics bank is unaffected.
    # Emitted only when the trainer asked (train.bc_anchor_coef
    # rides into the env cfg, same pattern as mirror_loss_coef)
    # and only on raw-18-joint tasks (the inverse action map is
    # joint_task's per-axis affine). Uses only per-episode attrs
    # already in mjx_host.SNAP_ATTRS (_rsi_ref_tick0,
    # _rise_ramp_i0, _step_i) — pool-restore safe by construction.
    _bc_coef = float(cfg_get(env.cfg, "train", "bc_anchor_coef",
                             default=0.0))
    if (env._is_rise and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0):
        _bc_ref_path = cfg_get(env.cfg, "reward", "rise_ref_path",
                               default=None)
        if _bc_ref_path:
            from .joint_task import q_rad_to_action
            _bc_ref = load_rise_ref(str(_bc_ref_path))
            # STATE-ALIGNED indexing (2026-08-11, cfg
            # train.bc_anchor_state_aligned, default 0 = legacy
            # clock-exact). The crouchrise1/2/3 + holdload1 chain
            # isolated the anchor as the sole remaining suspect for
            # the legs-1+4 hover-park: holdload1 kept the park at a
            # measured 4x hold-income loss, so the pose is TAUGHT,
            # not paid for. Mechanism: non-RSI crouch starts
            # time-align the clock at the BELLY ramp start
            # (_rise_ref_clock), so a robot sitting plant-adjacent
            # is supervised toward early-path lifted-leg poses —
            # and pi generalizes that obs->action association into
            # hold. State-aligned mode re-indexes every tick by
            # nearest reference pose to the CURRENT joints (the
            # identical RMS nearest-neighbor _reset_finalize
            # already trusts for RSI spawns): plant-adjacent
            # states can then only ever anchor toward the path's
            # planted tail, sagged states get "climb from where
            # you ARE", and the target stays one ref-tick ahead as
            # before. Reads only current qpos + the cached ref —
            # no per-episode state, pool-restore safe. The
            # rise-ref TRACKING REWARD keeps the shared clock
            # (semantics banks untouched; its income is
            # grounded-feet-gated so it cannot fund flag poses).
            # FLAT-START ABSOLUTE SCRIPT CLOCK (08-25, tucklook1
            # dig-in / probe_stance_pricing replay_script rows).
            # The whole 15-arm anchor-plumbing campaign (floors,
            # exemptions, script-index lookaheads) chased pursuit-
            # target geometry, but the measured optimum was TIMING:
            # replaying the mesh scripted ref on ITS OWN CLOCK from
            # a flat start earns +2021 (plant_ok, Imax 0.575A, no
            # over_current — the honest tuck sweep makes the press
            # nearly effortless) under the exact launched pricing
            # where every pursuit-taught behavior lands at -50..-770
            # (freeze -704, 2.64A ramp-aligned catch-up press -706
            # WITH an over_current trip). Nothing in the stack ever
            # supervised that timing: state-aligned pursuit lets
            # the matched index stall (freeze), while the legacy
            # ramp-aligned clock starts at ref ramp_i0 minus the
            # env's OWN hold window (~0.5s), skipping ~2s of the
            # 2.45s tuck and slamming the press. When
            # train.bc_anchor_flat_time_indexed > 0 and the episode
            # is a PURE FLAT rise start (non-RSI, start_at "zero",
            # start_curl 0 — the script's own start state, where
            # absolute time is honest), index the anchor by the
            # EPISODE's absolute clock (row 0 at t=0, one env tick
            # ahead, exactly the +2021 replay): the target advances
            # by itself, so a freeze accumulates loss instead of
            # converging on it. Every other start kind (partial,
            # crouch, bridge probes, rsi, bank) keeps state-aligned
            # pursuit unchanged — mid-path states have no honest
            # absolute clock. Reads only _step_i/_goal_traj/
            # _rsi_ref_tick0 (all SNAP_ATTRS) — pool-restore safe.
            # Default 0 = off, bit-exact.
            _bc_gt = env._goal_traj
            _bc_flat_clock = (
                float(cfg_get(env.cfg, "train",
                              "bc_anchor_flat_time_indexed",
                              default=0.0)) > 0.0
                and env._rsi_ref_tick0 is None
                and getattr(_bc_gt, "start_at", None) == "zero"
                and float(getattr(_bc_gt, "start_curl", 0.0)
                          or 0.0) == 0.0)
            if _bc_flat_clock:
                _bc_j = min(int(round(
                    env._step_i * env.dt / _bc_ref["dt"])),
                    len(_bc_ref["q"]) - 1)
                _bc_ahead = max(
                    int(round(env.dt / _bc_ref["dt"])), 1)
            elif float(cfg_get(env.cfg, "train",
                             "bc_anchor_state_aligned",
                             default=0.0)) > 0.0:
                _bc_qnow = env._mujoco_to_logical_q(
                    env.data.qpos[env._qadr])
                _bc_j = int(np.argmin(
                    ((_bc_ref["q"] - _bc_qnow[None, :]) ** 2)
                    .mean(axis=1)))
                # Pursuit lookahead: "one tick ahead of where you
                # ARE" stalls (the servo never fully converges
                # within a tick, so the matched index crawls —
                # measured 1 ref tick per 60 chained steps); the
                # lookahead must exceed the tracking lag. The
                # legacy clock never needed this because it
                # advances on its own.
                _bc_ahead = max(int(round(float(cfg_get(
                    env.cfg, "train", "bc_anchor_lookahead_s",
                    default=0.25)) / _bc_ref["dt"])), 1)
                # HEIGHT-FLOOR pursuit (08-12, cw-stand-footlow1
                # dig-in / probe_anchor_align): a TIME lookahead
                # degenerates to a near-zero POSE lookahead inside
                # the reference's low prep segment — this ref
                # spends 5+ s (ticks ~126-250) crawling 0->25 mm,
                # so at a stalled ~7 mm belly state the +0.5 s
                # target commands a pose only 1-5 mm higher and
                # the loaded-servo tracking sag (~0.3 s settle)
                # cancels it: the matched index PINS (measured:
                # j=128-133, 0 ticks advance over 3 s) while the
                # anchor loss reads low/converged — the anchor
                # actively supervises the stall. When
                # train.bc_anchor_min_h_ahead_mm > 0, additionally
                # require the target tick to command at least that
                # many mm above the chassis's CURRENT height
                # (first such tick at/after the match; path end if
                # none) — in flat segments the pursuit skips ahead
                # to where the reference genuinely climbs, in
                # steep segments the time lookahead already
                # satisfies it and nothing changes. Default 0 =
                # off, bit-exact. Needs ref["h"] (newer extracts;
                # absent -> floor is a no-op, time lookahead
                # unchanged). Stateless — pool-restore safe.
                _bc_min_h = float(cfg_get(
                    env.cfg, "train", "bc_anchor_min_h_ahead_mm",
                    default=0.0))
                # TUCK-EXEMPT floor (08-25, tuckfloor0 FAIL-MECH
                # follow-up): the mesh-native scripted rise ref's
                # tuck segment (ticks 0..ramp_i0) is height-flat by
                # design (belly carries the mass while feet sweep
                # to the plant footprint), so the floor above
                # always jumps a flat/tuck-matched state straight
                # to the press phase, skipping tuck supervision
                # entirely (measured: flatmix70/-s1, 0/12 flat
                # valid, 2.64A never-tucks press-up). Turning the
                # floor off everywhere (tuckfloor0/-s1) does not
                # recover the tuck either — it collapses BOTH flat
                # AND previously-clean bridge/crouch/rsi starts
                # into a NEW all-six-leg duty_cycle=0 total freeze
                # (measured: both seeds' flat probe 0/12 valid,
                # zero over_current, zero swings, height_err stuck
                # 79-86mm; standard DR-0 gate collapsed to 0/6+0/6
                # from meshref's 5/6+4/6, with new freezes mixed
                # into the surviving 2.64A pins) — the floor's
                # press-phase anti-stall role (its ORIGINAL 08-12
                # purpose) was load-bearing and got thrown out with
                # its flat-segment defect. When
                # train.bc_anchor_min_h_tuck_exempt_i0 > 0, gate the
                # floor on the matched index already being at/past
                # the reference's OWN tuck/press boundary
                # (``ref["ramp_i0"]``, a fixed property of the
                # reference file, not the episode clock): the tuck
                # segment gets pure time-lookahead pursuit (genuine
                # tuck supervision, no skip-ahead), and the press
                # segment keeps the exact legacy anti-freeze floor.
                # Default 0 = legacy (floor active whenever
                # min_h_ahead_mm > 0, regardless of segment) —
                # bit-exact unchanged.
                _bc_tuck_exempt = float(cfg_get(
                    env.cfg, "train",
                    "bc_anchor_min_h_tuck_exempt_i0", default=0.0))
                _bc_floor_active = _bc_min_h > 0.0 and "h" in _bc_ref
                if (_bc_floor_active and _bc_tuck_exempt > 0.0
                        and _bc_j < int(_bc_ref["ramp_i0"])):
                    _bc_floor_active = False
                if _bc_floor_active:
                    _bc_hnow = float(env.data.xpos[
                        env._chassis_bid, 2]) - env._z0
                    _bc_ks = np.flatnonzero(
                        _bc_ref["h"][_bc_j:]
                        >= _bc_hnow + _bc_min_h * 1e-3)
                    _bc_floor = (_bc_j + int(_bc_ks[0])
                                 if len(_bc_ks)
                                 else len(_bc_ref["q"]) - 1)
                    _bc_ahead = max(_bc_ahead, _bc_floor - _bc_j)
                # TUCK SCRIPT-INDEX floor (08-25, tuckrise campaign
                # dig-in follow-up to tuckfloor0/tuckexempt0, both
                # 2/2 seeds FAIL-MECHANISM, and tuckrise15/45's own
                # by-construction refutation of ref-content height-
                # shaping). tuck_exempt above correctly turns the
                # ACHIEVED-HEIGHT floor off inside the tuck (the
                # mesh ref's tuck is height-flat by design, so that
                # floor always measures "haven't climbed yet" and
                # jumps straight to ramp_i0, skipping tuck
                # supervision) — but that leaves ONLY the plain
                # time lookahead (bc_anchor_lookahead_s, default
                # 0.25s) driving pursuit through the tuck, and
                # measured (tuckfloor0/tuckexempt0, 4/4 seeds) that
                # collapses into a total duty=0 freeze: the tuck's
                # own trajectory changes little pose-per-tick, so a
                # 0.25s step barely moves the matched index and the
                # BC target is nearly IDENTICAL to the current pose
                # -> the aux-loss gradient vanishes -> freeze reads
                # as anchor-optimal. FIX: when
                # train.bc_anchor_tuck_lookahead_s > 0 and the
                # matched index is still inside the tuck (< the
                # reference's own fixed ramp_i0), widen the
                # lookahead to this larger value (~1.0-1.5s) purely
                # as a SCRIPT-INDEX offset from wherever the match
                # currently sits — NOT keyed to achieved height at
                # all, so unlike the height floor it cannot get
                # stuck measuring a frozen achieved height: it
                # always advances relative to the CURRENT MATCH,
                # guaranteeing a real pose delta (and thus gradient)
                # even through a height-flat segment. Composes with
                # the height floor via max() — if the height floor
                # is still active in-tuck (tuck_exempt=0) its own
                # (typically larger, jump-to-ramp_i0) target wins,
                # so this lever only changes behavior when paired
                # with tuck_exempt=1. Default 0 = off, bit-exact.
                _bc_tuck_ahead_s = float(cfg_get(
                    env.cfg, "train",
                    "bc_anchor_tuck_lookahead_s", default=0.0))
                if (_bc_tuck_ahead_s > 0.0
                        and _bc_j < int(_bc_ref["ramp_i0"])):
                    _bc_ahead = max(_bc_ahead, int(round(
                        _bc_tuck_ahead_s / _bc_ref["dt"])))
            else:
                _bc_j, _ = env._rise_ref_clock(_bc_ref)
                _bc_ahead = max(
                    int(round(env.dt / _bc_ref["dt"])), 1)
            _bc_jn = min(_bc_j + _bc_ahead, len(_bc_ref["q"]) - 1)
            info["bc_target"] = q_rad_to_action(
                _bc_ref["q"][_bc_jn]).astype(np.float32)
            info["bc_mode"] = 0    # rise (stratified sampling tag)
    # GETUP BC-anchor target (08-12, cw-getup2-r1 follow-up —
    # RL_PLAN queue; see bc_anchor.py header for the full story).
    # Warm-starting getup from the rise+hold specialist was not
    # enough: env/getup_S declined over training back toward the
    # from-scratch collapse, so the specialist's skill needs an
    # explicit pull, same as rise once needed. Cfg-gated by
    # train.bc_anchor_getup (default 0 = off, bit-exact). Reuses
    # the rise reference demo but ALWAYS state-aligned (nearest
    # reference pose to CURRENT joints) — getup starts are
    # arbitrary (belly/tangle/crouch/park/...), so there is no
    # live clock to time-align a fixed-index target to; a
    # clock-exact target here would repeat the exact
    # plant-adjacent-supervised-toward-early-path mistake the rise
    # lever's state-aligned mode was built to fix.
    elif (getattr(env, "_is_getup", False)
            and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0
            and float(cfg_get(env.cfg, "train", "bc_anchor_getup",
                              default=0.0)) > 0.0):
        _bc_ref_path = cfg_get(env.cfg, "reward", "rise_ref_path",
                               default=None)
        if _bc_ref_path:
            from .joint_task import q_rad_to_action
            _bc_ref = load_rise_ref(str(_bc_ref_path))
            _bc_qnow = env._mujoco_to_logical_q(
                env.data.qpos[env._qadr])
            _bc_j = int(np.argmin(
                ((_bc_ref["q"] - _bc_qnow[None, :]) ** 2)
                .mean(axis=1)))
            _bc_ahead = max(int(round(float(cfg_get(
                env.cfg, "train", "bc_anchor_lookahead_s",
                default=0.25)) / _bc_ref["dt"])), 1)
            _bc_jn = min(_bc_j + _bc_ahead, len(_bc_ref["q"]) - 1)
            info["bc_target"] = q_rad_to_action(
                _bc_ref["q"][_bc_jn]).astype(np.float32)
            info["bc_mode"] = 4    # getup
    # RECOVER BC-anchor target (08-15 directive: "preserve the
    # explicit state-aligned getup BC anchor that made cw-getup3
    # work; apply it on MASTERED rise/plant states so the
    # inherited skill cannot decay", with matching conditioned on
    # orientation/height/contact — not nearest-q alone). Same
    # nearest-q + lookahead emit as getup, but ELIGIBILITY-GATED:
    # the target only fires when the body is upright-ish (true
    # tilt <= 25 deg), at/below plant
    # height (no stilt supervision), and with real ground reaction
    # through the feet — a side/back/flipped robot is never pulled
    # toward rise poses it cannot reach from there. Cfg-gated by
    # train.bc_anchor_recover (default 0 = off, bit-exact).
    elif (getattr(env, "_is_recover", False)
            and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0
            and float(cfg_get(env.cfg, "train",
                              "bc_anchor_recover",
                              default=0.0)) > 0.0):
        info["recover_bc_eligible"] = 0.0
        _bc_ref_path = cfg_get(env.cfg, "reward", "rise_ref_path",
                               default=None)
        if _bc_ref_path:
            _r, _p = env._true_roll_pitch()
            _tilt = max(abs(_r), abs(_p)) * 180.0 / math.pi
            _touch_n = 0.0
            for _f in range(6):
                _adr = env._touch_adr[_f]
                if _adr >= 0:
                    _touch_n += max(
                        float(env.data.sensordata[_adr]), 0.0)
            _z_now = float(env.data.xpos[env._chassis_bid, 2])
            _z_pl, _ = env._getup_geom()
            if (_tilt <= 25.0 and _touch_n >= 0.5
                    and _z_now <= _z_pl + 0.02):
                info["recover_bc_eligible"] = 1.0
                from .joint_task import q_rad_to_action
                _bc_ref = load_rise_ref(str(_bc_ref_path))
                _bc_qnow = env._mujoco_to_logical_q(
                    env.data.qpos[env._qadr])
                _bc_dist = ((_bc_ref["q"] - _bc_qnow[None, :]) ** 2
                            ).mean(axis=1)
                # Recover starts span belly to plant height.  Nearest-q
                # alone was known to match a parked near-plant leg to a
                # low, slow part of the rise reference.  Restrict the
                # pose match to reference frames near the current
                # absolute belly->plant height whenever h_rel_m exists;
                # upright/contact eligibility above supplies the other
                # two state dimensions from the directive.
                _bc_hnow = None
                if "h" in _bc_ref:
                    _z_belly = 38.0 * 1e-3
                    _bc_hnow = max(_z_now - _z_belly, 0.0)
                    _h_tol = 25.0 * 1e-3
                    _height_rows = np.flatnonzero(
                        np.abs(_bc_ref["h"] - _bc_hnow) <= _h_tol)
                else:
                    _height_rows = np.empty(0, dtype=int)
                if len(_height_rows):
                    _bc_j = int(_height_rows[
                        np.argmin(_bc_dist[_height_rows])])
                else:
                    _bc_j = int(np.argmin(_bc_dist))
                _bc_ahead = max(int(round(float(cfg_get(
                    env.cfg, "train", "bc_anchor_lookahead_s",
                    default=0.25)) / _bc_ref["dt"])), 1)
                # Carry the proven footlow2 height-floor pursuit into
                # recovery.  Use absolute height above the belly datum,
                # not height above this episode's spawn (_z0): a
                # near-goal recovery starts are already near standing.
                _bc_min_h = float(cfg_get(
                    env.cfg, "train", "bc_anchor_min_h_ahead_mm",
                    default=0.0))
                if (_bc_min_h > 0.0 and "h" in _bc_ref
                        and _bc_hnow is not None):
                    _bc_ks = np.flatnonzero(
                        _bc_ref["h"][_bc_j:]
                        >= _bc_hnow + _bc_min_h * 1e-3)
                    _bc_floor = (_bc_j + int(_bc_ks[0])
                                 if len(_bc_ks)
                                 else len(_bc_ref["q"]) - 1)
                    _bc_ahead = max(_bc_ahead, _bc_floor - _bc_j)
                _bc_jn = min(_bc_j + _bc_ahead,
                             len(_bc_ref["q"]) - 1)
                info["bc_target"] = q_rad_to_action(
                    _bc_ref["q"][_bc_jn]).astype(np.float32)
                info["bc_mode"] = 6    # recover
                info["recover_bc_ref_index"] = float(_bc_j)
                info["recover_bc_target_index"] = float(_bc_jn)
    # HOLD/TRACK BC-anchor target (RL_PLAN queue 2.3, 08-11): the
    # rise lever repeated after two hold pricing misses (hard zero,
    # then a linear fade) neither reached a quiet plant. Hold/track
    # have no moving reference to chase, so the target is simply
    # the pose the episode actually settled at — self._q_nom,
    # already captured post-settle in _reset_finalize for the
    # hold-current reward term ("trivially available", RISE.md)
    # and already in mjx_host.SNAP_ATTRS. Constant for the whole
    # episode: this literally IS "stand still right here".
    elif (env._is_hold_bc and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0):
        from .joint_task import q_rad_to_action
        # Mode-seq hold segments anchor at the pose carried INTO
        # the segment (_seq_pose_anchor, captured at the switch);
        # None outside mode_seq = the legacy settled q_nom.
        _q_hold_base = (env._q_nom
                        if getattr(env, "_seq_pose_anchor", None)
                        is None else env._seq_pose_anchor)
        # HEIGHT-AWARE HOLD REFERENCE (08-25, train.bc_anchor_
        # hold_height_aware, default 0 = legacy height-BLIND
        # constant-q_nom target, bit-exact). The holdheight-rung1
        # mechanism canary (goal.hold_height_cmd_frac, moving
        # height_ref on hold episodes) trained WITHOUT any pose
        # anchor at all (a moving target would fight the fixed
        # q_nom pose), and lost the champion's clean quiet-stand
        # current/load profile even on the STATIC height_ref=0
        # DR-0 gate (cur_max 2.0-2.63A vs the champion's
        # 0.67-0.71A, 5/6 det episodes tripping hold_min_load) —
        # dropping the anchor entirely threw out its general pose
        # regularization, not just its height-blindness. Fix:
        # re-target the anchor at the pose that reaches the NEXT
        # commanded height (same one-tick-ahead FixedFootBodyIK
        # convention `bc_anchor_lower` already uses), so the
        # anchor keeps supervising pose quality while tracking a
        # moving target instead of fighting it. Only engages on
        # "hold" (not "track", which commands attitude the offset
        # would fight) and only when the commanded height is
        # actually nonzero (bit-exact no-op for
        # hold_height_cmd_frac=0 and the flat legacy hold).
        _hha = float(cfg_get(env.cfg, "train",
                             "bc_anchor_hold_height_aware",
                             default=0.0))
        if (_hha > 0.0 and env._goal_traj is not None
                and env._goal_traj.mode == "hold"):
            _g_next_h = env._goal_traj.at(env._step_i + 1)
            if float(_g_next_h.height_ref) != 0.0:
                from rl_move.body_ik import BodyOffset, FixedFootBodyIK
                _ik_h = FixedFootBodyIK()
                _ik_h.reset(_q_hold_base)
                _res_h = _ik_h.solve(BodyOffset(
                    height=float(_g_next_h.height_ref)))
                if _res_h.ok:
                    _q_hold_base = _res_h.q_rad
        _q_tgt = _q_hold_base
        # TIP-AWARE HOLD REFERENCE (08-13, train.bc_anchor_tilt_comp,
        # default 0 = legacy constant-q_nom target, bit-exact).
        # cw-stand-footlow2-tip1's gate consequence: tipped-start DR
        # with a tilt-BLIND anchor taught the policy to HOLD the
        # lean (target = q_nom regardless of attitude gives zero
        # leveling gradient; joint-space MSE is attitude-blind), and
        # the hardware candidate stands with a persistent ~8deg
        # lean. When enabled, HOLD episodes (not track — track
        # commands attitude goals the compensation would fight)
        # anchor toward the pose that COUNTER-ROTATES the measured
        # lean: FixedFootBodyIK from q_nom with
        # BodyOffset(roll/pitch = -comp * rel_attitude), i.e. a
        # proportional posture-feedback teacher. rel attitude is
        # measured against the episode tilt reference exactly like
        # the tipped-start recovery metric (tipped episodes keep the
        # ref LEVEL, so rel ~= true lean; mount-bias/slope stays
        # inside the ref). Soft deadband keeps the target continuous
        # and leaves settled-level ticks anchored at q_nom; the
        # commanded correction is clipped for IK safety. Solved
        # fresh per tick from SNAP_ATTRS state only (_q_nom,
        # _tilt_ref0, _state) — pool-restore safe, same pattern as
        # the lower anchor. imu roll/pitch and BodyOffset roll/pitch
        # share the same axis convention (rot_x/rot_y; verified in
        # test_bc_anchor.py::test_tilt_comp_counter_rotates).
        _tc = float(cfg_get(env.cfg, "train", "bc_anchor_tilt_comp",
                            default=0.0))
        if (_tc > 0.0 and env._goal_traj is not None
                and env._goal_traj.mode == "hold"
                and env._q_nom is not None):
            _dead = 1.5 * DEG2RAD
            # Cap default 6.0: measured expressibility boundary —
            # the counter-rotated pose from a settled hold stance
            # round-trips the [-1,1] action space EXACTLY up to 6
            # deg and saturates a joint bound from 7 deg (the
            # target must be a pose the policy can actually
            # command; a clipped target supervises garbage on the
            # saturated joints).
            _maxc = 6.0 * DEG2RAD

            def _soft(x: float) -> float:
                return math.copysign(max(abs(x) - _dead, 0.0), x)

            # Comp source (train.bc_anchor_tilt_from_settle,
            # default 0 = the original current-lean proportional
            # source, bit-exact). The proportional source is a
            # P-controller with a closed-loop fixed point at
            # (L0+deadband)/2 — as the student levels, the
            # commanded correction SHRINKS below what leveling
            # needs (probe_tilt_teacher, 08-13: a perfect student
            # settles 3.95deg from 6.5deg spawns vs the 3deg gate
            # bar; predicted 3.98). The settle-lean source uses the
            # episode's post-settle lean (_settle_lean, a
            # per-episode constant in SNAP_ATTRS): the ideal
            # student levels to the deadband (or the cap-limited
            # residual), where the income Gaussian regains
            # gradient and RL can finish the job.
            if float(cfg_get(env.cfg, "train",
                             "bc_anchor_tilt_from_settle",
                             default=0.0)) > 0.0:
                _er = _soft(env._settle_lean[0])
                _ep_ = _soft(env._settle_lean[1])
            else:
                _er = _soft(env._state.imu_roll
                            - env._tilt_ref0[0])
                _ep_ = _soft(env._state.imu_pitch
                             - env._tilt_ref0[1])
            if _er != 0.0 or _ep_ != 0.0:
                from rl_move.body_ik import BodyOffset, FixedFootBodyIK
                _cr = float(np.clip(-_tc * _er, -_maxc, _maxc))
                _cp = float(np.clip(-_tc * _ep_, -_maxc, _maxc))
                _ik = FixedFootBodyIK()
                _ik.reset(_q_hold_base)
                # Halving retry: a correction the stance geometry
                # can't reach degrades to a smaller one instead of
                # silently reverting to the tilt-blind target (the
                # 12deg default cap was IK-infeasible from the
                # settled hold stance — caught by the clip test).
                for _s in (1.0, 0.5, 0.25):
                    _res = _ik.solve(BodyOffset(
                        roll=_cr * _s, pitch=_cp * _s))
                    if _res.ok:
                        _q_tgt = _res.q_rad
                        break
        info["bc_target"] = q_rad_to_action(
            _q_tgt).astype(np.float32)
        info["bc_mode"] = 1        # hold/track
    # LOWER BC-anchor target (08-11, cfg train.bc_anchor_lower,
    # default 0 = legacy no-emission). The lower bank's strict
    # xfail pins the pricing gap (one-leg-aloft keeps ~85% of
    # honest income) and prescribes "strengthen the pricing (or
    # BC-anchor lower ticks)"; six runs showed pricing never moves
    # the behavior while anchor supervision does. The target is
    # the bank's own honest demonstration: the FixedFootBodyIK
    # descent — all six feet anchored at the SETTLED stance
    # (_q_nom, post-settle, already in SNAP_ATTRS), body tracking
    # the commanded height one tick ahead. Solved fresh per tick
    # (~5 us, analytic) from snapped state only — pool-restore
    # safe by construction, no per-episode IK object to snapshot.
    elif (getattr(env, "_is_lower_bc", False)
            and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0
            and float(cfg_get(env.cfg, "train", "bc_anchor_lower",
                              default=0.0)) > 0.0
            and env._q_nom is not None
            and env._goal_traj is not None):
        from rl_move.body_ik import BodyOffset, FixedFootBodyIK
        from .joint_task import q_rad_to_action
        # _step_i was already incremented at the top of
        # _step_finish; the next commanded tick is _step_i + 1
        # (same one-tick-ahead convention as the rise clock).
        _g_next = env._goal_traj.at(env._step_i + 1)
        _ik = FixedFootBodyIK()
        # Mode-seq lower segments descend from the stance carried
        # INTO the segment; None outside mode_seq = legacy q_nom.
        _ik.reset(
            env._q_nom
            if getattr(env, "_seq_pose_anchor", None) is None
            else env._seq_pose_anchor)
        _res = _ik.solve(BodyOffset(
            height=float(_g_next.height_ref)))
        if _res.ok:
            info["bc_target"] = q_rad_to_action(
                _res.q_rad).astype(np.float32)
            info["bc_mode"] = 2    # lower
    # WALK BC-anchor target (08-11, probe_walk_income follow-up):
    # the scripted TripodGait's joint pose one control tick ahead,
    # driven by the LIVE blended command (vx/vy/wz ref) — so the
    # target is command-conditioned in every direction, points at
    # a plant-hold on genuine stop segments (set_velocity(0,0)
    # holds the stance), and supplies the per-leg "step this way"
    # gradient the reward provably cannot (degenerates earn below
    # freeze yet PPO still found them). Reward stack untouched.
    elif (getattr(env, "_walk_bc_gait", None) is not None
            and getattr(env, "n_act", 0) == N_JOINTS
            and _bc_coef > 0.0):
        _bc_goal = env._current_goal()
        # ONLY on commanded ticks: TripodGait at zero velocity
        # marches in place (the bank's "stall" policy), so a stop
        # segment must get NO gait supervision — standing still is
        # the commanded behavior there and the kernel already pays
        # it (walk_kernel freeze income at s_ref=0 is legitimate).
        if _bc_goal is not None:
            _bc_wz = float(getattr(_bc_goal, "wz_ref", 0.0) or 0.0)
            _bc_cmd = (math.hypot(_bc_goal.vx_ref, _bc_goal.vy_ref)
                       > 1e-3 or abs(_bc_wz) > 1e-3)
            # COMBINED-TICK OMEGA BOOST (09-03, standwalk branch-(a)
            # follow-up to the combined-turn-probe finding): a
            # zero-training sweep of the teacher's own per-leg
            # foot-target formula (v_x_at = vx - omega*r*sin(a),
            # v_y_at = vy + omega*r*cos(a)) found the combined-tick
            # wz collapse is NOT an IK/workspace artifact (no IK
            # infeasibility, coxa-yaw excursion is if anything
            # LARGER under combined than pure-turn) but a
            # friction/thrust-ALLOCATION effect: vx numerically
            # dominates the per-leg omega contribution
            # (omega*r ~ 0.018 m/s vs vx ~ 0.08 m/s), so almost all
            # of the shared ground-reaction budget goes to forward
            # thrust, starving yaw. Multiplying the omega term by a
            # boost factor before it ever reaches the teacher's
            # foot-target math (equivalent to feeding TripodGait a
            # boosted omega, since `self.omega` is used nowhere
            # else in the class) recovers real wz at a graded vx
            # cost, measured with probe_turn_authority.py
            # --policy scripted --vx-cmds on THIS exact call site's
            # formula (boost 1.0->5.0: wz_med 0.072->0.207 rad/s,
            # vx_med 0.034->0.010 m/s at vx_cmd=0.08/wz_cmd=0.25;
            # boost=2.0 is the knee: wz +122%, vx -24%). Applied
            # ONLY on COMBINED ticks (vx_ref!=0 AND wz_ref!=0,
            # computed early here so it is available before
            # set_velocity) so pure-turn ticks (already-good
            # wz~0.18-0.23) and straight-walk ticks (omega=0, boost
            # is a no-op regardless) are bit-exact untouched.
            # Default 1.0 = legacy no-op (1.0x is mathematically
            # identity), exactly like every other bc_anchor_* knob
            # in this file. See test_bc_anchor.py
            # test_walk_combined_omega_boost_*.
            _bc_combined_early = (
                math.hypot(_bc_goal.vx_ref, _bc_goal.vy_ref) > 1e-3
                and abs(_bc_wz) > 1e-3)
            _bc_omega_boost = float(cfg_get(
                env.cfg, "train", "bc_anchor_teacher_omega_boost",
                default=1.0))
            _bc_wz_teacher = (
                _bc_wz * _bc_omega_boost
                if (_bc_combined_early and _bc_omega_boost != 1.0)
                else _bc_wz)
            # PHASE-SCHEDULED MULTI-TEACHER read-once (see the
            # emission site below, near bc_anchor_walk_combined_
            # dose, for the full derivation). Default 0.0 = off.
            _mt_blend_final = float(cfg_get(
                env.cfg, "train", "bc_anchor_multiteacher_blend",
                default=0.0))
            if _bc_cmd:
                from .joint_task import q_rad_to_action
                _g = env._walk_bc_gait
                _g.set_velocity(vx=float(_bc_goal.vx_ref),
                                vy=float(_bc_goal.vy_ref),
                                omega=_bc_wz_teacher)
                # _step_i was already incremented at the top of
                # _step_finish: it IS the next pre-step tick index,
                # so the next scripted action is desired_deg at
                # _step_i * dt (the bank rollouts command
                # desired_deg(step*dt) at pre-step tick `step`).
                _t_bc = env._step_i * env.dt
                if float(cfg_get(env.cfg, "train",
                                 "bc_anchor_phase_lock",
                                 default=0.0)) > 0.0:
                    # PHASE-LOCKED anchor clock (08-22, operator
                    # reward-alignment order fb_20260822T032514,
                    # phasedir2 line): with goal.walk_phase_obs=1
                    # the POLICY's clock advances only while a
                    # linear velocity is commanded
                    # (walk_task._augment_obs), and the phase BC
                    # clone was distilled against exactly that
                    # clock (bc_init_gait unwraps the phase obs to
                    # drive the teacher). The legacy wall-clock
                    # time above jumps the gait phase across every
                    # settle hold / stop segment (~0.33 cycle for
                    # the standard 1 s spawn hold), so the anchor
                    # would pull TOWARD A DIFFERENTLY-PHASED GAIT
                    # than the clock the policy sees. This
                    # accumulator advances by dt on exactly the
                    # ticks the obs clock advances (s_ref > 1e-3;
                    # a wz-only commanded tick keeps the clock —
                    # and the gait phase — frozen, matching the
                    # obs clock's linear-command gate). Default 0
                    # = legacy wall-clock, bit-exact.
                    _bc_clock_run = math.hypot(
                        _bc_goal.vx_ref, _bc_goal.vy_ref) > 1e-3
                    if (not _bc_clock_run
                            and float(cfg_get(
                                env.cfg, "goal",
                                "walk_phase_run_on_yaw",
                                default=0.0)) > 0.0):
                        # run_on_yaw GAP FIX (08-30, standwalk
                        # walkteach wave-2 prereq,
                        # OPERATOR_QUESTIONS q_20260830T1530Z item
                        # 3b): walk_task._augment_obs already
                        # advances the POLICY's obs phase clock on
                        # a wz-only commanded tick when
                        # goal.walk_phase_run_on_yaw=1 (amp M2-yaw,
                        # 08-22) — this accumulator did not mirror
                        # that, so a turn-in-place tick under
                        # run_on_yaw=1 froze the ANCHOR's gait
                        # phase while the policy's own clock kept
                        # advancing, pulling the anchor toward a
                        # stale phase. Gate identically to the obs
                        # clock (same key, same wz-nonzero test).
                        # Bit-exact no-op whenever run_on_yaw=0 OR
                        # every commanded tick is either linear or
                        # a true park (wz_ref==0 too) — e.g. every
                        # wave-1 walkteach run to date
                        # (walk_yaw_zero_frac=1.0, no turn ticks).
                        _bc_clock_run = abs(_bc_wz) > 1e-3
                    if _bc_clock_run:
                        _dt_bc = env.dt
                        # Speed-coupled clock (08-22, amp M2
                        # speedrange root cause): when
                        # goal.walk_phase_speed_scale>0 the obs
                        # clock in walk_task._augment_obs runs at
                        # hz_eff, not hz_base — scale the anchor
                        # accumulator by the same ratio so the
                        # anchor gait stays phase-locked to the
                        # clock the policy sees. Default 0 =
                        # legacy, bit-exact.
                        _k_coup = float(cfg_get(
                            env.cfg, "goal",
                            "walk_phase_speed_scale", default=0.0))
                        if _k_coup > 0.0:
                            from rl_move.sim.walk_task import (
                                phase_hz_effective,
                                PHASE_HZ_DEFAULT,
                                PHASE_SPEED_NOM_DEFAULT)
                            _hz0 = float(cfg_get(
                                env.cfg, "goal", "walk_phase_hz",
                                default=PHASE_HZ_DEFAULT))
                            _hz_eff = phase_hz_effective(
                                _hz0,
                                math.hypot(_bc_goal.vx_ref,
                                           _bc_goal.vy_ref),
                                _k_coup,
                                s_nom=float(cfg_get(
                                    env.cfg, "goal",
                                    "walk_phase_speed_nom",
                                    default=PHASE_SPEED_NOM_DEFAULT)),
                                hz_max=float(cfg_get(
                                    env.cfg, "goal",
                                    "walk_phase_hz_max",
                                    default=0.0)))
                            if _hz0 > 0.0:
                                _dt_bc = env.dt * (_hz_eff / _hz0)
                        env._walk_bc_t += _dt_bc
                    _t_bc = env._walk_bc_t
                # TURN-TICK ANCHOR GATE (08-31, standwalk dualbc5
                # turncap-turnpay-canary dose-ablation follow-up):
                # the anchor1p0/anchor0p3 canaries proved a global
                # coefficient cut (3.0 -> 1.0 -> 0.3, a 10x range)
                # does NOT restore turn authority — both post-RL
                # probes stayed <0.03 wz_med both signs with the
                # IDENTICAL walk_yaw_kernel_factor erosion curve
                # (0.34 -> ~0.05-0.09) as the uncut 3.0 baseline,
                # exonerating the anchor's DOSE. The still-untried
                # half of that verdict's own named lever is a
                # TARGETED gate: instead of shrinking the anchor
                # pull everywhere (which dilutes supervision on the
                # majority straight-walk ticks that need it), zero
                # the anchor emission ONLY on pure turn-in-place
                # ticks (vx_ref=vy_ref~0, wz_ref!=0) so the yaw
                # reward's own gradient is the sole supervisor of
                # the actor's mean action at those specific states,
                # while straight-walk ticks keep full anchor
                # coefficient/supervision untouched. Default 0 =
                # legacy (every commanded tick, including turn
                # ticks, gets a target) — bit-exact no-op whenever
                # train.bc_anchor_walk_turn_skip is unset, exactly
                # like every other bc_anchor_* knob in this file.
                _bc_pure_turn = (
                    math.hypot(_bc_goal.vx_ref, _bc_goal.vy_ref)
                    <= 1e-3 and abs(_bc_wz) > 1e-3)
                _bc_turn_skip = (
                    _bc_pure_turn
                    and float(cfg_get(
                        env.cfg, "train",
                        "bc_anchor_walk_turn_skip",
                        default=0.0)) > 0.0)
                _bc_combined = _bc_combined_early
                if not _bc_turn_skip:
                    _q_bc = np.asarray(
                        _g.desired_deg(_t_bc)) * DEG2RAD
                    info["bc_target"] = q_rad_to_action(
                        _q_bc).astype(np.float32)
                    info["bc_mode"] = 3    # walk
                    # PHASE-SCHEDULED (dose) COMBINED-TICK ANCHOR
                    # WEIGHT (09-03, standwalk item-2 escalation:
                    # candidate (i)-v2 combined_yaw_arm_scale
                    # closed 4/4 FAIL — every dose that wins the
                    # combined-tick wz axis blows the pure-turn
                    # regression cap, and the lever is bit-exact
                    # on pure-turn by construction, so the RL
                    # regression must come from the SHARED
                    # dual-core policy's representation being
                    # pulled by the combined-tick anchor target,
                    # not the geometry. The binary combined-skip
                    # gate above (dose 0 vs 1, no middle) is
                    # already refuted (train.bc_anchor_walk_
                    # combined_skip, FAIL). This is the untried
                    # middle: a CONTINUOUS per-tick anchor-weight
                    # multiplier on combined ticks only, so the
                    # walk BC-anchor loss can be dosed anywhere in
                    # (0, 1) instead of only the two extremes —
                    # full anchor pull (1.0, legacy) at one end,
                    # full skip (0.0, already refuted) at the
                    # other. Default 1.0 = legacy weight, bit-
                    # exact off: the collect callback treats a
                    # missing/1.0 ``bc_walk_weight`` identically to
                    # every prior tick in this lineage (see
                    # bc_anchor.py's weighted-MSE note). See
                    # test_bc_anchor.py test_walk_combined_dose_*.
                    _combined_dose = float(cfg_get(
                        env.cfg, "train",
                        "bc_anchor_walk_combined_dose",
                        default=1.0))
                    if _bc_combined and _combined_dose != 1.0:
                        info["bc_walk_weight"] = _combined_dose
                    # PHASE-SCHEDULED MULTI-TEACHER (09-05,
                    # standwalk item-1 escalation: the dose/skip
                    # family above (this knob + combined_skip +
                    # every geometry lever: yawarm/omegaboost/
                    # selomegaboost) is CLOSED 4/4-per-cell —
                    # every static reweight/rescale of the SAME
                    # single degraded-combined target either
                    # leaves the cap alone (no win) or blows the
                    # pure-turn regression cap once RL fine-tunes
                    # against it, because ALL of those levers hold
                    # ONE fixed target/weight for the entire
                    # training run. This is a structurally
                    # different class: instead of reweighting the
                    # single scripted-combined target, emit a
                    # SECOND ("aggressive") teacher target — a
                    # SEPARATE persistent TripodGait, driven by
                    # the same wall-clock tick stream but with
                    # vx/vy always zeroed, i.e. the UNDEGRADED
                    # pure-turn geometry TripodGait would command
                    # if this tick were turn-only (own object, own
                    # EMA smoothing state — never a second query
                    # on ``_g`` itself; see its allocation site's
                    # comment) — and blend the two at LOSS TIME
                    # (bc_anchor.py's train(), which alone knows
                    # ``self._current_progress_remaining``) on a
                    # schedule that ramps from the safe degraded
                    # target (blend=0, early training, matches
                    # every already-converged sibling) toward the
                    # aggressive target (blend->
                    # bc_anchor_multiteacher_blend, late training)
                    # over the first
                    # bc_anchor_multiteacher_schedule_frac of the
                    # run. Untried axis: every prior arm used a
                    # STATIC dose for the whole run; none varied
                    # the target/weight over TRAINING PROGRESS.
                    # Default 0.0 = legacy (no alt target emitted,
                    # no ring column touched) — bit-exact off, see
                    # bc_anchor.py's attach_bc_anchor/
                    # _bc_init_buffer and test_bc_anchor.py
                    # test_multiteacher_*.
                    _g_alt = getattr(env, "_walk_bc_gait_alt", None)
                    if (_bc_combined and _mt_blend_final > 0.0
                            and _g_alt is not None):
                        # Separate persistent object (see its
                        # allocation site) — NOT a second query on
                        # ``_g`` itself, which would hand the EMA
                        # smoother a dt=0 same-tick call and
                        # silently return the stale (still-
                        # combined) smoothed velocity instead of a
                        # genuine pure-turn trajectory.
                        _g_alt.set_velocity(vx=0.0, vy=0.0,
                                           omega=_bc_wz_teacher)
                        _q_bc_alt = np.asarray(
                            _g_alt.desired_deg(_t_bc)) * DEG2RAD
                        info["bc_target_alt"] = q_rad_to_action(
                            _q_bc_alt).astype(np.float32)
