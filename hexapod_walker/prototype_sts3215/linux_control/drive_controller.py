"""STS3215 drive loop: web/xbox command lines → TripodGait → FeetechBus.

Runs on the Uno Q Linux side. Prefer the MCU UART bridge (FE-URT on D0/D1);
fall back to a USB URT-2 if present.  Command language mirrors the v1
firmware enough that the web UI can stay familiar:

  ARM / X              arm torque / emergency limp
  P                    stand / park (planted stance)
  C                    centre all joints to 0°
  J vx vy omega [gait] live drive (vx,vy in mm/s; omega rad/s)
  K <lift_mm>          swing foot lift
  GTUNE key=value ...  tune GAIT 0 high-step tripod while stopped. Keys:
                       period, lift, stride, ramp, vx, vy, omega.
  GAIT <id> [alpha]    pick the walk gait: 0 = tripod (body-frame drag,
                       legacy), 1 = no-slip world-pinned tripod
                       (noslip_gait), 2 = no-slip RIPPLE (opposite
                       pairs, 4 feet down), 3 = no-slip WAVE (one leg
                       at a time, 5 feet down — steadiest, slowest),
                       4 = SE2 TETRAPOD (se2_foot_gait: per-leg
                       workspaces, Bézier swings, command auto-scaled
                       to reach), 5 = SE2 WAVE (same engine, one leg
                       at a time), 6 = SE2 CPG (same engine, loaded
                       parameters from a `cpg_controller_*.json`
                       search-track artifact — refused until CPGLOAD
                       picks one), 7 = no-slip CLAMP-FIT tripod
                       (smoothest measured timing under the servo clamp),
                       8 = middle-tuck quad crawl (middle legs up,
                       front/rear legs crawl), 9 = fluid no-slip tripod
                       (continuous body, near-zero shift/dwell), 10 = faster
                       fluid no-slip tripod with lower foot lift;
                       alpha 0..1 = body-motion overlap
                       for gait 1 (0 = step-then-shift, 1 =
                       continuous; ripple/wave/SE2/CPG run their
                       presets and ignore it). Swaps are refused while
                       walking — send J 0 0 0 first; alpha alone
                       retunes the live no-slip tripod at the next
                       phase boundary.
  CPGLIST              list available `cpg_controller_*.json` artifacts
                       (cpg track exports, `linux_control/policies` and
                       `rl_move/sim/policies`).
  CPGLOAD <name>       load one artifact's gait/period/swing_frac/lift/
                       cmd_tau/workspace_margin (does not swap gaits by
                       itself — send GAIT 6 after loading).
  # <j> <deg>          set one joint
  Q <j> <amp>          wiggle one joint
  HOLD                 freeze at present pose
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor"
MOTOR_SETUP = HERE.parent / "motor_setup"
ROOT = HERE.parent

# Prefer vendored SDK (offline Uno Q), then canonical motor_setup, then
# linux_control itself. reversed(): each insert(0) puts the LAST-inserted
# first, so iterate the priority list back-to-front. (The urt2_setup
# bundle entries were retired 2026-08-29 — that duplicate tree is gone,
# so there is exactly one copy of every module and nothing to shadow.)
for p in reversed((str(VENDOR), str(MOTOR_SETUP), str(HERE), str(ROOT))):
    if Path(p).is_dir() and p not in sys.path:
        sys.path.insert(0, p)

from feetech_bus import (  # noqa: E402
    ADDR_TORQUE_ENABLE, BAUD_DEFAULT, N_JOINTS, WALK_ACC,
    WALK_SPEED, deg_to_count, joint_to_servo_id, normalize_acc,
    normalize_speed, standing_pose_degrees,
)
from cpg_controller_loader import (  # noqa: E402
    list_cpg_controllers as _list_cpg_controllers,
    load_cpg_controller as _load_cpg_controller,
)
from mcu_feetech_bus import open_feetech_bus  # noqa: E402
from hexapod_core.noslip_gait import NoSlipGait  # noqa: E402
from hexapod_core.scripted_walk_contract import (  # noqa: E402
    SCRIPTED_WALK_ACC_UNITS,
    SCRIPTED_WALK_CONTROL_HZ,
    SCRIPTED_WALK_DT_S,
    SCRIPTED_WALK_SPEED_COUNTS_S,
)
from hexapod_core.se2_foot_gait import SE2FootGait  # noqa: E402
from hexapod_core.tripod_gait import TripodGait  # noqa: E402
from hexapod_core.demo_tripod import (  # noqa: E402
    DEFAULT_DEMO_TRIPOD, DemoTripodPreset, format_demo_tripod,
    parse_demo_tripod_tune_tokens, tune_demo_tripod,
)
from hexapod_core.middle_tuck_quad_gait import MiddleTuckQuadGait  # noqa: E402

try:
    from rl_walk_start import (  # noqa: E402
        SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG,
        walk_start_pose_degrees,
    )
except Exception:  # pragma: no cover - deploy bundle always ships it
    SIM_WALK_START_HIP_DEG = 20.0
    SIM_WALK_START_KNEE_DEG = 80.0

    def walk_start_pose_degrees() -> list[float]:
        return [0.0, SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG] * 6

# Scripted gait and MuJoCo share this 100 Hz contract.  The MCU stream bridge
# reduced a full SyncWrite to ~1-2 ms, leaving margin inside the 10 ms budget.
DT = SCRIPTED_WALK_DT_S
LIVE_SCAN_PERIOD_S = 2.0
WALK_START_TOL_DEG = 30.0
DEMO_TRIPOD_PERIOD_S = DEFAULT_DEMO_TRIPOD.period_s
DEMO_TRIPOD_LIFT_M = DEFAULT_DEMO_TRIPOD.lift_m
DEMO_TRIPOD_RAMP_S = DEFAULT_DEMO_TRIPOD.ramp_s
DEMO_TRIPOD_STRIDE_SCALE = DEFAULT_DEMO_TRIPOD.stride_scale
DEMO_TRIPOD_MAX_VX_MPS = DEFAULT_DEMO_TRIPOD.max_vx_mps
DEMO_TRIPOD_MAX_VY_MPS = DEFAULT_DEMO_TRIPOD.max_vy_mps
DEMO_TRIPOD_MAX_OMEGA_RAD_S = DEFAULT_DEMO_TRIPOD.max_omega_rad_s
# Refuse absolute centre/stand SyncWrites that yank any live joint farther
# than this from its *present* angle (2026-08-06 cooked-motor incident).
# Keep a broad emergency delta guard for direct one-shot moves. Normal web
# Stand uses the acquisition route; direct /cmd P now targets the tall
# walk-ready pose and still refuses if that would yank too far.
MAX_SAFE_DELTA_DEG = 90.0


def _advance_periodic_deadline(deadline: float, now: float,
                               period: float = DT) -> tuple[float, int]:
    """Advance a fixed-rate deadline without accumulating work-time drift."""
    deadline += period
    skipped = 0
    if deadline <= now:
        skipped = int((now - deadline) // period) + 1
        deadline += skipped * period
    return deadline, skipped


class DriveController:
    def __init__(self, port: str | None = None, *, baud: int = BAUD_DEFAULT,
                 dry_run: bool = False):
        self.port = port
        self.baud = baud
        self.dry_run = dry_run
        self.bus = None  # FeetechBus | McuFeetechBus
        self._demo_tripod: DemoTripodPreset = DEFAULT_DEMO_TRIPOD
        self.gait = self._new_demo_tripod_gait()
        self.armed = False
        self.mode = "idle"  # idle | stand | walk
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop_overruns = 0
        self._vx = self._vy = self._omega = 0.0
        self._gait_id = 0            # 0 = tripod (drag), 1 = no-slip
        self._noslip_alpha = 0.0     # body-motion overlap (no-slip only)
        self._lift_mm: float | None = None   # last K value, re-applied on swap
        self._cpg_loaded: dict | None = None  # last CPGLOAD result (gait 6)
        self._last_pose = walk_start_pose_degrees()
        self.status = "init"
        self._live_ids_cache: set[int] = set()
        self._live_ids_t = 0.0
        # Set by web_drive after construction (optional bench JSON API).
        self.bench = None
        self._sync_gait_walk_stance()

    def _new_demo_tripod_gait(self) -> TripodGait:
        """Hardware-show preset for the legacy body-frame tripod.

        Gait 0 deliberately remains the simple legacy gait, but the old
        0.75 s / 25 mm swing asked too much of grippy boots on the shop
        floor: the feet skimmed, then jammed. This instance-local preset
        leaves sim/training ``TripodGait()`` defaults untouched.
        """
        return TripodGait(**self._demo_tripod.tripod_kwargs())

    def start(self) -> None:
        if not self.dry_run:
            self.bus, port = open_feetech_bus(self.port, baud=self.baud)
            self.port = port
            # Boot limp — nothing moves until ARM.
            self._torque_all(False)
            self.status = f"bus:{port} disarmed"
        else:
            self.status = "dry-run (no bus)"
            print("[drive] dry-run — no bus opened")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        try:
            if self.bus and self.armed:
                self._torque_all(False)
        except Exception:
            pass
        if self.bus:
            try:
                self.bus.close()
            except Exception:
                pass

    # -- bus helpers ---------------------------------------------------------
    def _live_ids(self, *, force: bool = False,
                  allow_stale: bool = False) -> set[int]:
        if not self.bus:
            return set()
        now = time.monotonic()
        if (not force and self._live_ids_cache
                and (allow_stale
                     or now - self._live_ids_t < LIVE_SCAN_PERIOD_S)):
            return self._live_ids_cache
        try:
            self._live_ids_cache = {sid for sid in self.bus.scan(range(2, 20))}
            self._live_ids_t = now
        except Exception:
            pass
        return self._live_ids_cache

    def _torque_all(self, on: bool) -> None:
        if not self.bus:
            return
        if hasattr(self.bus, "enable_all_torque"):
            try:
                self.bus.enable_all_torque(on)
                return
            except Exception:
                pass
        for sid in sorted(self._live_ids(force=True) or
                          {joint_to_servo_id(j) for j in range(N_JOINTS)}):
            try:
                self.bus.pkt.write1ByteTxRx(
                    sid, ADDR_TORQUE_ENABLE, 1 if on else 0)
            except Exception:
                pass

    def _read_present_pose(self) -> list[float | None]:
        if not self.bus:
            return [None] * N_JOINTS
        # One bulk sync-read transaction when the bus supports it — 18
        # individual request/response reads can cost more than a whole
        # control period on the legacy path.
        bulk = getattr(self.bus, "read_all_positions", None)
        if bulk is not None:
            try:
                pos = bulk()
                if isinstance(pos, dict) and pos:
                    return [pos.get(j) for j in range(N_JOINTS)]
            except Exception:
                pass
        out: list[float | None] = []
        for j in range(N_JOINTS):
            try:
                out.append(self.bus.read_position_deg(j))
            except Exception:
                out.append(None)
        return out

    def _max_delta_vs_present(self, goal: list[float]
                              ) -> tuple[float, int | None]:
        """Largest |goal − present| on live joints that have a reading."""
        present = self._read_present_pose()
        live = self._live_ids()
        worst = 0.0
        worst_j: int | None = None
        for j, g in enumerate(goal):
            sid = joint_to_servo_id(j)
            if live and sid not in live:
                continue
            p = present[j] if j < len(present) else None
            if p is None:
                continue
            d = abs(float(g) - float(p))
            if d > worst:
                worst = d
                worst_j = j
        return worst, worst_j

    def _refuse_large_delta(self, goal: list[float], *,
                            force: bool, label: str) -> str | None:
        if force:
            return None
        worst, j = self._max_delta_vs_present(goal)
        if worst <= MAX_SAFE_DELTA_DEG:
            return None
        self.status = (
            f"refused {label}: max Δq={worst:.0f}° on j{j} "
            f"(>{MAX_SAFE_DELTA_DEG:.0f}°). set-zero-here or FORCE")
        return (
            f"refused {label}: would move j{j} by {worst:.1f}° "
            f"(max {MAX_SAFE_DELTA_DEG:.0f}° without FORCE). "
            f"If encoders disagree with the pose, POST /api/set_zero first."
        )

    def _write_pose(self, degrees: list[float], *,
                    speed: int = WALK_SPEED, acc: int = WALK_ACC) -> None:
        self._last_pose = list(degrees)
        if not self.bus or not self.armed:
            return
        speed = normalize_speed(speed)
        acc = normalize_acc(acc)
        # Never put a potentially 2.5 s SCAN transaction in the 100 Hz walk
        # loop. Walk start has already verified/populated the cache, while
        # the independent feedback guard continues to enforce missing-ID
        # safety during the run.
        live = self._live_ids(allow_stale=self.mode == "walk")
        for joint, deg in enumerate(degrees):
            sid = joint_to_servo_id(joint)
            if live and sid not in live:
                continue
            count = deg_to_count(joint, deg, self.bus.trims[joint])
            self.bus.pkt.SyncWritePosEx(sid, count, speed, acc)
        self.bus.pkt.groupSyncWrite.txPacket()
        self.bus.pkt.groupSyncWrite.clearParam()

    def _hold_here(self) -> None:
        if not self.bus or not self.armed:
            return
        present = self._read_present_pose()
        pose = [0.0 if d is None else float(d) for d in present]
        self._write_pose(pose, speed=250, acc=30)

    def _sync_gait_walk_stance(self) -> None:
        """Make scripted gaits use the same tall pose as Stand/RL walk."""
        self.gait.sync_plant_stance(
            SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG)

    def _walk_start_delta_vs_present(self) -> tuple[float | None, int | None]:
        if not self.bus:
            return 0.0, None
        present = self._read_present_pose()
        live = self._live_ids()
        goal = walk_start_pose_degrees()
        pairs = []
        for j, g in enumerate(goal):
            sid = joint_to_servo_id(j)
            if live and sid not in live:
                continue
            p = present[j] if j < len(present) else None
            if p is not None:
                pairs.append((j, float(p), float(g)))
        if len(pairs) < N_JOINTS - 4:
            return None, None
        worst = 0.0
        worst_j: int | None = None
        for j, p, g in pairs:
            d = abs(p - g)
            if d > worst:
                worst = d
                worst_j = j
        return worst, worst_j

    def _refuse_walk_if_not_ready(self) -> str | None:
        worst, j = self._walk_start_delta_vs_present()
        if worst is None:
            self.status = "refused walk: pose feedback unavailable"
            return ("refused walk: pose feedback unavailable - use Stand, "
                    "wait for stand verified, then retry")
        if worst <= WALK_START_TOL_DEG:
            return None
        self.status = (
            f"refused walk: not at walk-ready pose (max Δq={worst:.0f}° "
            f"on j{j})")
        return (
            f"refused walk: not at walk-ready pose (max Δq={worst:.1f}° "
            f"on j{j}; press Stand first and wait for stand verified)")

    # -- gait selection --------------------------------------------------------
    _GAIT_NAMES = {0: "tripod (drag)", 1: "noslip tripod",
                   2: "noslip RIPPLE (pairs)", 3: "noslip WAVE (one leg)",
                   4: "SE2 TETRAPOD (auto-scaled)",
                   5: "SE2 WAVE (auto-scaled)",
                   6: "SE2 CPG (loaded)",
                   7: "noslip CLAMP-FIT tripod",
                   8: "middle-tuck quad crawl",
                   9: "noslip FLUID tripod",
                   10: "noslip FLUID-FAST tripod",
                   11: "noslip FLUID-HYBRID tripod",
                   12: "noslip FLUID-PUSH tripod",
                   13: "noslip FLUID-PULSE tripod",
                   14: "noslip FLUID-MID tripod"}

    def _gait_desc(self) -> str:
        if self._gait_id == 0:
            return f"tripod high-step ({format_demo_tripod(self._demo_tripod)})"
        if self._gait_id == 1:
            return (f"noslip alpha={self._noslip_alpha:.2f} "
                    f"cap={self.gait.max_vx * 1000:.0f}mm/s")
        if self._gait_id == 7:
            return "noslip CLAMP-FIT tripod"
        if self._gait_id == 8:
            return "middle-tuck quad crawl"
        if self._gait_id == 9:
            return "noslip FLUID tripod (2.90s/18mm/continuous)"
        if self._gait_id == 10:
            return "noslip FLUID-FAST tripod (2.40s/14mm/continuous)"
        if self._gait_id == 11:
            return "noslip FLUID-HYBRID tripod (3.20s/18mm/alpha=.75)"
        if self._gait_id == 12:
            return "noslip FLUID-PUSH tripod (3.20s/18mm/alpha=.70)"
        if self._gait_id == 13:
            return "noslip FLUID-PULSE tripod (3.20s/18mm/alpha=.75)"
        if self._gait_id == 14:
            return "noslip FLUID-MID tripod (2.65s/16mm/continuous)"
        if self._gait_id == 6 and self._cpg_loaded is not None:
            return f"SE2 CPG ({self._cpg_loaded['name']})"
        return self._GAIT_NAMES.get(self._gait_id, "tripod (drag)")

    def _caps_for_gait(self, gait_id: int) -> tuple[float, float, float]:
        if int(gait_id) == 0:
            return (
                self._demo_tripod.max_vx_mps,
                self._demo_tripod.max_vy_mps,
                self._demo_tripod.max_omega_rad_s,
            )
        if int(gait_id) == 1:
            return (NoSlipGait.GAIT1_MAX_VX, NoSlipGait.MAX_VY,
                    NoSlipGait.MAX_OMEGA)
        return (0.20, 0.15, 0.9)

    def _moving(self) -> bool:
        return (
            self.mode == "walk"
            or abs(self._vx) + abs(self._vy) + abs(self._omega) > 1e-4
        )

    def scripted_contract_state(self) -> dict:
        """Operator-visible hardware/sim contract and missed deadlines."""
        return {
            "control_hz": SCRIPTED_WALK_CONTROL_HZ,
            "servo_speed_counts_s": SCRIPTED_WALK_SPEED_COUNTS_S,
            "servo_acc_units": SCRIPTED_WALK_ACC_UNITS,
            "deadline_overruns": self._loop_overruns,
        }

    def _apply_demo_tripod_tune(self, updates: dict[str, float]) -> str:
        if self._moving():
            self.status = "tripod tune refused while walking (J 0 0 0 first)"
            return "refused GTUNE while walking - send J 0 0 0 first"
        try:
            tuned = tune_demo_tripod(self._demo_tripod, updates)
        except ValueError as e:
            return f"bad GTUNE: {e}"
        self._demo_tripod = tuned
        if "lift" in updates or "lift_mm" in updates:
            self._lift_mm = tuned.lift_mm
        if self._gait_id == 0:
            self.gait = self._new_demo_tripod_gait()
            self._sync_gait_walk_stance()
            self.gait.reset_phase(t=time.monotonic())
        self.status = f"GTUNE {format_demo_tripod(self._demo_tripod)}"
        return self.status

    def list_cpg_controllers(self) -> list[dict]:
        """List `cpg_controller_*.json` artifacts available to CPGLOAD."""
        return _list_cpg_controllers()

    def load_cpg_controller(self, name: str) -> str:
        """CPGLOAD: parse + validate one artifact (no motion, no gait swap).

        Does not touch ``self.gait`` — send ``GAIT 6`` afterward (while
        stopped) to actually swap onto it. Keeping load and swap
        separate means a bad/missing artifact name can never silently
        leave a walking robot on a stale gait.
        """
        try:
            result = _load_cpg_controller(name)
        except (ValueError, OSError) as e:
            return f"bad CPGLOAD: {e}"
        self._cpg_loaded = result
        gk = result["gait_kw"]
        self.status = (f"loaded CPG '{result['name']}' ({result['gait']}, "
                       f"period={gk['period']:.2f} "
                       f"swing_frac={gk['swing_frac']:.3f} "
                       f"lift={gk['lift'] * 1000:.1f}mm) "
                       f"- send GAIT 6 to use it")
        return self.status

    def _set_gait(self, gait_id: int, alpha: float | None = None) -> str:
        """Swap / retune the walk gait (call with the lock held).

        Swaps only happen while NOT walking: a fresh gait re-pins its
        feet at neutral, which would yank mid-stride legs. Alpha alone
        retunes the live no-slip tripod safely (phase-boundary
        semantics); ripple/wave/CPG run their (or their loaded)
        presets.
        """
        gait_id = int(gait_id)
        if gait_id not in self._GAIT_NAMES:
            self.status = f"gait selection refused: unknown GAIT {gait_id}"
            return f"refused unknown GAIT {gait_id}"
        if gait_id == 6 and self._cpg_loaded is None:
            return "refused GAIT 6 - CPGLOAD a controller first"
        if alpha is not None:
            self._noslip_alpha = max(0.0, min(1.0, float(alpha)))
            if gait_id == 1 and self._gait_id == 1:
                self.gait.set_alpha(self._noslip_alpha)
        if gait_id == self._gait_id:
            return f"gait {self._gait_desc()}"
        moving = abs(self._vx) + abs(self._vy) + abs(self._omega) > 1e-4
        if self.mode == "walk" or moving:
            self.status = "gait swap refused while walking (J 0 0 0 first)"
            return "refused gait swap while walking - send J 0 0 0 first"
        if gait_id == 2:
            self.gait = NoSlipGait.ripple()
        elif gait_id == 3:
            self.gait = NoSlipGait.wave()
        elif gait_id == 4:
            self.gait = SE2FootGait.tetrapod()
        elif gait_id == 5:
            self.gait = SE2FootGait.wave()
        elif gait_id == 6:
            self.gait = SE2FootGait(gait=self._cpg_loaded["gait"],
                                    **self._cpg_loaded["gait_kw"])
        elif gait_id == 7:
            self.gait = NoSlipGait.clamp_fit()
        elif gait_id == 8:
            self.gait = MiddleTuckQuadGait.crawl()
        elif gait_id == 9:
            self.gait = NoSlipGait.fluid()
        elif gait_id == 10:
            self.gait = NoSlipGait.fluid_fast()
        elif gait_id == 11:
            self.gait = NoSlipGait.fluid_hybrid()
        elif gait_id == 12:
            self.gait = NoSlipGait.fluid_push()
        elif gait_id == 13:
            self.gait = NoSlipGait.fluid_pulse()
        elif gait_id == 14:
            self.gait = NoSlipGait.fluid_mid()
        elif gait_id == 1:
            self.gait = NoSlipGait.gait1(alpha=self._noslip_alpha)
        else:
            self.gait = self._new_demo_tripod_gait()
        self._sync_gait_walk_stance()
        if self._lift_mm is not None:
            self.gait.set_lift_mm(self._lift_mm)
        self.gait.reset_phase(t=time.monotonic())
        self._gait_id = gait_id
        self.status = f"gait -> {self._gait_desc()}"
        return f"gait {self._gait_desc()}"

    # -- command API ---------------------------------------------------------
    def handle(self, line: str) -> str:
        line = (line or "").strip()
        if not line:
            return "empty"
        with self._lock:
            return self._handle_locked(line)

    def _handle_locked(self, line: str) -> str:
        parts = line.split()
        cmd = parts[0].upper()

        if cmd in ("ARM",):
            self._torque_all(True)
            self.armed = True
            self.mode = "idle"
            self.status = "armed"
            return "armed"

        if cmd in ("X", "DISARM", "RELAX"):
            self.mode = "idle"
            self.gait.stop()
            self._vx = self._vy = self._omega = 0.0
            self._torque_all(False)
            self.armed = False
            self.status = "disarmed (limp)"
            return "limp"

        if cmd in ("SETTLE",):
            self.status = "SETTLE removed; use STEP lower, then X"
            return (
                "refused SETTLE: removed; run /api/standup "
                "direction=down, wait for done, then send X")

        if cmd == "P":
            if not self.armed:
                return "need ARM"
            force = any(p.upper() == "FORCE" for p in parts[1:])
            self.gait.stop()
            self._sync_gait_walk_stance()
            self.gait.reset_phase(t=time.monotonic())
            self._vx = self._vy = self._omega = 0.0
            stand = walk_start_pose_degrees()
            refused = self._refuse_large_delta(stand, force=force, label="stand")
            if refused:
                self.mode = "idle"
                return refused
            self.mode = "stand"
            self._last_pose = list(stand)
            self._write_pose(stand, speed=400, acc=20)
            self.status = "standing"
            return "stand"

        if cmd == "C":
            if not self.armed:
                return "need ARM"
            force = any(p.upper() == "FORCE" for p in parts[1:])
            goal = [0.0] * N_JOINTS
            refused = self._refuse_large_delta(goal, force=force, label="centre")
            if refused:
                self.mode = "idle"
                return refused
            self.mode = "idle"
            self.gait.stop()
            self._write_pose(goal, speed=300, acc=15)
            self.status = "centred"
            return "centre"

        if cmd == "HOLD":
            if self.armed:
                self.mode = "idle"
                self.gait.stop()
                self._hold_here()
            return "hold"

        if cmd == "GAITSTOP":
            if not self.armed:
                return "need ARM"
            if self.mode != "walk":
                return "not walking"
            # Keep the gait loop alive while its current swing finishes and
            # both groups repin at the neutral planted stance. J 0 follows
            # only after this bounded phase-aware settle interval.
            self.gait.stop()
            self._vx = self._vy = self._omega = 0.0
            period = max(0.4, float(getattr(self.gait, "period", 3.2)))
            settle_s = 1.5 * period + 0.5
            self.status = f"settling gait to neutral ({settle_s:.2f}s)"
            return f"gaitstop_s={settle_s:.3f}"

        if cmd == "J" and len(parts) >= 4:
            if not self.armed:
                return "need ARM"
            try:
                vx_mm = float(parts[1])
                vy_mm = float(parts[2])
                omega = float(parts[3])
            except ValueError:
                return "bad J"
            gid = None
            if len(parts) >= 5:
                try:
                    gid = int(parts[4])
                except ValueError:
                    gid = None
            target_gid = self._gait_id if gid is None else gid
            vx_cap, vy_cap, om_cap = self._caps_for_gait(target_gid)
            # UI uses mm/s; gait wants m/s. Cap gently for first teleop.
            vx = max(-vx_cap, min(vx_cap, vx_mm / 1000.0))
            vy = max(-vy_cap, min(vy_cap, vy_mm / 1000.0))
            om = max(-om_cap, min(om_cap, omega))
            moving = abs(vx) + abs(vy) + abs(om) > 1e-4
            was_walking = self.mode == "walk"
            if not moving:
                self.gait.stop()
                self._vx = self._vy = self._omega = 0.0
                if was_walking:
                    # Do not seed a stop from the MCU's asynchronous position
                    # cache. Under a dense gait stream that cache can lag by
                    # an entire swing and command a planted leg toward an old
                    # pose. Reissue the last command the servos already had.
                    self._write_pose(list(self._last_pose), speed=250, acc=30)
                self.mode = "idle"
                self.status = (
                    f"walk stopped[{self._gait_desc()}] quiet hold"
                    if was_walking else "quiet hold")
                return "J"
            if moving and not was_walking:
                refused = self._refuse_walk_if_not_ready()
                if refused:
                    self.gait.stop()
                    self._vx = self._vy = self._omega = 0.0
                    self.mode = "idle"
                    return refused
            if gid is not None and gid != self._gait_id:
                # Picker swap carried on the J stream: when starting from
                # stand, swap before publishing the nonzero command so the
                # gait selector does not misread this as a live swap.
                msg = self._set_gait(gid)
                if msg.startswith("refused"):
                    return msg
            self._vx, self._vy, self._omega = vx, vy, om
            self.mode = "walk" if moving else "stand"
            if not (was_walking and moving):
                # Scripted drive uses the same tall walk-ready stance as
                # Stand/RL walk. Never resync mid-walk: NoSlipGait's sync
                # re-pins the world anchors, which would snap planted feet
                # back to neutral under load.
                self._sync_gait_walk_stance()
                if moving:
                    # Fresh cycle on engage: re-pin feet under the robot
                    # NOW and restart the startup-softened phase machine.
                    self.gait.reset_phase(t=time.monotonic())
            self.gait.set_velocity(vx=vx, vy=vy, omega=om)
            self.status = (f"walk[{self._gait_desc()}] vx={self._vx:.3f} "
                           f"vy={self._vy:.3f} w={self._omega:.2f}")
            return "J"

        if cmd == "K" and len(parts) >= 2:
            try:
                lift_mm = float(parts[1])
            except ValueError:
                return "bad K"
            self._lift_mm = lift_mm       # survives gait swaps
            self.gait.set_lift_mm(lift_mm)
            if self._gait_id == 0:
                try:
                    self._demo_tripod = tune_demo_tripod(
                        self._demo_tripod, {"lift": lift_mm})
                except ValueError:
                    pass
            return "K"

        if cmd == "GTUNE":
            if len(parts) == 1:
                return f"GTUNE {format_demo_tripod(self._demo_tripod)}"
            try:
                updates = parse_demo_tripod_tune_tokens(parts[1:])
            except ValueError as e:
                return f"bad GTUNE: {e}"
            return self._apply_demo_tripod_tune(updates)

        if cmd == "GAIT":
            if len(parts) < 2:
                return f"gait {self._gait_desc()}"
            try:
                gid = int(parts[1])
            except ValueError:
                return "bad GAIT"
            alpha = None
            if len(parts) >= 3:
                try:
                    alpha = float(parts[2])
                except ValueError:
                    return "bad GAIT"
            return self._set_gait(gid, alpha)

        if cmd == "CPGLIST":
            import json as _json
            return _json.dumps(self.list_cpg_controllers())

        if cmd == "CPGLOAD" and len(parts) >= 2:
            return self.load_cpg_controller(parts[1])

        if cmd == "#" and len(parts) >= 3:
            if not self.armed:
                return "need ARM"
            try:
                j = int(parts[1])
                deg = float(parts[2])
            except ValueError:
                return "bad #"
            if not (0 <= j < N_JOINTS):
                return "bad joint"
            force = any(p.upper() == "FORCE" for p in parts[3:])
            # Always seed from *present* encoders — never yank other joints
            # toward a stale stand/zero _last_pose (2026-08-06 incident).
            present = self._read_present_pose()
            pose: list[float] = []
            for i in range(N_JOINTS):
                d = present[i]
                if d is None:
                    d = self._last_pose[i] if i < len(self._last_pose) else 0.0
                pose.append(float(d))
            pose[j] = deg
            refused = self._refuse_large_delta(pose, force=force, label=f"#{j}")
            if refused:
                return refused
            self.mode = "idle"
            self._write_pose(pose, speed=400, acc=25)
            return f"#{j}"

        if cmd == "Q" and len(parts) >= 3:
            try:
                j = int(parts[1])
                amp = abs(float(parts[2]))
            except ValueError:
                return "bad Q"
            if not (0 <= j < N_JOINTS):
                return "bad joint"
            # Stop stand/walk re-hold so it can't overwrite the wiggle.
            if not self.armed:
                self._torque_all(True)
                self.armed = True
            self.mode = "idle"
            self.gait.stop()
            self._vx = self._vy = self._omega = 0.0
            threading.Thread(
                target=self._wiggle, args=(j, amp), daemon=True).start()
            self.status = f"wiggle j{j} ±{amp:.0f}°"
            return f"Q{j}"

        # Ignore v1-only config / dances politely.
        if cmd in ("E", "Z", "$", "U", "CROUCH", "SIT") or cmd.startswith("M"):
            return "ignored"
        if cmd in ("V", "B", "O", "T"):
            return "ignored"

        return f"unknown:{cmd}"

    def _wiggle(self, joint: int, amp: float) -> None:
        """Nudge one joint ±amp around its *present* angle, then return."""
        with self._lock:
            if not self.bus:
                return
            if not self.armed:
                self._torque_all(True)
                self.armed = True
            self.mode = "idle"
            # Prefer live encoder readings — _last_pose is often stale
            # (e.g. after set-zero-here or hand-posing while limp). Seed
            # ALL joints from present so a sync-write doesn't yank the
            # rest of the body toward an old stand pose.
            present = self._read_present_pose()
            base = present[joint]
            if base is None:
                base = self._last_pose[joint]
            pose = list(self._last_pose)
            for j in range(N_JOINTS):
                if present[j] is not None:
                    pose[j] = present[j]
            self._last_pose = list(pose)

        for sign in (+1, -1, 0):
            with self._lock:
                if not self.armed or not self.bus:
                    return
                self.mode = "idle"
                pose = list(self._last_pose)
                pose[joint] = base + sign * amp
                self._write_pose(pose, speed=500, acc=30)
            time.sleep(0.45)

    # -- background loop -----------------------------------------------------
    def _loop(self) -> None:
        t0 = time.monotonic()
        deadline = t0
        stand_hold_t = t0
        while not self._stop.is_set():
            tick = time.monotonic()
            with self._lock:
                mode = self.mode
                armed = self.armed
                if mode == "demo":
                    pass  # bench / inplace_demos owns the bus
                elif armed and mode == "walk":
                    pose = self.gait.desired_deg(tick - t0)
                    self._write_pose(
                        pose,
                        speed=SCRIPTED_WALK_SPEED_COUNTS_S,
                        acc=SCRIPTED_WALK_ACC_UNITS,
                    )
                elif armed and mode == "stand":
                    # Occasional re-hold so stance doesn't droop. This
                    # must match the tall walk-ready stance used by
                    # Stand/RL walk and scripted J drive.
                    if tick - stand_hold_t >= 2.5:
                        hold = (list(self._last_pose)
                                if self._last_pose
                                else walk_start_pose_degrees())
                        self._write_pose(hold, speed=300, acc=20)
                        stand_hold_t = tick
                else:
                    stand_hold_t = tick
            deadline, skipped = _advance_periodic_deadline(
                deadline, time.monotonic())
            self._loop_overruns += skipped
            wait_s = deadline - time.monotonic()
            if wait_s > 0.0:
                self._stop.wait(wait_s)
