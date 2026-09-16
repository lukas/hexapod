"""Module-level reward/gate helpers of the balance env, moved verbatim out
of ``sim_env.py`` so the reward modules split from ``_step_finish`` can
import them without an import cycle: the valid-plant specification and
its footprint/support-margin geometry, the current/torque headroom and
action-rate prices, the lower depth fraction and the rise-reference
loader/cache.
"""
from __future__ import annotations

import numpy as np

from hexapod_core.joint_frame import JOINT_CONTRACT, FRAME_ROBOT_ABS
from rl_move.robot_state import DEG2RAD

# Rise-reference cache (reward.rise_ref_path): one load per process —
# the MJX vec envs build thousands of shims that share this module.
_RISE_REF_CACHE: dict[str, dict] = {}


def _load_robot_abs_q_npz(path: str, *, source: str) -> tuple[np.ndarray, object]:
    """Load a v2 joint trajectory/bank and reject unlabeled legacy data."""
    npz = np.load(path)
    frame = str(npz["joint_frame"]) if "joint_frame" in npz.files else None
    contract = (str(npz["joint_contract"])
                if "joint_contract" in npz.files else None)
    if frame != FRAME_ROBOT_ABS or contract != JOINT_CONTRACT:
        npz.close()
        raise ValueError(
            f"{source} {path}: expected {FRAME_ROBOT_ABS}/"
            f"{JOINT_CONTRACT}, got {frame}/{contract}; migrate or "
            "regenerate the artifact")
    return np.asarray(npz["q_rad"], dtype=float), npz


def load_rise_ref(path: str) -> dict:
    """npz with ``q_rad`` (T,18) joint trajectory of a known-good rise,
    ``dt`` (s/tick at recording) and ``ramp_i0`` (tick where the height
    ref leaves zero). Built by ``extract_rise_ref.py`` from a champion
    rollout (Stage-II reference, HumanUP/HoST style)."""
    ref = _RISE_REF_CACHE.get(path)
    if ref is None:
        q, z = _load_robot_abs_q_npz(path, source="rise_ref")
        if q.ndim != 2 or q.shape[1] != 18 or len(q) == 0:
            raise ValueError(
                f"rise_ref {path}: expected (T,18) q_rad, got {q.shape}")
        ref = {"q": q, "dt": float(z["dt"]), "ramp_i0": int(z["ramp_i0"])}
        # Per-tick chassis height above the start pose (newer extracts;
        # RSI needs it to command the REMAINING rise from a mid-path
        # spawn). Older npz lack it — RSI refuses, tracking still works.
        if "h_rel_m" in z.files:
            ref["h"] = np.asarray(z["h_rel_m"], dtype=float)
        z.close()
        _RISE_REF_CACHE[path] = ref
    return ref


def support_margin_m(feet_xy: np.ndarray, com_xy: np.ndarray) -> float:
    """Signed distance (m) from com_xy to the support-polygon boundary.

    Positive = inside (min distance to any edge), negative = outside.
    feet_xy: (N, 2) contact-foot positions. Needs N >= 3 non-collinear
    points; degenerate inputs return 0.0 (caller gates on contact count).
    Small-N convex hull via Andrew's monotone chain — no scipy.
    """
    pts = np.unique(np.round(np.asarray(feet_xy, dtype=float), 6), axis=0)
    if len(pts) < 3:
        return 0.0
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    cross = lambda o, a, b: ((a[0] - o[0]) * (b[1] - o[1])  # noqa: E731
                             - (a[1] - o[1]) * (b[0] - o[0]))
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(tuple(p))
    for p in pts[::-1]:
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(tuple(p))
    hull = lo[:-1] + up[:-1]          # CCW
    if len(hull) < 3:
        return 0.0                    # collinear feet: no polygon
    d = np.inf
    inside = True
    for i in range(len(hull)):
        a, b = np.array(hull[i]), np.array(hull[(i + 1) % len(hull)])
        e = b - a
        n = np.linalg.norm(e)
        if n < 1e-9:
            continue
        s = cross(a, b, com_xy) / n   # >0 = left of edge = inside (CCW)
        if s < 0:
            inside = False
        d = min(d, abs(s))
    return float(d if inside else -d)


def torque_headroom_debt_step(prev_debt: np.ndarray, current_abs: np.ndarray,
                               cap_a: float, margin_a: float,
                               alpha_d: float) -> np.ndarray:
    """One leaky-integrator update of the per-actuator torque-headroom
    "debt" (`reward.k_torque_headroom`, standwalk track 2026-09-11).

    ``redness`` is 0 outside a red zone that starts ``margin_a`` below the
    physical torque-saturation current ``cap_a`` and reaches 1 exactly at
    the rail. ``debt`` is an EMA of ``redness`` with time constant implied
    by ``alpha_d`` (``dt / tau_s``, pre-clipped to [0, 1] by the caller):
    it grows toward 1 only while the actuator dwells in the red zone and
    decays back toward 0 once it unloads, so a brief transient spike
    barely moves it while a SUSTAINED stall compounds. Pure/stateless
    (caller owns persistence + reset) so it can be unit-tested without a
    live physics/reward pipeline.
    """
    redness = np.clip(
        (np.abs(current_abs) - (cap_a - margin_a)) / max(margin_a, 1e-6),
        0.0, 1.0)
    return prev_debt + alpha_d * (redness - prev_debt)


def current_headroom_income_factor(cur_peak_a: float, cap_a: float,
                                    margin_a: float) -> float:
    """Instantaneous income-discount factor for
    ``reward.rise_score_income_headroom_gate`` (walkcurr track,
    2026-09-13 risebridge-s1 FAIL-MECHANISM escalation).

    Same "redness" shape as ``torque_headroom_debt_step`` (0 outside a
    red zone that starts ``margin_a`` below the physical
    torque-saturation current ``cap_a`` and reaches 1 exactly at the
    rail) but consumed directly as ``1 - redness`` -- an INCOME
    multiplier applied at the instant of the tick, not an integrated
    debt. The distinction matters: ``k_torque_headroom`` penalizes a
    SUSTAINED stall after the fact and did not stop a policy from
    banking the rise_score_prog income all the way to the current-limit
    trip; discounting the income itself denies the credit for the
    saturating push AT the moment it happens, while a later LOW-current
    path to the same score is unaffected (headroom_f == 1 there).  Pure/
    stateless (caller owns any state) so it is unit-testable without a
    live physics/reward pipeline.
    """
    redness = min(max((cur_peak_a - (cap_a - margin_a))
                       / max(margin_a, 1e-6), 0.0), 1.0)
    return 1.0 - redness


def lower_depth_frac(h_rel_m: float, h_target_m: float) -> float:
    """Fraction of a LOWER episode's own signed target depth reached so
    far (``reward.lower_score_prog``, walkcurr track, 2026-09-13
    ``lowerpartial-{s0,s1}`` FAIL-MECHANISM pair). ``h_rel_m`` is
    current chassis height relative to episode/segment start (sim_env's
    ``h_rel``); ``h_target_m`` is the episode's signed height target
    (negative for a lower episode -- sim_env's ``self._h_target``). Both
    are negative during a genuine descent, so their ratio is positive;
    clamped to [0, 1] (0 = at the start pose, 1 = at/past the target
    depth). Returns 0.0 for a non-lower target (``h_target_m >= 0``) so
    a caller can call this unconditionally without an extra branch.
    Pure/stateless -- the episode-level ratchet (best-depth-so-far) is
    the caller's job, same split as ``current_headroom_income_factor``.
    """
    if h_target_m >= 0.0:
        return 0.0
    return min(max(h_rel_m / h_target_m, 0.0), 1.0)


def action_rate_penalty(prev_action: np.ndarray,
                         action: np.ndarray) -> float:
    """Sum of squared per-joint normalized-action deltas between two
    consecutive ticks (``reward.k_action_rate``, standwalk track,
    2026-09-12 -- the "genuinely different structural mechanism" named
    after all 9 reward-pricing/schedule single-lever guesses on the
    dualbc7-...-termcost3 late-tail ``over_current`` collapse shared the
    same shape: a flat OR income-relative price on INSTANTANEOUS current
    never bounded it. ``safety.max_delta_q_deg`` already hard-clamps the
    per-tick joint-angle change, but does not forbid a policy from
    dithering right up against that clamp every tick (rapid direction
    reversal costs more RMS current for the same net displacement than a
    smooth hold/move, and is invisible to a pure instantaneous-current
    price) -- this charges the OUTPUT the policy actually chooses, not
    the clamp boundary, so a network that settles into micro-oscillating
    near a stall point pays for it directly regardless of whether that
    dithering happens to cross the over_current safety threshold.

    Both arguments are the already-clipped [-1, 1] normalized actions
    (same convention as ``self._prev_action``/``clipped`` in
    ``_step_finish``). Pure/stateless (caller owns persistence) so it is
    unit-testable without a live physics/reward pipeline.
    """
    return float(np.sum((np.asarray(action, dtype=np.float64)
                          - np.asarray(prev_action, dtype=np.float64)) ** 2))


# --------------------------------------------------------------------------
# Valid-plant specification (operator, 2026-08-10). "Standing" is a
# GEOMETRIC condition, not a torso height: every rise arm before this
# lost to a height-only cheat (flag-leg/tripod at height, b2p1; stilt
# pop, rfix-fresh1). A stand is VALID iff, at episode end:
#
#   height     |height_err| <= 15 mm of the commanded target
#   attitude   |roll| and |pitch| <= 10 deg (a stand is level;
#              the 25 deg envelope is for WALKING dynamics)
#   feet down  >= 5 of 6 pads within 20 mm of their grounded z
#   no flags   NO pad above 60 mm (a flag leg is never a stand)
#   support    robot CoM XY inside the down-feet support polygon
#              with >= 20 mm margin
#   footprint  mean body-frame foot XY within 40 mm of the walkable
#              plant footprint (the stance the walk champion expects;
#              rejects the stilt/splay family that passes height +
#              level + feet-down)
#   effort     max per-servo current <= 2.0 A (precarious poses fight;
#              informative once the holding-current model lands —
#              sim hold currents are ~5x under real today, SIM.md)
#
# One function, three consumers: the training reward gate, the eval
# harness (report + optional success gate), and the MDP_PREFLIGHT
# Fresh v2 rise banks must use these same canonical limits.

PLANT_SPEC = {
    "height_err_mm": 15.0,
    "attitude_deg": 10.0,
    "foot_down_mm": 20.0,
    "min_feet_down": 5,
    "flag_leg_mm": 60.0,
    "com_margin_mm": 20.0,
    "footprint_err_mm": 40.0,
    "max_current_a": 2.0,
}


def footprint_rent_m(fp_mm: float, free_mm: float) -> float:
    """Linear, UNBOUNDED per-tick rent (in metres) for footprint
    distance beyond ``free_mm``: 0 inside the free zone, growing
    1 mm-for-1 mm outside it with no upper saturation.

    Built 2026-09-11 as the "standalone anchor-distance penalty term
    outside the multiplicative plant_f product" the footprint-reprice-
    via-fade-shape DIG-IN asked for (CURRENT_TRUTHS "CLOSED: the
    footprint-reprice-via-fade-shape saga is dead", 2026-09-11 ~03:4x).
    That saga tried 4 reward-shape configs (legacy 40/80 fade, tightened
    25/40, widened 12/100, all with and without frozen exploration) and
    all 3-seed grids converged to the SAME 66-107mm footprint splay —
    because BOTH existing footprint terms stop charging the instant a
    policy settles at a steady, non-improving distance:
      - ``footprint_fade`` (a multiplicative INCOME gate) saturates to
        a constant <1.0 multiplier the policy can simply tolerate
        forever once other income streams outweigh the discount, and
      - ``k_curl_progress`` is POTENTIAL-based (pays only while
        distance is actively shrinking), so it is worth exactly 0 at
        any stable equilibrium, however far from the anchors.
    This function is additive and never saturates: a policy parked at a
    constant 90mm keeps paying the SAME rent every single tick for as
    long as it stays there, so unlike the fade/progress terms above,
    there is no distance at which "stop closing the gap" becomes free.
    """
    return max(0.0, fp_mm - free_mm) * 0.001


def footprint_fade(fp_mm: float, full_mm: float, zero_mm: float) -> float:
    """Full pay (1.0) at/below ``full_mm``, zero pay at/above ``zero_mm``,
    linear between. Legacy defaults (full=PLANT_SPEC['footprint_err_mm']=40,
    zero=2x that=80) reproduce the original rise-plant-factor footprint
    term bit-exact. Pulled out as a pure function (2026-09-11 stand50hz
    footprint-splay dig-in) so the fade band is directly unit-testable
    without stepping a sim: the legacy band pays FULL income at the exact
    40mm eval cliff and only starts fading OUTSIDE it, so nothing stops
    the reward optimum sitting just past the gate. cfg
    reward.rise_footprint_full_mm / rise_footprint_zero_mm move
    ``full_mm``/``zero_mm``; e.g. 25/40 makes the fade end exactly AT the
    gate cliff instead of starting there."""
    return min(max((zero_mm - fp_mm) / max(zero_mm - full_mm, 1e-9),
                    0.0), 1.0)


def valid_plant(*, pad_clear_m, feet_xy, com_xy,
                roll_rad, pitch_rad, height_err_m=None,
                footprint_err_m=None, max_current_a=None,
                spec: dict | None = None) -> tuple[bool, dict]:
    """PLANT_SPEC as a predicate. Returns (ok, detail); detail holds
    every sub-check so failures name themselves. None inputs skip
    their check (e.g. height when no target is commanded).
    ``feet_xy`` (6, 2) must be in the same frame as ``com_xy``; only
    the DOWN feet (clearance <= foot_down_mm) form the polygon."""
    s = dict(PLANT_SPEC)
    if spec:
        s.update(spec)
    clear_mm = np.asarray(pad_clear_m, dtype=float) * 1000.0
    down = clear_mm <= s["foot_down_mm"]
    n_down = int(np.sum(down))
    feet_down = np.asarray(feet_xy, dtype=float).reshape(-1, 2)[down]
    margin_mm = support_margin_m(
        feet_down, np.asarray(com_xy, dtype=float)) * 1000.0 \
        if n_down >= 3 else -1e9
    detail = {
        "height_ok": (True if height_err_m is None else
                      abs(height_err_m) * 1000.0 <= s["height_err_mm"]),
        "attitude_ok": (abs(roll_rad) <= s["attitude_deg"] * DEG2RAD
                        and abs(pitch_rad) <= s["attitude_deg"] * DEG2RAD),
        "feet_down_ok": n_down >= s["min_feet_down"],
        "no_flag_ok": float(np.max(clear_mm)) <= s["flag_leg_mm"],
        "support_ok": margin_mm >= s["com_margin_mm"],
        "footprint_ok": (True if footprint_err_m is None else
                         footprint_err_m * 1000.0
                         <= s["footprint_err_mm"]),
        "current_ok": (True if max_current_a is None else
                       max_current_a <= s["max_current_a"]),
        "n_feet_down": n_down,
        "com_margin_mm": round(float(margin_mm), 1),
        "max_clear_mm": round(float(np.max(clear_mm)), 1),
    }
    ok = all(v for k, v in detail.items() if k.endswith("_ok"))
    return bool(ok), detail
