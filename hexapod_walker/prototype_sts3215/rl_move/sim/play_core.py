"""Shared player/session machinery for play.py and web_session.py.

Moved verbatim out of play.py (2026-08-29) so the web MuJoCo session
(web_session.py) no longer reaches into the interactive player's
private internals. Contents: the scripted-gait picker rows and their
factory, obs-width -> role classification, the model panel data
(_ON_ROBOT/_PROMOTED/_CURATED/_DESC), trained goal-ramp profiles,
checkpoint scanning, and the _PlayTraj/_PlayEnv env wrapper both
front-ends drive. play.py keeps the cv2/pygame interaction layer
(keys, FIFO, gamepad, victory lap, main()).

Names keep their historical underscore spelling — they are the module
API here (moved verbatim; renaming would churn every use site for no
behavior change). ``__all__`` below is the official export list.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from hexapod_core.demo_tripod import DEFAULT_DEMO_TRIPOD

from .view import _InteractiveTraj
from .walk_task import SimHexapodJointWalkEnv, WalkGoal

__all__ = [
    "_CRUISE", "_CURATED", "_DEFAULT_STANCE_PROFILE", "_DESC", "_HIST_K",
    "_MIDDLE_TUCK_QUAD",
    "_N_MODE", "_NOSLIP", "_NOSLIP_CLEAN", "_NOSLIP_FACTORY",
    "_NOSLIP_MID", "_NOSLIP_RIPPLE", "_NOSLIP_TAGS", "_NOSLIP_WAVE",
    "_ON_ROBOT", "_PROMOTED", "_PlayEnv", "_PlayTraj", "_ROLE_OBS",
    "_SCRIPTED_SE2", "_SE2_CPG", "_SE2_TETRAPOD", "_SE2_WAVE",
    "_SCRIPTED_ALPHA", "_SCRIPTED_NOSLIP", "_SCRIPTED_ROWS",
    "_SCRIPTED_TRIPOD", "_SPEED_MAX", "_TRIPOD_GENTLE", "_TRIPOD_HW",
    "_TRIPOD_PRANCE", "_load_profiles", "_obs_width", "_sim_only_obs",
    "make_noslip_gait", "scan_policies",
]

_SPEED_MAX = 0.06     # champion's trained command band tops out here
_CRUISE = 0.05        # hold-to-drive speed (inside the trained band)


# Sentinel rows in the WALK panel: not checkpoints — they select the
# scripted no-slip gait (hexapod_core/noslip_gait.py) as the walk
# driver, at different alpha (body-motion overlap): 0.0 = the original
# step-then-shift, 0.5 = the midpoint of the continuum (half the body
# travel rides a constant drift through swings/dwells). Slower than the
# RL band (~0.02 m/s realized here) but stance feet are commanded to
# fixed world anchors at every alpha, and it turns (U/O). The clampfit
# row is NoSlipGait.CLAMP_FIT_KW — the 08-12 sweep's cleanest timing
# under this env's fitted ~31 deg/s servo clamp (alpha=1, swing-heavy
# 6 s cycle; zero true scrub, 4x less loaded foot drift).
_NOSLIP = Path("noslip_scripted_gait")
_NOSLIP_MID = Path("noslip_hybrid_a50")
_NOSLIP_CLEAN = Path("noslip_clampfit_gait")
_SCRIPTED_ALPHA = {_NOSLIP: 0.0, _NOSLIP_MID: 0.5, _NOSLIP_CLEAN: 1.0}
# Classic-gait rows: same world-pinned engine, different swing groups
# (NoSlipGait.ripple / .wave presets). Ripple swings opposite PAIRS
# (4 feet always down); wave swings ONE leg at a time, alternating
# sides (5 down — steadiest and slowest). Both verified zero true
# scrub in verify_noslip (08-20), like the clampfit tripod.
_NOSLIP_RIPPLE = Path("noslip_ripple_gait")
_NOSLIP_WAVE = Path("noslip_wave_gait")
_NOSLIP_FACTORY = {_NOSLIP_CLEAN: "clamp_fit", _NOSLIP_RIPPLE: "ripple",
                   _NOSLIP_WAVE: "wave"}
_NOSLIP_TAGS = {_NOSLIP: "tripod alpha=0.0", _NOSLIP_MID: "tripod alpha=0.5",
                _NOSLIP_CLEAN: "clamp-fit tripod",
                _NOSLIP_RIPPLE: "RIPPLE pairs (4 feet down)",
                _NOSLIP_WAVE: "WAVE one-leg (5 feet down)"}
_SCRIPTED_NOSLIP = frozenset(_SCRIPTED_ALPHA) | frozenset(_NOSLIP_FACTORY)


def make_noslip_gait(row: Path, cls):
    """Build the no-slip gait a picker row selects (cls = NoSlipGait)."""
    preset = _NOSLIP_FACTORY.get(row)
    if preset is not None:
        return getattr(cls, preset)()
    return cls(alpha=_SCRIPTED_ALPHA.get(row, 0.0))


_SE2_TETRAPOD = Path("se2_tetrapod_gait")
_SE2_WAVE = Path("se2_wave_gait")
_SE2_CPG = Path("se2_cpg_loaded_gait")
_SCRIPTED_SE2 = frozenset({_SE2_TETRAPOD, _SE2_WAVE, _SE2_CPG})
_MIDDLE_TUCK_QUAD = Path("middle_tuck_quad_crawl")
# Scripted TRIPOD gait rows (hexapod_core/tripod_gait.py) — the
# dance_walk victory-lap gaits, previewable here before hardware runs.
# "prance" = the aggressive horse settings (quick cadence, high knees,
# 1.5x the RL band); "gentle" = the stock walk-demo settings for
# comparison. cruise = hold-arrow speed; omega = the U/O clamp AND the
# P-key about-face turn rate.
_TRIPOD_HW = Path("tripod_highstep_demo_gait")
_TRIPOD_PRANCE = Path("tripod_prance_gait")
_TRIPOD_GENTLE = Path("tripod_walk_gait")
_SCRIPTED_TRIPOD = {
    _TRIPOD_HW: DEFAULT_DEMO_TRIPOD.play_row("hardware high-step demo"),
    _TRIPOD_PRANCE: dict(period=0.58, lift_mm=32.0, cruise=0.09,
                         omega=0.85, tag="PRANCE 0.58s/32mm"),
    _TRIPOD_GENTLE: dict(period=0.85, lift_mm=18.0, cruise=0.045,
                         omega=0.40, tag="gentle 0.85s/18mm"),
}
_SCRIPTED_ROWS = (
    _SCRIPTED_NOSLIP
    | _SCRIPTED_SE2
    | frozenset({_MIDDLE_TUCK_QUAD})
    | frozenset(_SCRIPTED_TRIPOD)
)


# Playable obs widths (see module docstring / sim_viewer/README.md).
# 78 = 72 + the 6-wide mode one-hot (transdagger GRU line); 1152 = 16
# stacked 72-dim frames (transformer/hist16 line); 74 (phase clock)
# joins only under --phase-obs.
_ROLE_OBS = {68: "stance", 72: "walk", 78: "walk", 1152: "walk"}
_N_MODE = 6          # walk_task.N_MODE_OBS (frozen slot order)
_HIST_K = 16         # frames in the hist16/transformer stack


# Checkpoints currently deployed on the physical robot — live slot
# files AND the selectable linux_control/policies/ picker entries
# (source: GET /api/rl/policies). Sorted to the top of each panel list.
_ON_ROBOT = {
    "ppo_goal_cw_stand_holdbc1_hard1",     # live stance slot
    "ppo_goal_cw_stand_footlow2_hard1",    # stand/lower roles
    "ppo_goal_cw_stance_dr10",             # picker fallback
    "ppo_goal_cw_dep_vref1_r1",            # live walk slot
    "ppo_goal_cw_dep_tip1",                # picker
    "ppo_goal_cw_dep_quad1_c2",            # picker
    "ppo_goal_cw_arch_noslipphase1_r4",    # picker (obs 74, 08-13)
}

# Panel order: robot-deployed first, then the checkpoints most worth
# trying (champions / hardened driving recipes per SKILLS.md), then the
# rest alphabetically.
_PROMOTED = [
    # stance group
    "ppo_goal_cw_stand_footlow2_hard1",
    "ppo_goal_cw_stand_holdbc1_hard1",
    "ppo_goal_cw_stand_footlow2_stable1",
    "ppo_goal_cw_stance_dr10",
    "ppo_goal_cw_stand_crouchrise1",
    "ppo_goal_cw_stance_raisefix",
    # walk group
    "ppo_goal_cw_dep_bcgait1_hard1",
    "ppo_goal_cw_arch_noslipphase1_r4",
    "ppo_goal_cw_dep_bcgait4_phasedir9_longrun17",
    "ppo_goal_cw_arch_hist16_dep1_c1",
    "ppo_goal_cw_arch_tf_r1_hard2_r1",
    "ppo_goal_cw_gru_dual_bc_transdagger2",
    "ppo_goal_cw_dep_vref1_r1",
    "ppo_goal_cw_dep_tip1",
    "ppo_goal_cw_walk_joyheadfric",
    "ppo_goal_cw_walk_joyheadfric_payload_r1",
    "ppo_goal_cw_walk_longdist_r2",
    "ppo_goal_cw_walk_wander30",
    "ppo_goal_cw_walk_slow2",
    "ppo_goal_cw_walk_anchorgate",
]

# Default picker contents: a TOP-TEN (operator request 08-18) — the
# best model per category plus what's on the robot; one scripted row
# (clamp-fit, the cleanest) joins these in main(). `--all` restores the
# full directory scan. The full list outgrew the 720px panel (~55 rows
# by 08-18) — rows past the bottom were drawn off-screen and could not
# be clicked, i.e. "I couldn't select gaits".
_CURATED = {
    # stance: best riser (default), live robot slot, classic champion
    "ppo_goal_cw_stand_footlow2_hard1",
    "ppo_goal_cw_stand_holdbc1_hard1",
    "ppo_goal_cw_stance_dr10",
    # walk: best all-round (default), best no-slip RL, on-robot walk,
    # best steering, fastest (sim-only), deployed picker fallback
    "ppo_goal_cw_dep_bcgait1_hard1",
    "ppo_goal_cw_arch_noslipphase1_r4",
    "ppo_goal_cw_dep_bcgait4_phasedir9_longrun17",
    "ppo_goal_cw_dep_vref1_r1",
    "ppo_goal_cw_walk_joyheadfric",
    "ppo_goal_cw_walk_longdist_r2",
    "ppo_goal_cw_dep_tip1",
    # newest experiments (operator request 08-18): transformer memory
    # walker + the one-brain rise/walk/sit GRU distillation
    "ppo_goal_cw_arch_tf_r1_hard2_r1",
    "ppo_goal_cw_gru_dual_bc_transdagger2",
    # newest gate-PASS champion (08-18 sweep of recent verdicts): the
    # dep-contract 16-frame memory walker — joystick-gated, slip in
    # the on-robot vref1 band, "a real hardware-ladder rung"
    "ppo_goal_cw_arch_hist16_dep1_c1",
}


# Plain-English one-liners (facts from RL_LOG.md / rl_docs; keep each
# under ~58 chars so it fits the 330px description column).
_DESC = {
    # --- stance group (obs 68) ---------------------------------------
    "ppo_goal_cw_friction": "stands up reliably even on slick or grippy floors",
    "ppo_goal_cw_long5m": "stands fine; raising taller works about half the time",
    "ppo_goal_cw_lower": "first model to stand up AND lie back down cleanly",
    "ppo_goal_cw_stance_clear": "failed experiment - can't raise height; skip",
    "ppo_goal_cw_stance_dr08": "solid stand/sit; raises height most of the time",
    "ppo_goal_cw_stance_dr10":
        "old sim champion for stand/sit; didn't transfer to hw",
    "ppo_goal_cw_stance_even": "tried to stop servos running hot; barely helped",
    "ppo_goal_cw_stance_raisefix": "fixed height-raise; all stance moves pass",
    "ppo_goal_cw_stand_dr05": "basic stand-up, easy physics setting",
    "ppo_goal_cw_stand_dr08": "basic stand-up, medium physics setting",
    "ppo_goal_cw_stand_dr10": "basic stand-up, hardest physics; once a hw pick",
    "ppo_goal_cw_stand_crouchrise1":
        "learned to rise from a crouch but wobbles standing",
    "ppo_goal_cw_stand_crouchrise3":
        "crouch-rise retry; leaves two legs parked - broken",
    "ppo_goal_cw_stand_holdbc1_hard1":
        "ON ROBOT: rock-steady stand, but tips when sitting here",
    "ppo_goal_cw_stand_footlow2_hard1":
        "BEST riser (08-17 eval: 14/14 rises, 0 falls); default",
    "ppo_goal_cw_stand_footlow2_stable1":
        "sibling of the best riser; failed half its rises here",
    "ppo_joint_goal": "leftover smoke-test file; ignore",
    "ppo_joint_goal_bc": "imitation-learning tryout; never documented",
    "ppo_joint_goal_bc2m": "imitation warm-start that made things worse",
    "ppo_joint_goal_scratch2m": "early proof raw joint control can learn to stand",
    # --- walk group (obs 72) -----------------------------------------
    "ppo_goal_cw_dep_quad1_c2": "holds a four-leg stance very precisely",
    "ppo_goal_cw_dep_tip1": "tried to learn tip-over recovery; never did",
    "ppo_goal_cw_dep_bcgait1_hard1":
        "BEST all-round walk (08-17 eval): tall, 0 falls; default",
    "ppo_goal_cw_dep_vref1_r1":
        "ON ROBOT: the walk the real robot runs today",
    "ppo_goal_cw_walk2_gait": "longer strides but still can't hold a speed",
    "ppo_goal_cw_walk_anchorgate": "walks with less foot slip than the sim champ",
    "ppo_goal_cw_walk_curr08": "wider speed-range attempt; fell short",
    "ppo_goal_cw_walk_dr04": "tougher-physics attempt; almost but not quite",
    "ppo_goal_cw_walk_fresh_gait": "control experiment; same foot-skating",
    "ppo_goal_cw_walk_longdist_r2":
        "fast sim walker but it skates its feet; sim-only",
    "ppo_goal_cw_walk_prog3": "reward tweak: lots of motion, zero speed control",
    "ppo_goal_cw_walk_slow": "first model to actually follow a speed command",
    "ppo_goal_cw_walk_slow2": "dependable slow walker",
    "ppo_goal_cw_walk_w08": "faster-speed attempt that got worse",
    "ppo_goal_cw_walk_w08_s1": "accidental exact copy of walk_w08; ignore",
    "ppo_goal_cw_walk_wander30": "drives around for 30s straight without falling",
    "ppo_mjx_joint_walk": "leftover from the GPU trainer; ignore",
    "noslip_scripted_gait":
        "hand-coded gait: feet never slide; U/O to turn",
    "noslip_hybrid_a50":
        "hand-coded, smoother body glide, still no slide",
    "noslip_clampfit_gait":
        "hand-coded, tuned to real servo speed; smoothest",
    "noslip_ripple_gait":
        "classic RIPPLE: pairs step, 4 feet down, no slide",
    "noslip_wave_gait":
        "classic WAVE: one leg at a time, steadiest, slow",
    "se2_tetrapod_gait":
        "hand-coded SE2 tetrapod: workspace-scaled, 4 feet down",
    "se2_wave_gait":
        "hand-coded SE2 wave: workspace-scaled, 5 feet down",
    "se2_cpg_loaded_gait":
        "loaded CPG/SE2 controller artifact, selected by CPGLOAD",
    "middle_tuck_quad_crawl":
        "front/rear four-leg crawl with the middle legs tucked up",
    "tripod_highstep_demo_gait":
        "same high-step tripod preset used by the real robot Drive page",
    "tripod_prance_gait":
        "hand-coded horse PRANCE - dance lap gait; P about-face",
    "tripod_walk_gait":
        "hand-coded gentle tripod (stock walk-demo pace)",
    "ppo_goal_cw_arch_noslipphase1_r4":
        "ON ROBOT: best RL walk, near-zero slip; needs --phase-obs",
    "ppo_goal_cw_bcnoslip_phase2_init":
        "imitation copy of the hand-coded gait; just a seed",
    "ppo_goal_cw_arch_noslipphase1_r1":
        "overtrained sibling; feet started sliding again",
    "ppo_goal_cw_arch_noslipphase1_r3":
        "shorter-trained sibling; just missed the bar",
    "ppo_goal_cw_dep_bcnoslip2":
        "failed: rocks its body, never found the rhythm",
    "ppo_goal_cw_walk_joyheadfric":
        "steers hard left/right, handles varied floors",
    "ppo_goal_cw_walk_joyheadfric_payload_r1":
        "same steering but also carries extra weight",
    "ppo_goal_cw_arch_tf_r1_hard2_r1":
        "NEW transformer memory: clean gait, low slip; sim-only",
    "ppo_goal_cw_arch_hist16_dep1_c1":
        "NEW memory walker on the robot's own senses; hw-ready",
    "ppo_goal_cw_gru_dual_bc_transdagger2":
        "NEW one GRU brain for rise+walk+sit (rise still shaky)",
    "ppo_goal_cw_dep_bcgait4_phasedir9_longrun17":
        "phase-BC directions; RL low-slip forward",
    "ppo_goal_cw_recover_any21_pop3_B14":
        "gets up from sprawls/tangles/belly (R key runs it)",
}


# Trained goal-ramp profiles (hold_s / ramp_s / target_m) per stance
# checkpoint, read from the exported robot weights JSONs
# (linux_control/policies/*.json meta["profile"] — the sb3 zips don't
# carry them). Driving a model with a DIFFERENT ramp than it trained on
# is out-of-distribution: holdbc1_hard1 (hold 5s, ramp 6s to +111mm)
# stalls its rise at ~55mm when fed the generic +45mm @ 12mm/s recipe —
# right under the player's 60mm success gate, i.e. "7 sometimes doesn't
# stand" (operator report 08-13). New learned stance artifacts must carry
# their own profile; these constants only define the scripted fallback.
_DEFAULT_STANCE_PROFILE = {
    "stand": {"hold_s": 5.0, "ramp_s": 4.0, "target_m": 0.045},
    "lower": {"hold_s": 0.0, "ramp_s": 5.0, "target_m": -0.060},
}


def _load_profiles() -> dict[str, dict]:
    out: dict[str, dict] = {}
    pdir = Path(__file__).resolve().parents[2] / "linux_control" / "policies"
    for f in sorted(pdir.glob("*.json")):
        try:
            meta = json.loads(f.read_text())["meta"]
        except Exception:
            continue
        stem = Path(meta.get("source", "")).stem
        prof = meta.get("profile")
        if stem and isinstance(prof, dict):
            out[stem] = prof
    return out


def _sim_only_obs(role: str, stem: str) -> bool:
    """True if the checkpoint trained on data the real robot can't sense.

    Walk-env checkpoints train by default with PRIVILEGED simulator
    body velocity in the obs (walk_task walk_obs_body_vel=1.0); the
    board has no velocity estimate, so those can never run honestly on
    hardware. The dep-* line AND the noslip phase line train with
    meas:=ref (mode 2.0) — the robot's exact contract. Stance obs (68)
    are encoders/IMU/goal only, all measurable on the robot."""
    return role == "walk" and "_dep" not in stem and "noslip" not in stem


def _obs_width(path: Path) -> int | None:
    """Obs width of an sb3 checkpoint WITHOUT loading it (no torch).

    sb3 zips carry a JSON ``data`` member whose observation_space entry
    includes a plain ``_shape`` list next to the pickled payload.
    """
    try:
        with zipfile.ZipFile(path) as z:
            data = json.loads(z.read("data"))
        shape = data["observation_space"]["_shape"]
        return int(shape[0]) if shape else None
    except Exception:
        return None


def scan_policies(pdir: Path, all_models: bool = False,
                  ) -> dict[str, list[Path]]:
    """Classify checkpoints in ``pdir`` into stance (68) / walk (72) lists.

    ``*_steps.zip`` autosaves are skipped — there are hundreds and the
    named finals are the ones worth cycling through. Unless
    ``all_models``, only the ``_CURATED`` stems are listed (the full
    scan no longer fits the panel).
    """
    out: dict[str, list[Path]] = {"stance": [], "walk": []}
    for p in sorted(pdir.glob("*.zip")):
        if p.stem.endswith("_steps"):
            continue
        if "recover" in p.stem:
            continue        # recovery checkpoints ride the R key, not a slot
        if not all_models and p.stem not in _CURATED:
            continue
        role = _ROLE_OBS.get(_obs_width(p) or -1)
        if role:
            out[role].append(p.resolve())
    def rank(p: Path):
        stem = p.stem
        return (_PROMOTED.index(stem) if stem in _PROMOTED
                else len(_PROMOTED), stem)

    for lst in out.values():
        lst.sort(key=rank)
    return out


class _PlayTraj(_InteractiveTraj):
    """Interactive stance goals + a live velocity command.

    Velocity ramps at ~0.06 m/s^2 toward the keyed target — training
    commands eased in over ~1 s, so instant steps are avoided the same
    way the tilt/height refs are ramped.
    """

    VEL_RATE = 0.06
    YAW_RATE = 0.30

    def __init__(self, dt: float = 0.04):
        super().__init__(dt)
        self.vx = 0.0           # user targets (keyboard writes here)
        self.vy = 0.0
        self.wz = 0.0
        self._pvx = 0.0         # published (ramped) command
        self._pvy = 0.0
        self._pwz = 0.0
        # Skill-family label read by walk_task's mode one-hot obs
        # (obs.mode_onehot; the transdagger GRU contract). The player's
        # state machine writes it every tick: rise/lower during autos,
        # walk while driving, hold otherwise. obs.mode_onehot_cmd=1
        # additionally routes zero-command "walk" ticks to hold, same
        # as the distillation streams.
        self.mode = "hold"

    def reset_published(self) -> None:
        super().reset_published()
        self._pvx = self._pvy = self._pwz = 0.0

    def at(self, step: int) -> WalkGoal:
        n = max(step - self._last_step, 0)
        dt = n * self._dt
        base = super().at(step)             # ramps tilt/height refs
        self._pvx = self._toward(self._pvx, self.vx, self.VEL_RATE * dt)
        self._pvy = self._toward(self._pvy, self.vy, self.VEL_RATE * dt)
        self._pwz = self._toward(self._pwz, self.wz, self.YAW_RATE * dt)
        return WalkGoal(roll_ref=base.roll_ref, pitch_ref=base.pitch_ref,
                        height_ref=base.height_ref,
                        unload_leg=base.unload_leg,
                        vx_ref=self._pvx, vy_ref=self._pvy,
                        wz_ref=self._pwz)


class _PlayEnv(SimHexapodJointWalkEnv):
    def __init__(self, *a, **kw):
        cfg = kw.get("cfg") or {}
        try:
            from ..config import cfg_get
            hz = float(cfg_get(cfg, "control", "hz", default=25.0) or 25.0)
        except Exception:
            hz = 25.0
        self.traj = _PlayTraj(1.0 / max(hz, 1e-6))
        super().__init__(*a, **kw)

    def _sample_goal(self):
        return self.traj
