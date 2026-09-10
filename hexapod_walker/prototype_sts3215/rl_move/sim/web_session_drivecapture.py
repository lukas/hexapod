"""web_session_drivecapture.py — headless capture through the ACTUAL
browser-facing joystick HTTP API (``rl_move.sim.web_server`` /
``SimWebSession``), not the ``drive_video.py`` direct-env-stepping
shortcut.

Why this exists (2026-09-10): CURRENT_TRUTHS/STATUS.md label "actually
clicking through the browser/window HUD to confirm the loaded
(non-scripted) policy live" as the one piece of the interactive
joystick sim-demo requirement still open for BOTH parent goals,
reasoning "needs a display no cloud pod has ... irreducible-to-cloud".
That is true of the OPTIONAL native MuJoCo viewer window
(``--viewer``, macOS/mjpython-only) but NOT of the HTTP JSON API the
browser's own ``app.js`` calls (``/api/rl/roles``, ``/api/rl/policy``,
``/api/rl/drive/start|cmd|stop``, ``/api/sim/frame.jpg``) -- that API
is served headlessly by default (``web_server.py`` main() only opens a
viewer when ``--viewer`` is passed; ``sim_web.sh``'s own
``SIM_WEB_VIEWER=0`` mode already runs headless). This script drives
that exact API end to end with plain ``urllib`` (no browser, no
display, no Playwright): boots the real server as a subprocess with a
named policy loaded via ``--walk`` (the already-documented reproducible
launch command), confirms via ``GET /api/rl/policy`` that a real PPO
checkpoint loaded (hidden-layer sizes + activation function reported,
not the ``"scripted"`` fallback), replays the identical "human" drive
script (forward/crab-right/diag-left/reverse/**stop**/**restart**) used
by ``drive_video.py`` through ``POST /api/rl/drive/cmd`` at the real
wall-clock cadence the session's own background stepping thread runs
at, captures periodic frames via ``GET /api/sim/frame.jpg``, and
confirms the identity check again at the end (no silent mid-session
fallback). Zero training, zero GPU, walk-only.

Example (from ``hexapod_walker/prototype_sts3215``):

    uv run --with imageio --with pillow --with opencv-python-headless \
      python -m rl_move.sim.web_session_drivecapture \
      rl_move/sim/policies/<champion>.zip \
      --out-dir logs/manual_drive/<champion>_websession_capture
"""
from __future__ import annotations

import argparse
import json
import math
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

_PROTO = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return int(port)


def http_get(base_url: str, path: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode())


def http_get_bytes(base_url: str, path: str, timeout: float = 10.0) -> bytes:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=timeout) as r:
        return r.read()


def http_post(base_url: str, path: str, payload: dict | None = None,
             timeout: float = 10.0) -> dict:
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        f"{base_url}{path}", data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_ready(base_url: str, timeout_s: float = 60.0) -> None:
    t0 = time.monotonic()
    last_err: Exception | None = None
    while time.monotonic() - t0 < timeout_s:
        try:
            resp = http_get(base_url, "/api/ping", timeout=3.0)
            if resp.get("ok"):
                return
        except (urllib.error.URLError, OSError, ConnectionError) as e:
            last_err = e
        time.sleep(0.5)
    raise TimeoutError(f"web_server did not answer /api/ping within "
                       f"{timeout_s}s (last error: {last_err})")


def policy_identity_ok(info: dict, expect_name: str) -> tuple[bool, str]:
    """Pure check: does an ``/api/rl/policy`` "walk" sub-dict describe a
    REAL loaded checkpoint matching ``expect_name`` (not the scripted
    fallback, not some other policy)? Returns (ok, reason)."""
    if not isinstance(info, dict):
        return False, "no walk info"
    activation = info.get("activation")
    if activation in (None, "scripted", "unavailable"):
        return False, f"activation={activation!r} (scripted/unavailable)"
    source = str(info.get("source") or "")
    if expect_name not in source:
        return False, f"source {source!r} does not name {expect_name!r}"
    hidden = info.get("hidden") or []
    if not hidden:
        return False, "no hidden-layer sizes reported (unexpected for a " \
                      "real SB3 checkpoint)"
    return True, (f"activation={activation} hidden={hidden} "
                  f"source={Path(source).name}")


def fell_during_session(status: str) -> bool:
    return "DOWN" in str(status or "")


_STALL_CMD_MPS = 0.02   # ignore near-zero commands (stop/final-stop phases)
_STALL_FRAC = 0.25      # measured/commanded speed floor to call it "moving"


def locomotion_fraction(rows: list[dict], cmd_vx: float, cmd_vy: float
                        ) -> float:
    """Mean measured body speed / commanded speed over ``rows``.

    Pure helper on telemetry rows (each with ``vx_body``/``vy_body``).
    Returns 1.0 (treated as fine) when nothing material was commanded
    or there is no data -- this is a stall detector, not a tracking-
    accuracy metric. Added 2026-09-10 after the first full-cfg PASS
    run (boot/final identity real, zero falls, zero rejected commands)
    turned out to be a FALSE POSITIVE: the champion's chassis rose
    from the 110mm trained plant height to a ~135mm plateau and body
    velocity decayed to ~0 by ~1.5s into a sustained "forward" command
    even though ``goal.height_ref`` stayed 0 and ``walk_obs_body_vel``
    correctly resolved to 1.0 the whole time (both prior candidate
    explanations in ``CURRENT_TRUTHS.md`` ruled out by direct in-
    process instrumentation, not just re-guessed) -- none of the three
    earlier boolean checks (identity/fell/rejected) can see a session
    that stays "active" while quietly failing to locomote."""
    cmd_mag = math.hypot(cmd_vx, cmd_vy)
    if cmd_mag < _STALL_CMD_MPS or not rows:
        return 1.0
    speeds = [math.hypot(r.get("vx_body") or 0.0, r.get("vy_body") or 0.0)
             for r in rows]
    return (sum(speeds) / len(speeds)) / cmd_mag


def directional_locomotion_fraction(rows: list[dict], cmd_vx: float,
                                    cmd_vy: float) -> float:
    """Mean measured body velocity PROJECTED ONTO the commanded direction,
    divided by commanded speed -- signed, unlike ``locomotion_fraction``.

    Added 2026-09-10 (idle-refill follow-up to the "reverse" residual
    CURRENT_TRUTHS labeled SETTLED-as-real-but-not-root-caused): the
    speed-magnitude metric above cannot distinguish "walking backward" from
    "jittering/oscillating in place at a decent speed" -- ``hypot(vx, vy)``
    is always >= 0 regardless of which way the body is actually moving.
    Re-reading the 8-repeat "reverse" telemetry with THIS metric instead
    shows every repeat (the 6 the magnitude metric called PASS and the 2 it
    called FAIL alike) nets only ~0.14-0.26 of the commanded speed in the
    actually-commanded direction -- a narrow, uniformly-weak band with no
    clean pass/fail split, unlike the magnitude read's 0.23-0.36 spread that
    straddled the 0.25 floor. This does not replace ``locomotion_fraction``
    (a deliberately generous stall/non-stall gate, kept bit-exact here) --
    it is a sharper diagnostic for whichever cycle root-causes the
    mechanism next: the honest open question is "why is net backward
    tracking uniformly weak" (a real, session-wide "reverse" gait quality
    gap), not "why does an otherwise-solid reverse gait intermittently
    freeze for one rep in four"."""
    cmd_mag = math.hypot(cmd_vx, cmd_vy)
    if cmd_mag < _STALL_CMD_MPS or not rows:
        return 1.0
    ux, uy = cmd_vx / cmd_mag, cmd_vy / cmd_mag
    proj = [(r.get("vx_body") or 0.0) * ux + (r.get("vy_body") or 0.0) * uy
           for r in rows]
    return (sum(proj) / len(proj)) / cmd_mag


def net_displacement_fraction(rows: list[dict], cmd_vx: float, cmd_vy: float
                              ) -> float | None:
    """TRUE net-displacement directional tracking, independent of the
    per-tick velocity SAMPLING RATE.

    Added 2026-09-10, closing the "telemetry-sampling artifact" branch
    CURRENT_TRUTHS.md left open next to the "real undertrained-direction
    skill gap" branch: ``directional_locomotion_fraction`` averages
    instantaneous ``vx_body``/``vy_body`` SAMPLES taken every ~0.2-0.3s
    (the HTTP poll cadence) -- if the true velocity signal aliases with
    the gait's stride period at that sampling rate, the sample-mean can
    misrepresent the actual mean velocity even though every individual
    sample is a real, correctly-measured reading. Actual body
    DISPLACEMENT over the window has no such aliasing risk: it is the
    exact integral of true velocity, regardless of how coarsely it is
    polled (position samples do not alias the way instantaneous rate
    samples can). This function uses the WORLD-frame chassis position
    (``pos_x``/``pos_y``, added alongside ``vx_body``/``vy_body`` in the
    telemetry row) and the body's own ``yaw_deg`` at the START of the
    window to rotate the net world-frame displacement into the same
    body-relative frame the (body-frame) command is expressed in, then
    reports it as an average-velocity-equivalent fraction of commanded
    speed -- directly comparable to ``directional_locomotion_fraction``.
    Assumes yaw does not change materially across the window (true for
    every phase used by this tool's own scripted "human" script -- none
    of them command a nonzero ``wz``); returns ``None`` (not 1.0/0.0)
    when position/yaw fields are missing (older telemetry captured
    before this field existed) so a caller can tell "no data" apart from
    "measured and near-zero", unlike the two velocity-based siblings
    above which predate this distinction and use 1.0 as their
    not-applicable sentinel."""
    cmd_mag = math.hypot(cmd_vx, cmd_vy)
    if cmd_mag < _STALL_CMD_MPS or len(rows) < 2:
        return None
    r0, r1 = rows[0], rows[-1]
    for key in ("pos_x", "pos_y", "yaw_deg"):
        if r0.get(key) is None or r1.get(key) is None:
            return None
    dt = _row_t(r1) - _row_t(r0)
    if dt <= 0:
        return None
    dx_world = float(r1["pos_x"]) - float(r0["pos_x"])
    dy_world = float(r1["pos_y"]) - float(r0["pos_y"])
    yaw0 = math.radians(float(r0["yaw_deg"]))
    cos_y, sin_y = math.cos(yaw0), math.sin(yaw0)
    # Rotate the WORLD displacement into the body frame at t=r0 (inverse
    # of the world<-body rotation by +yaw0).
    dx_body = cos_y * dx_world + sin_y * dy_world
    dy_body = -sin_y * dx_world + cos_y * dy_world
    ux, uy = cmd_vx / cmd_mag, cmd_vy / cmd_mag
    net_along = dx_body * ux + dy_body * uy
    return (net_along / dt) / cmd_mag


def _row_t(row: dict) -> float:
    """The row's SIMULATED time if captured (``sim_t_s``, added
    2026-09-10), else its wall-clock ``t`` for older telemetry. Phase
    boundaries from ``human_drive_phases`` are defined in simulated
    seconds (shared with ``drive_video.py``'s direct env-stepping,
    which runs near 1:1 sim:wall time); this HTTP-driven tool's own
    background server thread does NOT reliably run at 1:1 (measured as
    low as ~0.28x real-time on the controller pod under HTTP-poll/GIL
    contention), so windowing by wall-clock ``t`` against
    simulated-second phase boundaries silently shrank every phase's
    analyzed window to a fraction of its intended simulated duration --
    see the sim-time-pacing fix in ``main()`` and CURRENT_TRUTHS.md
    2026-09-10."""
    v = row.get("sim_t_s")
    return float(v) if v is not None else float(row["t"])


def stalled_phases(telemetry: list[dict], phases: list[tuple],
                   t_end: float, settle_s: float = 1.5,
                   frac_floor: float = _STALL_FRAC) -> list[dict]:
    """Which commanded-motion phases the session failed to actually walk
    during, skipping the velocity-ramp settle window (the live drive
    session ramps commanded velocity in over ~1s -- see ``_PlayTraj.
    VEL_RATE`` -- so judging from t=0 of a phase would flag the ramp
    itself, not a stall). Windows on SIMULATED time (``_row_t``), not
    wall-clock, since the phase boundaries themselves are simulated
    seconds (2026-09-10 fix)."""
    out = []
    for i, (t0, vx, vy, _wz, label) in enumerate(phases):
        cmd_mag = math.hypot(vx, vy)
        if cmd_mag < _STALL_CMD_MPS:
            continue
        t1 = phases[i + 1][0] if i + 1 < len(phases) else t_end
        window = [r for r in telemetry if t0 + settle_s <= _row_t(r) < t1]
        frac = locomotion_fraction(window, vx, vy)
        if frac < frac_floor:
            out.append({"label": label, "t0": t0, "t1": t1,
                       "cmd_mps": round(cmd_mag, 4),
                       "measured_fraction_of_cmd": round(frac, 3),
                       "n_ticks": len(window)})
    return out


def drive_cmd_rejected(status: str) -> bool:
    """True when a ``/api/rl/drive`` status shows the session silently
    stopped honoring joystick commands (``_engage_walk`` refusing, e.g.
    because the chassis sank under the trained walk threshold) -- a
    real regression, not a fall/termination, so ``fell_during_session``
    alone would miss it. Caught 2026-09-10: driving the walkcurr
    rl_only champion through the actual HTTP API with the web
    session's bare-default cfg (no ``--cfg-set``) silently stopped
    responding to every command after ~8s while still reporting
    ``active`` — this check is what should have failed that run."""
    s = str(status or "")
    return ("too low to walk" in s or "stand first" in s
           or "down - reset" in s)


def _annotate(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    from .train_ppo_sim import _annotate_frame
    return _annotate_frame(frame, lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--speed", type=float, default=0.06)
    ap.add_argument("--frame-every-s", type=float, default=2.0)
    ap.add_argument("--boot-timeout-s", type=float, default=90.0)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--cfg-set", action="append", default=[],
                    help="forwarded verbatim to web_server.py --cfg-set "
                         "(e.g. this run's own goal.joint_action_box_*/"
                         "bias_* values) so the interactive session "
                         "matches the checkpoint's training contract "
                         "instead of bare defaults")
    args = ap.parse_args()

    ckpt = args.checkpoint
    if not ckpt.is_absolute():
        ckpt = (_PROTO / ckpt).resolve()
    if not ckpt.is_file():
        raise SystemExit(f"no such checkpoint: {ckpt}")

    http_port = _free_port()
    https_port = _free_port()
    base_url = f"http://{args.bind}:{http_port}"

    out = args.out_dir or (
        _PROTO / "logs" / "manual_drive" /
        f"{ckpt.stem}_websession_{time.strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)

    cmd = [sys.executable, "-m", "rl_move.sim.web_server",
          "--bind", args.bind,
          "--http-port", str(http_port), "--https-port", str(https_port),
          "--walk", str(ckpt), "--no-vision"]
    for spec in args.cfg_set:
        cmd += ["--cfg-set", spec]
    print(f"[websession_capture] launching: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(_PROTO),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    server_log: list[str] = []
    telemetry: list[dict] = []
    frame_paths: list[Path] = []
    result: dict = {"checkpoint": str(ckpt), "http_port": http_port,
                    "server_cmd": cmd}
    try:
        wait_ready(base_url, timeout_s=args.boot_timeout_s)

        boot_info = http_get(base_url, "/api/rl/policy")["walk"]
        boot_ok, boot_reason = policy_identity_ok(boot_info, ckpt.stem)
        result["boot_policy_check"] = {"ok": boot_ok, "reason": boot_reason,
                                       "raw": boot_info}
        print(f"[websession_capture] boot identity check: {boot_ok} "
             f"({boot_reason})")

        start_resp = http_post(base_url, "/api/rl/drive/start")
        result["drive_start"] = start_resp

        from .drive_video import human_drive_phases
        phases = human_drive_phases(args.speed)
        t_end = phases[-1][0] + 3.0
        session_t0 = time.monotonic()
        fell = False
        rejected_ticks = 0
        first_rejected_t: float | None = None
        idx = 0
        next_frame_at = 0.0
        # SIM-TIME PACING (2026-09-10, root-cause finding this same
        # investigation surfaced): ``human_drive_phases``'s boundaries
        # (0, 5, 9, 13, 17, 19.5, 24) are SIMULATED seconds -- shared
        # with ``drive_video.py``, which steps the env directly and so
        # gets ~1:1 sim:wall time. THIS tool instead drives through the
        # real HTTP server, whose background stepping thread competes
        # (GIL/CPU) with this loop's own HTTP round-trips; measured on
        # this controller pod, ``sim_t_s`` advanced only ~7.7s over
        # ~27.2s of WALL clock (~0.28x real-time). Gating phase
        # transitions on wall-clock ``elapsed`` (the old behavior) cut
        # every phase down to ~0.28x its intended simulated duration --
        # e.g. the nominal 4 simulated seconds of "reverse" became ~1.0
        # actual simulated second, most or all of which sits inside the
        # velocity command's own 1.0-simulated-second blend ramp
        # (``_PlayTraj``/``WalkTrajectory``) -- so every phase's
        # "post-settle" analysis window may have been measuring the
        # ramp transient, not settled walking, regardless of host
        # speed. Fixed: phase transitions (and the overall session end)
        # now gate on the SERVER'S OWN ``live.t_s`` (simulated seconds),
        # so every phase always gets its full intended simulated
        # duration no matter how fast or slow this pod steps physics.
        sim_t_s = 0.0
        # HEARTBEAT FIX (2026-09-10, root-cause of the "full-cfg PASS was a
        # stalled-locomotion false positive" regression this same investigation
        # found): the real browser client resends the CURRENT (vx, vy, wz) at
        # 5 Hz the whole time a drive session is active (app.js `drvHb =
        # setInterval(drvSend, 200)`, ~3069/3336-3337), because
        # `SimWebSession._tick_locked`'s own dead-man's-switch
        # (`_DRIVE_HEARTBEAT_STALE_S = 0.6` real wall-clock seconds,
        # web_session.py) zeroes traj.vx/vy (silently, ok=True the whole
        # time) once 0.6s pass without a fresh `/api/rl/drive/cmd` POST. This
        # loop used to POST only once per phase TRANSITION (phases are 4-5s
        # apart) and otherwise only GET the read-only `/api/rl/drive` status
        # -- so the session spent >80% of every phase silently frozen in
        # "hold", not because of a policy/obs/env bug but because this
        # capture tool never re-armed the safety heartbeat the real UI always
        # sends. Resending the ACTIVE phase's command every loop iteration
        # (this loop already sleeps ~0.2s, matching the browser's own 200ms
        # cadence) is what a real held joystick input does; do not remove
        # this without re-checking web_session.py's own heartbeat contract.
        cur_vx, cur_vy, cur_wz, cur_label = 0.0, 0.0, 0.0, "boot"
        while True:
            elapsed = time.monotonic() - session_t0
            if idx < len(phases) and sim_t_s >= phases[idx][0]:
                _, cur_vx, cur_vy, cur_wz, cur_label = phases[idx]
                idx += 1
                print(f"[websession_capture] wall={elapsed:5.1f}s "
                     f"sim={sim_t_s:5.1f}s cmd={cur_label} "
                     f"vx={cur_vx:+.3f} vy={cur_vy:+.3f} wz={cur_wz:+.3f}")
            cmd_resp = http_post(base_url, "/api/rl/drive/cmd",
                                {"vx": cur_vx, "vy": cur_vy, "wz": cur_wz})
            state = http_get(base_url, "/api/rl/drive")
            live = state.get("live") or {}
            chassis_xyz = live.get("chassis_xyz_m") or [None, None, None]
            live_t_s = live.get("t_s")
            if live_t_s is not None:
                sim_t_s = float(live_t_s)
            row = {"t": round(elapsed, 2),
                  "label": phases[idx - 1][4] if idx else "boot",
                  "active": state.get("active"), "status": state.get("status"),
                  "vx_body": live.get("vx_body"), "vy_body": live.get("vy_body"),
                  "roll_deg": live.get("roll_deg"),
                  "pitch_deg": live.get("pitch_deg"),
                  # World-frame chassis x/y + body yaw, added 2026-09-10
                  # so a true net-DISPLACEMENT metric (not just an
                  # average of instantaneous velocity samples) can be
                  # computed post-hoc -- see
                  # ``net_displacement_fraction`` below and
                  # CURRENT_TRUTHS.md 2026-09-10 "telemetry-sampling
                  # artifact" open question. Purely additive fields;
                  # every existing consumer keys off vx_body/vy_body
                  # unchanged.
                  "pos_x": chassis_xyz[0], "pos_y": chassis_xyz[1],
                  "yaw_deg": live.get("yaw_deg"),
                  # Simulated time (the server's own ``self.sim_t``), NOT
                  # wall-clock ``elapsed`` -- added 2026-09-10 alongside
                  # pos_x/pos_y/yaw_deg to let a caller detect/correct
                  # for the sim background thread running slower than
                  # real wall-clock time under HTTP-poll overhead, which
                  # would bias a displacement/WALL-TIME average low even
                  # though displacement/SIM-TIME is correct.
                  "sim_t_s": live_t_s,
                  "height_mm": live.get("height_mm")}
            telemetry.append(row)
            if fell_during_session(state.get("status")):
                fell = True
                print(f"[websession_capture] FALL detected at t={elapsed:.1f}s"
                     f": status={state.get('status')!r}")
                break
            if idx > 0 and drive_cmd_rejected(state.get("status")):
                rejected_ticks += 1
                if first_rejected_t is None:
                    first_rejected_t = elapsed
                    print(f"[websession_capture] DRIVE COMMANDS REJECTED "
                         f"starting t={elapsed:.1f}s: "
                         f"status={state.get('status')!r} (session no "
                         f"longer honoring joystick input)")
            if elapsed >= next_frame_at:
                try:
                    jpg = http_get_bytes(base_url, "/api/sim/frame.jpg")
                    import imageio.v2 as imageio
                    from io import BytesIO
                    arr = imageio.imread(BytesIO(jpg))
                    arr = _annotate(arr, [
                        f"websession-drive t={elapsed:5.1f}s {row['label']}",
                        f"vx/vy {row['vx_body']}/{row['vy_body']} m/s",
                        f"roll/pitch {row['roll_deg']}/{row['pitch_deg']} deg",
                        f"status: {row['status']}"])
                    fp = frames_dir / f"frame_{len(frame_paths):03d}.png"
                    imageio.imwrite(fp, arr)
                    frame_paths.append(fp)
                except (urllib.error.URLError, OSError, RuntimeError) as e:
                    print(f"[websession_capture] frame capture failed at "
                         f"t={elapsed:.1f}s: {e}")
                next_frame_at = elapsed + args.frame_every_s
            if sim_t_s >= t_end:
                break
            # Wall-clock safety timeout, independent of the sim-time exit
            # above: a stalled/dead server would otherwise never advance
            # sim_t_s and this loop would hang forever. Generous multiple
            # (this pod measured ~0.28x real-time; allow for far worse).
            if elapsed >= t_end * 20.0 + 30.0:
                print(f"[websession_capture] WALL-CLOCK SAFETY TIMEOUT at "
                     f"wall={elapsed:.1f}s (sim only reached {sim_t_s:.1f}s "
                     f"of {t_end:.1f}s target) -- server may be stalled; "
                     f"aborting instead of hanging")
                result["timed_out"] = True
                break
            time.sleep(0.2)

        stop_resp = http_post(base_url, "/api/rl/drive/stop")
        result["drive_stop"] = stop_resp

        final_info = http_get(base_url, "/api/rl/policy")["walk"]
        final_ok, final_reason = policy_identity_ok(final_info, ckpt.stem)
        result["final_policy_check"] = {"ok": final_ok, "reason": final_reason,
                                        "raw": final_info}
        print(f"[websession_capture] final identity check: {final_ok} "
             f"({final_reason})")
        result["fell"] = fell
        result["drive_cmd_rejected_ticks"] = rejected_ticks
        result["drive_cmd_first_rejected_t"] = first_rejected_t
        result["n_frames"] = len(frame_paths)
        # NOTE (2026-09-10): this field name predates the sim-time-pacing
        # fix above and was actually reporting WALL-CLOCK elapsed the
        # whole time (misnamed, not a behavior bug) -- now reports the
        # true simulated seconds driven, with the wall-clock figure kept
        # alongside under its own honest name.
        result["sim_seconds_driven"] = round(sim_t_s, 2)
        result["wall_seconds_elapsed"] = round(elapsed, 2)
        stalled = stalled_phases(telemetry, phases, t_end)
        result["stalled_phases"] = stalled
        if stalled:
            print(f"[websession_capture] LOCOMOTION STALL: "
                 f"{len(stalled)} phase(s) commanded motion the session "
                 f"never delivered -- {[s['label'] for s in stalled]}")
    finally:
        proc.terminate()
        try:
            out_txt, _ = proc.communicate(timeout=10)
            server_log.append(out_txt or "")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()

    if frame_paths:
        import imageio.v2 as imageio
        rows_imgs = [imageio.imread(p) for p in frame_paths]
        w = max(r.shape[1] for r in rows_imgs)
        h = max(r.shape[0] for r in rows_imgs)
        padded = [np.pad(r, ((0, h - r.shape[0]), (0, w - r.shape[1]), (0, 0)))
                 for r in rows_imgs]
        strip = np.concatenate(padded, axis=1)
        imageio.imwrite(out / "contact_sheet.png", strip)

    (out / "server_log.txt").write_text("\n".join(server_log))
    (out / "telemetry.json").write_text(json.dumps(telemetry, indent=2))
    passed = (result.get("boot_policy_check", {}).get("ok")
             and result.get("final_policy_check", {}).get("ok")
             and not result.get("fell")
             and not result.get("drive_cmd_rejected_ticks")
             and not result.get("stalled_phases")
             and result.get("n_frames", 0) > 0)
    result["PASS"] = bool(passed)
    (out / "summary.json").write_text(json.dumps(result, indent=2))
    readme = f"""# Headless interactive drive-session capture

Checkpoint: `{ckpt.name}`
Result: {"PASS" if passed else "FAIL"}

This drove the ACTUAL browser-facing HTTP joystick API
(`rl_move.sim.web_server` / `SimWebSession`, the exact routes
`linux_control/webui/app.js` calls) headlessly via plain `urllib` --
no browser, no native viewer, no display -- through the same "human"
command sequence `ops.sh drivevideo --script human` uses
(forward/crab-right/diag-left/reverse/stop/restart).

- Boot identity check ({result.get('boot_policy_check', {}).get('ok')}):
  {result.get('boot_policy_check', {}).get('reason')}
- Final identity check ({result.get('final_policy_check', {}).get('ok')}):
  {result.get('final_policy_check', {}).get('reason')}
- Fell during session: {result.get('fell')}
- Drive commands rejected (session stopped honoring joystick input,
  e.g. chassis sank below the walk-engage threshold): \
{result.get('drive_cmd_rejected_ticks')} polls, first at t=\
{result.get('drive_cmd_first_rejected_t')}
- Frames captured: {result.get('n_frames')} (see `frames/`,
  `contact_sheet.png`)
- Locomotion stalls (commanded motion the session reported "active"
  for but never actually delivered -- measured body speed stayed
  below {int(_STALL_FRAC * 100)}% of the commanded speed for the
  whole phase, after the ~1.5s velocity-ramp settle window):
  {result.get('stalled_phases') or "none"}
- Full per-poll telemetry: `telemetry.json`
- Server stdout/stderr: `server_log.txt`

Reproduce: `uv run --with imageio --with pillow --with
opencv-python-headless python -m rl_move.sim.web_session_drivecapture
rl_move/sim/policies/{ckpt.name}`
"""
    (out / "README.md").write_text(readme)
    print(json.dumps(result, indent=2))
    print(f"[websession_capture] artifacts -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
