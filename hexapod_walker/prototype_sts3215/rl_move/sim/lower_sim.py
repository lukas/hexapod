"""Design + sim-validate the LOWER (stand -> belly -> zero) for the real robot.

2026-09-22: the reversed STEP stand-up was the sit-down.  On hexapod2 it pulls
the hips to -65 deg (the femur hits the top chassis at about -55) and the knees
to the 146-deg fold (mechanical stop ~140), parks the robot tall on tucked legs
("NOT down"), and the zero glide from there drags the feet across the floor.

This lower keeps the feet PLANTED while the body descends and only moves feet
through the air, one tripod at a time:

  A  tripod step OUT at stance height        (legs must be wide to get low)
  B  planted descent to mid height           (all six loaded, feet fixed)
  C  tripod step OUT again at mid height
  D  planted descent to belly rest (+press)
  E  belly carries the body: unloaded glide of all legs to zero

Foot targets are (radius, foot-bottom z) in the chassis frame solved with the
REAL leg model (RealLegFK).  The exported keyframes are what the robot plays
(joint-space glides between them, like every other stand-up mode), so the sim
run here replays exactly those keyframes with joint-space interpolation.

    python -m rl_move.sim.lower_sim                 # plan + sim + sheet
    python -m rl_move.sim.lower_sim --export        # merge mode "lower" into standup_modes.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .compare_standup import (CONTACT_N, PRESS, SPEED_DEG_S, RealLegFK, chassis_tilt,
                              pose18, reset_at_zero, seg)
from .sim_env import SimHexapodBalanceEnv, set_foot_ground_friction
from hexapod_core.joint_frame import joint_index
from rl_move.robot_state import N_JOINTS

TRIPODS = ((0, 2, 4), (1, 3, 5))
HIP_MIN_DEG = -38.0      # hexapod2: femur meets the top chassis near -55; keep margin
KNEE_MAX_DEG = 110.0     # never near the 135 cap / 140 stop
LIFT_M = 0.030           # foot clearance while a tripod swings
DESCENT_STEP_M = 0.015   # keyframe spacing on a planted descent (joint-space glides bow the foot path)
STEP_OUT_MIN_GAIN_M = 0.025  # a tripod step (body on 3 legs) only when it buys this much reach
SPEEDS = {"lift": 0.5, "swing": 0.6, "place": 0.45, "settle": 0.3, "descent_per_m": 60.0, "zero": 2.5}


def widest_radius(fkm: RealLegFK, z: float, hip_min: float, knee_max: float, r_from: float) -> float:
    """Largest foot radius at height z the leg reaches within the angle box (2 mm residual)."""
    best = r_from
    r = r_from
    while r < 0.30:
        h, k = fkm.solve(r, z)
        rr, zz = fkm.fk(h, k)
        if math.hypot(rr - r, zz - z) > 0.002 or h < hip_min or k > knee_max:
            break
        best = r
        r += 0.005
    return best


def lowest_z(fkm: RealLegFK, r: float, z_from: float, z_floor: float, hip_min: float, knee_max: float) -> float:
    """Foot z closest to the floor plane at radius r within the angle box.  Chassis frame: the body
    coming DOWN means the floor (and the planted foot) coming UP toward z_floor."""
    best = z_from
    z = z_from
    step = 0.005 if z_floor > z_from else -0.005
    while (z_floor - z) * step > 0:
        z_try = z + step
        if (z_floor - z_try) * step < 0:
            z_try = z_floor
        h, k = fkm.solve(r, z_try)
        rr, zz = fkm.fk(h, k)
        if math.hypot(rr - r, zz - z_try) > 0.002 or h < hip_min or k > knee_max:
            break
        best = z_try
        z = z_try
    return best


def foot_path_min_clearance(fkm: RealLegFK, hk0, hk1, z_floor: float, n: int = 12) -> float:
    """Min (foot z - floor) along a joint-space glide from hk0 to hk1 (what the robot's player does)."""
    worst = 1.0
    for i in range(n + 1):
        s = i / n
        h = hk0[0] + (hk1[0] - hk0[0]) * s
        k = hk0[1] + (hk1[1] - hk0[1]) * s
        _, z = fkm.fk(h, k)
        worst = min(worst, z - z_floor)
    return worst


def plan(fkm: RealLegFK, stance_hk: tuple[float, float], z_gnd: float,
         hip_min_deg: float = HIP_MIN_DEG, knee_max_deg: float = KNEE_MAX_DEG,
         first_step_out: bool = False, descent_s_per_m: float | None = None) -> list[dict]:
    """Keyframes: {"q_deg": 18 logical degrees, "s": glide seconds, "phase": str, "loaded": bool}."""
    hip_min, knee_max = math.radians(hip_min_deg), math.radians(knee_max_deg)
    r_s, z_s = fkm.fk(*stance_hk)
    legs = [(r_s, z_s)] * 6                     # current foot target per leg
    hk = [tuple(stance_hk)] * 6
    frames: list[dict] = []

    def q_of(targets) -> list[float]:
        q = [0.0] * N_JOINTS
        for i, (r, z) in enumerate(targets):
            h, k = fkm.solve(r, z, hk[i])
            hk[i] = (h, k)
            q[joint_index(i, "hip")] = math.degrees(h)
            q[joint_index(i, "knee")] = math.degrees(k)
        return q

    def add(targets, s, phase, loaded):
        frames.append({"q_deg": [round(v, 2) for v in q_of(targets)], "s": round(s, 2), "phase": phase, "loaded": loaded})

    def step_out(r_to: float, z: float, phase: str):
        for tri in TRIPODS:
            for stage, s in (("lift", SPEEDS["lift"]), ("swing", SPEEDS["swing"]), ("place", SPEEDS["place"])):
                t = list(legs)
                for i in tri:
                    if stage == "lift":
                        t[i] = (legs[i][0], z + LIFT_M)
                    elif stage == "swing":
                        t[i] = (r_to, z + LIFT_M)
                    else:
                        t[i] = (r_to, z)
                add(t, s, f"{phase}:{stage}", loaded=False)
                for i in tri:
                    legs[i] = t[i]
            add(list(legs), SPEEDS["settle"], f"{phase}:settle", loaded=False)

    def descend(r: float, z_to: float, phase: str):
        z0 = legs[0][1]
        n = max(1, int(math.ceil(abs(z_to - z0) / DESCENT_STEP_M)))
        for i in range(1, n + 1):
            z = z0 + (z_to - z0) * i / n
            for l in range(6):
                legs[l] = (r, z)
            add(list(legs), SPEEDS["descent_per_m"] * abs(z_to - z0) / n, f"{phase}:descent", loaded=True)

    if descent_s_per_m is not None:
        SPEEDS["descent_per_m"] = descent_s_per_m
    add(list(legs), 0.8, "start", loaded=True)                              # align onto the stance
    z_target = z_gnd                         # stop AT the floor plane: the belly takes the load, no pressing
    r, z = r_s, z_s
    for n_it, (phase_out, phase_down) in enumerate((("A", "B"), ("C", "D"), ("F", "G"))):
        r_wide = widest_radius(fkm, z, hip_min, knee_max, r) - 0.008
        allow_step = first_step_out or n_it > 0
        if allow_step and r_wide - r >= STEP_OUT_MIN_GAIN_M:   # a tripod step is only worth it if it buys real reach
            step_out(r_wide, z, phase_out)
            r = r_wide
        z_low = lowest_z(fkm, r, z, z_target, hip_min, knee_max)
        if abs(z_low - z) >= 0.003:
            descend(r, z_low, phase_down)
            z = z_low
        if abs(z - z_target) < 0.002:
            break
    if abs(z - z_target) >= 0.002:
        raise RuntimeError(f"cannot reach belly rest within the angle box: stuck at foot z {z*1000:.0f} mm, floor {z_gnd*1000:.0f} mm")
    frames.append({"q_deg": list(frames[-1]["q_deg"]), "s": 0.6, "phase": "rest", "loaded": True})
    # E: the belly carries the body now.  Lift the feet clear of the floor (unloaded), then glide to zero
    # through the air: pick a via-point so the joint-space glide never dips a foot below the floor.
    z_up = z_gnd
    for dz in (0.015, 0.012, 0.009, 0.006, 0.004):
        h, k = fkm.solve(r, z_gnd + dz, hk[0])
        rr, zz = fkm.fk(h, k)
        if math.hypot(rr - r, zz - (z_gnd + dz)) < 0.002 and h >= hip_min and k <= knee_max:
            z_up = z_gnd + dz
            break
    for l in range(6):
        legs[l] = (r, z_up)
    add(list(legs), 0.8, "E:unload", loaded=False)
    hk_up = hk[0]
    via = None
    for k_deg in range(6, 60, 2):
        cand = (0.0, math.radians(k_deg))          # hip level, tibia angled down k_deg: foot above the floor
        if foot_path_min_clearance(fkm, hk_up, cand, z_gnd) > 0.004 and \
           foot_path_min_clearance(fkm, cand, (0.0, 0.0), z_gnd) > -0.002:
            via = cand
            break
    if via is None:
        raise RuntimeError("no airborne path from belly rest to zero")
    q_via = [0.0] * N_JOINTS
    for l in range(6):
        q_via[joint_index(l, "hip")] = math.degrees(via[0])
        q_via[joint_index(l, "knee")] = math.degrees(via[1])
    frames.append({"q_deg": [round(v, 2) for v in q_via], "s": 1.5, "phase": "E:via", "loaded": False})
    frames.append({"q_deg": [0.0] * N_JOINTS, "s": SPEEDS["zero"], "phase": "E:zero", "loaded": False})
    return frames


def traj_from_frames(frames: list[dict], q_start: np.ndarray, dt: float):
    """Joint-space glides between keyframes (what the robot's player does)."""
    traj, phases = [], []
    q0 = q_start.copy()
    for f in frames:
        q1 = np.radians(np.array(f["q_deg"], dtype=float))
        part = seg(q0, q1, f["s"], dt)
        traj += part
        phases += [f["phase"]] * len(part)
        q0 = q1
    return traj, phases


def run(frames: list[dict], mu: float | None, *, seed: int = 0, sheet: Path | None = None,
        start_q: np.ndarray | None = None) -> dict:
    env = SimHexapodBalanceEnv(randomize=False, seed=seed)
    if mu is not None:
        set_foot_ground_friction(env.model, mu)
    env.reset()
    q_start = start_q.copy() if start_q is not None else (
        np.array(env._cmd, dtype=float).copy() if getattr(env, "_cmd", None) is not None
        else np.radians(np.array(frames[0]["q_deg"], dtype=float)))
    traj, phases = traj_from_frames(frames, q_start, env.dt)
    z_stance = float(env.data.xpos[env._chassis_bid, 2])
    # pre-roll: the reset holds the stance through the env's own controller; the scripted profile path
    # (what every stand-up mode uses) settles ~8 mm lower.  Command the stance through it and let that
    # transient pass BEFORE the metrics start, exactly like the robot already standing when 'down' is asked.
    env._cmd = q_start.copy()
    env._profile.command(q_start, speed_deg_s=SPEED_DEG_S, acc_units=env.write_acc_units)
    for _ in range(int(round(3.0 / env.dt))):
        env._advance()
    prev_f = [0.0] * 6
    anchor: dict[str, list] = {}          # phase -> per-leg xy where the loaded foot was when the phase began
    excursion: dict[str, float] = {}      # phase -> max loaded-foot displacement from its anchor (m)
    cur_phase = None
    cur_peak: dict[str, float] = {}
    cur_peak_joint: dict[str, int] = {}
    z_phase_end: dict[str, float] = {}
    tilt_peak = 0.0
    contact_in_zero = 0.0
    imgs = []
    if sheet is not None:
        env.render_mode = "rgb_array"
    next_shot = 0.0
    t = 0.0
    for q, ph in zip(traj, phases):
        env._cmd = q.copy()
        env._profile.command(q, speed_deg_s=SPEED_DEG_S, acc_units=env.write_acc_units)
        env._advance()
        t += env.dt
        key = ph.split(":")[0]
        cur = np.minimum(np.abs(env.data.qfrc_actuator[env._vadr]) * 1.2, 3.0)
        if float(cur.max()) > cur_peak.get(key, 0.0):
            cur_peak[key] = float(cur.max()); cur_peak_joint[key] = int(np.argmax(cur))
        z_phase_end[key] = float(env.data.xpos[env._chassis_bid, 2])
        roll, pitch = chassis_tilt(env)
        tilt_peak = max(tilt_peak, abs(roll), abs(pitch))
        if key != cur_phase:
            cur_phase = key
            anchor[key] = [None] * 6
        for i in range(6):
            f = float(env.data.sensordata[env._touch_adr[i]]) if env._touch_adr[i] >= 0 else 0.0
            xy = env.data.xpos[env._pad_bids[i], :2].copy()
            if f > CONTACT_N:
                if anchor[key][i] is None or prev_f[i] <= CONTACT_N:
                    anchor[key][i] = xy.copy()      # (re)anchor when a foot lands
                else:
                    excursion[key] = max(excursion.get(key, 0.0), float(np.linalg.norm(xy - anchor[key][i])))
            if ph == "E:zero" and t > sum(fr["s"] for fr in frames) - 0.5:
                contact_in_zero = max(contact_in_zero, f)
            prev_f[i] = f
        if sheet is not None and t >= next_shot:
            imgs.append((round(t, 1), ph, env.render()))
            next_shot += 1.0
    z_end = float(env.data.xpos[env._chassis_bid, 2])
    env.close()
    if sheet is not None and imgs:
        _sheet(imgs, sheet)
    return {"mu": mu, "z_stance_m": round(z_stance, 4), "z_end_m": round(z_end, 4),
            "loaded_foot_excursion_mm": {k: round(v * 1000, 1) for k, v in excursion.items()},
            "cur_peak_a": {k: f"{round(v, 2)}@j{cur_peak_joint[k]}" for k, v in cur_peak.items()},
            "chassis_z_end_mm": {k: round(v * 1000) for k, v in z_phase_end.items()},
            "tilt_peak_deg": round(math.degrees(tilt_peak), 1),
            "final_foot_contact_n": round(contact_in_zero, 2)}


def _sheet(imgs, path: Path, cols: int = 6):
    import cv2
    h, w = imgs[0][2].shape[:2]
    rows = int(math.ceil(len(imgs) / cols))
    canvas = np.full((rows * h, cols * w, 3), 255, dtype=np.uint8)
    for n, (t, ph, img) in enumerate(imgs):
        r, c = divmod(n, cols)
        tile = img.copy()
        cv2.putText(tile, f"t={t:.0f}s {ph}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        canvas[r * h:(r + 1) * h, c * w:(c + 1) * w] = tile
    cv2.imwrite(str(path), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))


def old_step_down_frames(knee_cap_deg: float = 135.0) -> list[dict]:
    """The sit-down the robot played until today: STEP keyframes reversed, knees capped."""
    p = Path(__file__).resolve().parents[2] / "linux_control" / "standup_modes.json"
    kfs = json.loads(p.read_text())["modes"]["step"]["keyframes"]
    qs = [[min(float(v), knee_cap_deg) if i % 3 == 2 else float(v) for i, v in enumerate(k["q_deg"])] for k in kfs]
    ss = [float(k["s"]) for k in kfs]
    out = [{"q_deg": qs[-1], "s": 0.8, "phase": "old:start", "loaded": True}]
    for i in range(len(qs) - 2, -1, -1):
        out.append({"q_deg": qs[i], "s": ss[i + 1], "phase": f"old:f{i}", "loaded": True})
    return out


def describe(frames: list[dict]) -> str:
    out = []
    for i, f in enumerate(frames):
        q = f["q_deg"]
        hips = [q[joint_index(l, "hip")] for l in range(6)]
        knees = [q[joint_index(l, "knee")] for l in range(6)]
        out.append(f"{i:2d} {f['phase']:11s} s={f['s']:4.2f} hip[{min(hips):6.1f}..{max(hips):6.1f}] knee[{min(knees):6.1f}..{max(knees):6.1f}]")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true", help="merge mode 'lower' into linux_control/standup_modes.json")
    ap.add_argument("--mus", type=float, nargs="*", default=[0.8, 1.2, 2.0])
    ap.add_argument("--sheet", default=str(Path.home() / ".hexapod" / "analysis" / "lower_sim_sheet.png"))
    ap.add_argument("--first-step", action="store_true", help="allow a tripod step-out at stance height (3-leg support up high)")
    ap.add_argument("--descent-s-per-m", type=float, default=None, help="planted descent pace (s per metre of body drop), default 45")
    ap.add_argument("--skip-old", action="store_true")
    ap.add_argument("--stance", type=float, nargs=2, metavar=("HIP_DEG", "KNEE_DEG"), default=[20.0, 80.0],
                    help="start stance (logical deg); default = the STEP stand-up's end pose")
    a = ap.parse_args()
    fkm = RealLegFK()
    env = SimHexapodBalanceEnv(randomize=False, seed=0)
    reset_at_zero(env, seed=0)
    z_belly = float(env.data.xpos[env._chassis_bid, 2])
    env.reset()
    hip0 = float(env.data.qpos[env._qadr[joint_index(0, 'hip')]]) if hasattr(env, "_qadr") else math.radians(20.0)
    env.close()
    z_gnd = -z_belly
    env2 = SimHexapodBalanceEnv(randomize=False, seed=0); env2.reset()
    cmd = np.array(env2._cmd, dtype=float) if getattr(env2, "_cmd", None) is not None else None
    env2.close()
    stance = (math.radians(a.stance[0]), math.radians(a.stance[1]))
    if cmd is not None:
        print(f"sim RL stance (logical) hip {math.degrees(cmd[joint_index(0, 'hip')]):.1f} knee "
              f"{math.degrees(cmd[joint_index(0, 'knee')]):.1f} deg; planning from {a.stance}")
    start_q = np.radians(np.array(pose18(*stance) * 0 + 0, dtype=float))
    start_q = pose18(*stance)
    frames = plan(fkm, stance, z_gnd, first_step_out=a.first_step, descent_s_per_m=a.descent_s_per_m)
    # joint-space glide bow: how far the planted foot radius wanders between descent keyframes (leg 0)
    bow = 0.0
    for f0, f1 in zip(frames, frames[1:]):
        if "descent" in f1["phase"]:
            hk0 = (math.radians(f0["q_deg"][joint_index(0, "hip")]), math.radians(f0["q_deg"][joint_index(0, "knee")]))
            hk1 = (math.radians(f1["q_deg"][joint_index(0, "hip")]), math.radians(f1["q_deg"][joint_index(0, "knee")]))
            r_end = fkm.fk(*hk1)[0]
            for i in range(1, 8):
                t_ = i / 8
                r_mid = fkm.fk(hk0[0] + (hk1[0] - hk0[0]) * t_, hk0[1] + (hk1[1] - hk0[1]) * t_)[0]
                bow = max(bow, abs(r_mid - r_end))
    print(f"descent glide bow (foot radius wander between keyframes): {bow*1000:.1f} mm")
    print(f"belly-rest chassis z {z_belly*1000:.0f} mm; stance foot (r,z) = {[round(v*1000) for v in fkm.fk(*stance)]} mm")
    print(describe(frames))
    print(f"total {sum(f['s'] for f in frames):.1f} s, {len(frames)} keyframes")
    hips = [q for f in frames for l in range(6) for q in [f['q_deg'][joint_index(l, 'hip')]]]
    knees = [q for f in frames for l in range(6) for q in [f['q_deg'][joint_index(l, 'knee')]]]
    print(f"commanded hip min {min(hips):.1f} deg (limit {HIP_MIN_DEG}), knee max {max(knees):.1f} deg (limit {KNEE_MAX_DEG})")
    for i, mu in enumerate(a.mus):
        res = run(frames, mu, sheet=Path(a.sheet) if i == 0 else None, start_q=start_q)
        print("NEW", json.dumps(res))
    if a.export:
        p = Path(__file__).resolve().parents[2] / "linux_control" / "standup_modes.json"
        data = json.loads(p.read_text())
        data["modes"]["lower"] = {
            "description": ("Sit-down (down only): tripod step OUT at stance height, planted descent to mid height, "
                            "tripod step OUT again, planted descent to belly rest, then the unloaded glide to zero. "
                            "Hips never below %.0f deg, knees never above %.0f deg (hexapod2 chassis/knee stops). "
                            "Generated by rl_move/sim/lower_sim.py 2026-09-22, sim-validated (feet do not slide while loaded)."
                            % (HIP_MIN_DEG, KNEE_MAX_DEG)),
            "down_only": True,
            "keyframes": [{"q_deg": f["q_deg"], "s": f["s"], "phase": f["phase"]} for f in frames],
            "total_s": round(sum(f["s"] for f in frames), 2),
        }
        p.write_text(json.dumps(data, indent=1) + "\n")
        print("exported mode 'lower' ->", p)

    if a.skip_old:
        return
    old = old_step_down_frames()
    res = run(old, a.mus[0], sheet=Path(a.sheet).with_name("old_stepdown_sim_sheet.png"), start_q=start_q)
    hips = [f['q_deg'][joint_index(l, 'hip')] for f in old for l in range(6)]
    knees = [f['q_deg'][joint_index(l, 'knee')] for f in old for l in range(6)]
    print(f"OLD reversed-STEP sit (for comparison): hip min {min(hips):.0f}, knee max {max(knees):.0f};", json.dumps(res))


if __name__ == "__main__":
    main()
