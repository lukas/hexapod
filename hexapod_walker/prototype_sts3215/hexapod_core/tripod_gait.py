"""Open-loop tripod gait for the STS3215 hexapod (no MuJoCo / numpy).

Port of ``mujoco_prototype.TripodGait`` + ``_leg_ik`` with pure stdlib math
so it can run on the Uno Q with only the Feetech bus SDK vendored.
"""
from __future__ import annotations

import math

# Geometry (mm) — keep in sync with hexapod_prototype / mujoco_prototype.
COXA_MM = 12.5
FEMUR_MM = 90.0
TIBIA_MM = 150.0
CHASSIS_FLAT_TO_FLAT_MM = 200.0  # matches hexapod_prototype.CHASSIS_FLAT_TO_FLAT
KNEE_ANGLE_CONVENTION = "absolute_tibia"
# Fallback stand home if feetech_bus / learned plant cannot be loaded.
STANCE_FEMUR_DEG = 19.0
STANCE_TIBIA_DEG = 28.0

M = 0.001
COXA = COXA_MM * M
FEMUR = FEMUR_MM * M
TIBIA = TIBIA_MM * M
STANCE_FEMUR = math.radians(STANCE_FEMUR_DEG)
STANCE_TIBIA = math.radians(STANCE_TIBIA_DEG)
LEG_RADIAL = (CHASSIS_FLAT_TO_FLAT_MM / 2.0) * M
HIP_LIMIT_DEG = (-80.0, 40.0)
KNEE_LIMIT_DEG = (-20.0, 150.0)


def _plant_hip_knee_deg() -> tuple[float, float]:
    """Stand-plant hip/knee (same source as ``standing_pose_degrees``)."""
    try:
        from motor_setup.feetech_bus import (DEFAULT_STAND_HIP_DEG,
                                             DEFAULT_STAND_KNEE_DEG,
                                             load_plant_pose)
        plant = load_plant_pose()
        return (float(plant.get("hip_deg", DEFAULT_STAND_HIP_DEG)),
                float(plant.get("knee_deg", DEFAULT_STAND_KNEE_DEG)))
    except Exception:
        return STANCE_FEMUR_DEG, STANCE_TIBIA_DEG


def foot_rz_from_hip_knee(hip_deg: float, knee_deg: float) -> tuple[float, float]:
    """Foot reach and z in the yaw frame.

    The measured robot matches an absolute tibia convention: hip is the
    femur angle and knee is the tibia angle in the same leg plane.  Logical
    zero is still straight out because both angles are 0 there.
    """
    hip = math.radians(float(hip_deg))
    knee = math.radians(float(knee_deg))
    reach = COXA + FEMUR * math.cos(hip) + TIBIA * math.cos(knee)
    z = -FEMUR * math.sin(hip) - TIBIA * math.sin(knee)
    return reach, z


def _in_limits(rad: float, limits_deg: tuple[float, float]) -> bool:
    deg = math.degrees(rad)
    return limits_deg[0] - 1e-6 <= deg <= limits_deg[1] + 1e-6


def _leg_ik(target_xyz_in_yaw_frame):
    u = float(target_xyz_in_yaw_frame[0]) - COXA
    w = -float(target_xyz_in_yaw_frame[2])
    L = math.hypot(u, w)
    if L > FEMUR + TIBIA - 1e-6 or L < abs(FEMUR - TIBIA) + 1e-6:
        return None
    gamma = math.atan2(w, u)
    cos_alpha = (L * L + FEMUR * FEMUR - TIBIA * TIBIA) / (2 * L * FEMUR)
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = math.acos(cos_alpha)
    candidates = []
    for hip in (gamma - alpha, gamma + alpha):
        knee = math.atan2(w - FEMUR * math.sin(hip),
                          u - FEMUR * math.cos(hip))
        score = 0.0
        if not _in_limits(hip, HIP_LIMIT_DEG):
            score += 1000.0
        if not _in_limits(knee, KNEE_LIMIT_DEG):
            score += 1000.0
        # Normal stand/walk poses have the tibia a little steeper than the
        # femur.  This selects that branch when both circle intersections fit.
        if knee < hip:
            score += 10.0
        score += 0.01 * abs(math.degrees(knee - hip))
        candidates.append((score, hip, knee))
    _score, hip, knee = min(candidates, key=lambda row: row[0])
    return hip, knee


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class TripodGait:
    MAX_VX = 0.28
    MAX_VY = 0.20
    MAX_OMEGA = 1.0
    SCALE_PERIOD_MIN = 0.40
    SCALE_PERIOD_MAX = 2.00
    SCALE_LIFT_MIN = 0.30
    SCALE_LIFT_MAX = 2.50
    SCALE_STRIDE_MIN = 0.30
    SCALE_STRIDE_MAX = 1.80
    STANCE_RADIUS_SCALE_MIN = 0.55
    STANCE_RADIUS_SCALE_MAX = 1.05

    def __init__(
        self,
        *,
        period: float = 0.75,
        lift: float = 0.025,
        ramp: float = 0.35,
        vx: float = 0.0,
        vy: float = 0.0,
        omega: float = 0.0,
        period_scale: float = 1.0,
        lift_scale: float = 1.0,
        stride_scale: float = 1.0,
        stance_radius_scale: float = 1.0,
        combined_yaw_arm_scale: float = 1.0,
        combined_yaw_amplify_scale: float = 1.0,
        combined_selective_omega_boost: float = 1.0,
        combined_group_duty_skew: float = 0.0,
    ):
        self.period = period
        self.lift = lift
        self.ramp = max(ramp, 1e-3)
        # standwalk Next item 2, candidate (i)-v2 (09-03): a per-tick
        # yaw-axis SafetyLayer clip (physically pinned at 0.375deg/tick
        # @100Hz = 37.5deg/s, operator order fb_20260824T174619_c49b7e --
        # NOT to be raised) saturates ~48% of combined (vx!=0 AND
        # omega!=0) walk ticks but ~0% of pure-turn ticks at the
        # identical |wz_cmd| (measured, probe_joint_tracking.py,
        # logs/ckpt_eval/joint_tracking_cap29_scripted_09-03.json).
        # Two same-mechanism variants were tried and REFUTED first:
        # boosting omega (train.bc_anchor_teacher_omega_boost, 09-03
        # 17:5x) recovered scripted-teacher wz cleanly but the RL-canary
        # traded a lopsided/sign-asymmetric gain for a pure-turn
        # regression >10% (4/4 FAIL); *discounting* omega on combined
        # ticks (probe_turn_authority.py --scripted-omega-boost <1,
        # zero training, this cycle) does not even help at the scripted
        # level -- combined wz_med gets MONOTONICALLY WORSE as the
        # discount strengthens (0.0723->0.0620 rad/s from dose 1.0->0.3
        # at wz_cmd=0.25/vx_cmd=0.08), because the raw per-tick yaw
        # delta is a period-INDEPENDENT direct function of the physical
        # foot velocity -- any uniform demand scaling (either sign)
        # trades achieved rotation 1:1 against clip relief, no net win.
        # This lever is different: instead of changing how much yaw
        # motion is COMMANDED, it changes the MOMENT ARM used to
        # convert the SAME true tangential foot displacement into a
        # commanded SERVO ANGLE (x_yaw's atan2 denominator only, in
        # desired_deg() below) -- hip/knee still IK the TRUE r_planar/z
        # target unchanged, so foot placement/lift are untouched; only
        # the yaw joint's own commanded angle shrinks for a given
        # physical swing, which needs less per-tick slew to reach.
        # Gated to combined ticks only (self.vx!=0 AND self.omega!=0,
        # mirroring the identical gate used by the omega-boost/reward-
        # boost candidates) so pure-turn is bit-exact regardless of
        # dose. Zero-training scripted-teacher probe (this cycle,
        # /tmp spike reproduced via the real code path, see
        # test_tripod_gait_combined_yaw_arm_scale.py): dose 1.0->2.0
        # improves combined wz_med +12% (0.0723->0.0807 rad/s, BOTH
        # wz signs) at flat vx_med, while pure-turn wz_med stays
        # EXACTLY 0.2198 (bit-identical) at every dose -- past 2.0 the
        # gain reverses (dose 5.0: wz_med 0.0290, worse than baseline).
        # Default 1.0 = legacy identity (atan2(y_yaw, x_yaw) unchanged)
        # -- bit-exact off, matching every other bc_anchor_*/gait
        # dose knob in this codebase.
        self.combined_yaw_arm_scale = float(combined_yaw_arm_scale)
        # standwalk Next item 2, candidate (iii) (09-04): per-leg
        # SELECTIVE variant of the above, built after the per-leg
        # foot-target instrumentation (probe_leg_yaw_rate.py) found the
        # combined-tick clip saturation is NOT uniform across legs --
        # projecting the true combined tangential foot velocity onto
        # each leg's own yaw-servo axis shows vx's cross term (-vx*
        # sin(leg_angle)) ADDS to omega*r for 3 of 6 legs (amplifying
        # them well past the pure-turn magnitude, e.g. 99 vs 34.5 deg/s
        # of commanded-yaw rate at vx=0.08/omega=0.25) while it
        # SUBTRACTS for the other 3 (attenuating them toward zero) --
        # a real per-leg cancellation/reinforcement pattern, not a
        # uniform "vx drowns out omega" effect. The already-tried
        # ``combined_yaw_arm_scale`` scales EVERY leg's atan2
        # denominator equally, spending correction budget on legs that
        # were never over the clip and distorting their foot-target
        # direction for no saturation benefit -- REFUTED zero-training
        # first (this cycle): a symmetric "detangle the cross term out
        # of the yaw numerator" alternative was tried and discarded
        # because at any dose that meaningfully de-saturates the worst
        # legs it flips the SIGN of the previously-near-cancelled
        # legs' yaw command (up to ~12deg foot-target direction error)
        # and, at full dose, creates a NEW saturated leg (4/6 over clip
        # vs the legacy 3/6) -- worse, not better.
        # This knob instead multiplies the SAME atan2 denominator as
        # ``combined_yaw_arm_scale`` but ONLY on legs where the true
        # combined tangential magnitude |y_yaw| exceeds that same
        # leg's pure-omega-only magnitude (i.e. only the AMPLIFIED
        # legs) -- the other 3 legs are bit-exact untouched at any
        # dose. Zero-training probe_leg_yaw_rate.py sweep: scale=3.0
        # applied only to the 3 amplified legs fully de-saturates ALL
        # SIX legs' commanded-yaw RATE (0/6 over the 37.5deg/s clip,
        # vs 3/6 for the unscaled baseline).
        # REFUTED anyway (09-04, same cycle, before any RL spend):
        # de-saturating the rate proxy does NOT translate into more
        # real turn authority -- probe_turn_authority.py's scripted-
        # teacher body wz_med at vx=0.08/wz_cmd=0.25 goes 0.0723
        # (dose 1.0) -> 0.0715 (1.5) -> 0.0737 (2.0) -> 0.0295 (3.0,
        # the fully-desaturating dose) -> 0.0104 (4.0), monotonically
        # WORSE past dose ~2.0, matching (and now generalizing) the
        # 09-04 05:35 finding that raising the SafetyLayer's yaw slew
        # clip 0.375->8.0deg barely moves combined wz either: shrinking
        # a leg's COMMANDED yaw excursion shrinks the PHYSICAL rotation
        # it produces right along with it, clip or no clip -- there is
        # no free "de-saturate without losing torque" regime for this
        # family of atan2-denominator tricks. See
        # test_probe_turn_authority.py::
        # test_yaw_amplify_scale_desaturates_clip_but_REGRESSES_real_wz
        # for the pinned numbers. Kept as a bit-exact-off knob (like
        # every other refuted dose lever in this file) for
        # reproducibility, NOT a candidate for BC-anchor wiring or an
        # RL canary. Default 1.0 = legacy identity (composes
        # multiplicatively with ``combined_yaw_arm_scale``, itself
        # default-off).
        self.combined_yaw_amplify_scale = float(combined_yaw_amplify_scale)
        # standwalk Next item 2, SELECTIVE per-leg omega boost (09-04,
        # the mirror image of ``combined_yaw_amplify_scale`` using the
        # SAME per-leg classification, but a genuinely DIFFERENT
        # mechanism). Every candidate in the 09-04 "reshape the
        # commanded yaw ANGLE" family (uniform ``combined_yaw_arm_
        # scale``, selective ``combined_yaw_amplify_scale``, the
        # unwired "detangle the vx cross term" idea) was refuted
        # because scaling the yaw SERVO angle's atan2 denominator only
        # changes how much slew is COMMANDED for a fixed true foot
        # offset -- it never changes the true offset itself, so the
        # physical rotation the leg produces shrinks right along with
        # the commanded angle. This knob instead changes the TRUE FOOT
        # OFFSET: on a combined tick (self.vx!=0 and self.omega!=0),
        # for each leg classified as ATTENUATED (the true combined
        # tangential magnitude |y_yaw| is SMALLER than that leg's own
        # pure-omega-only magnitude |y_turn| -- the vx cross term
        # ``-vx*sin(leg_angle)`` partially CANCELS omega*r for it,
        # mirror image of the AMPLIFIED legs ``combined_yaw_amplify_
        # scale`` targets), the ENTIRE foot target (dx/dy/dz, not just
        # the yaw angle) is recomputed with omega multiplied by this
        # dose before IK -- i.e. the leg is told to physically swing
        # through more angle, exactly mirroring the already-tried
        # UNIFORM ``train.bc_anchor_teacher_omega_boost`` mechanism
        # (09-03, proven to recover real scripted-teacher wz at the
        # cost of vx) but restricted to only the 3 legs that lost
        # authority to vx cancellation, leaving the 3 already-
        # AMPLIFIED legs byte-identical to dose 1.0 at any dose.
        # Gated to combined ticks only, so pure-turn and pure-walk are
        # bit-exact regardless of dose. Default 1.0 = legacy identity
        # (skips the extra _foot_target_in_body call entirely).
        self.combined_selective_omega_boost = float(
            combined_selective_omega_boost)
        # standwalk Next item 2, gait-STRUCTURE candidate (09-05, the
        # first lever in this file that changes DURATION rather than
        # MAGNITUDE — every candidate above changes how far/what angle
        # a leg is commanded within a FIXED swing/stance half-period;
        # all were refuted because, for a fixed time window, a
        # constant-velocity sweep already has the minimum possible peak
        # per-tick rate for a given excursion, so shrinking the
        # commanded magnitude to dodge the `safety.max_delta_q_deg`
        # slew clip trades 1:1 against achieved rotation (see the
        # combined_yaw_arm_scale / combined_yaw_amplify_scale /
        # combined_selective_omega_boost docstrings above for the
        # measured evidence). This knob instead re-times the EXISTING
        # two-tripod-group alternation itself: on a combined tick
        # (vx!=0 and omega!=0), `_classify_group_heavy` finds which
        # tripod-parity group (0={0,2,4} or 1={1,3,5}) contains MORE
        # "amplified" legs (the standwalk 09-04 per-leg classification:
        # true combined tangential magnitude > pure-omega-only
        # magnitude for that leg — proven prog/phase-INDEPENDENT, a
        # static function of leg angle + command sign only, verified
        # empirically across a full phase sweep + all 4 vx/omega sign
        # combos). That group's SWING window widens from the legacy
        # 50% of the cycle to `0.5 + combined_group_duty_skew` (the
        # OTHER group's swing narrows to `0.5 - combined_group_duty_
        # skew`, since the two groups' windows must still exactly
        # partition the cycle) — giving the amplified-heavy group's
        # legs MORE TIME to sweep the SAME true excursion (lower peak
        # rate) without touching any commanded angle/foot-target
        # magnitude at all. SAFE BY CONSTRUCTION regardless of dose:
        # unlike a per-leg duty change, this only ever re-splits ONE
        # shared boundary point on the phase circle between the two
        # EXISTING alternating tripod groups, so exactly one group is
        # always swinging and the other always stancing (the same
        # 3-up/3-down support invariant the legacy 50/50 split already
        # guarantees) at ANY skew in (-0.5, 0.5) -- no per-leg
        # asymmetric support-polygon risk, no new stability check
        # needed. UNTESTED AT THE PHYSICS LEVEL (09-05): narrowing the
        # OTHER group's swing (and, symmetrically, the heavy group's
        # OWN stance window) could raise ITS peak rate instead --
        # whether the net effect actually relieves combined-tick clip
        # saturation is an open empirical question for
        # `probe_turn_authority.py`/a dedicated clip-rate probe, not
        # assumed here. Default 0.0 = legacy identity (falls through
        # the ORIGINAL phi<pi/2*pi boundary code path unchanged, so
        # this knob costs nothing and is bit-exact off by construction
        # -- no new floating-point path when unused).
        self.combined_group_duty_skew = _clip(
            float(combined_group_duty_skew), -0.45, 0.45)
        self.vx = vx
        self.vy = vy
        self.omega = omega
        self.period_scale = period_scale
        self.lift_scale = [_clip(float(lift_scale), self.SCALE_LIFT_MIN,
                                 self.SCALE_LIFT_MAX)] * 6
        self.stride_scale = stride_scale
        self.leg_angles = [(i + 0.5) * math.pi / 3.0 for i in range(6)]
        self.stance_radius_scale = _clip(
            stance_radius_scale,
            self.STANCE_RADIUS_SCALE_MIN,
            self.STANCE_RADIUS_SCALE_MAX,
        )
        self._phase_offset = math.pi / 2.0
        self._vx_smooth = vx
        self._vy_smooth = vy
        self._om_smooth = omega
        self._last_t = None
        self._phase = 0.0
        self._elapsed = 0.0
        # Foot plant matches stand home (+19°/+28° or learned plant).
        self.sync_plant_stance()

    def sync_plant_stance(self, hip_deg: float | None = None,
                          knee_deg: float | None = None) -> None:
        """Set IK foot height / radius from stand-plant hip & knee degrees."""
        if hip_deg is None or knee_deg is None:
            h, k = _plant_hip_knee_deg()
            hip_deg = h if hip_deg is None else hip_deg
            knee_deg = k if knee_deg is None else knee_deg
        self.plant_hip_deg = float(hip_deg)
        self.plant_knee_deg = float(knee_deg)
        self.foot_neutral_x, self.foot_neutral_z = foot_rz_from_hip_knee(
            self.plant_hip_deg, self.plant_knee_deg)
        self._foot_radius = LEG_RADIAL + self.foot_neutral_x
        self._foot_radius_eff = self._foot_radius * self.stance_radius_scale
        self._fallback = (
            0.0,
            math.radians(self.plant_hip_deg),
            math.radians(self.plant_knee_deg),
        )

    def set_velocity(self, *, vx=None, vy=None, omega=None):
        if vx is not None:
            self.vx = _clip(float(vx), -self.MAX_VX, self.MAX_VX)
        if vy is not None:
            self.vy = _clip(float(vy), -self.MAX_VY, self.MAX_VY)
        if omega is not None:
            self.omega = _clip(float(omega), -self.MAX_OMEGA, self.MAX_OMEGA)

    def set_lift_mm(self, lift_mm: float) -> None:
        self.lift = max(0.004, min(0.050, float(lift_mm) * 0.001))

    def set_scales(self, *, period_scale=None, lift_scale=None, stride_scale=None):
        if period_scale is not None:
            self.period_scale = _clip(
                float(period_scale), self.SCALE_PERIOD_MIN, self.SCALE_PERIOD_MAX)
        if lift_scale is not None:
            s = _clip(float(lift_scale), self.SCALE_LIFT_MIN, self.SCALE_LIFT_MAX)
            self.lift_scale = [s] * 6
        if stride_scale is not None:
            self.stride_scale = _clip(
                float(stride_scale), self.SCALE_STRIDE_MIN, self.SCALE_STRIDE_MAX)

    def stop(self):
        self.set_velocity(vx=0.0, vy=0.0, omega=0.0)

    def reset_phase(self, *, phase: float = 0.0, t: float = 0.0):
        self._phase = phase % (2 * math.pi)
        self._elapsed = 0.0
        self._last_t = t
        self._vx_smooth = self.vx
        self._vy_smooth = self.vy
        self._om_smooth = self.omega

    def neutral_pose_deg(self) -> list[float]:
        """Standing plant — same as ``standing_pose_degrees()`` (learned/default)."""
        try:
            from motor_setup.feetech_bus import standing_pose_degrees
            return standing_pose_degrees()
        except Exception:
            out: list[float] = []
            for _ in range(6):
                out.extend([0.0, self.plant_hip_deg, self.plant_knee_deg])
            return out

    def _advance(self, t: float) -> float:
        if self._last_t is None:
            self._last_t = t
            return 0.0
        dt = max(0.0, t - self._last_t)
        self._last_t = t
        self._elapsed += dt
        self._phase = (
            self._phase
            + 2 * math.pi * dt / max(self.period * self.period_scale, 0.05)
        ) % (2 * math.pi)
        return dt

    def _smoothed_command(self, dt: float):
        if dt <= 0.0:
            return self._vx_smooth, self._vy_smooth, self._om_smooth
        tau = 0.15
        a = 1.0 - math.exp(-dt / tau)
        self._vx_smooth += a * (self.vx - self._vx_smooth)
        self._vy_smooth += a * (self.vy - self._vy_smooth)
        self._om_smooth += a * (self.omega - self._om_smooth)
        return self._vx_smooth, self._vy_smooth, self._om_smooth

    def _classify_group_heavy(self, vx, vy, omega):
        """Which tripod-parity group (0 or 1) has MORE "amplified" legs
        on a combined tick, or ``None`` if not combined / tied. A leg is
        "amplified" if the true combined tangential magnitude in its own
        yaw-servo frame exceeds that same leg's pure-omega-only (vx=0)
        magnitude — the identical per-leg test ``combined_selective_
        omega_boost``/``combined_yaw_amplify_scale`` use inline, factored
        out here because ``combined_group_duty_skew`` needs it ONCE per
        tick (not per leg) and, critically, needs it evaluated at a
        FIXED reference progress point rather than the live per-leg
        ``prog`` — verified empirically (09-05 design pass) that the
        classification is ``prog``-independent (the ratio |y_yaw|/
        |y_turn| cancels the shared ``prog`` scale factor for any
        nonzero ``prog``), so any nonzero reference value gives the
        same, correct, phase-independent answer. Pure math, no gait
        state mutation — safe to call speculatively even when the knob
        is off (only called when it is not, see below)."""
        if abs(vx) <= 1e-9 or abs(omega) <= 1e-9:
            return None
        t_eff = max(self.period * self.period_scale, 0.05)
        prog_ref = 0.5
        counts = [0, 0]
        for i, a in enumerate(self.leg_angles):
            sa, ca = math.sin(a), math.cos(a)
            v_x_at = vx - omega * self._foot_radius_eff * sa
            v_y_at = vy + omega * self._foot_radius_eff * ca
            v_x_turn = -omega * self._foot_radius_eff * sa
            v_y_turn = omega * self._foot_radius_eff * ca
            dx_b = prog_ref * v_x_at * t_eff / 2.0 * self.stride_scale
            dy_b = prog_ref * v_y_at * t_eff / 2.0 * self.stride_scale
            dx_t = prog_ref * v_x_turn * t_eff / 2.0 * self.stride_scale
            dy_t = prog_ref * v_y_turn * t_eff / 2.0 * self.stride_scale
            _, y_yaw = self._yaw_frame_xy(dx_b, dy_b, a)
            _, y_turn = self._yaw_frame_xy(dx_t, dy_t, a)
            if abs(y_yaw) > abs(y_turn) + 1e-12:
                counts[i % 2] += 1
        if counts[0] == counts[1]:
            return None
        return 0 if counts[0] > counts[1] else 1

    def _foot_target_in_body(self, i: int, vx, vy, omega):
        t_eff = max(self.period * self.period_scale, 0.05)
        ramp_amp = min(self._elapsed / self.ramp, 1.0)
        tripod = 0 if i % 2 == 0 else 1
        _combined = abs(vx) > 1e-6 and abs(omega) > 1e-6
        if _combined and self.combined_group_duty_skew != 0.0:
            heavy = self._classify_group_heavy(vx, vy, omega)
        else:
            heavy = None
        if heavy is None:
            # Legacy path, BIT-EXACT: identical code/float ops to the
            # pre-09-05 file whenever the knob is off, not a combined
            # tick, or the amplified-leg split is tied 3/3 (no group is
            # "heavier" to favor).
            phi = (self._phase + self._phase_offset
                   + tripod * math.pi) % (2 * math.pi)
            if phi < math.pi:
                s = phi / math.pi
                prog = -0.5 + s
                dz = self.lift * self.lift_scale[i] * ramp_amp * math.sin(math.pi * s)
            else:
                s = (phi - math.pi) / math.pi
                prog = 0.5 - s
                dz = 0.0
        else:
            # Re-timed path: ONE shared boundary on the phase circle
            # splits it into the "group-0-swings" arc and the
            # "group-1-swings" arc, still an exact partition (always
            # exactly one group swinging) but with unequal widths —
            # see the __init__ docstring for the derivation. Theta is
            # the SAME quantity the legacy path calls ``phi`` for
            # tripod=0 (phase+phase_offset, no tripod term), so at
            # skew=0 (heavy would be None and this branch is unreached
            # anyway) the two paths agree exactly.
            theta = (self._phase + self._phase_offset) % (2 * math.pi)
            width0 = math.pi * (1.0 + (self.combined_group_duty_skew
                                       if heavy == 0 else
                                       -self.combined_group_duty_skew))
            width0 = _clip(width0, 0.05 * math.pi, 1.95 * math.pi)
            width1 = 2 * math.pi - width0
            group0_swinging = theta < width0
            leg_is_group0 = (tripod == 0)
            leg_swinging = (group0_swinging == leg_is_group0)
            if leg_swinging:
                own_width = width0 if leg_is_group0 else width1
                local = theta if leg_is_group0 else (theta - width0)
                s = local / own_width
                prog = -0.5 + s
                dz = self.lift * self.lift_scale[i] * ramp_amp * math.sin(math.pi * s)
            else:
                own_width = width1 if leg_is_group0 else width0
                local = (theta - width0) if leg_is_group0 else theta
                s = local / own_width
                prog = 0.5 - s
                dz = 0.0
        a_i = self.leg_angles[i]
        sa, ca = math.sin(a_i), math.cos(a_i)
        v_x_at = vx - omega * self._foot_radius_eff * sa
        v_y_at = vy + omega * self._foot_radius_eff * ca
        dx = prog * v_x_at * t_eff / 2.0 * ramp_amp * self.stride_scale
        dy = prog * v_y_at * t_eff / 2.0 * ramp_amp * self.stride_scale
        return dx, dy, dz

    def _yaw_frame_xy(self, dx_b: float, dy_b: float, a: float) -> tuple[float, float]:
        """Project a body-frame foot offset ``(dx_b, dy_b)`` for the leg
        planted at angle ``a`` into that leg's own yaw-servo frame
        (radial ``x_yaw`` / tangential ``y_yaw``). Shared by the main
        ``desired_deg`` computation and the ``combined_yaw_amplify_scale``
        per-leg reference lookup so both use IDENTICAL geometry."""
        fx_b = self._foot_radius_eff * math.cos(a) + dx_b
        fy_b = self._foot_radius_eff * math.sin(a) + dy_b
        yaw_origin_x = LEG_RADIAL * math.cos(a)
        yaw_origin_y = LEG_RADIAL * math.sin(a)
        rx = fx_b - yaw_origin_x
        ry = fy_b - yaw_origin_y
        ca, sa = math.cos(a), math.sin(a)
        x_yaw = ca * rx + sa * ry
        y_yaw = -sa * rx + ca * ry
        return x_yaw, y_yaw

    def desired_deg(self, t: float) -> list[float]:
        """18 joint angles in degrees for time ``t`` (seconds)."""
        dt = self._advance(t)
        vx, vy, omega = self._smoothed_command(dt)
        # candidate (i)-v2 yaw-arm scale (see __init__ docstring): only
        # active on a genuine combined tick (mirrors the identical
        # combined-tick gate used by train.bc_anchor_teacher_omega_boost
        # / probe_turn_authority --scripted-omega-boost), so pure-turn
        # and pure-walk ticks are bit-exact regardless of dose.
        _combined = abs(self.vx) > 1e-6 and abs(self.omega) > 1e-6
        yaw_arm_scale = (self.combined_yaw_arm_scale
                         if (_combined and self.combined_yaw_arm_scale != 1.0)
                         else 1.0)
        out: list[float] = []
        for i, a in enumerate(self.leg_angles):
            dx_b, dy_b, dz_b = self._foot_target_in_body(i, vx, vy, omega)
            # SELECTIVE per-leg omega boost (see __init__ docstring):
            # unlike yaw_arm_scale/amplify_scale, this changes the TRUE
            # foot target (dx/dy/dz), not just the yaw-angle denominator
            # -- only for legs the vx cross term ATTENUATES below their
            # own pure-omega-only magnitude, and only on a combined
            # tick. Runs BEFORE the yaw-angle reshaping levers below so
            # they compose on top of the (possibly boosted) true target
            # exactly like they compose with each other.
            if _combined and self.combined_selective_omega_boost != 1.0:
                x_yaw0, y_yaw0 = self._yaw_frame_xy(dx_b, dy_b, a)
                dx_t, dy_t, _ = self._foot_target_in_body(i, 0.0, vy, omega)
                x_turn, y_turn = self._yaw_frame_xy(dx_t, dy_t, a)
                if abs(y_yaw0) < abs(y_turn) - 1e-12:
                    dx_b, dy_b, dz_b = self._foot_target_in_body(
                        i, vx, vy, omega * self.combined_selective_omega_boost)
            x_yaw, y_yaw = self._yaw_frame_xy(dx_b, dy_b, a)
            # candidate (iii) combined_yaw_amplify_scale (see __init__
            # docstring): only multiplies THIS leg's denominator (on
            # top of the uniform yaw_arm_scale, if any) when the true
            # combined tangential magnitude exceeds the same leg's
            # pure-omega-only magnitude -- i.e. only legs the vx cross
            # term AMPLIFIES past pure-turn, never the attenuated ones.
            # Skipped entirely (bit-exact) when the dose is 1.0 or the
            # tick isn't combined, so it costs nothing by default.
            leg_yaw_arm_scale = yaw_arm_scale
            if _combined and self.combined_yaw_amplify_scale != 1.0:
                dx_t, dy_t, _ = self._foot_target_in_body(i, 0.0, vy, omega)
                x_turn, y_turn = self._yaw_frame_xy(dx_t, dy_t, a)
                if abs(y_yaw) > abs(y_turn) + 1e-12:
                    leg_yaw_arm_scale = (leg_yaw_arm_scale
                                         * self.combined_yaw_amplify_scale)
            # r_planar (hip/knee IK) always uses the TRUE (unscaled)
            # x_yaw/y_yaw -- only the yaw SERVO ANGLE's own atan2
            # denominator is scaled, so foot reach/height are never
            # touched by this knob, only the commanded yaw excursion.
            yaw_angle = math.atan2(y_yaw, x_yaw * leg_yaw_arm_scale)
            r_planar = math.hypot(x_yaw, y_yaw)
            ik = _leg_ik((r_planar, 0.0, self.foot_neutral_z + dz_b))
            if ik is None:
                yaw, pitch, knee = self._fallback
            else:
                pitch, knee = ik
                yaw = yaw_angle
            out.extend([math.degrees(yaw), math.degrees(pitch),
                        math.degrees(knee)])
        return out
