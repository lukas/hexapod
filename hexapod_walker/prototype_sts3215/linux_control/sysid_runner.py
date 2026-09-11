"""On-robot sysid protocol runner: deterministic command streams + logging.

Executes a sysid protocol (see ``sysid_protocol.py``) at the protocol's
tick rate, streaming position targets exactly like the deployed RL
runner (a new absolute target every tick, fixed write speed/acc), while
recording synchronized telemetry with per-tick send/receive timestamps
so end-to-end latency DISTRIBUTIONS can be estimated offline (sysid
plan, Phases 1-2).

Safety (same posture as motor_dynamics.py — air battery rules):

- Soft torque limit for the whole run; limp immediately on any trip.
- The runner POSITIONS THE LEGS ITSELF: before the first segment it
  glides slowly (``GLIDE_RATE_DEG_S``) to the protocol's start pose
  (``home_deg`` / a leading traj's first row) — no hand-posing. The
  glide streams eased targets with every trip active — but on the
  wider ``GLIDE_CURRENT_A`` budget, since unfolding the whole body off
  the floor is not the quasi-static motion the protocol measures — and
  the run aborts if the pose does not verify within ``GLIDE_TOL_DEG``.
- ``step``/``sine`` segments move ONE joint; all others just hold the
  pose captured at segment start (successful reads only — never
  invent 0°).
- ``traj`` segments (whole-body champion replay, Phase 8) require
  ``force=True`` from the API layer; a traj after other segments must
  be continuous with the present pose (``start_tol_deg``) or the run
  trips — wrong-zero-frame / bad-protocol protection.
- Trips: per-joint current, temperature, tracking error blow-up
  (unexpected force / wrong logical zero -> limp + descriptive error),
  missing servo reads, and stale or nonadvancing runtime state samples.

Output: ``logs/sysid_<name>_<stamp>.csv`` + ``..._summary.json`` with
the full protocol embedded (raw data is never overwritten).

HTTP: ``POST /api/sysid/run`` (bench_api.sysid_run).
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Callable

from feetech_bus import HOLD_SPEED, N_JOINTS, joint_to_servo_id

try:
    from feetech_bus import AXIS_LIMITS_DEG as _BUS_LIMITS
    AXIS_LIMITS = {"yaw": tuple(_BUS_LIMITS["yaw"]),
                   "hip": tuple(_BUS_LIMITS["hip"]),
                   "knee": tuple(_BUS_LIMITS["knee"])}
except Exception:  # pragma: no cover - old bus module
    from sysid_protocol import AXIS_LIMITS_DEG as AXIS_LIMITS

from sysid_protocol import (
    DEFAULT_MAX_CURRENT_A, DEFAULT_SOFT_TORQUE, DEFAULT_WRITE_ACC,
    DEFAULT_WRITE_SPEED, axis_of, materialize, protocol_hash, start_pose,
    validate,
)

LOG_DIR = Path(__file__).resolve().parent / "logs"

MAX_TEMP_C = 55.0
# The MCU bridge occasionally corrupts a temp byte (observed 34->42/50/66,
# single-bit flips of 0x22). Real overheating persists for minutes, so a
# trip needs this many CONSECUTIVE fresh feedback polls at/over the limit
# (3 polls @ 10 Hz = 0.3 s) — a lone glitched read must never limp a run.
TEMP_TRIP_POLLS = 3
DEFAULT_CURRENT_TRIP_POLLS = 1
DEFAULT_HARD_CURRENT_A = 3.0
# Above this a reading is not a measurement — same line safe_zero.py draws
# (IMPLAUSIBLE_CURRENT_A), same failure mode: a corrupted current byte on the
# shared bus. On 2026-09-10 the L2 ground radial shear ladder died on "joint 0
# overcurrent 126.46 A" while the same poll cycle's segment snapshots read
# 0.0 / 0.013 A peak and a flat 38 C. The bus cannot deliver 126 A and the
# servo would not survive it. Not lowered to ~5 A on purpose: a REAL
# overcurrent lives between the hard cap and here (the 08-06 incident held
# about 7 A), so a tighter bound would silently disarm the guard.
IMPLAUSIBLE_CURRENT_A = 12.0
# Consecutive FRESH polls at/over ``hard_current_a`` before the hard ceiling
# latches. Was effectively 1 — and not even fresh-gated, so one glitched byte
# (cached ~3 ticks at 10 Hz) ended a 1740-tick ladder. A real jam holds, so
# confirming costs ~0.1 s of exposure; the soft limit already confirms x3 and
# the temp guard x3 (TEMP_TRIP_POLLS) for exactly this reason.
HARD_CURRENT_TRIP_POLLS = 2
# Tracking trip compares present against a reference that slews toward
# the command at the commanded profile speed — NOT the raw target: a step
# larger than the limit (e.g. the ±40 deg ladder rungs) would trip on its
# very first tick before the servo has any chance to move.
MAX_TRACK_ERR_DEG = 30.0       # active-joint |slew_ref - present| trip
MAX_MISSED_READS = 3           # consecutive bulk-read misses of a joint
FEEDBACK_HZ = 10.0             # full-feedback (current/temp) throttle
DEFAULT_START_TOL_DEG = 12.0   # traj continuity gate (mid-protocol)
GLIDE_RATE_DEG_S = 12.0        # slow start-pose glide (air)
# Soft-current floor for the glide only. A protocol's ``max_current_a`` is
# the budget for the motion it MEASURES (single-leg quasi-static work: the
# per-leg ladders carry 0.75 A). The glide is a different move: unfolding
# the whole body from wherever the last run left it down to the start pose,
# with feet on the floor carrying body weight. On 2026-09-10 the L4 ladder
# died 2.2 s into a 10 s glide from a folded ground pose — joint 14 read
# 0.73 -> 1.38 A extending the loaded knee, over the protocol's 0.75 A, and
# limped at tick -88 with 0/430 protocol ticks run. That is honest lifting
# work, not a jam. 2.0 A is the house "loaded current budget" the ground
# protocols use; ``hard_current_a`` (3.0) still trips on two
# consecutive in-range polls (HARD_CURRENT_TRIP_POLLS), as do the temp and
# MAX_TRACK_ERR_DEG guards.
GLIDE_CURRENT_A = 2.0
GLIDE_TIMEOUT_S = 45.0
GLIDE_SETTLE_S = 1.0
# Post-glide worst-joint verification. Was 3.0: on 2026-09-10 the lab
# measured 3.4-3.8 deg of gravity droop on weight-bearing hips/knees at the
# loaded stand pose, so every whole-body protocol with a loaded home pose
# died here before tick one ("joint 1 off by 3.4 deg after glide") -- the
# gate was rejecting the robot's own compliance. 8 deg clears the measured
# droop with margin and still catches the failures it exists for: a jam or
# a wrong logical zero shows up as 20-30+ deg (MAX_TRACK_ERR_DEG is 30).
# Then 8.0 -> 15.0 later the same day: a KNEE carrying body weight belly-down
# holds a much bigger residual than a hip at the stand pose (11 deg measured
# in the l4_vertical_ground_load_ladder_v1 pre-roll), and safe_zero's own
# arrival tolerance moved to GROUND_DROOP_TOL_DEG = 15 for it. A start pose
# safe_zero accepts must not then fail here one step downstream. Still under
# the 20-30 deg a real jam shows. Confirmed by the l4 re-run at 00:06 UTC
# 09-11 (430/430 ticks): its glide came down from knees at 80-93 deg and
# ARRIVED 0.8 deg short (worst joint, L5 hip) — the number this gate
# actually reads — peaking at 3.6 deg in transit, so it now passes on
# real margin, not on the widening. Keep it equal to
# safe_zero.GROUND_DROOP_TOL_DEG; move both together or not at all.
GLIDE_TOL_DEG = 15.0
DEFAULT_MIN_VOLTAGE_V = 10.8
DEFAULT_MAX_VOLTAGE_V = 13.0
DEFAULT_MAX_STATE_AGE_MS = 1500.0


def _fmt(v, nd=3):
    return "" if v is None else f"{float(v):.{nd}f}"


def _telemetry_admission(
    bus,
    *,
    expected_live_motors: int,
    healthy_motor_samples: int,
    max_state_age_ms: float,
    voltage_bounds_v: tuple[float, float],
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bool, str, dict]:
    """Require consecutive fresh full-bus samples before torque enable.

    ``read_all_feedback`` is a synchronous MCU transaction, so each completed
    call is a new sample.  Its elapsed call time bounds the age of the oldest
    data in that response.  Keeping the generated completion timestamps and
    requiring them to advance makes that freshness contract explicit and easy
    to fault-inject in offline tests.
    """

    min_voltage_v, max_voltage_v = voltage_bounds_v
    if (healthy_motor_samples < 1 or expected_live_motors < 1
            or max_state_age_ms <= 0.0 or min_voltage_v > max_voltage_v):
        return False, "invalid telemetry admission requirements", {}
    expected_joints = set(range(expected_live_motors))
    completed_at: list[float] = []
    observed_voltages: list[float] = []
    for sample_index in range(healthy_motor_samples):
        started = clock()
        try:
            feedback = bus.read_all_feedback()
        except Exception as error:
            return False, f"telemetry sample {sample_index + 1} failed: {error}", {}
        completed = clock()
        state_age_ms = max(0.0, completed - started) * 1000.0
        if not isinstance(feedback, dict) or set(feedback) != expected_joints:
            count = len(feedback) if isinstance(feedback, dict) else 0
            return False, (
                f"telemetry sample {sample_index + 1} incomplete: "
                f"{count}/{expected_live_motors} servos"
            ), {}
        if state_age_ms > max_state_age_ms:
            return False, (
                f"telemetry sample {sample_index + 1} stale: "
                f"{state_age_ms:.1f} ms > {max_state_age_ms:.1f} ms"
            ), {}
        if completed_at and completed <= completed_at[-1]:
            return False, "telemetry sample timestamps did not advance", {}
        voltages = []
        for joint, record in feedback.items():
            try:
                voltage = float(record["volt"])
            except (KeyError, TypeError, ValueError):
                return False, f"telemetry sample missing voltage for joint {joint}", {}
            if not min_voltage_v <= voltage <= max_voltage_v:
                return False, (
                    f"telemetry voltage out of bounds for joint {joint}: "
                    f"{voltage:.2f} V not in "
                    f"[{min_voltage_v:.2f}, {max_voltage_v:.2f}] V"
                ), {}
            voltages.append(voltage)
        observed_voltages.extend(voltages)
        completed_at.append(completed)
        if sample_index + 1 < healthy_motor_samples:
            sleep(0.05)
    return True, "ok", {
        "samples": len(completed_at),
        "servos_per_sample": expected_live_motors,
        "min_voltage_v": min(observed_voltages),
        "max_voltage_v": max(observed_voltages),
        "max_state_age_ms": max_state_age_ms,
        "sample_timestamps": completed_at,
    }


def run_sysid_protocol(
    bus,
    protocol: dict,
    *,
    force: bool = False,
    abort_check: Callable[[], bool] | None = None,
    on_progress: Callable[[dict], None] | None = None,
    log_dir: Path | None = None,
    expected_live_motors: int = N_JOINTS,
    healthy_motor_samples: int = 3,
    max_state_age_ms: float = DEFAULT_MAX_STATE_AGE_MS,
    voltage_bounds_v: tuple[float, float] = (
        DEFAULT_MIN_VOLTAGE_V, DEFAULT_MAX_VOLTAGE_V),
    runtime_state_clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Execute a sysid protocol. Returns a result/summary dict."""
    abort_check = abort_check or (lambda: False)
    errs = validate(protocol)
    if errs:
        return {"ok": False, "mode": "sysid",
                "error": "invalid protocol: " + "; ".join(errs)}
    has_traj = any(s.get("kind") in ("traj", "rel_traj")
                   for s in protocol.get("segments", []))
    if has_traj and not force:
        return {"ok": False, "mode": "sysid",
                "error": "traj (whole-body) segments require force=true "
                         "and live camera/guarded-runner supervision"}

    try:
        from inplace_demos import (
            _enable_torque, _live_robot_ids, _limp_all,
            _set_torque_limit, _write_pose,
        )
    except ImportError as e:
        return {"ok": False, "mode": "sysid",
                "error": f"inplace_demos missing: {e}"}

    mat = materialize(protocol)
    hz = mat["hz"]
    dt = 1.0 / hz
    ticks = mat["ticks"]
    name = str(protocol.get("name", "unnamed"))
    phash = protocol_hash(protocol)
    write_speed = int(protocol.get("write_speed", DEFAULT_WRITE_SPEED))
    write_acc = int(protocol.get("write_acc", DEFAULT_WRITE_ACC))
    soft_torque = int(max(200, min(800, protocol.get(
        "soft_torque", DEFAULT_SOFT_TORQUE))))
    max_cur = float(protocol.get("max_current_a", DEFAULT_MAX_CURRENT_A))
    current_trip_polls = max(1, int(protocol.get(
        "current_trip_polls", DEFAULT_CURRENT_TRIP_POLLS)))
    hard_current_a = max(max_cur, float(protocol.get(
        "hard_current_a", DEFAULT_HARD_CURRENT_A)))

    def _progress(msg: str, **extra):
        if on_progress:
            try:
                on_progress({"msg": msg, "mode": "sysid", **extra})
            except Exception:
                pass

    live_ids = _live_robot_ids(bus)
    live_joints = sorted(j for j in range(N_JOINTS)
                         if joint_to_servo_id(j) in live_ids)
    needed = sorted({j for t in ticks for j in t["active"]})
    missing = [j for j in needed if j not in live_joints]
    if missing:
        return {"ok": False, "mode": "sysid",
                "error": f"protocol needs dead joints {missing} "
                         f"(live: {live_joints})"}

    telemetry_ok, telemetry_error, telemetry_admission = _telemetry_admission(
        bus,
        expected_live_motors=expected_live_motors,
        healthy_motor_samples=healthy_motor_samples,
        max_state_age_ms=max_state_age_ms,
        voltage_bounds_v=voltage_bounds_v,
    )
    if not telemetry_ok:
        return {"ok": False, "mode": "sysid",
                "error": "telemetry admission failed: " + telemetry_error}

    log_dir = Path(log_dir) if log_dir else LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = log_dir / f"sysid_{name}_{stamp}.csv"
    sum_path = log_dir / f"sysid_{name}_{stamp}_summary.json"

    def _read_pose() -> tuple[dict[int, float], list[int]]:
        pos = bus.read_all_positions()
        if not isinstance(pos, dict):
            pos = {}
        return pos, [j for j in live_joints if j not in pos]

    runtime_state_completed_at: float | None = None

    def _read_runtime_pose() -> tuple[dict[int, float], list[int], str | None]:
        """Read one runtime state sample and enforce age/advancement.

        The synchronous bus transaction is the sysid executor's state stream.
        Its completion timestamp must advance and the transaction must finish
        inside the same state-age bound used at admission.  This check is made
        before the first streamed target and after every later target, so a
        stalled stream cannot permit another command tick.
        """

        nonlocal runtime_state_completed_at
        started = runtime_state_clock()
        pose, missing = _read_pose()
        completed = runtime_state_clock()
        age_ms = max(0.0, completed - started) * 1000.0
        if age_ms > max_state_age_ms:
            return pose, missing, (
                f"runtime state stream stale: {age_ms:.1f} ms > "
                f"{max_state_age_ms:.1f} ms"
            )
        if (runtime_state_completed_at is not None
                and completed <= runtime_state_completed_at):
            return pose, missing, "runtime state timestamp did not advance"
        runtime_state_completed_at = completed
        return pose, missing, None

    def _read_pose_debounced(
            attempts: int = MAX_MISSED_READS) -> tuple[dict[int, float], list[int]]:
        """Merge fresh pre-command reads so one dropped ID never trips."""
        merged: dict[int, float] = {}
        missing = list(live_joints)
        for attempt in range(attempts):
            sampled, _ = _read_pose()
            merged.update(sampled)
            missing = [j for j in live_joints if j not in merged]
            if not missing:
                break
            if attempt + 1 < attempts:
                time.sleep(0.1)
        return merged, missing

    pose0, miss0 = _read_pose_debounced()
    if miss0:
        return {"ok": False, "mode": "sysid",
                "error": f"servo IDs not answering: joints {miss0}"}
    # Start pose the runner will glide to by itself (no hand-posing):
    # protocol home_deg, or a leading traj's first row.
    glide_target = start_pose(protocol)

    _progress(f"sysid '{name}' ({phash}): {len(ticks)} ticks @ {hz:g} Hz, "
              f"soft torque {soft_torque}; telemetry admission "
              f"{telemetry_admission['samples']}x"
              f"{telemetry_admission['servos_per_sample']} passed")
    _set_torque_limit(bus, live_ids, soft_torque)
    _enable_torque(bus, live_ids)

    # Hold pose from successful reads only (motor_dynamics pattern).
    base_pose = [0.0] * N_JOINTS
    hold_ids: set[int] = set()
    for j, d in pose0.items():
        base_pose[j] = float(d)
        hold_ids.add(joint_to_servo_id(j))
    if hold_ids:
        _write_pose(bus, base_pose, hold_ids, speed=HOLD_SPEED, acc=25)
    time.sleep(0.3)

    def _bail(error: str, extra: dict | None = None) -> dict:
        try:
            _set_torque_limit(bus, live_ids, 1000)
        except Exception:
            pass
        try:
            _limp_all(bus, live_ids)
        except Exception:
            pass
        res = {"ok": False, "mode": "sysid", "error": error,
               "csv": str(csv_path), **(extra or {})}
        _progress(f"TRIP: {error}")
        return res

    def _write_active(tick: dict, cmd_abs: list[float]) -> None:
        if len(tick["active"]) == 1 and hasattr(bus, "write_joint"):
            j = tick["active"][0]
            bus.write_joint(j, cmd_abs[j], speed=write_speed, acc=write_acc)
        else:
            bus.write_all(cmd_abs, speed=write_speed, acc=write_acc)

    seg_home: dict[int, list[float]] = {}
    seg_stats: list[dict] = []
    cur_seg = -1
    t_run0: float | None = None
    overruns = 0
    clamped = 0
    missed: dict[int, int] = {j: 0 for j in live_joints}
    overcurrent_polls: dict[int, int] = {j: 0 for j in live_joints}
    hard_current_polls: dict[int, int] = {j: 0 for j in live_joints}
    wild_current_reads = 0   # implausible decodes discarded, for the report
    tripped_error: str | None = None
    aborted = False
    last_fb: dict[int, dict] = {}
    last_fb_t = -1e9
    hot_polls: dict[int, int] = {}   # consecutive fresh polls >= MAX_TEMP_C
    last_pose = dict(pose0)
    # Slew-limited tracking-trip reference (deg per tick at the commanded
    # Feetech profile speed; 400 counts/s ~= 35 deg/s).
    trip_ref: dict[int, float] = {}
    trip_slew_deg = write_speed * (360.0 / 4096.0) * dt

    fields = (["t_s", "tick", "seg", "phase", "joint",
               "t_send_s", "t_recv_s", "overrun"]
              + [f"q{j}_deg" for j in range(N_JOINTS)]
              + [f"cmd{j}_deg" for j in range(N_JOINTS)]
              + ["cur_a", "load_pct", "volt", "temp_c"]
              # Full per-joint currents from the throttled 10 Hz bus poll
              # (values repeat between polls): the loaded/contact phases
              # need every servo's draw, not one summary sample.
              + [f"cur{j}_a" for j in range(N_JOINTS)])

    t0 = time.monotonic()
    started_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(fields)

        def _log_row(k: int, seg: int, phase: str, act_j: int,
                     t_send: float, t_recv: float, overrun: int,
                     cmd_abs: list[float], fb_row: tuple) -> None:
            w.writerow(
                [f"{t_send:.4f}", k, seg, phase, act_j,
                 f"{t_send:.4f}", f"{t_recv:.4f}", overrun]
                + [_fmt(last_pose.get(j), 3) for j in range(N_JOINTS)]
                + [f"{c:.3f}" for c in cmd_abs]
                + [_fmt(fb_row[0]), _fmt(fb_row[1], 1),
                   _fmt(fb_row[2], 2), _fmt(fb_row[3], 1)]
                + [_fmt(abs(float(last_fb[j].get("current_a") or 0.0)))
                   if j in last_fb else ""
                   for j in range(N_JOINTS)])

        def _trip_feedback(active: list[int], soft_a: float | None = None
                           ) -> tuple:
            """Throttled current/temp trips; returns the fb CSV cells.

            ``soft_a`` overrides the protocol's soft current budget for
            callers whose motion is not the measured one (the glide).
            """
            soft_cur = max_cur if soft_a is None else soft_a
            nonlocal last_fb, last_fb_t, tripped_error, wild_current_reads
            t_now = time.monotonic()
            fresh = False
            if t_now - last_fb_t >= 1.0 / FEEDBACK_HZ:
                try:
                    fb = bus.read_all_feedback()
                    if isinstance(fb, dict) and fb:
                        last_fb = fb
                        last_fb_t = t_now
                        fresh = True
                except Exception:
                    pass
            # CSV feedback cells follow the HIGHEST-current joint of the
            # active set (multi-joint traj mode used to log whichever
            # joint came last — useless for diagnosing an overcurrent).
            fb_row = (None, None, None, None)
            fb_row_cur = -1.0
            for j in active:
                rec = last_fb.get(j)
                if not rec:
                    continue
                cur_a = abs(float(rec.get("current_a") or 0.0))
                temp = float(rec.get("temp_c") or 0.0)
                if cur_a > IMPLAUSIBLE_CURRENT_A:
                    # Not a measurement — a corrupted byte. It gets no vote:
                    # no trip, no peak_current_a, and it neither advances nor
                    # RESETS a counter (a glitch landing inside a real
                    # overcurrent must not erase the evidence either way).
                    if fresh:
                        wild_current_reads += 1
                        _progress(f"joint {j} read {cur_a:.1f} A — "
                                  f"implausible above "
                                  f"{IMPLAUSIBLE_CURRENT_A:.0f} A, discarded "
                                  f"(suspect the bus, not the joint); "
                                  f"{wild_current_reads} so far")
                    continue
                if seg_stats:
                    seg_stats[-1]["peak_current_a"] = max(
                        seg_stats[-1]["peak_current_a"], cur_a)
                if fresh and cur_a > soft_cur:
                    overcurrent_polls[j] = overcurrent_polls.get(j, 0) + 1
                elif fresh:
                    overcurrent_polls[j] = 0
                if fresh:
                    # Only FRESH polls advance the hard counter: last_fb is
                    # cached for ~3 ticks between 10 Hz polls, so counting
                    # ticks would let one bad byte satisfy "consecutive".
                    if cur_a >= hard_current_a:
                        hard_current_polls[j] = (
                            hard_current_polls.get(j, 0) + 1)
                    else:
                        hard_current_polls[j] = 0
                if hard_current_polls.get(j, 0) >= HARD_CURRENT_TRIP_POLLS:
                    tripped_error = (f"joint {j} overcurrent {cur_a:.2f} A "
                                     f"(hard limit {hard_current_a:.2f}, "
                                     f"{hard_current_polls[j]} consecutive "
                                     f"polls) — "
                                     f"possible jam or wrong logical zero; "
                                     f"limped")
                elif overcurrent_polls.get(j, 0) >= current_trip_polls:
                    tripped_error = (f"joint {j} overcurrent {cur_a:.2f} A "
                                     f"(limit {soft_cur:.2f}, "
                                     f"{overcurrent_polls[j]} consecutive "
                                     f"polls) — possible "
                                     f"jam or wrong logical zero; limped")
                elif temp >= MAX_TEMP_C:
                    # Debounced: only fresh polls advance the counter, so a
                    # single corrupted byte (cached for ~3 ticks) can't trip.
                    if fresh:
                        hot_polls[j] = hot_polls.get(j, 0) + 1
                    if hot_polls.get(j, 0) >= TEMP_TRIP_POLLS:
                        tripped_error = (f"joint {j} hot {temp:.0f} C "
                                         f"({hot_polls[j]} consecutive "
                                         f"polls); limped")
                elif fresh:
                    hot_polls[j] = 0
                if cur_a > fb_row_cur:
                    fb_row_cur = cur_a
                    fb_row = (cur_a, float(rec.get("load_pct") or 0.0),
                              float(rec.get("volt") or 0.0), temp)
            return fb_row

        # Establish the runtime stream before issuing the first streamed
        # target.  Admission alone does not prove that state will continue to
        # advance after torque enable.
        runtime_pose, runtime_missing, runtime_error = _read_runtime_pose()
        if runtime_error:
            tripped_error = runtime_error
        elif runtime_missing:
            tripped_error = (
                f"runtime state stream incomplete: joints {runtime_missing}"
            )
        else:
            last_pose.update(runtime_pose)

        # -- automatic start-pose glide (no operator hand-posing) --------
        if glide_target is not None and tripped_error is None:
            start = [pose0.get(j, 0.0) for j in range(N_JOINTS)]
            target = list(glide_target)
            for j in range(N_JOINTS):
                lo, hi = AXIS_LIMITS[axis_of(j)]
                target[j] = min(hi, max(lo, target[j]))
            travel = max(abs(target[j] - start[j])
                         for j in range(N_JOINTS))
            if travel > GLIDE_TOL_DEG:
                dur = min(GLIDE_TIMEOUT_S,
                          max(0.5, travel / GLIDE_RATE_DEG_S))
                n_glide = int(round((dur + GLIDE_SETTLE_S) * hz))
                _progress(f"glide to start pose: worst joint "
                          f"{travel:.0f} deg over {dur:.1f} s")
                tg0 = time.monotonic()
                for k in range(n_glide):
                    if abort_check():
                        aborted = True
                        break
                    t_sched = tg0 + k * dt
                    now = time.monotonic()
                    if now < t_sched:
                        time.sleep(t_sched - now)
                    frac = min(1.0, (k / hz) / dur)
                    ease = frac * frac * (3.0 - 2.0 * frac)
                    cmd_abs = [start[j] + (target[j] - start[j]) * ease
                               for j in range(N_JOINTS)]
                    t_send = time.monotonic() - t0
                    try:
                        bus.write_all(cmd_abs, speed=write_speed,
                                      acc=write_acc)
                    except Exception as e:
                        tripped_error = f"bus write failed (glide): {e}"
                        break
                    pose, _miss, runtime_error = _read_runtime_pose()
                    t_recv = time.monotonic() - t0
                    if runtime_error:
                        tripped_error = runtime_error
                        break
                    last_pose.update(pose)
                    fb_row = _trip_feedback(
                        list(range(N_JOINTS)),
                        soft_a=max(max_cur, GLIDE_CURRENT_A))
                    if tripped_error:
                        break
                    for j in range(N_JOINTS):
                        if (j in pose and abs(cmd_abs[j] - pose[j])
                                > MAX_TRACK_ERR_DEG):
                            tripped_error = (
                                f"joint {j} fell {abs(cmd_abs[j] - pose[j]):.0f}"
                                f" deg behind during the start-pose glide "
                                f"— mechanical jam or wrong logical zero; "
                                f"limped. Re-check set_zero.")
                            break
                    if tripped_error:
                        break
                    _log_row(-n_glide + k, -1, "glide", -1, t_send,
                             t_recv, 0, cmd_abs, fb_row)
                # Polls counted against the wider glide budget must not
                # carry into segment 0's tighter one.
                for j in list(overcurrent_polls):
                    overcurrent_polls[j] = 0
                # Verify the pose actually arrived before any segment runs.
                if tripped_error is None and not aborted:
                    pose, miss = _read_pose_debounced()
                    if miss:
                        tripped_error = (f"joints {miss} not answering "
                                         f"after glide")
                    else:
                        worst_j = max(range(N_JOINTS), key=lambda j: abs(
                            pose.get(j, 0.0) - target[j]))
                        worst = abs(pose.get(worst_j, 0.0) - target[worst_j])
                        if worst > GLIDE_TOL_DEG:
                            tripped_error = (
                                f"start pose did not verify: joint "
                                f"{worst_j} off by {worst:.1f} deg after "
                                f"glide (tol {GLIDE_TOL_DEG:g}) — check "
                                f"for obstruction / wrong logical zero.")

        for k, tick in enumerate(ticks):
            if tripped_error or aborted:
                break
            if abort_check():
                aborted = True
                break
            # -- fixed-rate schedule (rl_policy pattern), anchored AFTER
            # the glide so its duration doesn't count as overrun ----------
            if t_run0 is None:
                t_run0 = time.monotonic()
            t_sched = t_run0 + k * dt
            now = time.monotonic()
            if now < t_sched:
                time.sleep(t_sched - now)
            elif now - t_sched > 0.5 * dt:
                overruns += 1

            # -- segment bookkeeping / home capture -----------------------
            if tick["seg"] != cur_seg:
                cur_seg = tick["seg"]
                pose, miss, runtime_error = _read_runtime_pose()
                if runtime_error:
                    tripped_error = runtime_error
                    break
                if miss:
                    tripped_error = (f"seg {cur_seg}: joints {miss} not "
                                     f"answering at segment start")
                    break
                spec = protocol["segments"][cur_seg]
                if spec.get("kind") == "traj" and cur_seg > 0:
                    # Mid-protocol traj must be continuous with the pose
                    # the previous segments left behind.
                    tol = float(spec.get("start_tol_deg",
                                         DEFAULT_START_TOL_DEG))
                    row0 = spec["q_deg"][0]
                    worst_j = max(range(N_JOINTS), key=lambda j: abs(
                        pose.get(j, 0.0) - row0[j]))
                    worst = abs(pose.get(worst_j, 0.0) - row0[worst_j])
                    if worst > tol:
                        tripped_error = (
                            f"traj seg {cur_seg}: present pose off by "
                            f"{worst:.1f} deg at joint {worst_j} (tol "
                            f"{tol:.0f}) — protocol discontinuity; limped")
                        break
                seg_home[cur_seg] = [pose.get(j, 0.0)
                                     for j in range(N_JOINTS)]
                seg_stats.append({"seg": cur_seg,
                                  "label": mat["seg_labels"][cur_seg],
                                  "ticks": 0, "peak_current_a": 0.0})
                _progress(f"seg {cur_seg + 1}/{len(mat['seg_labels'])}: "
                          f"{mat['seg_labels'][cur_seg]}",
                          seg=cur_seg, tick=k, total=len(ticks))
                last_pose.update(pose)
                trip_ref = dict(pose)   # re-anchor trip ref at the segment

            # -- build absolute command -----------------------------------
            home = seg_home[cur_seg]
            cmd_abs = list(home)
            for j in tick["active"]:
                v = (tick["cmd"][j] if tick["mode"] == "abs"
                     else home[j] + tick["cmd"][j])
                lo, hi = AXIS_LIMITS[axis_of(j)]
                cv = min(hi, max(lo, v))
                if cv != v:
                    clamped += 1
                cmd_abs[j] = cv

            # -- send, then read -------------------------------------------
            t_send = time.monotonic() - t0
            try:
                _write_active(tick, cmd_abs)
            except Exception as e:
                tripped_error = f"bus write failed: {e}"
                break
            pose, miss, runtime_error = _read_runtime_pose()
            t_recv = time.monotonic() - t0
            if runtime_error:
                tripped_error = runtime_error
                break
            for j in live_joints:
                if j in miss:
                    missed[j] += 1
                    if missed[j] >= MAX_MISSED_READS:
                        tripped_error = (f"joint {j} (ID "
                                         f"{joint_to_servo_id(j)}) missed "
                                         f"{missed[j]} consecutive reads")
                        break
                else:
                    missed[j] = 0
            if tripped_error:
                break
            last_pose.update(pose)

            # -- throttled full feedback (current/temp) --------------------
            act_j = tick["active"][0] if len(tick["active"]) == 1 else -1
            fb_row = _trip_feedback(tick["active"])
            if tripped_error:
                break

            # -- tracking blow-up trip (unexpected force / wrong zero) -----
            # Reference slews toward cmd at the profile speed so large
            # steps don't self-trip; a stalled servo still trips within
            # ~MAX_TRACK_ERR_DEG / profile-speed seconds.
            for j in tick["active"]:
                ref = trip_ref.get(j, pose.get(j, cmd_abs[j]))
                d = cmd_abs[j] - ref
                ref += max(-trip_slew_deg, min(trip_slew_deg, d))
                trip_ref[j] = ref
                if j in pose and abs(ref - pose[j]) > MAX_TRACK_ERR_DEG:
                    tripped_error = (
                        f"joint {j} tracking error "
                        f"{abs(ref - pose[j]):.0f} deg > "
                        f"{MAX_TRACK_ERR_DEG:.0f} (cmd {cmd_abs[j]:.1f}, "
                        f"ref {ref:.1f}, present {pose[j]:.1f}) — "
                        f"mechanical jam or wrong logical zero; limped. "
                        f"Re-check set_zero.")
                    break
            if tripped_error:
                break

            seg_stats[-1]["ticks"] += 1
            _log_row(k, cur_seg, tick["phase"], act_j, t_send, t_recv,
                     1 if now - t_sched > 0.5 * dt else 0, cmd_abs, fb_row)
            if (k + 1) % int(hz) == 0:
                fh.flush()

    # Always limp at the end — never leave torque on a sysid pose.
    try:
        _set_torque_limit(bus, live_ids, 1000)
    except Exception:
        pass
    try:
        _limp_all(bus, live_ids)
    except Exception:
        pass

    done = sum(s["ticks"] for s in seg_stats)
    result = {
        "ok": tripped_error is None and not aborted,
        "mode": "sysid",
        "name": name,
        "protocol_hash": phash,
        "hz": hz,
        "ticks_planned": len(ticks),
        "ticks_done": done,
        "overruns": overruns,
        "clamped_cmds": clamped,
        "wild_current_reads": wild_current_reads,
        "aborted": aborted,
        "error": tripped_error,
        "csv": str(csv_path),
        "segments": seg_stats,
        "started": started_iso,
        "ended": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    sum_path.write_text(json.dumps(
        {**result, "protocol": protocol}, indent=1))
    result["summary_json"] = str(sum_path)
    _progress("aborted" if aborted else
              (f"TRIP: {tripped_error}" if tripped_error else
               f"done · {done}/{len(ticks)} ticks · limp"))
    return result
