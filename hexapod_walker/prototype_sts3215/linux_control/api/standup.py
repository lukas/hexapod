"""BenchAPI route group: stand-up lab modes.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403


class StandupApi:
    # -- stand-up lab ---------------------------------------------------------
    # Sim-validated stand-up strategies (rl_move/sim/compare_standup.py):
    # keyframes baked into standup_modes.json, played back as chained
    # ease_to_pose glides. See the JSON's per-mode descriptions.
    STANDUP_FILE = lc_dir() / "standup_modes.json"

    def _load_standup(self) -> dict:
        # Read fresh each call (small file) so a re-deployed bake is
        # picked up without restarting the service.
        return json.loads(self.STANDUP_FILE.read_text())

    def standup_modes(self) -> dict:
        """List the available stand-up strategies (web UI selector)."""
        try:
            data = self._load_standup()
        except (OSError, ValueError) as e:
            return {"ok": False, "error": f"standup_modes.json: {e}"}
        return {
            "ok": True,
            "frame": data.get("frame", ""),
            "modes": [
                {"name": name,
                 "description": m.get("description", ""),
                 "keyframes": len(m.get("keyframes", [])),
                 "total_s": m.get("total_s")}
                for name, m in (data.get("modes") or {}).items()],
        }

    def standup(self, *, mode: str = "step", speed: float = 1.0,
                direction: str = "up", force: bool = False,
                torque: int = 700, abort_current_a: float = 3.0,
                sync_gen: int | None = None) -> dict:
        """Play one baked stand-up strategy (async).

        ``direction="up"`` normally starts from the ZERO pose (belly down,
        legs straight out); if the robot is already upright, it adjusts
        and verifies the sim walk-ready stance instead of re-running a rise.
        Otherwise it ACQUIRES zero first (08-11 directive), then plays
        the keyframes. ``direction="down"`` plays the same keyframes in
        reverse only when the robot is normally upright; down from a
        not-standing/tangled pose delegates to safe-zero recovery.
        Acquisition failure stops everything with an error and the
        keyframes never play.
        Aborts between keyframes if any servo peaked above
        ``abort_current_a`` (stall-fight = the pinned-feet failure this
        lab exists to fix; do not grind on it).

        ``sync_gen`` (internal): run the whole job INLINE in the
        calling worker thread under the caller's demo generation —
        used by ``_acquire_start`` to chain safe-zero → stand-up. No
        job-slot claim, no preempt, returns the final result dict.

        Hardware truth 08-10: tuck stood at 2.48 A peak, step at
        2.97 A; blend stalled short at only 0.57 A (the servos give up
        quietly under the torque limit — matches the sim's low-torque
        rows). Faster tempos raise push currents toward the guard.
        """
        try:
            from inplace_demos import (
                CurrentPeakTracker, PoseStreamer, _enable_torque,
                _live_robot_ids, _set_torque_limit, _write_pose,
                ease_to_pose,
            )
            from drive_controller import MAX_SAFE_DELTA_DEG
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        try:
            data = self._load_standup()
            if str(mode) == "plant":
                return {"ok": False,
                        "error": "stand-up mode 'plant' was removed; use 'step'"}
            m = data["modes"][str(mode)]
            keyframes = m["keyframes"]
        except (OSError, ValueError, KeyError, ImportError) as e:
            return {"ok": False, "error": f"unknown stand-up mode: {e}"}
        down = str(direction) == "down"
        if sync_gen is None and self._drive_active():
            return {"ok": False,
                    "error": ("drive session active/stopping; use End "
                              "session and wait for 'Session ended' before "
                              "stand/lower")}
        if sync_gen is None and (self._demo_thread
                                 and self._demo_thread.is_alive()):
            if not self._preempt_demo_thread(reason="→ standup",
                                             timeout=5.0):
                return {"ok": False, "error": "previous job still running"}

        if not force:
            # State machine for ordinary stand/lower requests:
            # - UP + already upright: adjust/verify the sim walk-ready stance.
            # - UP + not upright: safe-zero first, then STEP-up below.
            # - DOWN + upright: play the selected reverse keyframes
            #   (standard callers select STEP).
            # - DOWN + not upright/tangled: use safe-zero recovery instead
            #   of blindly reverse-playing stand-up keyframes.
            present, missing = self._present_pose18()
            standing = (None if missing else
                        self._normal_standing_pose(present))
        else:
            standing = None
        if not down and standing:
            res = self.go_zero(pose="stand", force=force)
            res["route"] = "stand_adjust"
            res["standing"] = standing
            return res
        safe_zero_before_up = bool(not force and not down
                                   and standing is None)
        if down and not force and standing is None:
            if sync_gen is None:
                res = self.safe_zero(force=force)
                res["route"] = "safe_zero_not_standing"
                return res
            res = self._safe_zero_sync(
                abort_check=self._demo_abort.is_set)
            res["route"] = "safe_zero_not_standing"
            return res

        speed = max(0.25, min(10.0, float(speed)))
        torque = max(300, min(1000, int(torque)))
        # frames: (18-joint target deg, glide seconds). Reversed playback
        # keeps each segment's duration with its segment: the glide from
        # keyframe i to i-1 takes what i-1 -> i took, plus a short
        # align glide onto the last keyframe first.
        frames = [([float(v) for v in kf["q_deg"]], float(kf["s"]))
                  for kf in keyframes]
        if down:
            qs = [q for q, _ in frames]
            ss = [s for _, s in frames]
            frames = [(qs[-1], 0.8)] + [
                (qs[i], ss[i + 1]) for i in range(len(qs) - 2, -1, -1)]
        first = frames[0][0]
        acquire_zero_first = False
        safe_down_instead = False
        if safe_zero_before_up:
            acquire_zero_first = True
        if not force:
            worst, j = self._delta_vs_present(first)
            if worst is None:
                return {"ok": False,
                        "error": ("no encoder readings (bus warming "
                                  "up after restart?) — cannot check "
                                  "the start pose; retry in a few "
                                  "seconds")}
            if worst > MAX_SAFE_DELTA_DEG:
                # 08-11 directive: acquire the start pose instead of
                # refusing. Up → safe zero first. Down from a pose the
                # keyframes weren't baked for → the safe descent IS
                # the down path (never play reversed keyframes from an
                # unknown stance).
                if down:
                    safe_down_instead = True
                else:
                    acquire_zero_first = True

        verb = "sit-down" if down else "stand-up"
        if sync_gen is None:
            self._demo_gen += 1
            gen = self._demo_gen
            self._demo_abort.clear()
            with self._lock:
                self._demo_name = (f"standup_{mode}"
                                   + ("_down" if down else ""))
                self._demo_status = f"{verb} · {mode} (x{speed:.2f})"
                self._demo_params = {"mode": mode, "speed": speed,
                                     "direction": direction,
                                     "torque": torque}
                self._cal_result = None
                self._cal_progress = {"msg": self._demo_status}
            self._set_activity("demo", self._demo_status)
        else:
            gen = int(sync_gen)
            with self._lock:
                self._cal_progress = {
                    "msg": f"{verb} · {mode} (x{speed:.2f})"}

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            live = _live_robot_ids(d.bus)
            tracker = CurrentPeakTracker()
            result: dict = {"ok": False, "mode": mode,
                            "direction": direction}
            # Worker-local copy: the down path drops the wide frame
            # (kf_path = kf_path[1:]); assigning to the closure name
            # `frames` would make it worker-local and blow up every
            # earlier read (UnboundLocalError — bit us 08-11).
            kf_path = list(frames)
            try:
                from event_log import emit
                emit("standup", f"{mode} {verb} x{speed:g} start",
                     data={"mode": mode, "direction": direction,
                           "speed": speed, "keyframes": len(kf_path),
                           "live_ids": sorted(live)})
            except Exception:
                pass
            try:
                self._bus_hot_begin()

                def _acq_prog(p: dict) -> None:
                    with self._lock:
                        self._cal_progress = dict(p)

                if safe_down_instead:
                    # Not at this mode's stance — the collision-aware
                    # descent is the whole down job.
                    res = self._safe_zero_sync(
                        abort_check=self._demo_abort.is_set,
                        on_progress=_acq_prog)
                    result.update(res)
                    result["via"] = "safe_zero"
                    result.setdefault("ok", False)
                    if gen != self._demo_gen:
                        return
                    with self._lock:
                        self._cal_result = result
                        self._demo_status = (
                            "done · safe descent to zero (was not at "
                            "stance)" if result.get("ok") else
                            str(result.get("error") or "aborted"))
                        self._cal_progress = {"msg": self._demo_status}
                    return result
                if acquire_zero_first:
                    res_a = self._acquire_start("zero", gen=gen,
                                                on_progress=_acq_prog)
                    if gen != self._demo_gen:
                        return
                    if not res_a.get("ok"):
                        result["error"] = (
                            "start pose not reached — "
                            + str(res_a.get("error") or "aborted"))
                        with self._lock:
                            self._cal_result = result
                            self._demo_status = result["error"]
                            self._cal_progress = {
                                "msg": self._demo_status}
                        return result

                _set_torque_limit(d.bus, live, torque)
                _enable_torque(d.bus, live)
                n = len(kf_path)

                def guard_msg() -> str:
                    return (f"stopped: {tracker.peak_a:.2f} A peak on "
                            f"joint {tracker.peak_joint} (> "
                            f"{abort_current_a:.1f} A) — stall-fight, "
                            "not grinding on it")

                # Guard semantics (08-10, after a 3.04 A spike aborted
                # a healthy 10x stand at 60%): trip on STALL-FIGHT —
                # a joint over the limit while NOT MOVING, two sweeps
                # in a row — not on an instantaneous reading. A moving
                # joint briefly over 3 A is honest acceleration work.
                # Hard cap 4.0 A trips regardless.
                HARD_CAP_A = 4.0
                stall_prev: set = set()

                def stall_trip() -> bool:
                    nonlocal stall_prev
                    if tracker.peak_a > HARD_CAP_A:
                        return True
                    now = {fb["joint"] for fb in tracker.last_fb
                           if abs(fb["current_a"]) > abort_current_a
                           and abs(fb["speed_deg_s"]) < 8.0}
                    hit = bool(now & stall_prev)
                    stall_prev = now
                    return hit

                def _replant(target_q: list[float]) -> bool:
                    """Re-seat all six feet at target_q, one tripod
                    at a time. Loaded feet cannot slide sideways
                    against ground friction (sim-validated) — lifting
                    is the only way to move them. Lift via hip -6 /
                    knee +6: near tibia-vertical a knee-only lift
                    barely clears the floor (cos ~ 0), the hip raise
                    gives ~9 mm."""
                    for legs in ((0, 2, 4), (1, 3, 5)):
                        if self._demo_abort.is_set():
                            return False
                        q_lift = list(target_q)
                        for lg in legs:
                            q_lift[3 * lg + 1] -= 6.0
                            q_lift[3 * lg + 2] += 6.0
                        _write_pose(d.bus, q_lift, live,
                                    speed=400, acc=50)
                        time.sleep(0.4)
                        _write_pose(d.bus, target_q, live,
                                    speed=300, acc=40)
                        time.sleep(0.45)
                    return True

                # PURSUE — stream the interpolated keyframe path at
                # ~20 Hz for ALL tempos. Per-keyframe glides settle-
                # polled to within 2.5 deg at EVERY waypoint; loaded
                # joints never converge, so each waypoint burned its
                # full timeout (measured: 24 s for the 8.8 s tuck at
                # 1x — operator, 08-10: "ridiculously slow"). The old
                # "careful" per-keyframe path is gone; pursuit has the
                # same current guard and abort checks. Sizing gotchas
                # (operator, 08-10, "starts slow then pops up"): the
                # module MAX_STREAM_SPEED=450 (~40 deg/s) let targets
                # outrun the servos and the final settle covered the
                # backlog in one pop — pass an explicit cap; size each
                # write by the ACTUAL elapsed tick (the current sweep
                # steals 0.1-0.3 s).
                q0 = kf_path[0][0]
                aborted = False
                t_run0 = time.monotonic()
                if down and len(kf_path) >= 2:
                    # Sit starts at the wide (tibia-vertical) stance;
                    # the feet must come back UNDER the body before
                    # the fold, and loaded feet can't slide inward —
                    # re-seat them on the narrow stance by tripods.
                    # If the robot already stands narrow (old-stance
                    # or RL walk-ready start) skip the wide frame instead
                    # of easing outward pointlessly.
                    with self.drive._lock:
                        w_wide, _ = (self.drive
                                     ._max_delta_vs_present(
                                         kf_path[0][0]))
                        w_narrow, _ = (self.drive
                                       ._max_delta_vs_present(
                                           kf_path[1][0]))
                    if w_narrow <= w_wide:
                        kf_path = kf_path[1:]
                        q0 = kf_path[0][0]
                    else:
                        with self._lock:
                            self._cal_progress = {
                                "msg": f"{mode} {verb}: re-seating "
                                       "feet under body"}
                        if not _replant(kf_path[1][0]):
                            aborted = True
                        else:
                            kf_path = kf_path[1:]
                            q0 = kf_path[0][0]
                with self.drive._lock:
                    worst0, _ = self.drive._max_delta_vs_present(q0)
                if worst0 > 5.0 and not aborted:
                    with self._lock:
                        self._cal_progress = {
                            "msg": f"{mode} {verb}: aligning"}
                    ok = ease_to_pose(
                        d.bus, q0,
                        abort_check=self._demo_abort.is_set,
                        seconds=max(0.6, kf_path[0][1] / speed),
                        label=f"{mode} align",
                        current_tracker=tracker)
                    aborted = not ok
                # Schedule: each segment gets max(authored/tempo,
                # travel-at-90deg/s). PER-SEGMENT, not a uniform
                # rescale: servo_fb traces (08-10, sit x10) showed
                # authored-duration pacing idles the servos through
                # slow phases (13 deg/s measured) then demands
                # 130 deg/s+ through fast ones — loaded servos fell
                # 76 deg behind and the settle glide did the last
                # quarter of the motion in one yank ("pauses a bunch
                # of times"). Travel-based pacing keeps the target
                # moving at a rate the hardware actually tracks.
                RATE_DPS = 90.0
                ts, qs = [0.0], [q0]
                for q_deg, kf_s in kf_path[1:]:
                    d_seg = max(abs(b - a) for a, b in
                                zip(qs[-1], q_deg))
                    ts.append(ts[-1] + max(0.02, kf_s / speed,
                                           d_seg / RATE_DPS))
                    qs.append(q_deg)
                streamer = PoseStreamer()
                # Prime: we are already at q0 (aligned / guarded), so
                # skip the streamer's gentle first-write ease (speed
                # 120 ≈ 10 deg/s — measured as a near-stalled first
                # 0.3 s of every run).
                streamer.last = list(q0)
                tripped = False
                seg, last_sample = 1, -1.0
                t0 = time.monotonic()
                align_s = t0 - t_run0
                t_prev = 0.0
                nticks, write_s, sample_s = 0, 0.0, 0.0
                # Carrot lookahead: command the pose ~2 ticks AHEAD of
                # the schedule. Sizing speeds to finish a step exactly
                # within one tick means any jitter makes the servo
                # arrive EARLY and park until the next write — an
                # ~18 Hz stutter (operator 08-10: "still glitchy").
                # With the target held ahead, the servo never runs out
                # of goal and moves continuously; the settle absorbs
                # the small trailing gap.
                LOOKAHEAD_S = 0.12

                def _q_at(tq: float) -> list[float]:
                    tq = min(tq, ts[-1])
                    s = seg
                    while s < len(qs) and tq > ts[s]:
                        s += 1
                    s = min(s, len(qs) - 1)
                    f = ((tq - ts[s - 1])
                         / max(ts[s] - ts[s - 1], 1e-6))
                    f = min(max(f, 0.0), 1.0)
                    return [a + (b - a) * f for a, b in
                            zip(qs[s - 1], qs[s])]

                # Adaptive tempo: the 90 deg/s base is the LOADED
                # tracking rate; unloaded the STS3215 does 270 deg/s
                # at 12 V (spec: 0.222 s/60deg no-load). Advance the
                # schedule through a rate multiplier steered by the
                # measured tracking error each feedback sweep — air
                # phases speed up toward the no-load ceiling, loaded
                # phases back off instead of piling up backlog.
                rate = 1.0
                t = 0.0
                wall_prev = t0
                while not aborted and not tripped:
                    if self._demo_abort.is_set():
                        aborted = True
                        break
                    wall = time.monotonic()
                    t += (wall - wall_prev) * rate
                    wall_prev = wall
                    while seg < len(qs) and t > ts[seg]:
                        seg += 1
                    if seg >= len(qs):
                        break
                    q = _q_at(t + LOOKAHEAD_S * rate)
                    w0 = time.monotonic()
                    # dt*0.75: cancels _speed_for_delta's 0.9
                    # undershoot AND commands ~1.2x the carrot rate so
                    # accumulated lag drains — at exactly 1.0x a lag
                    # persists forever and pins the adaptive rate.
                    streamer.write(
                        d.bus, q, live,
                        dt=min(max(wall - t0 - t_prev, 0.03), 0.25)
                        * 0.75,
                        deadband=0.3, max_speed=3000, max_acc=200)
                    write_s += time.monotonic() - w0
                    nticks += 1
                    t_prev = wall - t0
                    if wall - t0 - last_sample > 0.25:
                        # feedback sweep costs real bus time —
                        # sample sparsely, mid-motion
                        s0 = time.monotonic()
                        tracker.sample(d.bus, live)
                        sample_s += time.monotonic() - s0
                        _emit_servo_fb(
                            f"{mode} {verb} t={t:.1f}s r={rate:.1f}",
                            tracker, target=q)
                        last_sample = wall - t0
                        # lag vs the SCHEDULE pose (not the carrot,
                        # which is deliberately ahead by rate*look)
                        q_sched = _q_at(t)
                        err = max(
                            (abs(q_sched[fb["joint"]] - fb["deg"])
                             for fb in tracker.last_fb), default=0.0)
                        if err < 16.0:
                            rate = min(rate * 1.35, 2.8)
                        elif err > 28.0:
                            rate = max(rate * 0.6, 0.6)
                        with self._lock:
                            self._cal_progress = {
                                "msg": (f"{mode} {verb}: "
                                        f"{t:.1f}/{ts[-1]:.1f}s "
                                        f"x{rate:.1f} peak "
                                        f"{tracker.peak_a:.2f}A"),
                                    "keyframe": seg, "of": n}
                        tripped = stall_trip()
                    time.sleep(0.05)
                stream_s = time.monotonic() - t0
                settle_s, worst = 0.0, -1.0
                if not aborted and not tripped:
                    # settle: direct command to the final pose, then
                    # up to 3 slow corrective RE-commands. Loaded
                    # joints stop a few degrees short on the first
                    # write (foot friction / stiction), and at high
                    # tempo the feet land with more scatter — the
                    # operator sees a "weird stance". Re-commanding
                    # the same absolute target at low speed nudges
                    # each joint the rest of the way; converge to
                    # 1.2 deg, not 2.5.
                    st0 = time.monotonic()
                    _write_pose(d.bus, qs[-1], live,
                                speed=900, acc=80)
                    deadline = st0 + 1.2
                    while time.monotonic() < deadline:
                        if self._demo_abort.is_set():
                            aborted = True
                            break
                        with self.drive._lock:
                            worst, _ = (self.drive
                                        ._max_delta_vs_present(
                                            qs[-1]))
                        if worst < 2.5:
                            break
                        time.sleep(0.1)
                    with self.drive._lock:
                        worst, _ = (self.drive
                                    ._max_delta_vs_present(qs[-1]))
                    if (verb == "stand-up" and worst > 1.5
                            and not aborted
                            and not self._demo_abort.is_set()):
                        # Stiction re-plant: re-commanding the same
                        # target can't drag a LOADED foot sideways —
                        # the joint just stalls against ground
                        # friction (measured: 3 corrective passes
                        # left 2.4 deg / 2.3 A). Re-seat each foot
                        # friction-free where it belongs.
                        if not _replant(qs[-1]):
                            aborted = True
                        with self.drive._lock:
                            worst, _ = (self.drive
                                        ._max_delta_vs_present(
                                            qs[-1]))
                    if verb == "stand-up" and not aborted:
                        # Hold at FULL torque: the motion ran at
                        # τ700 for the guard, but holding a loaded
                        # stance at 700 lets knees buckle within
                        # seconds (measured 08-11: leg 5 knee +13 deg
                        # ~10 s after a clean 1.9 deg settle). The
                        # legacy glide always held at τ1000.
                        _set_torque_limit(d.bus, live, 1000)
                        _write_pose(d.bus, qs[-1], live,
                                    speed=300, acc=40)
                    tracker.sample(d.bus, live)
                    _emit_servo_fb(f"{mode} {verb} settle",
                                   tracker, target=qs[-1])
                    settle_s = time.monotonic() - st0
                    tripped = tracker.peak_a > HARD_CAP_A
                timing = (f"align {align_s:.2f}s (worst0 "
                          f"{worst0:.1f}deg) + stream "
                          f"{stream_s:.2f}s (sched {ts[-1]:.2f}s, "
                          f"{nticks} ticks, write {write_s:.2f}s, "
                          f"sample {sample_s:.2f}s) + settle "
                          f"{settle_s:.2f}s (end err "
                          f"{worst:.1f}deg) = "
                          f"{time.monotonic() - t_run0:.2f}s")
                print(f"[standup] {mode} {verb} x{speed:g}: "
                      f"{timing}, peak {tracker.peak_a:.2f}A",
                      flush=True)
                result["timing"] = timing
                if tripped:
                    result["error"] = guard_msg()
                elif aborted:
                    result["aborted"] = True
                else:
                    result["ok"] = True
                result["keyframes_done"] = min(seg, n)
                result["peak_a"] = round(tracker.peak_a, 2)
                result["peak_joint"] = tracker.peak_joint
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = result
                    self._demo_status = (
                        f"done · {mode} {verb} peak "
                        f"{tracker.peak_a:.2f} A"
                        if result["ok"] else
                        result.get("error", "aborted"))
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._demo_status = f"error: {e}"
                    self._cal_result = {"ok": False, "error": str(e),
                                        "mode": mode}
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                try:
                    _set_torque_limit(d.bus, live, 1000)
                except Exception:
                    pass
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                self._set_activity(
                    "armed" if d.armed else "limp", st or "standup done")
            return result

        if sync_gen is not None:
            # Inline run inside the caller's worker (acquisition
            # chaining). Returns the final result, not a job handle.
            res = _worker()
            if res is None:
                res = {"ok": False, "mode": mode,
                       "error": "preempted by another job"}
            return res

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "mode": mode, "speed": speed,
                "direction": direction, "keyframes": len(frames),
                "calibrate": self.calibrate_state()}

    # ------------------------------------------------------------------
    # Measurement lab (web UI "Measure" tab, 2026-08-10).
    #
    # Operator-run data collection that settles open sim-calibration
    # decisions (rl_docs/HARDWARE.md "Experiment backlog"):
    #   walk  — tape-measured distance vs commanded (slip / contact
    #           pricing; scripted gait, same caps as
    #           rl_move/scripts/tape_measure_walk.py). Also does the
    #           commanded-turn sign check (omega-only runs).
    #   hold  — planted-vs-hover per-servo holding currents (the last
    #           effort-pricing gap in the sim reward).
    #   note  — standalone operator record (e.g. tape distance for an
    #           RL walk episode; auto-attaches the newest rl_walk CSV).
    #
    # Every run samples /api/rl/feedback-shaped telemetry at ~3 Hz into
    # logs/meas_<stamp>_{servo,imu}.csv (the same CSV shapes the
    # calibration tooling reads). Runs that need a physical reading
    # leave a PENDING record; measure_annotate() merges the operator's
    # numbers and appends the finished record to logs/measurements.jsonl.
    # Fetch: scp arduino@hexapod.local:hexapod_sts/linux_control/logs/
    # {measurements.jsonl,meas_*.csv} rl_move/hardware_traces/

    MEAS_MAX_VX_MM = 60.0
    MEAS_MAX_VY_MM = 40.0
    MEAS_MAX_OMEGA = 0.5
    MEAS_MAX_WALK_S = 60.0
    MEAS_MAX_HOLD_S = 120.0
    MEAS_TILT_STOP_DEG = 30.0   # working gait rocks ±10-20°; 30 = wrong
    MEAS_POLL_S = 0.3

