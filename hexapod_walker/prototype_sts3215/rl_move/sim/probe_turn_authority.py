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
from collections import Counter
from pathlib import Path

import numpy as np


from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD
from .servo_model import SimServoParams
from .walk_task import SimHexapodJointWalkEnv
from .joint_task import q_rad_to_action


def _support_point(contacts):
    """Normal-load-weighted contact centroid, independent of contact order."""
    if not contacts:
        return None
    points, loads = zip(*contacts)
    return np.average(np.asarray(points), axis=0, weights=loads)


def _material_slip(contacts, x0, r0, x1, r1):
    """Mean distance of loaded pad material points (norm BEFORE averaging)."""
    if not contacts:
        return 0.0
    points, loads = zip(*contacts)
    points = np.asarray(points)
    moved = (points - x0) @ r0 @ r1.T + x1
    return float(np.average(np.linalg.norm((moved - points)[:, :2], axis=1),
                            weights=loads))


def _contact_cone_usage(wrench, friction, dim, cone):
    """Normalized full wrench in the active contact-frame friction cone.

    MuJoCo order: tangent1, tangent2, spin, roll1, roll2. Elliptic
    cones use the L2 norm; pyramidal edge combinations give the L1
    bound. Torque friction coefficients have length units, so each
    torque is divided by its own coefficient * normal force.

    Undefined/invalid data return a reason, never a false zero usage.
    The five returned components are zero for inactive condim axes.
    """
    if dim not in (1, 3, 4, 6) or cone not in (0, 1):
        return None, None, "unknown contact dimension or cone type"
    w = np.asarray(wrench, dtype=float)
    if w.shape != (6,) or not np.isfinite(w[:dim]).all():
        return None, None, "nonfinite or malformed contact wrench"
    if w[0] <= 0:
        return None, None, "nonpositive normal force"
    z = np.zeros(5)
    if dim > 1:
        mu = np.asarray(friction, dtype=float)
        if mu.size < dim - 1 or not np.isfinite(mu[:dim - 1]).all():
            return None, None, "missing or nonfinite friction coefficients"
        mu = mu[:dim - 1]
        if np.any(mu < 0):
            return None, None, "negative friction coefficient"
        f = np.abs(w[1:dim])
        if np.any((mu == 0) & (f != 0)):
            return None, None, "nonzero force on zero friction component"
        np.divide(f, mu * w[0], out=z[:dim - 1], where=mu > 0)
    # mjCONE_PYRAMIDAL=0; mjCONE_ELLIPTIC=1.
    usage = np.linalg.norm(z, ord=1 if cone == 0 else 2)
    if not np.isfinite(usage):
        return None, None, "nonfinite normalized contact wrench"
    return float(usage), z, None


class _ContactAudit:
    """Read-only, environment-local MuJoCo proxy for physics-step auditing.

    mj_step leaves contact wrenches and their geometry at the force-evaluation
    state, while qpos/qvel have advanced. Integrate those solved wrenches once
    per actual physics step. Compute endpoint angular momentum on PRIVATE
    MjData, never by refreshing the live solver state. Raw force signs follow
    MuJoCo's force-on-geom2 convention; validation never repairs their sign.
    """

    N_BINS = 12
    # traction extension (09-08 focus note: direct contact-force /
    # friction-cone diagnostic). Purely additive per-substep fields;
    # every pre-existing output is byte-identical.
    SLIP_MPS = 0.02     # material slip speed that counts as "slipping"
    NEAR_CONE = 0.90    # applied separately to planar and full-cone usage
    LOW_CONE = 0.50     # low usage alone does not establish a slip cause
    RAIL_FRAC = 0.95    # |actuator_force| >= frac*rail = saturated

    def __init__(self, env):
        self.mj = env._mujoco
        self.env = env
        m = env.model
        self.root = int(m.body_rootid[env._chassis_bid])
        self.robot_bodies = np.flatnonzero(m.body_rootid == self.root)
        self.root_dofs = np.flatnonzero(m.dof_bodyid == self.root)
        self.robot_geoms = set(np.flatnonzero(
            np.isin(m.geom_bodyid, self.robot_bodies)))
        self.pads = [m.body(f"L{i}_pad").id for i in range(6)]
        self.geom_foot = {g: f for f, b in enumerate(self.pads)
                          for g in range(m.ngeom) if m.geom_bodyid[g] == b}
        self.weight_n = float(np.sum(m.body_mass[self.robot_bodies])
                              * -m.opt.gravity[2])
        rail = np.abs(m.actuator_forcerange).max(axis=1)
        self.act_rail = np.where(rail > 0, rail, np.inf)
        self.cone_type = int(m.opt.cone)
        self.cone_dims_seen: set[int] = set()
        self.cone_invalid_reasons: set[str] = set()
        self.scratch = self.mj.MjData(m)
        self.rows: list[dict] = []
        self.pending: list[dict] = []
        self.recording = False
        self.n_ticks = 0
        self.prev_q_safe = None
        self.jrows: list[dict] = []
        self.unsupported: set[str] = set()
        if int(m.opt.integrator) != int(self.mj.mjtIntegrator.mjINT_EULER):
            self.unsupported.add("only Euler wrench integration validated")
        if m.opt.viscosity or m.opt.density:
            self.unsupported.add("fluid forces not included")
        if m.neq:
            self.unsupported.add("equality-constraint external wrenches not audited")
        if np.any(m.body_gravcomp[self.robot_bodies]):
            self.unsupported.add("gravity compensation not included")
        if np.any(m.dof_armature[self.root_dofs]):
            self.unsupported.add("free-root armature momentum not included")

    def __getattr__(self, name):
        return getattr(self.mj, name)

    def begin_interval(self, *, phase, record=True):
        self.pending = []
        self.phase = float(phase % (2.0 * math.pi))
        self.recording = record

    def _endpoint(self):
        m, d, s = self.env.model, self.env.data, self.scratch
        s.qpos[:] = d.qpos
        s.qvel[:] = d.qvel
        s.mocap_pos[:] = d.mocap_pos
        s.mocap_quat[:] = d.mocap_quat
        self.mj.mj_kinematics(m, s)
        self.mj.mj_comPos(m, s)
        self.mj.mj_comVel(m, s)
        self.mj.mj_subtreeVel(m, s)
        return (float(s.subtree_angmom[self.root, 2]),
                s.xpos[self.pads].copy(),
                s.xmat[self.pads].reshape(6, 3, 3).copy())

    def mj_step(self, m, d):
        if not self.recording:
            return self.mj.mj_step(m, d)
        t0 = float(d.time)
        lz0, _, _ = self._endpoint()
        self.mj.mj_step(m, d)  # exactly one real step; never mj_forward live
        h = float(d.time) - t0
        if h <= 0:
            self.unsupported.add("physics time did not advance")
            return
        lz1, pad_x1, pad_r1 = self._endpoint()
        com = d.subtree_com[self.root].copy()
        r_body = d.xmat[self.env._chassis_bid].reshape(3, 3)
        fz, tau_f, tau_c = np.zeros(6), np.zeros(6), np.zeros(6)
        contacts = [[] for _ in range(6)]
        external_contact_tau = 0.0
        # traction extension: per-foot normal / tangential force sums,
        # slide-mu, and per-contact friction-cone usage (load-weighted
        # mean + max) at this solved physics step.
        fn_sum, ft_sum = np.zeros(6), np.zeros(6)
        mu_min = np.full(6, np.inf)
        u_wsum, u_max = np.zeros(6), np.zeros(6)
        full_fn, full_wsum, full_max = np.zeros(6), np.zeros(6), np.zeros(6)
        component_wsum, component_max = np.zeros((6, 5)), np.zeros((6, 5))
        full_invalid = np.zeros(6, dtype=int)
        f6 = np.zeros(6)
        for ci in range(d.ncon):
            c = d.contact[ci]
            if c.efc_address < 0:
                continue  # detected gap contacts have no solved constraint
            inside1, inside2 = c.geom1 in self.robot_geoms, c.geom2 in self.robot_geoms
            if inside1 == inside2:
                continue  # internal contacts cancel; outside contacts irrelevant
            sign = -1.0 if inside1 else 1.0
            robot_geom = c.geom1 if inside1 else c.geom2
            self.mj.mj_contactForce(m, d, ci, f6)
            frame = np.asarray(c.frame).reshape(3, 3)
            force, couple = sign * (frame.T @ f6[:3]), sign * (frame.T @ f6[3:])
            p = c.pos.copy()
            moment = float(np.cross(p - com, force)[2])
            external_contact_tau += moment + float(couple[2])
            foot = self.geom_foot.get(robot_geom)
            if foot is None:
                continue
            fz[foot] += float(force[2])
            tau_f[foot] += moment
            tau_c[foot] += float(couple[2])
            if f6[0] > 0:
                contacts[foot].append((p, float(f6[0])))
                fn_c, ft_c = float(f6[0]), float(np.hypot(f6[1], f6[2]))
                _fric = getattr(c, "friction", None)  # synthetic-test proxies
                mu_c = float(_fric[0]) if _fric is not None else 0.0
                fn_sum[foot] += fn_c
                ft_sum[foot] += ft_c
                mu_min[foot] = min(mu_min[foot], mu_c)
                if mu_c > 0:
                    u = ft_c / (mu_c * fn_c)
                    u_wsum[foot] += fn_c * u
                    u_max[foot] = max(u_max[foot], u)
                # Full condim-aware budget; preserve the legacy planar
                # estimate above solely as a separately labelled diagnostic.
                dim = int(getattr(c, "dim", 0))
                self.cone_dims_seen.add(dim)
                fu, components, reason = _contact_cone_usage(
                    f6, _fric, dim, self.cone_type)
                if reason is not None:
                    full_invalid[foot] += 1
                    self.cone_invalid_reasons.add(reason)
                else:
                    full_fn[foot] += fn_c
                    full_wsum[foot] += fn_c * fu
                    full_max[foot] = max(full_max[foot], fu)
                    component_wsum[foot] += fn_c * components
                    component_max[foot] = np.maximum(
                        component_max[foot], components)
        # Applied Cartesian wrench is world force/torque at the body's COM.
        applied_tau = sum(float(np.cross(d.xipos[b] - com,
                                         d.xfrc_applied[b, :3])[2]
                                + d.xfrc_applied[b, 5])
                          for b in self.robot_bodies)
        # Uniform gravity has zero net moment about the whole-robot COM.
        # Generalized/free-root forces cannot be assumed internal torques.
        if np.any(d.qfrc_applied):
            self.unsupported.add("generalized applied forces not included")
        if np.any(np.abs(d.qfrc_passive[self.root_dofs]) > 1e-12):
            self.unsupported.add("free-root passive forces not included")
        loaded = np.array([bool(c) for c in contacts])
        rel_body = np.full((6, 2), np.nan)
        slip_center, slip_material = np.zeros(6), np.zeros(6)
        for f, b in enumerate(self.pads):
            if not loaded[f]:
                continue
            point = _support_point(contacts[f])
            rel_body[f] = (r_body.T @ (point - com))[:2]
            x0, r0 = d.xpos[b], d.xmat[b].reshape(3, 3)
            slip_center[f] = np.linalg.norm((pad_x1[f] - x0)[:2])
            slip_material[f] = _material_slip(contacts[f], x0, r0,
                                               pad_x1[f], pad_r1[f])
        with np.errstate(invalid="ignore"):
            u_wmean = np.where(fn_sum > 0, u_wsum / np.maximum(fn_sum, 1e-12),
                               np.nan)
        mu_min[~np.isfinite(mu_min)] = 0.0
        self.pending.append({
            "phase": self.phase, "h": h, "fz": fz,
            "tau_f": tau_f, "tau_c": tau_c, "loaded": loaded,
            "rel_body": rel_body, "slip_center": slip_center,
            "slip_material": slip_material, "delta_lz": lz1 - lz0,
            "external_tau": external_contact_tau + applied_tau,
            "nonfoot_tau": external_contact_tau - float((tau_f + tau_c).sum()),
            "applied_tau": applied_tau,
            "fn": fn_sum, "ft": ft_sum, "mu": mu_min,
            "u_wmean": u_wmean, "u_max": u_max,
            "full_fn": full_fn,
            "full_u_wmean": full_wsum / np.maximum(full_fn, 1e-12),
            "full_u_max": full_max,
            "full_component_wmean": component_wsum / np.maximum(full_fn[:, None], 1e-12),
            "full_component_max": component_max, "full_invalid": full_invalid,
            "act_sat": (np.abs(d.actuator_force) / self.act_rail
                        if getattr(d, "actuator_force", None) is not None
                        and len(self.act_rail)   # synthetic-test proxies
                        else np.zeros(0)),
        })

    def tick(self, *, q_prop, q_safe, q_act):
        if not self.pending:
            return
        self.rows.extend(self.pending)
        self.pending = []
        self.n_ticks += 1
        env = self.env
        if q_prop is not None and q_safe is not None and q_act is not None:
            j = {"clip_gap": np.abs(np.asarray(q_prop) - np.asarray(q_safe)),
                 "track_err": np.abs(np.asarray(q_act) - np.asarray(q_safe))}
            if self.prev_q_safe is not None:
                j["slew_sat"] = (np.abs(np.asarray(q_safe) - self.prev_q_safe)
                                 >= 0.98 * env.safety.max_dq)
            self.jrows.append(j)
            self.prev_q_safe = np.asarray(q_safe, dtype=float).copy()

    def summary(self) -> dict:
        if not self.rows:
            return {"n_ticks": 0, "n_substeps": 0,
                    "angmom_check": {"valid": False, "reason": "insufficient data"}}
        h = np.array([r["h"] for r in self.rows])
        fz = np.stack([r["fz"] for r in self.rows])
        tau_f = np.stack([r["tau_f"] for r in self.rows])
        tau_c = np.stack([r["tau_c"] for r in self.rows])
        loaded = np.stack([r["loaded"] for r in self.rows])
        phase = np.array([r["phase"] for r in self.rows])
        x = np.array([r["external_tau"] for r in self.rows]) * h
        y = np.array([r["delta_lz"] for r in self.rows])
        # Match impulse with momentum change over the SAME physics interval.
        # Correlation alone cannot validate scale (e.g. slope=0.3, corr=1).
        resid = y - x
        rms = lambda a: float(np.sqrt(np.mean(a * a)))
        scale = max(rms(x), rms(y), 1e-12)
        relative = rms(resid) / scale
        xt, yt = x / h, y / h
        xc, yc = xt - np.mean(xt), yt - np.mean(yt)
        var = float(xc @ xc)
        corr = (float((xc @ yc) / np.sqrt(var * (yc @ yc)))
                if var > 1e-24 and yc @ yc > 1e-24 else None)
        angmom = {"valid": (not self.unsupported
                             and (relative <= 0.15 or rms(resid) <= 1e-9)),
                  "unaccounted": sorted(self.unsupported),
                  "slope": float(xc @ yc / var) if var > 1e-24 else None,
                  "corr": corr, "relative_rms_residual": relative,
                  "rms_impulse_residual_Nms": rms(resid),
                  "net_external_impulse_Nms": float(x.sum()),
                  "delta_lz_Nms": float(y.sum()),
                  "med_abs_resid": float(np.median(np.abs(resid / h)))}
        bins = np.minimum((phase / (2 * math.pi) * self.N_BINS).astype(int),
                          self.N_BINS - 1)
        phase_bins = []
        for b in range(self.N_BINS):
            sel = bins == b
            phase_bins.append({
                "n": int(sel.sum()), "duration_s": float(h[sel].sum()),
                "contact_frac": np.average(loaded[sel], axis=0, weights=h[sel]).tolist(),
                "tau_z_mean": np.average((tau_f + tau_c)[sel], axis=0, weights=h[sel]).tolist(),
                "fz_mean": np.average(fz[sel], axis=0, weights=h[sel]).tolist(),
            } if sel.any() else None)
        rel = np.stack([r["rel_body"] for r in self.rows])
        stance_xy = []
        for f in range(6):
            good = loaded[:, f]
            stance_xy.append(np.average(rel[good, f], axis=0, weights=h[good]).tolist()
                             if good.any() else None)
        sum_fz_med = float(np.median(fz.sum(axis=1)))
        out = {
            "audit_version": 2, "n_ticks": self.n_ticks,
            "n_substeps": len(self.rows), "duration_s": float(h.sum()),
            "physics_timestep_s": float(self.env.model.opt.timestep),
            "control_timestep_s": float(self.env.dt),
            "integrator": int(self.env.model.opt.integrator),
            "model_nmesh": int(self.env.model.nmesh),
            "sign_flipped": False, "support_force_sign_valid": sum_fz_med >= 0,
            "sum_fz_med_N": sum_fz_med, "weight_N": self.weight_n,
            "angmom_check": angmom,
            "bc_anchor_resid": {
                "available": False,
                "reason": ("returned bc_target belongs to the next action; "
                           "teacher phase/clock alignment is unverified"),
            },
            "per_foot": {
                "duty": np.average(loaded, axis=0, weights=h).tolist(),
                "fz_mean_loaded_N": [float(np.average(fz[loaded[:, f], f],
                                            weights=h[loaded[:, f]]))
                                     if loaded[:, f].any() else None for f in range(6)],
                "yaw_imp_force_Nms": (h @ tau_f).tolist(),
                "yaw_imp_couple_Nms": (h @ tau_c).tolist(),
                "slip_center_m": np.sum([r["slip_center"] for r in self.rows], axis=0).tolist(),
                "slip_material_m": np.sum([r["slip_material"] for r in self.rows], axis=0).tolist(),
                "stance_center_body_xy_m": stance_xy,
            },
            "yaw_imp_total_Nms": float(h @ (tau_f + tau_c).sum(axis=1)),
            "nonfoot_yaw_imp_Nms": float(h @ np.array([r["nonfoot_tau"] for r in self.rows])),
            "applied_yaw_imp_Nms": float(h @ np.array([r["applied_tau"] for r in self.rows])),
            "slip_definition": "normal-load-weighted mean pad material-point XY distance per physics step",
            "phase_bins": phase_bins,
        }
        # ---- traction extension (additive; 09-08 focus note) ----
        fn = np.stack([r["fn"] for r in self.rows])
        ft = np.stack([r["ft"] for r in self.rows])
        mu = np.stack([r["mu"] for r in self.rows])
        u_w = np.stack([r["u_wmean"] for r in self.rows])
        u_mx = np.stack([r["u_max"] for r in self.rows])
        act_sat = np.stack([r["act_sat"] for r in self.rows])
        slip_v = np.stack([r["slip_material"] for r in self.rows]) / h[:, None]
        tau_all = tau_f + tau_c
        pos = np.where(tau_all > 0, tau_all, 0.0).sum(axis=1)
        neg = np.where(tau_all < 0, tau_all, 0.0).sum(axis=1)
        net = tau_all.sum(axis=1)
        gross = pos - neg
        with np.errstate(divide="ignore", invalid="ignore"):
            cancel = np.where(gross > 1e-9, np.abs(net) / gross, np.nan)
        med = lambda a: float(np.median(a)) if len(a) else None
        per_foot_tr = {}
        for f in range(6):
            sel = loaded[:, f]
            uw = u_w[sel, f]; uw = uw[np.isfinite(uw)]
            sslip = sel & (slip_v[:, f] > self.SLIP_MPS)
            us = u_mx[sslip, f]
            per_foot_tr[f] = {
                "loaded_substeps": int(sel.sum()),
                "fn_med_N": med(fn[sel, f]),
                "ft_med_N": med(ft[sel, f]),
                "mu_med": med(mu[sel, f]),
                "cone_usage_wmean_med": med(uw),
                "cone_usage_max_med": med(u_mx[sel, f]),
                "cone_usage_max_p90": (float(np.percentile(u_mx[sel, f], 90))
                                       if sel.any() else None),
                "frac_loaded_near_cone": (float(np.mean(
                    u_mx[sel, f] > self.NEAR_CONE)) if sel.any() else None),
                "slip_substeps": int(sslip.sum()),
                "slip_speed_med_mps": med(slip_v[sslip, f]),
                "cone_usage_max_med_on_slip": med(us),
                "frac_slip_near_cone": (float(np.mean(us > self.NEAR_CONE))
                                        if len(us) else None),
                "frac_slip_low_cone": (float(np.mean(us < self.LOW_CONE))
                                       if len(us) else None),
                "tau_z_med_loaded_Nm": med(tau_all[sel, f]),
            }
        sat = {}
        n_act = act_sat.shape[1]
        for ax, nm in ((0, "yaw"), (1, "hip"), (2, "knee")):
            vals = [act_sat[loaded[:, f], 3 * f + ax] for f in range(6)
                    if 3 * f + ax < n_act and loaded[:, f].any()]
            v = np.concatenate(vals) if vals else np.array([])
            sat[nm] = {"force_sat_med": med(v),
                       "frac_at_rail": (float(np.mean(v >= self.RAIL_FRAC))
                                        if len(v) else None)}
        out["traction"] = {
            "thresholds": {"SLIP_MPS": self.SLIP_MPS,
                           "NEAR_CONE": self.NEAR_CONE,
                           "LOW_CONE": self.LOW_CONE,
                           "RAIL_FRAC": self.RAIL_FRAC},
            "per_foot": per_foot_tr,
            "yaw_budget": {
                "net_tau_z_med_Nm": med(net),
                "pos_sum_med_Nm": med(pos),
                "neg_sum_med_Nm": med(-neg),
                "net_over_gross_med": med(cancel[np.isfinite(cancel)]),
                "couple_imp_share_of_net": (
                    float(abs(h @ tau_c.sum(axis=1))
                          / max(abs(h @ net), 1e-12))),
            },
            "actuator_force_saturation_stance": sat,
        }
        full_fn = np.stack([r["full_fn"] for r in self.rows])
        full_u = np.stack([r["full_u_wmean"] for r in self.rows])
        full_max = np.stack([r["full_u_max"] for r in self.rows])
        component_max = np.stack([r["full_component_max"] for r in self.rows])
        invalid = np.stack([r["full_invalid"] for r in self.rows])
        full_per_foot = {}
        for f in range(6):
            # Keep the original any-positive-contact mask for compatibility.
            # Invalid samples are explicitly excluded and invalidate the
            # full-cone result, rather than masquerading as sub-cone samples.
            sel = loaded[:, f] & (full_fn[:, f] > 0) & (invalid[:, f] == 0)
            sslip = sel & (slip_v[:, f] > self.SLIP_MPS)
            us = full_max[sslip, f]
            full_per_foot[f] = {
                "loaded_substeps": int(loaded[:, f].sum()),
                "valid_loaded_substeps": int(sel.sum()),
                "invalid_contact_samples": int(invalid[:, f].sum()),
                "usage_wmean_med": med(full_u[sel, f]),
                "usage_max_med": med(full_max[sel, f]),
                "usage_max_p90": (float(np.percentile(full_max[sel, f], 90))
                                  if sel.any() else None),
                "normalized_component_max_p90": (
                    np.percentile(component_max[sel, f], 90, axis=0).tolist()
                    if sel.any() else [None] * 5),
                "frac_loaded_near_cone": (float(np.mean(
                    full_max[sel, f] > self.NEAR_CONE)) if sel.any() else None),
                "slip_substeps": int(sslip.sum()),
                "usage_max_med_on_slip": med(us),
                "frac_slip_near_cone": (float(np.mean(us > self.NEAR_CONE))
                                        if len(us) else None),
                "frac_slip_low_cone": (float(np.mean(us < self.LOW_CONE))
                                       if len(us) else None),
            }
        out["traction"]["legacy_cone_usage_definition"] = (
            "planar slide only: hypot(tangent1,tangent2)/(friction[0]*fn); "
            "omits anisotropy/spin/roll and cannot exclude full-cone saturation")
        out["traction"]["loaded_definition"] = (
            "any active compressive contact (fn>0); no 2 N load threshold")
        out["traction"]["full_cone"] = {
            "valid": not self.cone_invalid_reasons,
            "invalid_contact_samples": int(invalid.sum()),
            "invalid_reasons": sorted(self.cone_invalid_reasons),
            "cone_type": ("pyramidal" if self.cone_type == 0 else
                          "elliptic" if self.cone_type == 1 else "unknown"),
            "norm": "L1" if self.cone_type == 0 else "L2",
            "observed_condim": sorted(self.cone_dims_seen),
            "component_order": ["tangent1", "tangent2", "spin", "roll1", "roll2"],
            "definition": (
                "per-contact abs(wrench[1:condim])/(friction[:condim-1]*fn), "
                "then cone norm; no averaging opposing wrenches first"),
            "loaded_definition": out["traction"]["loaded_definition"],
            "slip_conditioning": (
                "per-foot normal-load-weighted material XY speed; "
                "usage is maximum across that foot's active contacts"),
            "per_foot": full_per_foot,
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
            scripted_stance_radius_scale: float = 1.0,
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
        # clock; the scripted TripodGait is independently seeded below.
        env._phase = float(phase_offset) % (2.0 * math.pi)
    audit = _ContactAudit(env) if contact_audit else None
    if audit is not None:
        env._mujoco = audit
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
    scripted_start_phase = None
    if policy == "scripted":
        from hexapod_core.tripod_gait import TripodGait
        gait = TripodGait(
            vx=0.0,
            combined_yaw_arm_scale=scripted_yaw_arm_scale,
            combined_yaw_amplify_scale=scripted_yaw_amplify_scale,
            combined_selective_omega_boost=scripted_selective_omega_boost,
            combined_group_duty_skew=scripted_group_duty_skew)
        if scripted_stance_radius_scale != 1.0:
            # 09-07 turn-authority audit: radial stance-center
            # displacement A/B (--policy scripted only). The constructor
            # clips to the hardware-era [0.55, 1.05] band; diagnostic
            # doses outside it are set directly on the instance (no
            # shared-code change) — sync_plant_stance() below recomputes
            # _foot_radius_eff so foot POSITION and the omega stroke
            # term move together (geometry-consistent by construction,
            # see _yaw_frame_xy/_foot_target_in_body).
            gait.stance_radius_scale = float(scripted_stance_radius_scale)
        gait.sync_plant_stance(*WALK_PLANT)
        gait.reset_phase(phase=phase_offset)
        scripted_start_phase = float(gait._phase)
    step = 0
    wz_list: list[float] = []
    vx_list: list[float] = []
    modes_seen: list[str] = []
    fell = False
    try:
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
            if audit is not None:
                audit.begin_interval(phase=(gait._phase if policy == "scripted"
                                            else float(getattr(env, "_phase", 0.0))),
                                     record=step >= hold_n + ramp_n)
            obs, r, term, trunc, info = env.step(act)
            gm = info.get("goal_mode")
            modes_seen.append(gm)
            if step >= hold_n + ramp_n and gm == "walk":
                wz_list.append(float(env._body_wz()))
                vx_list.append(float(env._body_vel_xy()[0]))
                if audit is not None:
                    audit.tick(
                        q_prop=cap.get("q_prop"),
                        q_safe=env.safety._last_safe.copy(),
                        q_act=(env._state.joint_position.copy()
                               if env._state is not None else None))
            step += 1
            if term:
                fell = True
            if term or trunc:
                break
    finally:
        if audit is not None:
            env._mujoco = audit.mj
        env.close()
    wz_arr = np.array(wz_list)
    wz_err = np.abs(wz_arr - wz_cmd)
    vx_arr = np.array(vx_list)
    vx_err = np.abs(vx_arr - vx_cmd)
    return {
        "wz_cmd": wz_cmd,
        "vx_cmd": vx_cmd,
        "phase_offset": phase_offset,
        "scripted_start_phase": scripted_start_phase,
        "scripted_stance_radius_scale": (float(gait.stance_radius_scale)
                                          if policy == "scripted" else None),
        "scripted_foot_radius_m": (float(gait._foot_radius_eff)
                                    if policy == "scripted" else None),
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
    verdict = ("INSUFFICIENT DATA (no scored walk ticks)" if med_err is None else
               "FROZEN-BODY (no real turn tracking)" if frozen else
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
    ap.add_argument("--scripted-stance-radius-scale", type=float,
                    default=1.0,
                    help="--policy scripted only: radial stance-center "
                         "displacement (TripodGait stance_radius_scale, "
                         "diagnostic doses may exceed the hardware clip "
                         "band; 09-07 turn-authority audit); default "
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
                              scripted_stance_radius_scale=(
                                  args.scripted_stance_radius_scale),
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
                          f"angmom valid={am.get('valid')} "
                          f"relative_rms_residual={am.get('relative_rms_residual')} "
                          f"corr={am.get('corr')} slope={am.get('slope')} "
                          f"unaccounted={am.get('unaccounted')}")

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
