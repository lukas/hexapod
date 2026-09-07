"""probe_turn_authority.py — turn-in-place wz-tracking probe.

WHY (standwalk wave-2 turn-diet canary gate, 08-30): the gate text for
any turn-ticks arm on the walkteach/dualbc lineage names a specific
required instrument — "a turn-in-place probe (tip_ccw/tip_cw rollout
or held wz command) shows real wz tracking (wz_err well below the
frozen-body wz_err~wz_ref prediction)" — that did not exist as a
runnable tool before this: `eval_checkpoint.py` never computes a body
yaw-rate error (its own `info["walk_wz"]`/`reward_walk_yaw` fields are
only populated when `reward.k_walk_yaw > 0`, which the walkteach/dualbc
reward stack never sets as of 08-30 — it relies on BC-anchor imitation
for turning, not the OMNI yaw kernel; STALE as of the yawcredit/turncap
wave, cw-standwalk-stage2-dualbc6-...-cap29-stdwalklo-hi's own ledger
cfg sets `reward.k_walk_yaw=1.0` (plus walk_yaw_kernel_gate/k_yaw_prog/
k_yaw_still/etc) applied to every walk tick — this tool's own combined-
tick reads still hold, this note just no longer describes why the tool
was needed), and the single-mode `eval_cmd_suite`/
`hybrid_demo` session tools do not support this dual-core 4-submode
`joint_walk` checkpoint family at all (documented INCOMPATIBLE-obs-
contract class, standwalk STATUS 08-30).

WHAT IT DOES: holds a fixed body-frame wz command (vx_ref=vy_ref=0,
i.e. a pure turn-in-place segment, matching `test_task_semantics.py`'s
`_turn_rollout` pinned-command convention) for a full episode, steps
either a loaded checkpoint (GRU dual-core auto-detected + threaded
hidden state via `gru_policy.RecurrentPredictor`, exactly like
`eval_checkpoint`) or the scripted `TripodGait` reference (the
`--policy scripted` sanity control — this is what proves the
methodology can measure a REAL nonzero wz at all: the checkpoint-only
read has no independent way to tell "policy achieves ~0 wz" apart from
"probe never captures real wz"), and reads the ALWAYS-computed
`env._body_wz()` every tick (never `info["walk_wz"]`, which is reward-
gated off in this recipe family — see WHY above; a first version of
this tool used the info field and produced a false "frozen body"
result on the scripted control, caught by mismatching the fix's own
env-mechanics sanity check).

Ticks are filtered to `info["goal_mode"] == "walk"` before scoring:
`goal.mode_seq` composes rise/walk/lower/hold SEQUENCES within one
episode even when the goal generator's own per-mode probabilities are
forced to walk-only (verified 08-30: a forced-p_walk=1.0 episode still
transitioned walk -> lower mid-episode) — scoring un-filtered ticks
silently mixes in submodes where zero wz is the CORRECT behavior, not
evidence of a turn-tracking failure.

CHECKPOINT-POLICY CFG WARNING (09-03, found triaging the yawarm{1p5,
2p0} canaries): ``--policy checkpoint`` needs the FULL non-``train.*``
``--cfg-set`` list from the checkpoint's own training command replayed
here, not a short "obs-width" summary (e.g. just ``goal.walk_yaw_cmd``/
``obs.mode_onehot``/``goal.mode_seq``/``goal.walk_phase_obs``/``goal.
walk_obs_body_vel``). A missing ``goal.*`` field that feeds the phase-
obs channel (e.g. ``goal.walk_phase_hz``, ``goal.walk_phase_run_on_
yaw``) puts the model on an out-of-distribution observation and
silently returns a near-zero/"frozen" ``wz_med`` even on a checkpoint
that tracks turns fine — reproduced on a KNOWN-PASSING checkpoint
(near-zero with the short cfg vs the correct +0.22/-0.25 pure-turn
read with the full cfg replayed). Tick counts / ``modes`` composition
will still MATCH between the short and full cfg (goal-mode sequencing
is a DR-free function of seed, independent of the policy), so do not
use matching tick counts as evidence the cfg is sufficient. Always
sanity-check a new probe cfg against a checkpoint with an already-
verified read before trusting a fresh number.

Usage:
  uv run python -m rl_move.sim.probe_turn_authority CKPT.zip \
      --cfg-set goal.walk_yaw_cmd=1 --cfg-set goal.walk_phase_run_on_yaw=1 \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --seeds 0,1 --out logs/ckpt_eval/turn_probe.json

  # sanity control (proves the tool can see a real turn at all):
  uv run python -m rl_move.sim.probe_turn_authority --policy scripted \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --out logs/ckpt_eval/turn_probe_scripted.json

  # COMBINED walk+turn probe (09-03, standwalk redesign-spec item 2
  # sub-step: every prior anchor-coef/turn-authority read here held
  # vx_ref=0 — this crosses a nonzero forward command with wz so the
  # SAME tool answers "does wz/vx tracking hold when both are
  # commanded at once", zero training required either against the
  # scripted teacher (the BC anchor's own target) or a live checkpoint:
  uv run python -m rl_move.sim.probe_turn_authority --policy scripted \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25,0.0 --vx-cmds 0.0,0.08 \
      --out logs/ckpt_eval/turn_probe_combined_scripted.json

Output JSON: per (wz_cmd, vx_cmd, seed) wz_med/wz_p90_abs/wz_err_med
and vx_med/vx_err_med (body-frame forward speed, robust to a rotating
heading) over walk-mode ticks only, plus the frozen-body wz
prediction (|wz_cmd|) for direct comparison, and an aggregate
PASS/FAIL-style summary line printed to stdout (median |wz_err| vs a
configurable `--frozen-margin` fraction of |wz_cmd|) — the summary
verdict is wz-only and unaffected by `--vx-cmds`; read vx_err_med
per-row for the combined-tick course question.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.config import load_config  # noqa: E402
from rl_move.robot_state import DEG2RAD  # noqa: E402
from .servo_model import SimServoParams  # noqa: E402
from .walk_task import SimHexapodJointWalkEnv  # noqa: E402
from .joint_task import q_rad_to_action  # noqa: E402


class _ContactAudit:
    """Per-foot contact-wrench + slip + joint-tracking recorder (09-07,
    todaypolicy turn-authority operator focus note): answers WHICH stance
    legs generate/brake yaw about the instantaneous whole-robot COM, how
    much of foot motion is material-point skating (audit_slip_frame.py's
    contact-point identification + material-slip math reused verbatim),
    and whether commanded->postclip->actual joint tracking (slew clip /
    servo lag) explains a turn deficit. Diagnostic only: instantiated only
    under ``--contact-audit``; the default path is bit-exact untouched.

    Sign convention is SELF-VALIDATED per rollout, not assumed: the force
    on each pad is oriented so the summed vertical contact force supports
    the robot (median sum_fz ~ +weight), and the per-tick summed contact
    yaw torque about the COM is regressed against d(Lz)/dt from MuJoCo's
    own ``mj_subtreeVel``/``subtree_angmom`` (gravity exerts no torque
    about the COM, so contacts are the only external yaw torque source —
    slope ~1 validates both the wrench signs and the COM lever arms).
    """

    N_BINS = 12

    def __init__(self, env):
        import mujoco
        self.mj = mujoco
        self.env = env
        m = env.model
        self.pads = [m.body(f"L{i}_pad").id for i in range(6)]
        self.pad_geoms = [
            {g for g in range(m.ngeom) if m.geom_bodyid[g] == b}
            for b in self.pads]
        self.floor = {g for g in range(m.ngeom) if m.geom_bodyid[g] == 0}
        self.weight_n = float(np.sum(m.body_mass)) * 9.81
        self.dt = env.dt
        # per-scored-tick histories
        self.rows: list[dict] = []
        self.prev_lz: float | None = None
        self.prev_pad_x = None      # (6,3) previous tick pad centers
        self.prev_pad_r = None      # (6,3,3)
        self.prev_cpos = None       # list of 6 contact positions or None
        self.prev_loaded = None     # (6,) bool
        self.prev_q_safe = None
        self.jrows: list[dict] = []

    def tick(self, *, phase: float, q_prop, q_safe, q_act) -> None:
        env = self.env
        d, m = env.data, env.model
        self.mj.mj_subtreeVel(m, d)
        lz = float(d.subtree_angmom[0][2])
        com = d.subtree_com[0].copy()
        r_body = d.xmat[env._chassis_bid].reshape(3, 3)
        fz = np.zeros(6)
        tau_f = np.zeros(6)          # (contact - COM) x force, z component
        tau_c = np.zeros(6)          # contact couple, z component
        cpos: list = [None] * 6
        f6 = np.zeros(6)
        for ci in range(d.ncon):
            c = d.contact[ci]
            foot = None
            sign = 1.0
            for f in range(6):
                if c.geom1 in self.pad_geoms[f] and c.geom2 in self.floor:
                    foot, sign = f, -1.0   # wrench-on-geom2 convention;
                    break                  # flip when the PAD is geom1
                if c.geom2 in self.pad_geoms[f] and c.geom1 in self.floor:
                    foot, sign = f, 1.0
                    break
            if foot is None:
                continue
            self.mj.mj_contactForce(m, d, ci, f6)
            frame = np.asarray(c.frame, dtype=float).reshape(3, 3)
            f_w = sign * (frame.T @ f6[:3])
            c_w = sign * (frame.T @ f6[3:])
            p = c.pos.copy()
            fz[foot] += float(f_w[2])
            tau_f[foot] += float(np.cross(p - com, f_w)[2])
            tau_c[foot] += float(c_w[2])
            cpos[foot] = p if cpos[foot] is None else 0.5 * (cpos[foot] + p)
        # global sign self-validation happens in summary(); record raw
        pad_x = np.array([d.xpos[b].copy() for b in self.pads])
        pad_r = np.array([d.xmat[b].reshape(3, 3).copy() for b in self.pads])
        loaded = np.array([
            env._touch_adr[f] >= 0
            and float(d.sensordata[env._touch_adr[f]]) > 0.5
            for f in range(6)])
        slip_center = np.zeros(6)
        slip_material = np.zeros(6)
        if self.prev_pad_x is not None and self.prev_loaded is not None:
            for f in range(6):
                if not self.prev_loaded[f]:
                    continue
                dxy = float(np.linalg.norm(
                    pad_x[f, :2] - self.prev_pad_x[f, :2]))
                slip_center[f] = dxy
                pc = self.prev_cpos[f]
                if pc is None:
                    slip_material[f] = dxy  # untracked: count like gate
                    continue
                x0, x1 = self.prev_pad_x[f], pad_x[f]
                r0, r1 = self.prev_pad_r[f], pad_r[f]
                p_mat = x1 + r1 @ (r0.T @ (pc - x0))
                slip_material[f] = float(np.linalg.norm((p_mat - pc)[:2]))
        # stance-center position of each loaded foot relative to the COM,
        # in the BODY frame (the placement-geometry read the focus note
        # asks for; +x forward, +y left)
        rel_body = np.full((6, 2), np.nan)
        for f in range(6):
            if loaded[f] and cpos[f] is not None:
                rel_body[f] = (r_body.T @ (cpos[f] - com))[:2]
        dlz = (None if self.prev_lz is None
               else (lz - self.prev_lz) / self.dt)
        self.rows.append({
            "phase": float(phase % (2.0 * math.pi)),
            "fz": fz, "tau_f": tau_f, "tau_c": tau_c,
            "loaded": loaded, "rel_body": rel_body,
            "slip_center": slip_center, "slip_material": slip_material,
            "dlz": dlz,
        })
        # joint tracking: commanded (pre-clip) vs postclip (slew-limited)
        # vs actual, all in the logical q_rad frame
        if q_prop is not None and q_safe is not None and q_act is not None:
            j = {"clip_gap": np.abs(np.asarray(q_prop) - np.asarray(q_safe)),
                 "track_err": np.abs(np.asarray(q_act) - np.asarray(q_safe))}
            if self.prev_q_safe is not None:
                lim = 0.98 * env.safety.max_dq
                j["slew_sat"] = (np.abs(np.asarray(q_safe)
                                        - self.prev_q_safe) >= lim)
            self.jrows.append(j)
            self.prev_q_safe = np.asarray(q_safe, dtype=float).copy()
        self.prev_lz = lz
        self.prev_pad_x, self.prev_pad_r = pad_x, pad_r
        self.prev_cpos, self.prev_loaded = cpos, loaded

    def summary(self) -> dict:
        if not self.rows:
            return {"n_ticks": 0}
        n = len(self.rows)
        fz = np.stack([r["fz"] for r in self.rows])            # (T,6)
        tau_f = np.stack([r["tau_f"] for r in self.rows])
        tau_c = np.stack([r["tau_c"] for r in self.rows])
        loaded = np.stack([r["loaded"] for r in self.rows])
        slip_c = np.stack([r["slip_center"] for r in self.rows])
        slip_m = np.stack([r["slip_material"] for r in self.rows])
        phase = np.array([r["phase"] for r in self.rows])
        # sign self-validation: force-on-pad must SUPPORT the robot
        sum_fz_med = float(np.median(fz.sum(axis=1)))
        sgn = 1.0 if sum_fz_med >= 0 else -1.0
        fz, tau_f, tau_c = sgn * fz, sgn * tau_f, sgn * tau_c
        # angular-momentum validation: sum contact yaw torque vs dLz/dt
        tau_tot = (tau_f + tau_c).sum(axis=1)
        dlz = np.array([r["dlz"] if r["dlz"] is not None else np.nan
                        for r in self.rows])
        ok = ~np.isnan(dlz)
        angmom = {}
        if ok.sum() > 10:
            x, y = tau_tot[ok], dlz[ok]
            vx = float(np.var(x))
            slope = float(np.cov(x, y)[0, 1] / vx) if vx > 1e-12 else None
            corr = (float(np.corrcoef(x, y)[0, 1])
                    if vx > 1e-12 and np.var(y) > 1e-12 else None)
            angmom = {"slope": slope, "corr": corr,
                      "med_abs_resid": float(np.median(np.abs(y - x)))}
        bins = np.minimum((phase / (2.0 * math.pi) * self.N_BINS).astype(int),
                          self.N_BINS - 1)
        phase_bins = []
        for b in range(self.N_BINS):
            sel = bins == b
            if not sel.any():
                phase_bins.append(None)
                continue
            phase_bins.append({
                "n": int(sel.sum()),
                "contact_frac": [round(float(loaded[sel, f].mean()), 3)
                                 for f in range(6)],
                "tau_z_mean": [round(float((tau_f + tau_c)[sel, f].mean()), 4)
                               for f in range(6)],
                "fz_mean": [round(float(fz[sel, f].mean()), 3)
                            for f in range(6)],
            })
        rel = np.stack([r["rel_body"] for r in self.rows])     # (T,6,2)
        stance_xy = []
        for f in range(6):
            good = ~np.isnan(rel[:, f, 0])
            stance_xy.append(
                [round(float(np.nanmean(rel[good, f, k])), 4)
                 for k in (0, 1)] if good.any() else None)
        out = {
            "n_ticks": n,
            "sign_flipped": sgn < 0,
            "sum_fz_med_N": round(abs(sum_fz_med), 3),
            "weight_N": round(self.weight_n, 3),
            "angmom_check": angmom,
            "per_foot": {
                "duty": [round(float(loaded[:, f].mean()), 3)
                         for f in range(6)],
                "fz_mean_loaded_N": [
                    round(float(fz[loaded[:, f], f].mean()), 3)
                    if loaded[:, f].any() else None for f in range(6)],
                "yaw_imp_force_Nms": [
                    round(float(tau_f[:, f].sum() * self.dt), 5)
                    for f in range(6)],
                "yaw_imp_couple_Nms": [
                    round(float(tau_c[:, f].sum() * self.dt), 5)
                    for f in range(6)],
                "slip_center_m": [round(float(slip_c[:, f].sum()), 4)
                                  for f in range(6)],
                "slip_material_m": [round(float(slip_m[:, f].sum()), 4)
                                    for f in range(6)],
                "stance_center_body_xy_m": stance_xy,
            },
            "yaw_imp_total_Nms": round(
                float((tau_f + tau_c).sum() * self.dt), 5),
            "phase_bins": phase_bins,
        }
        if self.jrows:
            clip = np.stack([j["clip_gap"] for j in self.jrows])   # (T,18)
            track = np.stack([j["track_err"] for j in self.jrows])
            sat_rows = [j["slew_sat"] for j in self.jrows
                        if "slew_sat" in j]
            sat = (np.stack(sat_rows) if sat_rows
                   else np.zeros((1, 18), dtype=bool))
            cls = {"yaw": [3 * l for l in range(6)],
                   "hip": [3 * l + 1 for l in range(6)],
                   "knee": [3 * l + 2 for l in range(6)]}
            out["joints"] = {
                k: {"clip_gap_med_rad": round(
                        float(np.median(clip[:, idx])), 5),
                    "clip_gap_p95_rad": round(
                        float(np.percentile(clip[:, idx], 95)), 5),
                    "track_err_med_rad": round(
                        float(np.median(track[:, idx])), 5),
                    "slew_sat_frac": round(
                        float(sat[:, idx].mean()), 4)}
                for k, idx in cls.items()}
        return out

# Preserve the probe's original physical pose after the repository-wide
# robot-absolute coordinate migration.  Its former compatibility wrapper took
# (hip=20, relative-knee=80) and commanded absolute tibia 20+80=100 degrees.
WALK_PLANT = (20.0, 100.0)


def _build_cfg(cfg_set: list[str] | None, mode_onehot: bool = False) -> dict:
    from .train_ppo_sim import _parse_cfg_set
    cfg = load_config()
    for key, parsed in _parse_cfg_set(cfg_set or []).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    if mode_onehot:
        cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    return cfg


def make_env(cfg_set: list[str] | None, seed: int,
             episode_seconds: float, mode_onehot: bool = False):
    cfg = _build_cfg(cfg_set, mode_onehot=mode_onehot)
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg,
        render_mode=None)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def _load_model(checkpoint: Path):
    from .gru_policy import load_checkpoint_auto, RecurrentPredictor
    model = load_checkpoint_auto(checkpoint, device="cpu")
    obs_width = int(model.observation_space.shape[0])
    if getattr(model.policy, "lstm_actor", None) is not None:
        model = RecurrentPredictor(model)
    return model, obs_width


def rollout(*, model, env_cls_kwargs: dict, wz_cmd: float, seed: int,
            episode_seconds: float, policy: str = "checkpoint",
            model_obs_width: int | None = None,
            vx_cmd: float = 0.0,
            scripted_omega_boost: float = 1.0,
            scripted_yaw_arm_scale: float = 1.0,
            scripted_yaw_amplify_scale: float = 1.0,
            scripted_selective_omega_boost: float = 1.0,
            scripted_group_duty_skew: float = 0.0,
            contact_audit: bool = False,
            phase_offset: float = 0.0) -> dict:
    """``vx_cmd`` (09-03, standwalk redesign-spec item 2 sub-step,
    "COMBINED walk+turn ticks specifically" branch — every prior
    anchor-coef/turn-authority probe in this lineage held vx_ref=0,
    i.e. PURE turn-in-place; nobody had measured wz/vx tracking with a
    simultaneous nonzero linear command). Default 0.0 reproduces the
    exact prior behavior bit-for-bit (``traj.vx[:] = 0.0`` either way,
    same ramp-from-zero shape since ramping 0->0 is a no-op) — this is
    an additive probe capability, not a semantics change. When nonzero,
    vx is ramped over the SAME 1s hold + ramp window as wz so both
    axes reach their commanded value together, and per-tick BODY-FRAME
    forward speed (``env._body_vel_xy()[0]``, robust to the heading
    rotating under a live wz command — unlike a world-frame track)
    is recorded over the identical walk-mode-filtered tick set as wz.

    ``scripted_omega_boost`` (09-03, standwalk branch-(a) combined-tick
    fix candidate, ``--policy scripted`` only): multiplies the omega
    handed to ``TripodGait.set_velocity`` ONLY on a combined tick
    (vx_cmd!=0 AND wz_cmd!=0) — mirrors the sim_env.py BC-anchor
    ``train.bc_anchor_teacher_omega_boost`` knob exactly (same gate,
    same multiply site: `self.omega` is used nowhere else in
    TripodGait). Default 1.0 is bit-exact (identity multiply, and a
    no-op on pure-turn/pure-walk ticks regardless since the gate
    requires BOTH nonzero).

    ``scripted_yaw_arm_scale`` (09-03, standwalk candidate (i)-v2,
    ``--policy scripted`` only): forwarded straight to
    ``TripodGait(combined_yaw_arm_scale=...)`` -- the combined-tick
    gate lives INSIDE TripodGait itself (see its docstring), so this
    probe just passes the dose through at construction. Default 1.0
    is bit-exact.

    ``scripted_yaw_amplify_scale`` (09-04, standwalk candidate (iii),
    ``--policy scripted`` only): forwarded straight to
    ``TripodGait(combined_yaw_amplify_scale=...)`` -- the SELECTIVE
    per-leg sibling of ``scripted_yaw_arm_scale`` (only the legs the
    vx cross term amplifies past pure-turn magnitude are touched; see
    ``TripodGait.__init__`` docstring and
    ``rl_move.sim.probe_leg_yaw_rate`` for the zero-training rate/
    de-saturation evidence). Default 1.0 is bit-exact.

    ``scripted_selective_omega_boost`` (09-04, standwalk Next item 2
    "selective per-leg omega boost" candidate, ``--policy scripted``
    only): forwarded straight to
    ``TripodGait(combined_selective_omega_boost=...)`` -- the mirror
    image of ``scripted_yaw_amplify_scale`` (same per-leg
    classification, opposite leg SET, and a genuinely different
    mechanism: it boosts the TRUE foot target via omega, not just the
    yaw-angle atan2 denominator, so hip/knee move too). Default 1.0
    is bit-exact.

    ``scripted_group_duty_skew`` (09-05, standwalk Next item 2
    gait-STRUCTURE candidate, ``--policy scripted`` only): forwarded
    straight to ``TripodGait(combined_group_duty_skew=...)`` -- unlike
    every candidate above (all reshape a commanded MAGNITUDE within a
    fixed time window), this re-times the existing two-tripod-group
    alternation so the amplified-heavy group's swing window widens
    (see ``TripodGait.__init__``/``_foot_target_in_body`` docstrings
    for the derivation and the safe-by-construction argument). Default
    0.0 is bit-exact.
    """
    mode_onehot = False
    env = make_env(env_cls_kwargs["cfg_set"], seed, episode_seconds,
                   mode_onehot=env_cls_kwargs.get("mode_onehot", False))
    if model_obs_width is not None:
        n_env = int(env.observation_space.shape[0])
        if model_obs_width != n_env:
            from .walk_task import N_MODE_OBS
            if model_obs_width == n_env + N_MODE_OBS:
                env.close()
                env = make_env(env_cls_kwargs["cfg_set"], seed,
                               episode_seconds, mode_onehot=True)
            else:
                raise SystemExit(
                    f"checkpoint obs width {model_obs_width} does not "
                    f"fit env ({n_env}); wrong --cfg-set?")
    obs, info = env.reset()
    if policy == "checkpoint" and hasattr(model, "reset"):
        model.reset()
    if phase_offset != 0.0:
        # start the walk phase clock at a different point in the tripod
        # cycle (09-07 turn-authority audit: both start phases). The 1 s
        # zero-command hold keeps the clock frozen (run=False) so the
        # offset survives until the ramp starts. Applies to the env obs
        # clock; the scripted TripodGait keeps its own time base.
        env._phase = float(phase_offset) % (2.0 * math.pi)
    audit = _ContactAudit(env) if contact_audit else None
    cap: dict = {}
    if contact_audit:
        _orig_atq = env._act_to_q

        def _atq_rec(clipped, _orig=_orig_atq, _cap=cap):
            out = _orig(clipped)
            _cap["q_prop"] = np.asarray(out[0], dtype=float).copy()
            return out

        env._act_to_q = _atq_rec
    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd
    traj.vy[:] = 0.0
    traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0
    traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)
    if policy == "scripted":
        from hexapod_core.tripod_gait import TripodGait
        gait = TripodGait(
            vx=0.0,
            combined_yaw_arm_scale=scripted_yaw_arm_scale,
            combined_yaw_amplify_scale=scripted_yaw_amplify_scale,
            combined_selective_omega_boost=scripted_selective_omega_boost,
            combined_group_duty_skew=scripted_group_duty_skew)
        gait.sync_plant_stance(*WALK_PLANT)
        gait.reset_phase()
    step = 0
    wz_list: list[float] = []
    vx_list: list[float] = []
    modes_seen: list[str] = []
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        if policy == "scripted":
            t = step * env.dt
            _combined = abs(cmd_vx) > 1e-3 and abs(cmd_wz) > 1e-3
            _omega = (cmd_wz * scripted_omega_boost
                      if (_combined and scripted_omega_boost != 1.0)
                      else cmd_wz)
            gait.set_velocity(vx=cmd_vx, omega=_omega)
            act = q_rad_to_action(np.asarray(gait.desired_deg(t)) * DEG2RAD)
        else:
            act, _ = model.predict(obs, deterministic=True)
        obs, r, term, trunc, info = env.step(act)
        gm = info.get("goal_mode")
        modes_seen.append(gm)
        if step >= hold_n + ramp_n and gm == "walk":
            wz_list.append(float(env._body_wz()))
            vx_list.append(float(env._body_vel_xy()[0]))
            if audit is not None:
                audit.tick(
                    phase=float(getattr(env, "_phase", 0.0)),
                    q_prop=cap.get("q_prop"),
                    q_safe=env.safety._last_safe.copy(),
                    q_act=(env._state.joint_position.copy()
                           if env._state is not None else None))
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()
    wz_arr = np.array(wz_list)
    wz_err = np.abs(wz_arr - wz_cmd)
    vx_arr = np.array(vx_list)
    vx_err = np.abs(vx_arr - vx_cmd)
    return {
        "wz_cmd": wz_cmd,
        "vx_cmd": vx_cmd,
        "phase_offset": phase_offset,
        "contact_audit": audit.summary() if audit is not None else None,
        "seed": seed,
        "n_walk_ticks": len(wz_arr),
        "n_total_ticks": step,
        "modes": dict(Counter(modes_seen)),
        "wz_med": float(np.median(wz_arr)) if len(wz_arr) else None,
        "wz_p90_abs": (float(np.percentile(np.abs(wz_arr), 90))
                       if len(wz_arr) else None),
        "wz_err_med": float(np.median(wz_err)) if len(wz_arr) else None,
        "frozen_body_wz_err_pred": abs(wz_cmd),
        "vx_med": float(np.median(vx_arr)) if len(vx_arr) else None,
        "vx_err_med": (float(np.median(vx_err)) if len(vx_arr) else None),
        "fell": fell,
    }


def summarize(results: list[dict], frozen_margin: float = 0.5) -> dict:
    """Pure aggregation: median |wz_err| vs the frozen-body prediction.

    FAIL (frozen) when the achieved median error stays ABOVE
    ``frozen_margin`` of the frozen-body prediction (|wz_cmd|) — i.e.
    the policy tracks meaningfully less than half the commanded rate.
    Split out from ``main()`` so the threshold logic is unit-testable
    without spinning up MuJoCo.
    """
    errs = [r["wz_err_med"] for r in results if r.get("wz_err_med") is not None]
    preds = [r["frozen_body_wz_err_pred"] for r in results]
    med_err = float(np.median(errs)) if errs else None
    med_pred = float(np.median(preds)) if preds else None
    frozen = (med_err is not None and med_pred is not None
              and med_err > frozen_margin * med_pred)
    verdict = ("FROZEN-BODY (no real turn tracking)" if frozen else
               "TRACKS (wz_err well below frozen-body prediction)")
    return {"med_wz_err": med_err, "frozen_body_pred": med_pred,
            "frozen": frozen, "verdict": verdict}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", nargs="?", type=Path, default=None)
    ap.add_argument("--policy", choices=("checkpoint", "scripted"),
                    default="checkpoint")
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--wz-cmds", default="0.25,-0.25",
                    help="comma-separated commanded wz values (rad/s)")
    ap.add_argument("--vx-cmds", default="0.0",
                    help="comma-separated commanded body-frame forward "
                         "speeds (m/s), crossed with every --wz-cmds "
                         "value (09-03 COMBINED walk+turn probe "
                         "extension) — default '0.0' reproduces the "
                         "original pure-turn-in-place behavior exactly")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--cells", default=None,
                    help="explicit comma-separated vx:wz cell list (e.g. "
                         "'0.08:0,0:0.3,0.08:-0.15'); overrides the "
                         "--wz-cmds x --vx-cmds cross product (09-07 "
                         "turn-authority audit: probe exactly the gate's "
                         "straight/tip/arc cells, nothing else)")
    ap.add_argument("--contact-audit", action="store_true",
                    help="record per-foot contact wrenches about the COM "
                         "(force + couple z-torque), normal load, "
                         "material-point slip, phase-resolved bins, and "
                         "cmd/postclip/actual joint tracking per rollout "
                         "(09-07 todaypolicy turn-authority diagnostic); "
                         "default off is bit-exact legacy")
    ap.add_argument("--phase-offsets", default="0.0",
                    help="comma-separated walk-phase-clock start offsets "
                         "in radians (e.g. '0,3.14159' = both tripod "
                         "start phases); each cell is run at every "
                         "offset; default 0.0 is bit-exact legacy")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--frozen-margin", type=float, default=0.5,
                    help="PASS if median wz_err <= this fraction of "
                         "the frozen-body prediction |wz_cmd|")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--scripted-omega-boost", type=float, default=1.0,
                    help="--policy scripted only: multiply omega by "
                         "this factor on combined ticks only (mirrors "
                         "sim_env.py's train.bc_anchor_teacher_omega_"
                         "boost); default 1.0 is bit-exact")
    ap.add_argument("--scripted-yaw-arm-scale", type=float, default=1.0,
                    help="--policy scripted only: TripodGait's "
                         "combined_yaw_arm_scale (standwalk candidate "
                         "(i)-v2) on combined ticks only; default 1.0 "
                         "is bit-exact")
    ap.add_argument("--scripted-yaw-amplify-scale", type=float, default=1.0,
                    help="--policy scripted only: TripodGait's "
                         "combined_yaw_amplify_scale (standwalk "
                         "candidate (iii), SELECTIVE per-leg sibling "
                         "of --scripted-yaw-arm-scale) on combined "
                         "ticks only; default 1.0 is bit-exact")
    ap.add_argument("--scripted-selective-omega-boost", type=float, default=1.0,
                    help="--policy scripted only: TripodGait's "
                         "combined_selective_omega_boost (standwalk "
                         "Next item 2, selective per-leg omega boost "
                         "candidate) on combined ticks only, ONLY the "
                         "legs the vx cross term attenuates; default "
                         "1.0 is bit-exact")
    ap.add_argument("--scripted-group-duty-skew", type=float, default=0.0,
                    help="--policy scripted only: TripodGait's "
                         "combined_group_duty_skew (standwalk Next "
                         "item 2, gait-STRUCTURE/duration candidate) "
                         "on combined ticks only; default 0.0 is "
                         "bit-exact")
    args = ap.parse_args()

    if args.policy == "checkpoint" and args.checkpoint is None:
        raise SystemExit("--policy checkpoint requires a CKPT.zip path")

    model = None
    model_obs_width = None
    if args.policy == "checkpoint":
        model, model_obs_width = _load_model(args.checkpoint)

    if args.cells:
        cells = []
        for tok in args.cells.split(","):
            if not tok.strip():
                continue
            vx_s, wz_s = tok.split(":")
            cells.append((float(vx_s), float(wz_s)))
    else:
        wz_cmds = [float(x) for x in args.wz_cmds.split(",") if x.strip()]
        vx_cmds = [float(x) for x in args.vx_cmds.split(",") if x.strip()]
        cells = [(vx, wz) for wz in wz_cmds for vx in vx_cmds]
    phase_offsets = [float(x) for x in args.phase_offsets.split(",")
                     if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    env_kwargs = {"cfg_set": args.cfg_set}
    results = []
    for vx_cmd, wz_cmd in cells:
        for phase_offset in phase_offsets:
            for seed in seeds:
                res = rollout(model=model, env_cls_kwargs=env_kwargs,
                              wz_cmd=wz_cmd, vx_cmd=vx_cmd, seed=seed,
                              episode_seconds=args.episode_seconds,
                              policy=args.policy,
                              model_obs_width=model_obs_width,
                              contact_audit=args.contact_audit,
                              phase_offset=phase_offset,
                              scripted_omega_boost=(
                                  args.scripted_omega_boost),
                              scripted_yaw_arm_scale=(
                                  args.scripted_yaw_arm_scale),
                              scripted_yaw_amplify_scale=(
                                  args.scripted_yaw_amplify_scale),
                              scripted_selective_omega_boost=(
                                  args.scripted_selective_omega_boost),
                              scripted_group_duty_skew=(
                                  args.scripted_group_duty_skew))
                results.append(res)
                if args.contact_audit and res.get("contact_audit"):
                    ca = res["contact_audit"]
                    am = ca.get("angmom_check", {})
                    print(f"  cell vx={vx_cmd} wz={wz_cmd} "
                          f"ph={phase_offset:.2f} seed={seed}: "
                          f"wz_med={res['wz_med']} "
                          f"yaw_imp_total={ca.get('yaw_imp_total_Nms')} "
                          f"fzsum={ca.get('sum_fz_med_N')}/"
                          f"{ca.get('weight_N')}N "
                          f"angmom corr={am.get('corr')} "
                          f"slope={am.get('slope')}")

    summary = summarize(results, frozen_margin=args.frozen_margin)
    print(f"[probe_turn_authority] policy={args.policy} "
          f"med|wz_err|={summary['med_wz_err']} "
          f"frozen_body_pred={summary['frozen_body_pred']} -> "
          f"{summary['verdict']}")

    out = {"policy": args.policy,
           "checkpoint": str(args.checkpoint) if args.checkpoint else None,
           **summary, "results": results}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2))
        print(f"[probe_turn_authority] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
