"""`rl_only` lifecycle composition: rise+hold stance -> WALK-role
handoff, DIRECT (no scripted blend) -- the concrete "Next" item
`bundle_rlonly_stance_v1/GO_NOGO.md` named 2026-09-17 ("design and
build the rise+hold -> walk-ready handoff ... chaining two
independently trained rl_only roles instead of one any_means bundle").

THE QUESTION: `bundle_rlonly_stance_v1` (rise-from-flat + hold) and
`bundle_rlonly_v2` (forward walk) are two SEPARATELY trained clean-RL
checkpoints -- RL_GOALS.md explicitly allows composing them instead of
requiring one monolithic actor, but nobody had ever run the walk
champion on the stance role's own settled physical state. Does it work
without a scripted joint-blend (a "scripted motion role", banned from
the rl_only lineage per tracks.json), or does the walk champion
stumble on the handoff?

WHY TWO ENV INSTANCES, NOT ONE: the two checkpoints' own training
recipes use materially DIFFERENT actuator/safety cfg (bus.write_speed
1024-default vs 4096, safety.max_delta_q_deg 0.75 vs 7.2,
goal.joint_action_bias_{hip,knee}_deg 30.9/36.1 vs 40.0/35.0) --
SimServoParams/SafetyLayer cache these at env __init__, so a single
live env can't hot-swap them mid-episode. Two ``SimHexapodJointWalkEnv``
instances (same MJCF, same qpos/qvel layout -- the class hierarchy is
literally SimHexapodJointWalkEnv(SimHexapodJointGoalEnv), see
joint_task.py/walk_task.py) are built, one per role's own recorded
cfg-set (stance: probe_currentcap29_flatonly's BASE_CFG_ARGS +
FLATONLY_OVERRIDE_ARGS, the ONLY validated stance regime; walk:
cfg_recipe_walk50hz_rlonly_v2.CFG_ARGS). At the handoff tick the raw
PHYSICAL state (qpos/qvel/ctrl/act + the safety layer's `_last_safe`
slew memory, all in physical units, model-independent) is copied
across -- exactly ``eval_handoff.py``'s established
``reanchor_keep_state()`` trick (same-env case), generalized to a
cross-env copy. This is role-selection/config-selection plumbing (RL_
GOALS.md's allowed non-motion category), not a scripted motion role:
no joint trajectory is scripted, the SAME physical state is kept, only
which policy (and which policy's OWN safety/actuator envelope) is live
changes.

Two arms per episode:

  direct   stance runs a genuine flat-start rise+hold episode to a
           settled hold, then the WALK checkpoint takes over directly
           on the stance's exact physical state (bookkeeping re-anchor
           only, per RL_GOALS.md-allowed plumbing).
  plant    control: walk champion from its OWN clean plant reset, same
           drive schedule -- defines the noise band / "what a perfect
           handoff would look like" reference.

Usage:
    uv run python -m rl_move.sim.eval_lifecycle_handoff_rlonly \\
        --stance rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_klrollback05_acq15m.zip \\
        --walk   rl_move/sim/policies/ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1.zip \\
        --episodes 6 --out logs/ckpt_eval/lifecycle_handoff_rlonly.json \\
        --strips logs/ckpt_eval/lifecycle_handoff_rlonly_strips

Verdict: direct is CLEAN if handoff_falls==0 and its drive metrics sit
inside the plant arm's band (same rule of thumb as eval_handoff.py).
This eval does NOT claim `lower` (still closed) or a full sit-walk-sit
cycle -- rise+hold -> walk only, matching what the two source bundles
actually cover.

FULL-DIRECTION EXTENSION (2026-09-20, walkcurr): the original tool only
ever drove straight forward (vx=speed, vy=0) -- fine for validating the
handoff mechanic itself, but `bundle_rlonly_lifecycle_v1` is otherwise
the composed rise+hold->walk demo Goal 2 ("full-direction joystick
walking plus rise/hold/lower") would point to, and it had never been
run at any other heading. The walk champion's own OFF-forward headings
are the already-closed 13/13-mechanism chronic front-pair-sacrifice
failure (bundle_rlonly_v2/GO_NOGO.md); `rot60_fullcircle` already
proved wrapping that SAME checkpoint in `rot60.Rot60Policy` removes it
(0 falls/16 episodes, sustained 60s, full heading set) but only for the
walk role in isolation, starting from ITS OWN clean plant reset, never
composed after a real rise+hold handoff. Two new, bit-exact-when-unset
flags close that gap: ``--heading-deg`` (default 0.0 = old forward-only
behavior) drives at an arbitrary commanded heading instead of pure
forward, and ``--rot60`` (default off) wraps the walk policy in
``Rot60Policy`` before driving (the SAME wrapper/checkpoint
`rot60_fullcircle` validated, zero retrain). This is composition/
role-selection plumbing, not a new scripted motion role -- the wrapper
only permutes which of the walk champion's OWN already-trained actions
applies to which leg index, per `rot60.py`'s own exact-symmetry
argument.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import DEG2RAD, N_JOINTS, over_current_reading

PHASE_A_S = 12.5     # stance rise+settle horizon (mirrors eval_handoff.py)
STUMBLE_S = 2.0
DEFAULT_HOLD_S = 6.0   # matches the original forward-only default exactly


def schedule(vx: float, vy: float, hold_s: float = DEFAULT_HOLD_S):
    return [(1.0, 0.0, 0.0), (hold_s, vx, vy), (2.0, 0.0, 0.0)]
CONTACT_N = 0.5   # SAME threshold eval_checkpoint.py uses for touch contact


def sacrificed_legs(contact: np.ndarray, pad_xy: np.ndarray) -> list[int]:
    """Identical formula to ``eval_checkpoint.py``'s walk-mode
    gait-validity gate (guardrails, external review Sec 5b): a leg is
    sacrificed if it is airborne (duty<0.10, a parked flag leg) or
    grounded the whole window with zero swings (duty>0.95, a dragged
    anchor). ``contact``: (T,6) bool, ``pad_xy``: (T,6,2) world xy.
    Pure array function, reused here (not re-derived) so the composed
    lifecycle's own pathology read is directly comparable to every
    other gait_valid number in this codebase."""
    duty = contact.mean(axis=0)
    swings = np.zeros(6, dtype=int)
    for f in range(6):
        d = np.diff(contact[:, f].astype(int))
        swings[f] = int(np.sum(d == -1))
    return [f for f in range(6)
            if duty[f] < 0.10 or (duty[f] > 0.95 and swings[f] == 0)]


def joint_label(j: int) -> str:
    """``"L<leg> <axis>"`` for joint index ``j`` (0-17) -- same naming
    convention as ``safety._joint_name`` (not imported directly so this
    module keeps its existing zero extra-import footprint over
    ``hexapod_core.joint_frame``), reused here so forensics output
    reads in the same vocabulary as a live ``over_current`` safety-trip
    log line."""
    from hexapod_core.joint_frame import axis_of, leg_of
    return f"L{leg_of(j)} {axis_of(j)}"


def trip_summary(current_trace: np.ndarray, max_current: float,
                 qvel_trace: np.ndarray | None = None,
                 height_trace_mm: np.ndarray | None = None,
                 stall_qvel: float = 0.05,
                 min_height_delta_mm: float = 5.0,
                 qpos_trace: np.ndarray | None = None,
                 joint_limit_rad: np.ndarray | None = None,
                 near_limit_margin_rad: float = 0.05) -> dict:
    """Walkcurr/todaypolicy over_current FORENSICS (2026-10-01): pure
    array analysis of a (T, 18) trip-relevant current trace (the SAME
    signal ``SafetyLayer`` keys its ``over_current`` termination on --
    ``over_current_signal`` if present else ``servo_current``, see
    ``robot_state.over_current_reading``), answering "which joint
    tripped, and how long had it already been hot" for one failing
    episode. No mujoco/env dependency -- testable with a synthetic
    array.

    Returns (all per-joint arrays length 18):
      per_joint_max       -- max |current| over the whole trace
      per_joint_max_tick   -- tick index of that max
      final_joint          -- argmax(|current|) at the LAST tick (the
                               joint the safety layer was tracking when
                               the episode ended, matching its own
                               ``max(current_ids, key=...)`` rule)
      final_joint_label    -- "L<leg> <axis>" for ``final_joint``
      final_current_a      -- that joint's current at the last tick
      hot_run_ticks        -- length of the trailing run of consecutive
                               ticks (ending at the last tick) where
                               ``final_joint`` alone already exceeded
                               ``max_current`` (how long it was already
                               cooking before the trip, in ticks)
      trip_frac            -- (last tick index + 1) / T, i.e. how far
                               through the captured trace the trip
                               landed (this trace already stops AT
                               termination, so this is always 1.0 for a
                               genuinely-terminated trace; kept as a
                               named field so a caller slicing a longer
                               held trace can reuse this function)

    OPTIONAL stall corroboration (2026-10-01, forensics follow-up): per
    the operator's 2026-09-04 ``audit_over_current.py`` directive, "a
    bit-exact 2.64 A trip is the torque-estimator's RAIL IMAGE, not
    independent evidence of an unsafe stall" -- the lower-role
    forensics item never applied that same corroboration to its own
    over_current count. When ``qvel_trace`` (T, 18) -- the SAME joints,
    actuated-only, no floating-base offset -- and ``height_trace_mm``
    (T,) are both given, classify the trailing ``hot_run_ticks`` window
    on ``final_joint`` the same way ``audit_over_current.classify_trace``
    does for a genuine stall, but WITHOUT the npz/lowpass-deconvolution
    machinery (this trace already IS the exact trip signal, not a
    torque proxy needing inversion) and without the rising-only height
    bias (a descent counts as "progressing" too, not just a rise):
      hot_qvel_med_rad_s        -- median |qvel| of final_joint over
                                    the trailing hot window
      hot_window_height_delta_mm -- signed chassis-height change over
                                    that same window
      stall_classification      -- "CORROBORATED_STALL" if the joint
                                    was essentially static (median
                                    |qvel| < stall_qvel) AND the body
                                    made no progress (|height delta| <=
                                    min_height_delta_mm) over the
                                    window; else "RAIL_MOVING" (hot but
                                    still doing work -- not dispositive
                                    evidence of an unsafe stall per the
                                    same operator directory).
    Omitted entirely (no keys added) when either optional array is None
    -- existing callers/tests are unaffected.

    OPTIONAL joint-limit proximity (2026-10-01, L1-hip root-cause
    follow-up named in ``lowerrole_overcurrent_systemid_2026-10-01/
    SUMMARY.md``): answers "is ``final_joint`` being driven toward its
    MuJoCo hinge range limit (an architecture/bias artifact), or is it
    sitting mid-range fighting an asymmetric load with room to move (a
    reward-pricing/coordination artifact)?" When ``qpos_trace`` (T, 18,
    raw MuJoCo hinge angle -- NOT the robot_abs logical convention;
    ``jnt_range`` bounds this coordinate directly) and
    ``joint_limit_rad`` ((18, 2), ``(lo, hi)`` per joint, e.g.
    ``model.jnt_range[joint_ids(model)]``) are both given, adds:
      hot_qpos_med_rad       -- median qpos of ``final_joint`` over the
                                 same trailing hot window used above
      joint_limit_lo_rad/joint_limit_hi_rad -- that joint's own range
      limit_margin_rad       -- distance from ``hot_qpos_med_rad`` to
                                 the NEARER of the two bounds (can be
                                 negative only from float roundoff at an
                                 exact limit; MuJoCo clamps qpos inside
                                 ``jnt_range`` so this is >=0 in practice)
      near_joint_limit       -- True if ``limit_margin_rad <
                                 near_limit_margin_rad`` (default 0.05
                                 rad ~= 2.9 deg) -- a real "pinned at the
                                 mechanical stop" reading, not a loose
                                 threshold tuned to the data.
    Omitted when either array is None, independent of the qvel/height
    option above (a caller can supply one, both, or neither).
    """
    arr = np.abs(np.asarray(current_trace, dtype=float))
    if arr.ndim != 2 or arr.shape[0] == 0:
        raise ValueError("current_trace must be a non-empty (T, 18) array")
    t_last = arr.shape[0] - 1
    per_joint_max = arr.max(axis=0)
    per_joint_max_tick = arr.argmax(axis=0)
    final_joint = int(np.argmax(arr[t_last]))
    final_current_a = float(arr[t_last, final_joint])
    hot_run = 0
    for t in range(t_last, -1, -1):
        if arr[t, final_joint] > max_current:
            hot_run += 1
        else:
            break
    out = {
        "per_joint_max": per_joint_max.round(3).tolist(),
        "per_joint_max_tick": per_joint_max_tick.tolist(),
        "final_joint": final_joint,
        "final_joint_label": joint_label(final_joint),
        "final_current_a": round(final_current_a, 3),
        "hot_run_ticks": hot_run,
        "trip_frac": round((t_last + 1) / arr.shape[0], 4),
    }
    if qvel_trace is not None and height_trace_mm is not None:
        qarr = np.asarray(qvel_trace, dtype=float)
        if qarr.shape[0] != arr.shape[0]:
            raise ValueError("qvel_trace must have the same T as "
                             "current_trace")
        harr = np.asarray(height_trace_mm, dtype=float)
        if harr.shape[0] != arr.shape[0]:
            raise ValueError("height_trace_mm must have the same T as "
                             "current_trace")
        w0 = t_last - hot_run + 1 if hot_run > 0 else t_last
        hot_qvel_med = float(np.median(np.abs(qarr[w0:t_last + 1,
                                                    final_joint])))
        h_window = harr[w0:t_last + 1]
        h_delta = (float(h_window[-1] - h_window[0])
                  if h_window.shape[0] > 1 else 0.0)
        static = hot_qvel_med < stall_qvel
        progressing = abs(h_delta) > min_height_delta_mm
        out["hot_qvel_med_rad_s"] = round(hot_qvel_med, 4)
        out["hot_window_height_delta_mm"] = round(h_delta, 2)
        out["stall_classification"] = ("CORROBORATED_STALL"
                                       if static and not progressing
                                       else "RAIL_MOVING")
    if qpos_trace is not None and joint_limit_rad is not None:
        qparr = np.asarray(qpos_trace, dtype=float)
        if qparr.shape[0] != arr.shape[0]:
            raise ValueError("qpos_trace must have the same T as "
                             "current_trace")
        lim = np.asarray(joint_limit_rad, dtype=float)
        if lim.shape != (arr.shape[1], 2):
            raise ValueError("joint_limit_rad must have shape (n_joints, 2)")
        w0 = t_last - hot_run + 1 if hot_run > 0 else t_last
        hot_qpos_med = float(np.median(qparr[w0:t_last + 1, final_joint]))
        lo, hi = float(lim[final_joint, 0]), float(lim[final_joint, 1])
        margin = min(hot_qpos_med - lo, hi - hot_qpos_med)
        out["hot_qpos_med_rad"] = round(hot_qpos_med, 4)
        out["joint_limit_lo_rad"] = round(lo, 4)
        out["joint_limit_hi_rad"] = round(hi, 4)
        out["limit_margin_rad"] = round(margin, 4)
        out["near_joint_limit"] = bool(margin < near_limit_margin_rad)
    return out


def heading_to_vxvy(speed: float, heading_deg: float) -> tuple[float, float]:
    """Commanded (vx, vy) for a body-frame heading in degrees, 0 = pure
    forward (matches ``eval_checkpoint.py``'s ``_HEADING_LABELS``
    convention: 0/+-45/+-90/+-135/180). Pure function, no env/model
    dependency, so it's testable without mujoco."""
    rad = math.radians(heading_deg)
    return speed * math.cos(rad), speed * math.sin(rad)


def write_mp4(frames: list, path: Path, fps: int) -> None:
    """Write ``frames`` (list of HxWx3 uint8 arrays) to ``path`` as an
    mp4 at ``fps``. Pure I/O helper, no env/model dependency, so it is
    testable with plain numpy arrays -- same convention as
    ``eval_checkpoint.py``'s ``_save_video`` (macro_block_size=1 so
    non-multiple-of-16 render resolutions don't get silently cropped),
    kept as a standalone function here rather than importing that
    module's private helper (this tool has no other dependency on
    ``eval_checkpoint``).  No-op on an empty frame list (caller's
    responsibility to skip the call, mirrored here defensively)."""
    import imageio
    if not frames:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, frames, fps=fps, macro_block_size=1)


def _set_mix(gen, **p) -> None:
    for attr in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, attr, 0.0)
    gen.p_walk = 0.0
    for k, v in p.items():
        setattr(gen, f"p_{k}", v)


@dataclass
class PhysicalState:
    """Raw, model-independent physical state carried across a role
    handoff -- everything a real hardware controller would ALSO carry
    across a policy swap (joint angles/velocities, the actuator's live
    ctrl/act, and the safety layer's slew memory), nothing task/reward
    specific."""
    qpos: np.ndarray
    qvel: np.ndarray
    ctrl: np.ndarray
    act: np.ndarray | None
    last_safe: np.ndarray


def capture_physical_state(env) -> PhysicalState:
    d = env.data
    return PhysicalState(
        qpos=d.qpos.copy(), qvel=d.qvel.copy(), ctrl=d.ctrl.copy(),
        act=(d.act.copy() if d.act.size else None),
        last_safe=env.safety._last_safe.copy())


def zeroed_qvel_state(state: PhysicalState) -> PhysicalState:
    """DIAGNOSTIC ablation, not a production handoff variant (see
    ``--diag-zero-lower-qvel``): returns a COPY of ``state`` with
    ``qvel`` zeroed and every other field untouched. Root-causes the
    walkcurr 2026-09-24 ~13:0x s0 composition-fall finding's own named
    leading suspect -- but re-reads it as CARRIED MOMENTUM, not
    "servo current state" literally: the walk gait's real mid-stride
    joint/root velocities are exactly the kind of initial condition
    the `lower`-role SAC recipe's own isolated-gate reset (always a
    static, zero-velocity post-rise hold, never a moving leg) never
    trained against. Zeroing qvel at the handoff isolates that one
    variable; it is a diagnostic probe of WHY composition fails, not
    a proposed fix (a real fix is retraining `lower` with nonzero-
    velocity initial states in its own curriculum, not silently
    stripping momentum in an eval harness). Pure array function, no
    mujoco/env dependency, so it is testable without a live model."""
    return PhysicalState(qpos=state.qpos.copy(),
                          qvel=np.zeros_like(state.qvel),
                          ctrl=state.ctrl.copy(),
                          act=(state.act.copy() if state.act is not None
                               else None),
                          last_safe=state.last_safe.copy())


def apply_physical_state(env, state: PhysicalState) -> None:
    """Overwrite ``env``'s live physical state in place. Caller must
    call ``mujoco.mj_forward`` + rebuild ``env._state``/obs afterward
    (kept OUT of this function so it stays pure-array and testable
    without a live mujoco model)."""
    d = env.data
    d.qpos[:] = state.qpos
    d.qvel[:] = state.qvel
    d.ctrl[:] = state.ctrl
    if state.act is not None and d.act.size:
        d.act[:] = state.act
    env.safety._last_safe = state.last_safe.copy()


def _compose_lower_cfg_args(recipe_cfg_args: list[str],
                             extra_cfg: list[str] | None) -> list[str]:
    """``--lower-recipe``'s own fixed CFG_ARGS list, plus any ``--lower-
    cfg`` overrides appended after it (so cfg_set's own later-duplicate-
    key-wins parsing lets an override win). Pulled out of ``main()`` so
    this plumbing (the actual fix for the train/eval cfg-mismatch bug
    found 2026-10-02 on the hippitchmax lower-role arms) is unit-
    testable without constructing a real mujoco env."""
    return list(recipe_cfg_args) + list(extra_cfg or [])


def _build_env(cfg_args: list[str], *, episode_seconds: float, seed: int,
               render: bool):
    from rl_move.config import load_config
    from .cfg_set import parse_cfg_set
    from .servo_model import SimServoParams
    from .walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for key, parsed in parse_cfg_set(cfg_args).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), cfg=cfg, randomize=False,
        episode_seconds=episode_seconds, seed=seed,
        render_mode="rgb_array" if render else None)
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stance", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_stance50hz_rlonly_currentcap29_"
                                 "s5_klrollback05_acq15m.zip"))
    ap.add_argument("--walk", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_"
                                 "warmadapt_acq1.zip"))
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--speed", type=float, default=0.06)
    ap.add_argument("--hold-s", type=float, default=DEFAULT_HOLD_S,
                     help="seconds the commanded heading is held after "
                          "the 1s settle+before the 2s stop (default "
                          "6.0 = old behavior; the closed chronic "
                          "off-forward sacrifice mechanism is a "
                          "SUSTAINED (>10s) pathology, so a full-"
                          "heading check needs a longer hold than the "
                          "original forward-only smoke duration)")
    ap.add_argument("--heading-deg", type=float, default=0.0,
                     help="commanded body-frame heading in degrees, "
                          "0=forward (default, matches the original "
                          "forward-only behavior bit-exactly); "
                          "+-45/+-90/+-135/180 match eval_checkpoint.py's "
                          "PINNED_HEADING_DEFAULTS convention")
    ap.add_argument("--rot60", action="store_true",
                     help="wrap the WALK policy in rot60.Rot60Policy "
                          "(default off = bit-exact unwrapped champion) "
                          "-- the same wrapper rot60_fullcircle already "
                          "validated removes the chronic off-forward "
                          "front-pair-sacrifice failure, tested here "
                          "AFTER a real rise+hold handoff instead of "
                          "the walk role's own isolated clean reset")
    ap.add_argument("--walk-recipe",
                     choices=("rlonly_v2", "slew_smooth_s0",
                              "safewiden6_acq1"),
                     default="rlonly_v2",
                     help="which versioned walk-role cfg-set recipe to "
                          "build env_walk from (default rlonly_v2 = "
                          "bit-exact original behavior, the "
                          "bundle_rlonly_v2/crutchoff-s0-warmadapt-acq1 "
                          "champion's own trained contract); "
                          "slew_smooth_s0 = the promoted "
                          "cw-walk50hz-slew-smooth-s0 hardware-transfer "
                          "reference's own trained contract; "
                          "safewiden6_acq1 = the fs-bisect 5-group "
                          "safe-widen DR-robustness alternative "
                          "(cw-walk50hz-fs-bisect-drv-safewiden6-acq1, "
                          "21/24 gait_valid) -- pass --walk pointing at "
                          "the matching checkpoint's .zip too when "
                          "using either non-default recipe")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--strips", type=Path, default=None,
                    help="dir for 1 fps frame-strip PNGs (episode 0 of "
                         "each arm)")
    ap.add_argument("--video", type=Path, default=None,
                    help="dir for full-fps <arm>_<ep>.mp4 (episode 0 of "
                         "each arm; default None = no video rendered, "
                         "matches the pre-2026-09-20 tool exactly). "
                         "Polish item named in bundle_rlonly_lifecycle_v1/"
                         "GO_NOGO.md's own 09-20 Next list ('an mp4, not "
                         "just 1fps strips, would make the demo easier "
                         "to show')")
    ap.add_argument("--stochastic", action="store_true",
                    help="sample both policies stochastically instead "
                         "of deterministic (default det, matches the "
                         "stance bundle's own det gate)")
    ap.add_argument("--lower", type=Path, default=None,
                    help="OPTIONAL 3rd role: after the walk drive "
                         "schedule ends (direct AND plant arms), hand "
                         "off the walk episode's own physical state to "
                         "a genuinely distinct `lower`-role checkpoint "
                         "(same cross-env reanchor trick as the "
                         "rise->walk handoff -- role-selection "
                         "plumbing, not a scripted motion role) and "
                         "drive it for its own full training episode. "
                         "Default None = fully bit-exact old rise->walk"
                         "-only behavior (this track's own historical "
                         "'lower still closed' limitation). Currently "
                         "only the cw-stance50hz-rlonly-lowerrole-"
                         "scratch-sac-*-drramp-acq1 cfg-set recipe is "
                         "wired (--lower-recipe); pass a checkpoint "
                         "trained on that exact recipe.")
    ap.add_argument("--lower-recipe", choices=("lowerrole_sac_drramp",),
                    default="lowerrole_sac_drramp",
                    help="which versioned lower-role cfg-set recipe to "
                         "build env_lower from (only one registered so "
                         "far -- see cfg_recipe_stance50hz_rlonly_"
                         "lowerrole_scratch_sac_drramp.py)")
    ap.add_argument("--lower-episode-s", type=float, default=15.0,
                    help="lower-role episode length in seconds, "
                         "matching this recipe's own trained "
                         "--episode-seconds (default 15.0)")
    ap.add_argument("--lower-cfg", action="append", default=None,
                    help="EXTRA cfg-set override(s) (k=v, repeatable) "
                         "applied ON TOP OF --lower-recipe's own "
                         "versioned CFG_ARGS when building env_lower. "
                         "Default None = bit-exact legacy behavior "
                         "(recipe's CFG_ARGS only). Needed whenever the "
                         "--lower checkpoint was actually trained with "
                         "a NEW safety/env cfg key that postdates the "
                         "fixed recipe module's own verbatim list (e.g. "
                         "safety.hip_pitch_max_deg=29.8 for the "
                         "2026-10-02 hippitchmax lower-role arms) -- "
                         "without this, env_lower silently reverts to "
                         "the OLD/default value for that key, a real "
                         "train/eval cfg mismatch the recipe module's "
                         "own fixed-list design (by construction) can't "
                         "catch. Root-caused 2026-10-02: the "
                         "hippitchmax-acq1-r2-cont1 composed gate read "
                         "0/36 lower_ok on BOTH direct and (same-role-"
                         "clean-reset) plant arms, a uniformity that "
                         "pointed at an eval-env construction bug "
                         "rather than genuine policy failure.")
    ap.add_argument("--lower-rot60", action="store_true",
                    help="wrap the `lower` role in "
                         "rot60_lower.Rot60LowerPolicy, sector k fixed "
                         "at the walk->lower handoff from the WALK "
                         "role's own final rot60.Rot60Policy.k (default "
                         "off = bit-exact unwrapped lower checkpoint). "
                         "Requires --rot60 and --lower both set (the "
                         "walk role must itself be sector-canonicalized "
                         "for there to be a k to read). Scoped fix for "
                         "the 2026-10-03 heading-sign forensics finding "
                         "(walkcurr/STATUS.md Next 1): the composed "
                         "`lower_ok` collapse on NEGATIVE headings is "
                         "hypothesized to be a frame-alignment mismatch "
                         "between the walk role's own canonical frame "
                         "and the lower role's fixed real-leg habit, "
                         "not a lower-role training defect -- see "
                         "rot60_lower.py's module docstring for the "
                         "full argument.")
    ap.add_argument("--lower-specialist", type=Path, default=None,
                    help="OPTIONAL composed sub-controller (2026-10-04, "
                         "walkcurr/STATUS.md Next 6, lowerrole_"
                         "terminal_support_forensics_2026-10-02 item 1): "
                         "a SEPARATELY trained terminal-hold specialist "
                         "checkpoint (goal.lower_term_bank + "
                         "goal.lower_term_start_frac=1.0 at train time) "
                         "that takes over from --lower at a fixed tick "
                         "(--lower-specialist-switch-s) for the "
                         "remainder of the lower-phase episode, via "
                         "two_stage_lower_policy.TwoStageLowerPolicy. "
                         "Default None = bit-exact single-checkpoint "
                         "--lower behavior. Requires --lower.")
    ap.add_argument("--lower-specialist-switch-s", type=float,
                    default=7.0,
                    help="wall-clock seconds into the lower-phase "
                         "episode at which control switches from "
                         "--lower to --lower-specialist (default 7.0 = "
                         "the lowerrole_sac_drramp recipe's own fixed "
                         "goal.lower_hold_s=1.0 + default goal."
                         "lower_ramp_s=5.0 ramp-completion tick plus a "
                         "1.0s settle margin -- recompute if either "
                         "recipe default changes). Ignored when "
                         "--lower-specialist is unset.")
    ap.add_argument("--diag-zero-lower-qvel", action="store_true",
                    help="DIAGNOSTIC ONLY (default off = bit-exact): "
                         "zero qpos/qvel's velocity component at the "
                         "walk->lower handoff before dropping it into "
                         "env_lower, isolating whether CARRIED MOMENTUM "
                         "(not qpos/ctrl/act) is why some seeds fall "
                         "under composition that don't fall in their "
                         "own isolated gate. Root-cause probe named in "
                         "walkcurr/STATUS.md 2026-09-24 ~13:0x Next(2); "
                         "not a proposed production handoff -- a real "
                         "fix belongs in the lower role's own training "
                         "curriculum, not this eval harness.")
    ap.add_argument("--current-trace-dir", type=Path, default=None,
                    help="DIAGNOSTIC ONLY (default None = off, zero "
                         "extra cost/output when unset): for every "
                         "FAILED lower-phase episode (lower_fall is "
                         "not None), write "
                         "<dir>/<arm>_<ep>_<lower_fall>.json with the "
                         "full per-tick (T,18) trip-relevant current "
                         "trace (the same signal the SafetyLayer trips "
                         "on, robot_state.over_current_reading) plus "
                         "``trip_summary()`` (which joint, how long it "
                         "was already hot) and the walk-exit qpos/qvel "
                         "fed into the lower role, for the walkcurr/"
                         "todaypolicy over_current FORENSICS item "
                         "(STATUS.md Next 1): which joints trip, at "
                         "what phase, from which walk-exit pose. Also "
                         "captures the per-tick raw MuJoCo hinge qpos "
                         "trace + the model's own jnt_range table so "
                         "trip_summary can classify the hot joint as "
                         "pinned-at-its-mechanical-limit vs mid-range "
                         "(2026-10-01 L1-hip root-cause follow-up).")
    ap.add_argument("--minload-trace-dir", type=Path, default=None,
                    help="DIAGNOSTIC ONLY (default None = off, zero "
                         "extra cost/output when unset): for EVERY "
                         "lower-phase episode regardless of outcome "
                         "(unlike --current-trace-dir, which only "
                         "dumps FAILED episodes), write "
                         "<dir>/<arm>_<ep>_<lower_ok|lower_fall>.json "
                         "with the per-tick worst-over-feet touch force "
                         "(env._minload_min_force_now(floor_n), the "
                         "EXACT quantity the hold_min_load EMA tracks) "
                         "plus the per-leg raw touch-sensor forces. "
                         "Lets an offline replay check candidate "
                         "min-over-feet-force termination thresholds "
                         "against HEALTHY direct-arm episodes without "
                         "spending GPU per candidate -- this is how "
                         "the 2026-10-01 `hold_min_load_apply_lower` "
                         "LOWER-mode extension was shown to false-fire "
                         "on ~100pct of ticks of every lower episode "
                         "(walkcurr/STATUS.md Next 1); that cfg key "
                         "was removed 2026-10-02 once its motivating "
                         "run (minloadlower-acq1) was verdicted and not "
                         "adopted, but this trace tool stays generically "
                         "useful for any future load-based candidate.")
    ap.add_argument("--term-bank-harvest-out", type=Path, default=None,
                    help="DIAGNOSTIC/DATA-COLLECTION ONLY (default None "
                         "= off, zero extra cost/behavior change when "
                         "unset): harvest a `goal.lower_term_bank`-"
                         "compatible npz (q_rad robot_abs, qvel_mujoco, "
                         "target_m -- same format as harvest_lower_"
                         "term_bank.py's output) from THIS composed "
                         "rise->walk->lower run's own REAL per-tick "
                         "trajectory, instead of an isolated standalone "
                         "lower-only episode. Samples every --term-bank-"
                         "sample-every-s seconds starting at --lower-"
                         "specialist-switch-s (the same tick a two-stage "
                         "specialist would take over) through episode "
                         "end, from every episode (both arms) that ends "
                         "lower_ok, using whatever --lower checkpoint is "
                         "driving (do NOT also pass --lower-specialist "
                         "when harvesting -- the point is to capture the "
                         "champion's OWN genuine composed post-switch-"
                         "tick trajectory, not a specialist's). Fixes "
                         "the termspecialist-sac-s0-canary2m CANARY FAIL "
                         "- MECHANISM root cause (2026-10-04): the "
                         "original harvest_lower_term_bank.py draws "
                         "states from an ISOLATED lower-only episode "
                         "(no walk handoff) at t>=7.5s, while the "
                         "composed eval switches control at t=7.0s -- "
                         "both a different entry-state distribution AND "
                         "a tick the old bank never covered at all.")
    ap.add_argument("--term-bank-sample-every-s", type=float, default=0.3,
                    help="sampling period for --term-bank-harvest-out "
                         "(default 0.3s, matches harvest_lower_term_"
                         "bank.py's own default)")
    args = ap.parse_args()
    if args.lower_rot60 and not (args.rot60 and args.lower is not None):
        ap.error("--lower-rot60 requires both --rot60 and --lower")
    if args.term_bank_harvest_out is not None and args.lower is None:
        ap.error("--term-bank-harvest-out requires --lower")

    import mujoco

    from hexapod_core.joint_frame import (
        FRAME_ROBOT_ABS, JOINT_CONTRACT, mujoco_rel_rad_to_robot_abs_deg,
    )
    from rl_move.env import build_obs
    from .gru_policy import load_checkpoint_auto, wrap_recurrent_predictor
    if args.walk_recipe == "slew_smooth_s0":
        from .cfg_recipe_walk50hz_slew_smooth_s0 import (
            CFG_ARGS as WALK_CFG_ARGS,
        )
    elif args.walk_recipe == "safewiden6_acq1":
        from .cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1 import (
            CFG_ARGS as WALK_CFG_ARGS,
        )
    else:
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_CFG_ARGS
    from .probe_currentcap29_flatonly import (
        BASE_CFG_ARGS, FLATONLY_OVERRIDE_ARGS,
    )

    stance_cfg_args = list(BASE_CFG_ARGS) + list(FLATONLY_OVERRIDE_ARGS)
    want_strips = args.strips is not None
    want_video = args.video is not None
    want_render = want_strips or want_video

    env_rise = _build_env(stance_cfg_args, episode_seconds=15.0,
                           seed=args.seed, render=want_render)
    walk_episode_s = max(20.0, args.hold_s + 1.0 + 2.0 + 2.0)  # +2s margin
    env_walk = _build_env(WALK_CFG_ARGS, episode_seconds=walk_episode_s,
                           seed=args.seed, render=want_render)
    env_lower = None
    lower_joint_limit_rad = None
    if args.lower is not None:
        from .cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp \
            import CFG_ARGS as LOWER_CFG_ARGS
        lower_cfg_args = _compose_lower_cfg_args(LOWER_CFG_ARGS,
                                                  args.lower_cfg)
        env_lower = _build_env(lower_cfg_args,
                                episode_seconds=args.lower_episode_s,
                                seed=args.seed, render=want_render)
        from .servo_model import joint_ids
        lower_joint_limit_rad = env_lower.model.jnt_range[
            joint_ids(env_lower.model)].copy()

    # wrap_recurrent_predictor is a no-op passthrough for every plain
    # (feedforward) checkpoint this harness has ever been pointed at;
    # it only activates (threading a real hidden state across this
    # episode's ticks, reset at episode start via the hasattr(reset)
    # checks already below) for a recurrent (GRU) stance/walk/lower/
    # specialist checkpoint -- the lower role's recurrent-SAC lineage
    # (recurrent_sac.py, 2026-10-04) is the first one that needs this;
    # stance/walk were never previously wrapped here (a latent
    # "lobotomy" gap for a hypothetical recurrent stance/walk
    # checkpoint, same bug class RecurrentPredictor's own docstring
    # warns about elsewhere) -- fixed for free, zero behavior change
    # for any existing feedforward checkpoint.
    stance = wrap_recurrent_predictor(
        load_checkpoint_auto(args.stance, device="cpu"))
    walk = wrap_recurrent_predictor(
        load_checkpoint_auto(args.walk, device="cpu"))
    if args.rot60:
        from .rot60 import Rot60Policy
        walk = Rot60Policy(walk)
    lower = (wrap_recurrent_predictor(
                load_checkpoint_auto(args.lower, device="cpu"))
             if args.lower is not None else None)
    if args.lower_specialist is not None:
        if lower is None:
            raise SystemExit("--lower-specialist requires --lower")
        from .two_stage_lower_policy import TwoStageLowerPolicy
        specialist = wrap_recurrent_predictor(load_checkpoint_auto(
            args.lower_specialist, device="cpu"))
        switch_tick = int(round(args.lower_specialist_switch_s
                                / env_lower.dt))
        lower = TwoStageLowerPolicy(lower, specialist,
                                    switch_tick=switch_tick)
        print(f"[lower-specialist] {args.lower_specialist} takes over "
              f"at tick {switch_tick} ({args.lower_specialist_switch_s}s)")
    n_stance = int(stance.observation_space.shape[0])
    n_env_rise = int(env_rise.observation_space.shape[0])
    n_env_walk = int(env_walk.observation_space.shape[0])
    assert walk.observation_space.shape[0] == n_env_walk, (
        f"walk policy obs {walk.observation_space.shape} != "
        f"env_walk {n_env_walk}")
    assert n_stance <= n_env_rise, (
        "stance policy obs must fit inside env_rise's obs "
        f"(got {n_stance} vs {n_env_rise})")
    n_lower = None
    if lower is not None:
        # Same truncation trick as the stance role (n_stance <=
        # n_env_rise): SimHexapodJointWalkEnv is a strict-superset-obs
        # subclass of SimHexapodJointGoalEnv (the `--task joint_goal`
        # class the lower checkpoint actually trained under), so the
        # checkpoint's own obs width can be narrower than this eval
        # harness's env_lower build; feed it only its own leading
        # obs[:n_lower] slice, exactly like `stance.predict(obs[:n_stance])`.
        n_lower = int(lower.observation_space.shape[0])
        n_env_lower = int(env_lower.observation_space.shape[0])
        assert n_lower <= n_env_lower, (
            "lower policy obs must fit inside env_lower's obs "
            f"(got {n_lower} vs {n_env_lower})")
    deterministic = not args.stochastic

    strip_frames: list = []
    video_frames: list = []

    def grab(env, final: bool = False) -> None:
        if not want_strips and not want_video:
            return
        frame = None
        if want_video:
            frame = env.render()
            video_frames.append(frame)
        if want_strips and (final or (grab.n % max(
                1, int(round(1.0 / env.dt))) == 0)):
            strip_frames.append(frame if frame is not None else env.render())
        grab.n += 1
    grab.n = 0

    def save_strip(name: str) -> None:
        if not want_strips or not strip_frames:
            return
        import imageio.v2 as imageio
        args.strips.mkdir(parents=True, exist_ok=True)
        imageio.imwrite(args.strips / f"{name}.png",
                        np.hstack(strip_frames))
        strip_frames.clear()

    def save_video(name: str) -> None:
        if not want_video or not video_frames:
            return
        write_mp4(list(video_frames), args.video / f"{name}.mp4",
                  fps=round(1.0 / env_walk.dt))
        video_frames.clear()

    def rise_phase(ep_seed: int) -> tuple[dict, bool, PhysicalState | None]:
        gen = env_rise._goal_gen
        _set_mix(gen, rise=1.0)
        gen.force_rise_start = "flat"
        obs, _ = env_rise.reset(seed=ep_seed)
        gen.force_rise_start = None
        for _ in range(int(round(PHASE_A_S / env_rise.dt))):
            a, _ = stance.predict(obs[:n_stance], deterministic=deterministic)
            obs, _rw, term, trunc, info = env_rise.step(a)
            grab(env_rise)
            if term or trunc:
                return ({"rise_fall": str(
                    info.get("termination_reason") or "end")}, False, None)
        h_err = (float(env_rise.data.xpos[env_rise._chassis_bid, 2])
                 - (env_rise._z0 + env_rise._h_target))
        ok, detail = env_rise.plant_report(height_err_m=h_err)
        rep = {"rise_valid_plant": bool(ok),
               "rise_fail": [k for k, v in detail.items()
                             if k.endswith("_ok") and not v],
               "rise_height_err_mm": round(h_err * 1000.0, 1)}
        return rep, True, capture_physical_state(env_rise)

    def handoff_obs(state: PhysicalState):
        """Fresh plant-frame walk episode (walk champion's own training
        frame), then the specialist's physical state dropped in."""
        gen = env_walk._goal_gen
        _set_mix(gen, walk=1.0)
        env_walk.reset(seed=args.seed)
        apply_physical_state(env_walk, state)
        mujoco.mj_forward(env_walk.model, env_walk.data)
        env_walk._state = env_walk._read_state()
        return env_walk._final_obs(
            build_obs(env_walk.cfg, env_walk._state, env_walk._q_nom,
                      env_walk._prev_action, goal=env_walk._current_goal(),
                      tilt_ref=env_walk._tilt_ref0), reset=True)

    def lower_handoff_obs(state: PhysicalState):
        """Same cross-env reanchor trick as `handoff_obs`, applied to
        the WALK episode's ending physical state instead of the rise
        episode's: a fresh `lower`-mode reset establishes the target
        env's own height reference (`_z0`/`_h_target`, negative for a
        descent) before the real qpos/qvel/ctrl/act/slew state is
        dropped in on top -- nothing is teleported, no scripted joint
        path is used."""
        gen = env_lower._goal_gen
        _set_mix(gen, lower=1.0)
        env_lower.reset(seed=args.seed)
        if args.diag_zero_lower_qvel:
            state = zeroed_qvel_state(state)
        apply_physical_state(env_lower, state)
        mujoco.mj_forward(env_lower.model, env_lower.data)
        env_lower._state = env_lower._read_state()
        return env_lower._final_obs(
            build_obs(env_lower.cfg, env_lower._state, env_lower._q_nom,
                      env_lower._prev_action, goal=env_lower._current_goal(),
                      tilt_ref=env_lower._tilt_ref0), reset=True)

    term_bank_all_q: list = []
    term_bank_all_qvel: list = []
    term_bank_all_target: list = []
    term_bank_episodes_ok = [0]

    def lower_phase(state: PhysicalState, name: str = "ep") -> dict:
        """Drive the `lower` role for its own full trained episode
        length starting from the walk episode's ending physical state.
        Success bar mirrors eval_checkpoint.py's `_success("lower", ...)`
        rule of thumb: not terminated AND |height_err_end_mm|<=15.

        When ``args.current_trace_dir`` is set (over_current FORENSICS,
        walkcurr/STATUS.md Next 1), also collects the per-tick
        trip-relevant current reading (``over_current_reading`` -- the
        SAME array the SafetyLayer's own over_current trip reads) PLUS
        the per-tick actuated-joint qvel and chassis height (2026-10-01
        stall-corroboration follow-up: lets ``trip_summary`` apply the
        same CORROBORATED_STALL/RAIL_MOVING classification the operator's
        2026-09-04 ``audit_over_current.py`` directive already requires
        before treating a bit-exact 2.64 A trip as a real unsafe stall)
        and, on a FAILED episode only, writes it all + ``trip_summary()``
        + the walk-exit qpos/qvel to ``<dir>/<name>_<lower_fall>.json``.
        Zero cost/behavior change when the flag is unset (default).

        ``args.lower_rot60`` (default off, bit-exact when unset): wraps
        `lower` in ``rot60_lower.Rot60LowerPolicy`` with the sector k
        read from the WALK role's own final ``Rot60Policy.k`` right
        here at the handoff (the walk drive loop has already finished
        for this episode, so ``walk.k`` holds its LAST sector -- see
        rot60_lower.py's module docstring)."""
        obs = lower_handoff_obs(state)
        lower_model = lower
        if args.lower_rot60:
            from .rot60_lower import Rot60LowerPolicy
            lower_model = Rot60LowerPolicy(lower, walk.k)
        if hasattr(lower_model, "reset"):
            lower_model.reset()
        term = trunc = False
        info: dict = {}
        want_trace = args.current_trace_dir is not None
        want_minload = args.minload_trace_dir is not None
        want_term_bank = args.term_bank_harvest_out is not None
        minload_floor_n = float(cfg_get(
            env_lower.cfg, "safety", "hold_min_load_terminate_n",
            default=0.3))
        current_trace: list = []
        qvel_trace: list = []
        height_trace_mm: list = []
        qpos_trace: list = []
        contact_trace: list = []
        minforce_trace: list = []
        perleg_force_trace: list = []
        minload_qpos_trace: list = []
        minload_qvel_trace: list = []
        term_bank_q_rows: list = []
        term_bank_qvel_rows: list = []
        term_bank_target_rows: list = []
        term_bank_next_sample_s = args.lower_specialist_switch_s
        n_steps = max(1, int(round(args.lower_episode_s / env_lower.dt)))
        for _ in range(n_steps):
            a, _ = lower_model.predict(obs[:n_lower],
                                       deterministic=deterministic)
            obs, _rw, term, trunc, info = env_lower.step(a)
            grab(env_lower)
            if want_term_bank:
                t_lower = env_lower._step_i * env_lower.dt
                if (t_lower >= term_bank_next_sample_s
                        and t_lower < args.lower_episode_s):
                    q_deg = mujoco_rel_rad_to_robot_abs_deg(
                        env_lower.data.qpos[env_lower._qadr])
                    term_bank_q_rows.append(
                        np.asarray(q_deg, dtype=float))
                    term_bank_qvel_rows.append(
                        np.asarray(env_lower.data.qvel[env_lower._vadr],
                                  dtype=float))
                    term_bank_target_rows.append(float(
                        env_lower._goal_traj.height[min(
                            env_lower._step_i,
                            len(env_lower._goal_traj.height) - 1)]))
                    term_bank_next_sample_s += args.term_bank_sample_every_s
            if want_minload:
                minforce_trace.append(
                    env_lower._minload_min_force_now(minload_floor_n))
                perleg_force_trace.append([
                    max(float(env_lower.data.sensordata[adr]), 0.0)
                    if adr >= 0 else float("nan")
                    for adr in env_lower._touch_adr])
                minload_qpos_trace.append(
                    np.asarray(env_lower.data.qpos[env_lower._qadr],
                              dtype=float).copy())
                minload_qvel_trace.append(
                    np.asarray(env_lower.data.qvel[6:6 + N_JOINTS],
                              dtype=float).copy())
            if want_trace:
                cur = over_current_reading(env_lower._state)
                current_trace.append(
                    (np.zeros(N_JOINTS) if cur is None
                     else np.asarray(cur, dtype=float)).copy())
                qvel_trace.append(
                    np.asarray(env_lower.data.qvel[6:6 + N_JOINTS],
                              dtype=float).copy())
                height_trace_mm.append(
                    1000.0 * float(env_lower.data.xpos[
                        env_lower._chassis_bid, 2]))
                qpos_trace.append(
                    np.asarray(env_lower.data.qpos[env_lower._qadr],
                              dtype=float).copy())
                contact_trace.append(
                    [float(env_lower.data.sensordata[adr]) > CONTACT_N
                     if adr >= 0 else False
                     for adr in env_lower._touch_adr])
            if term or trunc:
                break
        h_err_mm = round(1000.0 * (
            float(env_lower.data.xpos[env_lower._chassis_bid, 2])
            - (env_lower._z0 + env_lower._h_target)), 1)
        lower_fall = (str(info.get("termination_reason") or "end")
                      if term else None)
        if want_trace and lower_fall is not None and current_trace:
            trace_arr = np.stack(current_trace)
            qvel_arr = np.stack(qvel_trace)
            height_arr = np.asarray(height_trace_mm)
            qpos_arr = np.stack(qpos_trace)
            contact_arr = np.asarray(contact_trace, dtype=bool)
            dump = {
                "name": name, "lower_fall": lower_fall,
                "n_ticks": int(trace_arr.shape[0]),
                "n_steps_budget": n_steps,
                "lower_episode_s": args.lower_episode_s,
                "walk_exit_qpos": state.qpos.tolist(),
                "walk_exit_qvel": state.qvel.tolist(),
                "current_trace_a": trace_arr.round(3).tolist(),
                "qpos_trace_rad": qpos_arr.round(4).tolist(),
                "joint_limit_rad": lower_joint_limit_rad.round(4).tolist(),
                "contact_trace": contact_arr.tolist(),
                "trip_summary": trip_summary(
                    trace_arr, env_lower.safety.max_current,
                    qvel_trace=qvel_arr, height_trace_mm=height_arr,
                    qpos_trace=qpos_arr,
                    joint_limit_rad=lower_joint_limit_rad),
            }
            args.current_trace_dir.mkdir(parents=True, exist_ok=True)
            out = args.current_trace_dir / f"{name}_{lower_fall}.json"
            out.write_text(json.dumps(dump))
        lower_ok = (not term) and abs(h_err_mm) <= 15.0
        if want_term_bank and lower_ok and term_bank_q_rows:
            term_bank_all_q.extend(term_bank_q_rows)
            term_bank_all_qvel.extend(term_bank_qvel_rows)
            term_bank_all_target.extend(term_bank_target_rows)
            term_bank_episodes_ok[0] += 1
        if want_minload and minforce_trace:
            minload_dump = {
                "name": name, "lower_fall": lower_fall,
                "lower_ok": lower_ok,
                "n_ticks": len(minforce_trace),
                "dt": env_lower.dt,
                "minload_floor_n": minload_floor_n,
                "min_force_trace_n": [round(float(v), 4)
                                      for v in minforce_trace],
                "perleg_force_trace_n": [
                    [round(float(v), 4) for v in row]
                    for row in perleg_force_trace],
                "qpos_trace_rad": [
                    [round(float(v), 4) for v in row]
                    for row in minload_qpos_trace],
                "qvel_trace_rad_s": [
                    [round(float(v), 4) for v in row]
                    for row in minload_qvel_trace],
                "joint_limit_rad": (lower_joint_limit_rad.round(4).tolist()
                                    if lower_joint_limit_rad is not None
                                    else None),
            }
            args.minload_trace_dir.mkdir(parents=True, exist_ok=True)
            tag = lower_fall if lower_fall is not None else "ok"
            out2 = args.minload_trace_dir / f"{name}_{tag}.json"
            out2.write_text(json.dumps(minload_dump))
        return {
            "lower_fall": lower_fall,
            "lower_height_err_end_mm": h_err_mm,
            "lower_ok": lower_ok,
        }

    pads_walk = [env_walk.model.body(f"L{i}_pad").id for i in range(6)]

    def drive(obs) -> dict:
        if hasattr(walk, "reset"):
            walk.reset()   # rot60 sector state is per-episode
        traj = env_walk._goal_traj
        r = {"fall": None, "trk_err": 0.0, "dist_m": 0.0,
             "stumble_max_tilt_deg": 0.0, "stumble_min_height_mm": 1e9}
        n_err, t = 0, 0.0
        p0 = np.array(env_walk.data.qpos[:2], dtype=float)
        cmd_vx, cmd_vy = heading_to_vxvy(args.speed, args.heading_deg)
        contact_hist: list = []
        pad_xy_hist: list = []
        for seconds, vx, vy in schedule(cmd_vx, cmd_vy, args.hold_s):
            for _ in range(max(1, int(round(seconds / env_walk.dt)))):
                if hasattr(traj, "vx"):
                    traj.vx[:] = vx
                    traj.vy[:] = vy
                if getattr(traj, "wz", None) is not None:
                    traj.wz[:] = 0.0
                a, _ = walk.predict(obs, deterministic=deterministic)
                obs, _rw, term, trunc, info = env_walk.step(a)
                grab(env_walk)
                t += env_walk.dt
                contact_hist.append([
                    float(env_walk.data.sensordata[adr]) > CONTACT_N
                    for adr in env_walk._touch_adr])
                pad_xy_hist.append(
                    [env_walk.data.xpos[b, :2].copy() for b in pads_walk])
                if t <= STUMBLE_S:
                    tr, tp = env_walk._true_roll_pitch()
                    r["stumble_max_tilt_deg"] = max(
                        r["stumble_max_tilt_deg"],
                        math.degrees(max(abs(tr), abs(tp))))
                    r["stumble_min_height_mm"] = min(
                        r["stumble_min_height_mm"],
                        float(env_walk.data.xpos[env_walk._chassis_bid, 2])
                        * 1000.0)
                v = env_walk._body_vel_xy()
                r["trk_err"] += math.hypot(v[0] - vx, v[1] - vy)
                n_err += 1
                if term or trunc:
                    r["fall"] = str(
                        info.get("termination_reason") or "episode_end")
                    break
            if r["fall"]:
                break
        r["trk_err"] = round(r["trk_err"] / max(n_err, 1), 4)
        r["dist_m"] = round(float(np.hypot(
            *(np.array(env_walk.data.qpos[:2], dtype=float) - p0))), 3)
        r["stumble_max_tilt_deg"] = round(r["stumble_max_tilt_deg"], 1)
        r["stumble_min_height_mm"] = round(r["stumble_min_height_mm"], 1)
        contact_arr = np.asarray(contact_hist, dtype=bool)
        pad_xy_arr = np.asarray(pad_xy_hist)
        sac = (sacrificed_legs(contact_arr, pad_xy_arr)
               if len(contact_hist) > 1 else [])
        r["sacrificed_legs"] = sac
        r["gait_valid"] = not sac
        return r

    results: dict = {"stance": str(args.stance), "walk": str(args.walk),
                      "walk_recipe": args.walk_recipe,
                      "lower": (str(args.lower) if args.lower else None),
                      "speed": args.speed, "heading_deg": args.heading_deg,
                      "rot60": bool(args.rot60),
                      "lower_rot60": bool(args.lower_rot60),
                      "diag_zero_lower_qvel": bool(args.diag_zero_lower_qvel),
                      "deterministic": deterministic,
                      "episodes": []}

    for arm in ("direct", "plant"):
        for ep in range(args.episodes):
            rec = {"arm": arm, "ep": ep}
            name = f"{arm}_{ep}"
            strip_frames.clear()
            video_frames.clear()
            if arm == "plant":
                gen = env_walk._goal_gen
                _set_mix(gen, walk=1.0)
                obs, _ = env_walk.reset(seed=args.seed + 1000 + ep)
                rec.update(drive(obs))
            else:
                rep, alive, state = rise_phase(args.seed + ep)
                rec.update(rep)
                if alive:
                    obs = handoff_obs(state)
                    rec.update(drive(obs))
                else:
                    rec["fall"] = "before_handoff"
            lower_ran = False
            if lower is not None and rec.get("fall") is None:
                walk_end_state = capture_physical_state(env_walk)
                rec.update(lower_phase(walk_end_state, name=name))
                lower_ran = True
            if (want_strips or want_video) and ep == 0:
                if lower_ran:
                    final_env = env_lower
                elif rec.get("fall") == "before_handoff":
                    final_env = env_rise
                else:
                    final_env = env_walk
                grab(final_env, final=True)
                save_strip(name)
                save_video(name)
            results["episodes"].append(rec)
            print(f"[{arm:6s}] ep{ep} "
                  f"rise_ok={rec.get('rise_valid_plant', '-')} "
                  f"fall={rec.get('fall')} trk={rec.get('trk_err', '-')} "
                  f"dist={rec.get('dist_m', '-')} "
                  f"tilt2s={rec.get('stumble_max_tilt_deg', '-')} "
                  f"hmin2s={rec.get('stumble_min_height_mm', '-')} "
                  f"gait_valid={rec.get('gait_valid', '-')} "
                  f"sacrificed={rec.get('sacrificed_legs', '-')} "
                  f"lower_fall={rec.get('lower_fall', '-')} "
                  f"lower_h_err_mm={rec.get('lower_height_err_end_mm', '-')}")

    def band(arm: str, key: str) -> list:
        vals = [e[key] for e in results["episodes"]
                if e["arm"] == arm and key in e and e.get("fall") is None]
        return ([round(float(min(vals)), 3), round(float(max(vals)), 3)]
                if vals else [])

    summary = {}
    for arm in ("direct", "plant"):
        eps = [e for e in results["episodes"] if e["arm"] == arm]
        handed = [e for e in eps if e.get("fall") != "before_handoff"]
        summary[arm] = {
            "episodes": len(eps),
            "rise_valid_plant": sum(
                1 for e in eps if e.get("rise_valid_plant")),
            "rise_failed_pre_handoff": sum(
                1 for e in eps if e.get("fall") == "before_handoff"),
            "handoff_falls": sum(1 for e in handed if e.get("fall")),
            "gait_valid": sum(1 for e in handed if e.get("gait_valid")),
            "sacrificed_legs_union": sorted({
                leg for e in handed for leg in e.get("sacrificed_legs", [])
            }),
            "trk_err_band": band(arm, "trk_err"),
            "dist_band": band(arm, "dist_m"),
            "stumble_tilt_band": band(arm, "stumble_max_tilt_deg"),
        }
        if lower is not None:
            lowered = [e for e in handed if "lower_height_err_end_mm" in e]
            summary[arm]["lower_attempted"] = len(lowered)
            summary[arm]["lower_falls"] = sum(
                1 for e in lowered if e.get("lower_fall"))
            summary[arm]["lower_ok"] = sum(
                1 for e in lowered if e.get("lower_ok"))
            summary[arm]["lower_height_err_end_mm_band"] = band(
                arm, "lower_height_err_end_mm")
    results["summary"] = summary
    print(json.dumps(summary, indent=1))
    direct = summary["direct"]
    direct_ok = (direct["handoff_falls"] == 0
                 and direct["rise_failed_pre_handoff"] < direct["episodes"])
    direct_gait_valid = (direct_ok
                          and direct["gait_valid"] == direct["episodes"])
    print("LIFECYCLE HANDOFF (direct, no scripted blend):",
          "CLEAN — no falls after switching on the stance role's pose"
          if direct_ok else "NOT CLEAN — see per-episode records")
    print("LIFECYCLE GAIT VALIDITY (direct, no sacrificed leg):",
          "CLEAN" if direct_gait_valid else
          f"NOT CLEAN — sacrificed_legs_union={direct['sacrificed_legs_union']}")
    if lower is not None:
        d_low = direct.get("lower_attempted", 0)
        d_low_ok = direct.get("lower_ok", 0)
        d_low_falls = direct.get("lower_falls", 0)
        print("LIFECYCLE LOWER (direct, rise->walk->lower, 3 clean-RL "
              "roles):",
              f"{d_low_ok}/{d_low} ok, {d_low_falls} falls "
              f"(err band {direct.get('lower_height_err_end_mm_band')})"
              if d_low else "NOT ATTEMPTED (walk phase itself fell)")
    if args.term_bank_harvest_out is not None:
        if not term_bank_all_q:
            raise RuntimeError(
                "--term-bank-harvest-out: harvested zero rows -- no "
                "lower_ok composed episode reached the "
                "--lower-specialist-switch-s sample window")
        q_deg_arr = np.stack(term_bank_all_q, axis=0)
        qvel_arr = np.stack(term_bank_all_qvel, axis=0)
        target_arr = np.asarray(term_bank_all_target, dtype=float)
        if q_deg_arr.shape[1] != N_JOINTS or qvel_arr.shape != q_deg_arr.shape:
            raise ValueError(
                f"shape mismatch: q_deg {q_deg_arr.shape}, qvel "
                f"{qvel_arr.shape}, expected (K,{N_JOINTS}) both")
        args.term_bank_harvest_out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(args.term_bank_harvest_out,
                 q_rad=q_deg_arr * DEG2RAD, qvel_mujoco=qvel_arr,
                 target_m=target_arr, joint_frame=FRAME_ROBOT_ABS,
                 joint_contract=JOINT_CONTRACT,
                 source_lower=str(args.lower),
                 source_composed=True,
                 switch_s=args.lower_specialist_switch_s,
                 episodes=2 * args.episodes,
                 episodes_ok=term_bank_episodes_ok[0],
                 sample_every_s=args.term_bank_sample_every_s)
        print(f"wrote {args.term_bank_harvest_out}: {q_deg_arr.shape[0]} "
              f"rows from {term_bank_episodes_ok[0]}/{2 * args.episodes} "
              f"lower_ok composed episode(s) (both arms, real "
              f"rise->walk->lower trajectories, sampled from t>="
              f"{args.lower_specialist_switch_s}s)")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=1))
        print(f"wrote {args.out}")
    return 0 if direct_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
