"""Whole-body walking experiments, measured by the overhead camera.

A walk protocol is a small JSON file in ``sysid/protocols/`` with
``"walk_protocol": 1``: a list of legs, each a gait velocity command
(``vx`` mm/s forward, ``vy`` mm/s to the robot's right, ``omega`` rad/s
clockwise seen from above) held for some seconds. The loop runs them like
any other protocol; this module does the work in-process:

1. stand the robot up if it is on the floor (``/api/standup``);
2. for each leg, stream ``J vx vy omega gait`` at 10 Hz while sampling the
   chassis tag's floor position and heading from the camera server
   (``/api/poses`` marker 0), the tag's pixel position (``/api/detections.json``,
   to stop before the robot leaves the frame), and ``/api/feedback`` for
   currents, temperatures and IMU tilt;
3. stop with ``J 0 0 0`` (the robot holds its stance), sit down at the end.

What comes out is what the goal is about: mean speed and straight-line
travel against the command, heading change against the commanded turn,
lateral drift, tilt, total current, and how long the camera lost the tag.
Everything is written next to the run (``walk_summary.json`` and three
CSVs) and the compact summary goes to the planner.

Stops that are not failures: the robot reaching the edge of the camera's
view or the tag being hidden for two seconds end the leg early and the
next leg (an out-and-back's return) still runs. Failures: a tripped or
hot servo, tilt beyond 30 degrees, or the robot not answering for five
seconds; the run stops and the robot sits.
"""
from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen

from .config import Settings

WALK_KEY = "walk_protocol"
J_HZ = 10.0
POSE_EVERY_S = 0.2
FEEDBACK_EVERY_S = 0.3
TILT_ABORT_DEG = 30.0
TAG_LOST_S = 2.0
FEEDBACK_LOST_S = 5.0
FRAME_EDGE_FRAC = 0.12
EDGE_NOISE_FRAC = 0.03       # camera 1's fix-to-fix jitter is tens of mm; a real move out is more than this
EDGE_WINDOW = 5              # distance samples (about a second) in the median that the edge rule compares
BODY_YAW_AXIS_M = 0.0875     # body centre to a yaw servo's output shaft (chassis apothem 100 mm - 12.5 mm)
TAG_BLACK_M = 0.0272         # black square of the robot's tags; sets the pixel scale around each tag
STAND_WAIT_S = 25.0
SETTLE_S = 1.5
# Teleop caps; the robot's drive controller clips harder.
MAX_VX, MAX_VY, MAX_OMEGA, MAX_SECONDS = 60.0, 40.0, 0.5, 40.0
RL_KEY = "rl_policy"               # protocol field: drive with this RL policy file instead of the J gait
RL_MAX_VX, RL_MAX_VY = 120.0, 80.0  # mm/s; the policies' command band is about 0.06-0.12 m/s
RL_READY_WAIT_S = 45.0
RL_START_WAIT_S = 12.0     # drive/start is async; wait for /api/rl/drive active
RL_NO_SESSION_TICKS = 10   # a second of 'no drive session' answers means the session ended
GARBAGE_TEMP_C = 100.0     # no servo is this hot; a corrupted byte is
HOT_POLLS = 3              # consecutive feedback samples at or above warn_c before the walk stops
RL_STOP_WAIT_S = 25.0
OBSTACLE_LEG_S = 3.0     # leg length when the look saw something within a body length


@dataclass
class Leg:
    name: str
    vx: float = 0.0
    vy: float = 0.0
    omega: float = 0.0
    seconds: float = 10.0
    gait: int = 1
    rl: bool = False          # RL drive session (body-frame m/s, rad/s) instead of the scripted J gait

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def command(self) -> str:
        return f"J {self.vx:.1f} {self.vy:.1f} {self.omega:.3f} {self.gait}"

    def drive_body(self) -> dict:
        """/api/rl/drive/cmd body: the RL runner takes m/s and rad/s (hexapod 2's floorkeeper did the same)."""
        return {"vx": round(self.vx / 1000.0, 4), "vy": round(self.vy / 1000.0, 4), "wz": round(self.omega, 4), "dh": 0}

    def stop_command(self) -> str:
        return f"J 0 0 0 {self.gait}"

    def reversed(self) -> "Leg":
        neg = lambda v: -v if v else 0.0          # keep zeros as 0.0, not -0.0, in the command text
        return Leg(self.name + "_back", neg(self.vx), neg(self.vy), neg(self.omega), self.seconds, self.gait, self.rl)


def is_walk_protocol(doc: dict) -> bool:
    return bool(isinstance(doc, dict) and doc.get(WALK_KEY))


def rl_policy_of(doc: dict) -> Optional[str]:
    """The RL policy file a walk protocol drives with, or None for the scripted gait."""
    v = (doc or {}).get(RL_KEY)
    return str(v) if v else None


def legs_of(doc: dict) -> List[Leg]:
    """Legs from a protocol document, expanded for out-and-back, clipped to the caps.
    RL walks get the RL caps: the 100 Hz policies were trained around 0.08 m/s."""
    out: List[Leg] = []
    rl = rl_policy_of(doc) is not None
    cap_vx, cap_vy = (RL_MAX_VX, RL_MAX_VY) if rl else (MAX_VX, MAX_VY)
    for raw in doc.get("legs") or []:
        leg = Leg(name=str(raw.get("name") or f"leg{len(out)}"),
                  vx=max(-cap_vx, min(cap_vx, float(raw.get("vx_mm_s", 0.0)))),
                  vy=max(-cap_vy, min(cap_vy, float(raw.get("vy_mm_s", 0.0)))),
                  omega=max(-MAX_OMEGA, min(MAX_OMEGA, float(raw.get("omega_rad_s", 0.0)))),
                  seconds=max(2.0, min(MAX_SECONDS, float(raw.get("seconds", 10.0)))),
                  gait=int(raw.get("gait", doc.get("gait", 1))), rl=rl)
        out.append(leg)
        if raw.get("out_and_back", doc.get("out_and_back", False)):
            out.append(leg.reversed())
    return out


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------ I/O

def _http_get(url: str, timeout: float = 6.0) -> dict:
    with urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _http_post(url: str, body: Optional[dict] = None, raw: Optional[bytes] = None, timeout: float = 60.0) -> Any:
    data = raw if raw is not None else json.dumps(body or {}).encode()
    headers = {} if raw is not None else {"Content-Type": "application/json"}
    with urlopen(Request(url, data=data, method="POST", headers=headers), timeout=timeout) as r:
        text = r.read().decode()
    try:
        return json.loads(text)
    except ValueError:
        return text.strip()


def camera_base(settings: Settings) -> str:
    """The camera server root, from the pose-state URL the runner already uses."""
    url = settings.vision_url
    for suffix in ("/api/pose-state", "/api/poses", "/api/pose-state.json"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url.rsplit("/api", 1)[0]


def chassis_euler_z(settings: Settings) -> Optional[float]:
    """Rotation from body +x to the chassis tag's +x, from the installed tag layout."""
    path = settings.prototype_dir / "hexapod-tracker" / "configs" / "hexapod-1-apriltag-layout.json"
    try:
        layout = json.loads(path.read_text())
        for tag in layout.get("robot_tags", []):
            if tag.get("kind") == "chassis_tag":
                return float(tag["frame_from_tag"]["euler_xyz_deg"][2])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


# ------------------------------------------------------------- session

@dataclass
class PoseSample:
    t: float
    leg: str
    x: Optional[float]
    y: Optional[float]
    yaw: Optional[float]
    px: Optional[float] = None
    py: Optional[float] = None
    tracked: bool = False


def distance_frac(frac: Optional[tuple]) -> float:
    """How far the robot is from the middle of the picture, as a fraction of the frame (0.5 = at an edge)."""
    return math.hypot(frac[0] - 0.5, frac[1] - 0.5) if frac else 0.0


def near_edge(frac: Optional[tuple]) -> bool:
    if frac is None:
        return False
    return min(frac[0], 1.0 - frac[0], frac[1], 1.0 - frac[1]) < FRAME_EDGE_FRAC


class EdgeWatch:
    """Is the robot near an edge of the picture and clearly moving further out?

    Compares the median distance-from-centre over the last EDGE_WINDOW samples
    with the lowest such median seen so far: body sway during the gait moves the
    chassis tag by 20-40 px each step (2026-09-12, standing tall at the top of
    camera 1), which a single-sample rule read as walking out."""

    def __init__(self) -> None:
        self.hist: List[float] = []
        self.best: Optional[float] = None
        self.last_near = False

    def update(self, frac: Optional[tuple]) -> Optional[str]:
        """"tag_lost", "frame_edge" or None for this sample."""
        if frac is None:
            return "tag_lost" if self.last_near else None
        near = near_edge(frac)
        self.hist.append(distance_frac(frac))
        self.hist = self.hist[-EDGE_WINDOW:]
        med = sorted(self.hist)[len(self.hist) // 2]
        if self.best is None or med < self.best:
            self.best = med
        going_out = len(self.hist) >= EDGE_WINDOW and med > self.best + EDGE_NOISE_FRAC
        self.last_near = near
        return "frame_edge" if near and going_out else None


def _tag_centre(corners) -> tuple:
    return (sum(p[0] for p in corners) / 4.0, sum(p[1] for p in corners) / 4.0)


def _tag_heading_up_deg(corners) -> float:
    """The tag's +x (corner 0 toward corner 1) as a heading in the picture with y up, degrees."""
    return math.degrees(math.atan2(-(corners[1][1] - corners[0][1]), corners[1][0] - corners[0][0]))


def _tag_edge_px(corners) -> float:
    return sum(math.dist(corners[i], corners[(i + 1) % 4]) for i in range(4)) / 4.0


def _wrap(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def fit_body(tags: dict, layout: dict, yaws_deg: Dict[int, float]) -> Optional[dict]:
    """Where the body is and which way it faces, from the tags in one picture.

    The chassis tag gives both directly. Without it, each horizontal hip lid
    does: its heading in the picture is body heading + the leg's zero azimuth
    - the yaw servo's angle + the lid's own rotation (layout ``frame_from_tag``
    euler z), and its centre sits BODY_YAW_AXIS_M out from the body centre
    along body heading + azimuth. Checked live on 2026-09-12 against the
    chassis tag in three cameras (lids agreed within 1 deg in the top view);
    the sign of the yaw-servo term follows the layout's joint_conventions and
    was checked only at yaw = 0. Knee lids tilt with the knee and are not used.

    Returns ``{"px": (x, y), "heading_px": (ux, uy), "heading_up_deg", "source", "n"}``
    in picture pixels (y down), or None when neither kind of tag is there."""
    robot_tags = layout.get("robot_tags") or []
    azimuth = {int(k): float(v) for k, v in (layout.get("leg_zero_azimuth_body_deg") or {}).items()}

    def euler_z(t) -> float:
        return float(((t.get("frame_from_tag") or {}).get("euler_xyz_deg") or [0, 0, 0])[2])

    def result(px, heading_up, source, n):
        a = math.radians(heading_up)
        return {"px": px, "heading_px": (math.cos(a), -math.sin(a)), "heading_up_deg": round(heading_up, 1),
                "source": source, "n": n}

    chassis = next((t for t in robot_tags if t.get("kind") == "chassis_tag" and str(t.get("id")) in tags), None)
    if "0" in tags or chassis is not None:
        tid = str(chassis["id"]) if chassis else "0"
        corners = tags[tid]
        heading = _tag_heading_up_deg(corners) - (euler_z(chassis) if chassis else 0.0)
        return result(_tag_centre(corners), _wrap(heading), "tag0", 1)
    headings, centres = [], []
    for t in robot_tags:
        if t.get("kind") != "servo_lid" or t.get("joint") != "hip" or str(t.get("id")) not in tags:
            continue
        leg = int(t.get("leg", -1))
        if leg not in azimuth:
            continue
        corners = tags[str(t["id"])]
        body_heading = _wrap(_tag_heading_up_deg(corners) - euler_z(t) - azimuth[leg] + float(yaws_deg.get(leg, 0.0)))
        headings.append(body_heading)
        scale = _tag_edge_px(corners) / TAG_BLACK_M                    # px per metre around this tag
        out = math.radians(body_heading + azimuth[leg])                # lid sits out along the leg's zero azimuth
        cx, cy = _tag_centre(corners)
        centres.append((cx - BODY_YAW_AXIS_M * scale * math.cos(out), cy + BODY_YAW_AXIS_M * scale * math.sin(out)))
    if not headings:
        return None
    mean_heading = math.degrees(math.atan2(sum(math.sin(math.radians(h)) for h in headings),
                                           sum(math.cos(math.radians(h)) for h in headings)))
    n = float(len(centres))
    return result((sum(c[0] for c in centres) / n, sum(c[1] for c in centres) / n), mean_heading, "lids", len(centres))


@dataclass
class Session:
    settings: Settings
    run_dir: Path
    post: Callable = _http_post
    get: Callable = _http_get
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    log: Callable[[str], None] = print
    notes: List[str] = field(default_factory=list)
    camera_index: Optional[int] = None
    frame_size: Optional[tuple] = None
    seen_camera: Optional[int] = None
    proxy: bool = False                   # last pixel() came from leg tags, not the chassis tag
    heading_px: Optional[tuple] = None    # body +x as a unit vector in the picture (x right, y down), when tags gave one
    fit_source: str = ""                  # "tag0", "lids", "centroid" or "" for the last pixel()
    _robot_ids: Optional[set] = None
    _layout: Optional[dict] = None
    _fb_last: Optional[tuple] = None      # (clock time, feedback dict)

    @property
    def robot(self) -> str:
        return self.settings.robot_url.rstrip("/")

    @property
    def camera(self) -> str:
        return camera_base(self.settings)

    # -- robot --------------------------------------------------------
    def feedback(self) -> Optional[dict]:
        try:
            fb = self.get(f"{self.robot}/api/feedback")
        except Exception:  # noqa: BLE001
            return None
        if isinstance(fb, dict) and fb.get("ok", True):
            self._fb_last = (self.clock(), fb)
            return fb
        return None

    def recent_feedback(self, max_age_s: float = 1.0) -> Optional[dict]:
        """The last feedback if it is fresh, else a new one (keeps body_fit from doubling the polling)."""
        if self._fb_last and self.clock() - self._fb_last[0] <= max_age_s:
            return self._fb_last[1]
        return self.feedback()

    def yaw_joints_deg(self) -> Dict[int, float]:
        """Leg -> yaw servo angle from the freshest feedback; missing joints read 0."""
        joints = ((self.recent_feedback() or {}).get("joints") or [])
        out: Dict[int, float] = {}
        for leg in range(6):
            j = joints[3 * leg] if 3 * leg < len(joints) else None
            try:
                out[leg] = float((j or {}).get("deg") or 0.0)
            except (TypeError, ValueError):
                out[leg] = 0.0
        return out

    def mode(self) -> str:
        try:
            st = self.get(f"{self.robot}/api/rl/state")
            return str((st.get("pose") or {}).get("mode") or "")
        except Exception:  # noqa: BLE001
            return ""

    def knees_deg(self, fb: Optional[dict]) -> List[float]:
        joints = (fb or {}).get("joints") or []
        return [float(j["deg"]) for j in joints[2::3] if isinstance(j, dict) and j.get("deg") is not None]

    def stand(self) -> bool:
        """Stand up if on the floor. True when the robot is standing."""
        fb = self.feedback()
        knees = self.knees_deg(fb)
        if knees and min(knees) > 60.0 and self.mode() in ("stand", "idle", "walk"):
            self.log("already standing")
            return True
        self.log("standing up")
        try:
            res = self.post(f"{self.robot}/api/standup", {"mode": "step", "direction": "up"})
        except Exception as exc:  # noqa: BLE001
            self.notes.append(f"standup refused: {exc}")
            return False
        if isinstance(res, dict) and not res.get("ok", True):
            self.notes.append(f"standup refused: {res}")
            return False
        t0 = self.clock()
        while self.clock() - t0 < STAND_WAIT_S:
            self.sleep(1.0)
            knees = self.knees_deg(self.feedback())
            if knees and min(knees) > 60.0 and self.mode() != "demo":
                self.sleep(SETTLE_S)
                return True
        self.notes.append("stand-up did not finish in time")
        return False

    def stand_adjust(self) -> bool:
        """Re-hold the walk-ready stance on a robot that is already standing (the STEP
        route's stand_adjust): the scripted gait's stop leaves the swing tripod
        mid-stride and the drive refuses the next command until this is done."""
        try:
            res = self.post(f"{self.robot}/api/standup", {"mode": "step", "direction": "up"})
        except Exception as exc:  # noqa: BLE001
            self.notes.append(f"stand adjust refused: {exc}")
            return False
        if isinstance(res, dict) and not res.get("ok", True):
            self.notes.append(f"stand adjust refused: {res}")
            return False
        t0 = self.clock()
        while self.clock() - t0 < STAND_WAIT_S:
            self.sleep(1.0)
            if self.mode() != "demo":
                break
        self.sleep(SETTLE_S)
        return True

    def sit(self, wait: bool = False) -> bool:
        """STEP down. With ``wait`` poll until the knees are straight (or 25 s)."""
        try:
            self.post(f"{self.robot}/api/standup", {"mode": "step", "direction": "down"})
        except Exception as exc:  # noqa: BLE001
            self.notes.append(f"sit refused: {exc}")
            return False
        if not wait:
            return True
        t0 = self.clock()
        while self.clock() - t0 < 25.0:
            self.sleep(1.0)
            knees = self.knees_deg(self.feedback())
            if knees and max(knees) < 20.0 and self.mode() != "demo":
                return True
        self.notes.append("sit-down did not finish in time")
        return False

    def stop(self, leg: Leg) -> None:
        if leg.rl:
            self.rl_stop()
            return
        try:
            self.post(f"{self.robot}/cmd", raw=leg.stop_command().encode())
        except Exception as exc:  # noqa: BLE001
            self.notes.append(f"stop command failed: {exc}")

    # -- RL drive (the policies hexapod 2 ran on its grid) ------------
    def rl_json(self, path: str, body: Optional[dict] = None) -> dict:
        try:
            r = self.post(f"{self.robot}{path}", body if body is not None else {}) if body is not None \
                else self.get(f"{self.robot}{path}")
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return r if isinstance(r, dict) else {"ok": False, "error": str(r)[:120]}

    def rl_prepare(self, policy: str) -> bool:
        """Select the walk policy, keep the hold role, and get to the sim walk-ready stance."""
        sel = None
        for _ in range(20):                      # refused while a job is still winding down
            sel = self.rl_json("/api/rl/policy_select", {"file": policy})
            if sel.get("ok"):
                break
            self.sleep(1.0)
        if not (sel or {}).get("ok"):
            self.notes.append(f"policy_select {policy} refused: {(sel or {}).get('error')}")
            return False
        # hexapod 2's floorkeeper gave the same policy the hold role as well: a drive
        # session refuses to open without a learned hold policy.
        self.rl_json("/api/rl/roles", {"role": "walk", "file": policy})
        self.rl_json("/api/rl/roles", {"role": "hold", "file": policy})
        if self.rl_json("/api/rl/preflight?mode=walk").get("ok"):
            return True
        return self.rl_walk_ready()

    def rl_walk_ready(self) -> bool:
        """Stand into the sim walk-ready stance with the RL stand routine and confirm with preflight."""
        self.log("not walk-ready; asking the robot to stand into the walk-ready stance")
        st = self.rl_json("/api/rl/stand", {})
        if not st.get("ok"):
            self.notes.append(f"rl stand refused: {st.get('error')}")
            return False
        t0 = self.clock()
        while self.clock() - t0 < RL_READY_WAIT_S:
            self.sleep(1.5)
            cal = self.rl_json("/api/rl/state").get("calibrate") or {}
            if not cal.get("running"):
                break
        pre = self.rl_json("/api/rl/preflight?mode=walk")
        if not pre.get("ok"):
            self.notes.append(f"not walk-ready after stand: {pre.get('error')}")
            return False
        return True

    def rl_start(self) -> bool:
        """Open the drive session and wait until it is live: drive/start is asynchronous,
        and a command sent before the loop is up answers 'no drive session'."""
        r = self.rl_json("/api/rl/drive/start", {})
        if not r.get("ok") and "walk-ready" in str(r.get("error", "")):
            # The previous leg's policy stop left a hip far from the stance (2026-09-12: L4 hip
            # 71 deg off). Stand into it once and ask again, as the scripted gait path does.
            self.notes.append("drive/start refused for pose; re-standing into walk-ready and retrying once")
            if self.rl_walk_ready():
                r = self.rl_json("/api/rl/drive/start", {})
        if not r.get("ok"):
            self.notes.append(f"drive/start refused: {r.get('error')}")
            return False
        t0 = self.clock()
        while self.clock() - t0 < RL_START_WAIT_S:
            st = self.rl_json("/api/rl/drive")
            if st.get("active"):
                return True
            res = st.get("result") or {}
            if res and res.get("mode") == "drive" and not res.get("ok", True):
                self.notes.append(f"drive session did not open: {res.get('error')}")
                return False
            self.sleep(0.25)
        self.notes.append(f"drive session not live after {RL_START_WAIT_S:.0f} s")
        return False

    def rl_stop(self) -> None:
        for _ in range(6):
            self.rl_json("/api/rl/drive/cmd", {"vx": 0, "vy": 0, "wz": 0, "dh": 0})
            self.sleep(0.2)
        self.rl_json("/api/rl/drive/stop", {})
        t0 = self.clock()
        while self.clock() - t0 < RL_STOP_WAIT_S:    # the session decelerates and hands off to the hold policy
            self.sleep(0.5)
            if not self.rl_json("/api/rl/drive").get("active"):
                break

    def rl_result(self) -> Optional[dict]:
        """The runner's own drive statistics once the session has ended."""
        t0 = self.clock()
        while self.clock() - t0 < 15.0:
            cal = self.rl_json("/api/rl/state").get("calibrate") or {}
            if not cal.get("running"):
                res = cal.get("result") or {}
                if res.get("mode") == "drive":
                    t = res.get("timing") or {}
                    return {k: res.get(k) for k in ("ok", "error", "ended", "ticks", "overruns", "fell",
                                                    "tilt_rel_max_deg", "stale_stream_ticks")} | {
                        "mean_service_ms": t.get("mean_service_ms"), "max_service_ms": t.get("max_service_ms")}
                return None
            self.sleep(1.0)
        return None

    # -- camera -------------------------------------------------------
    def pose(self, leg_name: str) -> PoseSample:
        t = self.clock()
        try:
            doc = self.get(f"{self.camera}/api/poses")
        except Exception:  # noqa: BLE001
            return PoseSample(t, leg_name, None, None, None)
        m = ((doc or {}).get("markers") or {}).get("0") or {}
        if m.get("status") != "tracked":
            return PoseSample(t, leg_name, None, None, None)
        cams = [int(c) for c in (m.get("camera_indices") or [])]
        if cams and self.camera_index is None:
            top = int(getattr(self.settings, "top_camera", -1))
            self.camera_index = top if top in cams else cams[0]     # stay inside the top camera's frame when it tracks the tag
        # The fused marker mixes every camera that sees the tag; a weakly calibrated
        # side view (camera 0 with one floor anchor, 2026-09-12) turned a 30 mm/s walk
        # into 250 mm/s. Take the top camera's own observation when it has one.
        obs = next((o for o in (m.get("observations") or [])
                    if int(o.get("camera_index", -1)) == self.camera_index), None) or m
        pos = obs.get("position_mm") or {}
        yaw = (obs.get("rotation_degrees") or {}).get("yaw")
        return PoseSample(t, leg_name, pos.get("x"), pos.get("y"), yaw, tracked=True)

    def layout(self) -> dict:
        """The installed tag layout, read once: {} when there is none."""
        if self._layout is None:
            path = Path(getattr(self.settings, "tracker_checkout", Path("/nonexistent"))) / "configs" / "hexapod-1-apriltag-layout.json"
            try:
                self._layout = json.loads(path.read_text())
            except (OSError, ValueError):
                self._layout = {}
        return self._layout

    def robot_tag_ids(self) -> set:
        """Every tag id the tracker's layout puts on the robot (parts + chassis tag)."""
        if self._robot_ids is None:
            ids = {0}
            try:
                ids.update(int(t["id"]) for t in self.layout().get("robot_tags", []))
            except (ValueError, KeyError, TypeError):
                pass
            if len(ids) == 1:                   # no layout file: the tracker's parts (yoke faces) will do
                try:
                    doc = self.get(f"{self.camera}/api/poses")
                    for part in ((doc or {}).get("parts") or {}).values():
                        ids.update(int(t) for t in (part.get("configured_tag_ids") or []))
                except Exception:  # noqa: BLE001
                    pass
            self._robot_ids = ids
        return self._robot_ids

    def pixel(self) -> Optional[tuple]:
        """Where the robot is in the frame, as fractions: tag 0's centre, or the centroid
        of whatever robot tags are visible when the chassis tag is not.

        Always the top camera (settings.top_camera) when it is streaming: the
        frame-edge stop and the recentre steer inside that picture and must not
        silently switch to another camera when the tag leaves it (2026-09-12: the
        robot walked out of the bottom of camera 1 and a recentre then chased
        camera 0's pixels). Only when no camera is designated, or the designated
        one is absent, the first camera that decodes tag 0 is used. Works whether
        or not the view is floor-calibrated."""
        try:
            doc = self.get(f"{self.camera}/api/detections.json")
        except Exception:  # noqa: BLE001
            return None
        cams = (doc or {}).get("cameras") or []
        want = self.camera_index if self.camera_index is not None else int(getattr(self.settings, "top_camera", -1))
        chosen = [c for c in cams if int(c.get("index", -1)) == want]
        if not chosen:
            chosen = [c for c in cams if (c.get("tags") or {}).get("0")][:1]
        for c in chosen:
            tags = c.get("tags") or {}
            if not c.get("width") or not c.get("height"):
                continue
            self.frame_size = (int(c["width"]), int(c["height"]))
            self.seen_camera = int(c.get("index", -1))
            fit = fit_body(tags, self.layout(), self.yaw_joints_deg() if "0" not in tags else {})
            if fit is not None:
                self.proxy = fit["source"] != "tag0"
                self.fit_source = fit["source"]
                self.heading_px = fit["heading_px"]
                return fit["px"][0] / float(c["width"]), fit["px"][1] / float(c["height"])
            # No chassis tag and no hip lid: the centroid of whatever robot tags are there.
            robot = [crn for tid, crn in tags.items() if int(tid) in self.robot_tag_ids() and crn]
            if not robot:
                return None
            pts = [[sum(p[0] for p in crn) / 4.0, sum(p[1] for p in crn) / 4.0] for crn in robot]
            self.proxy, self.fit_source, self.heading_px = True, "centroid", None
            n = float(len(pts))
            return sum(p[0] for p in pts) / n / float(c["width"]), sum(p[1] for p in pts) / n / float(c["height"])
        return None

    @staticmethod
    def near_edge(frac: Optional[tuple]) -> bool:
        return near_edge(frac)


# ---------------------------------------------------------------- legs

def run_leg(s: Session, leg: Leg, writers: dict) -> Dict[str, Any]:
    """Stream one gait command and measure. Returns the leg's metrics.

    Whatever happens inside the loop, the stop command is sent."""
    st: Dict[str, Any] = {"poses": [], "tilt": [], "currents": [], "hottest": 0.0, "fb_samples": 0,
                          "reason": "duration", "fatal": None, "tag_lost_s": 0.0, "lost_since": None, "ticks": 0}
    start_pose = s.pose(leg.name)
    if not start_pose.tracked:
        s.notes.append(f"{leg.name}: chassis tag not tracked at start")
    st["poses"].append(start_pose)
    writers["pose"].writerow([round(start_pose.t, 3), leg.name, start_pose.x, start_pose.y, start_pose.yaw, "", ""])
    t0 = s.clock()
    try:
        if leg.rl and not s.rl_start():
            st["fatal"], st["reason"] = "drive session refused: " + "; ".join(s.notes[-1:]), "refused"
        else:
            _stream(s, leg, writers, st, t0)
            if (not leg.rl and st["reason"] == "refused" and "walk-ready" in str(st["fatal"]) and st["ticks"] <= 2):
                # The previous leg's stop left the swing tripod mid-stride; re-hold the stance and go again.
                s.log("gait refused for walk-ready; re-standing once and retrying")
                s.notes.append(f"{leg.name}: re-stood once after 'not at walk-ready'")
                if s.stand_adjust():
                    st.update(fatal=None, reason="duration", ticks=0)
                    t0 = s.clock()
                    _stream(s, leg, writers, st, t0)
    except Exception as exc:  # noqa: BLE001
        st["fatal"], st["reason"] = f"runner error: {type(exc).__name__}: {exc}", "error"
    finally:
        seconds = s.clock() - t0
        s.stop(leg)
    if leg.rl:
        st["drive"] = s.rl_result()
    s.sleep(SETTLE_S)
    end_pose = s.pose(leg.name)
    st["poses"].append(end_pose)
    writers["pose"].writerow([round(end_pose.t, 3), leg.name, end_pose.x, end_pose.y, end_pose.yaw, "", ""])
    if st["lost_since"] is not None:
        st["tag_lost_s"] += (t0 + seconds) - st["lost_since"]
    tilt, currents = st["tilt"], st["currents"]
    m = metrics(leg, st["poses"], seconds, st["ticks"])
    m.update({
        "stopped": st["reason"], "fatal": st["fatal"], "ticks_sent": st["ticks"], "feedback_samples": st["fb_samples"],
        "tilt_max_deg": round(max(tilt), 1) if tilt else None,
        "tilt_rms_deg": round(math.sqrt(sum(t * t for t in tilt) / len(tilt)), 1) if tilt else None,
        "current_total_mean_a": round(sum(currents) / len(currents), 2) if currents else None,
        "current_total_peak_a": round(max(currents), 2) if currents else None,
        "hottest_c": round(st["hottest"], 1) if st["hottest"] else None,
        "tag_lost_s": round(st["tag_lost_s"], 1),
    })
    if leg.rl:
        m["drive"] = st.get("drive")
        m["command"] = json.dumps(leg.drive_body())
    return m


def _stream(s: Session, leg: Leg, writers: dict, st: Dict[str, Any], t0: float) -> None:
    """The 10 Hz command loop with camera and feedback sampling; fills ``st``."""
    next_tick = t0
    last_fb_ok = t0
    last_fb_at = -1e9
    last_pose_at = -1e9
    while True:
        now = s.clock()
        if now - t0 >= leg.seconds:
            return
        if now >= next_tick:
            try:
                if leg.rl:
                    r = s.post(f"{s.robot}/api/rl/drive/cmd", leg.drive_body())
                    if isinstance(r, dict) and r.get("ok") is False and not r.get("active", True):
                        st["no_session"] = st.get("no_session", 0) + 1
                        if st["no_session"] >= RL_NO_SESSION_TICKS:      # the session really ended (trip, cap, fall)
                            st["fatal"], st["reason"] = f"drive session ended: {r.get('error')}", "refused"
                            return
                    else:
                        st["no_session"] = 0
                else:
                    r = s.post(f"{s.robot}/cmd", raw=leg.command().encode())
                if isinstance(r, str) and "refused" in r.lower():
                    st["fatal"], st["reason"] = f"gait refused: {r[:120]}", "refused"
                    return
            except Exception as exc:  # noqa: BLE001
                text = getattr(exc, "reason", None) or str(exc)
                body = ""
                if hasattr(exc, "read"):
                    try:
                        body = exc.read().decode(errors="ignore")   # HTTPError carries the robot's sentence
                    except Exception:  # noqa: BLE001
                        body = ""
                if "refused" in (body + str(text)).lower():
                    st["fatal"], st["reason"] = f"gait refused: {(body or text)[:120]}", "refused"
                    return
                if now - last_fb_ok > FEEDBACK_LOST_S:
                    st["fatal"], st["reason"] = f"robot not answering: {exc}", "unreachable"
                    return
            st["ticks"] += 1
            next_tick += 1.0 / J_HZ
        if now - last_pose_at >= POSE_EVERY_S:
            last_pose_at = now
            p = s.pose(leg.name)
            frac = s.pixel()
            if frac:
                p.px, p.py = round(frac[0], 3), round(frac[1], 3)
            st["poses"].append(p)
            writers["pose"].writerow([round(p.t, 3), leg.name, p.x, p.y, p.yaw, p.px, p.py])
            # Near the edge and moving further out: stop. Starting at the edge and coming
            # back in is allowed (2026-09-12: every RL leg died at its first sample because
            # the robot began the walk at the bottom of camera 1). Losing the robot right
            # after it was near the edge means it left the picture: stop too.
            watch = st.setdefault("edge_watch", EdgeWatch())
            verdict = watch.update(frac)
            if verdict == "tag_lost":
                st["reason"] = "tag_lost"
                s.notes.append(f"{leg.name}: stopped early, robot left the camera's view")
                return
            if verdict == "frame_edge":
                st["reason"] = "frame_edge"
                s.notes.append(f"{leg.name}: stopped early, robot near the edge of the camera's view and moving out")
                return
            if p.tracked:
                if st["lost_since"] is not None:
                    st["tag_lost_s"] += now - st["lost_since"]
                    st["lost_since"] = None
            else:
                if st["lost_since"] is None:
                    st["lost_since"] = now
                elif now - st["lost_since"] > TAG_LOST_S:
                    st["tag_lost_s"] += now - st["lost_since"]
                    st["lost_since"] = None
                    if frac:
                        # The tag is in the picture but the view has no floor calibration:
                        # the robot is standing on the floor tags, or none is in frame.
                        st["reason"] = "uncalibrated"
                        s.notes.append(f"{leg.name}: stopped early, chassis tag seen by camera {s.seen_camera} "
                                       f"but the view has no floor calibration (floor tags covered or out of frame)")
                    else:
                        st["reason"] = "tag_lost"
                        s.notes.append(f"{leg.name}: stopped early, chassis tag hidden for {TAG_LOST_S:.0f} s")
                    return
        if now - last_fb_at >= FEEDBACK_EVERY_S:
            last_fb_at = now
            fb = s.feedback()
            if fb is None:
                if now - last_fb_ok > FEEDBACK_LOST_S:
                    st["fatal"], st["reason"] = "robot feedback silent for 5 s", "unreachable"
                    return
            else:
                last_fb_ok = now
                st["fb_samples"] += 1
                roll, pitch = fb.get("roll_deg"), fb.get("pitch_deg")
                if roll is not None and pitch is not None:
                    t_deg = math.hypot(float(roll), float(pitch))
                    st["tilt"].append(t_deg)
                    writers["imu"].writerow([round(now, 3), leg.name, roll, pitch])
                    if t_deg > TILT_ABORT_DEG:
                        st["fatal"], st["reason"] = f"tilt {t_deg:.0f} deg", "tilt"
                        return
                joints = fb.get("joints") or []
                total = sum(abs(float((j or {}).get("cur_a") or 0.0)) for j in joints)
                st["currents"].append(total)
                # A temperature byte can arrive corrupted (150 C on a 31 C servo in the archive);
                # readings at or above GARBAGE_TEMP_C are dropped, and the hot stop needs
                # HOT_POLLS consecutive samples, like the on-robot runner's temp guard.
                temps = [float((j or {}).get("temp_c") or 0.0) for j in joints]
                temps = [t for t in temps if t < GARBAGE_TEMP_C]
                st["hottest"] = max([st["hottest"]] + temps)
                writers["servo"].writerow([round(now, 3), leg.name, round(total, 3)]
                                          + [(j or {}).get("deg") for j in joints]
                                          + [(j or {}).get("cur_a") for j in joints])
                servo = fb.get("servo") or {}
                tripped = servo.get("tripped") or []
                warn_c = float(servo.get("warn_c") or 55.0)
                if tripped:
                    st["fatal"], st["reason"] = f"servo tripped: {servo.get('tripped_names') or tripped}", "tripped"
                    return
                if temps and max(temps) >= warn_c:
                    st["hot_polls"] = st.get("hot_polls", 0) + 1
                    if st["hot_polls"] >= HOT_POLLS:
                        st["fatal"], st["reason"] = f"servo at {max(temps):.0f} C for {HOT_POLLS} samples", "hot"
                        return
                else:
                    st["hot_polls"] = 0
        s.sleep(0.01)


def metrics(leg: Leg, poses: List[PoseSample], seconds: float, ticks: int) -> Dict[str, Any]:
    """Speed, travel and heading numbers from the tracked chassis-tag path."""
    tracked = [p for p in poses if p.tracked and p.x is not None and p.y is not None]
    out: Dict[str, Any] = {
        "leg": leg.name, "command": leg.command(), "vx_mm_s": leg.vx, "vy_mm_s": leg.vy,
        "omega_rad_s": leg.omega, "seconds": round(seconds, 2),
        "commanded_mm": round(leg.speed * seconds, 1),
        "commanded_rot_deg": round(-math.degrees(leg.omega * seconds), 1),   # + omega is clockwise; z-up frame counts CCW +
        "pose_samples": len(tracked),
    }
    if len(tracked) < 2:
        out["measured"] = False
        return out
    # Start and end as the median of the first and last few fixes: a single camera
    # fix of the small chassis tag jitters by tens of mm, and summing that jitter
    # along the path made a 3 s walk read 250 mm/s on 2026-09-12. Speed is the
    # straight-line displacement over the leg, as hexapod 2's grid speed was.
    def _median_pose(samples):
        xs = sorted(q.x for q in samples); ys = sorted(q.y for q in samples)
        yaws = [q.yaw for q in samples if q.yaw is not None]
        yaw = None
        if yaws:
            ref = yaws[0]
            yaw = wrap_deg(ref + sorted(wrap_deg(v - ref) for v in yaws)[len(yaws) // 2])
        return PoseSample(samples[0].t, samples[0].leg, xs[len(xs) // 2], ys[len(ys) // 2], yaw, tracked=True)
    k = min(3, len(tracked) // 2) or 1
    a, b = _median_pose(tracked[:k]), _median_pose(tracked[-k:])
    dx, dy = b.x - a.x, b.y - a.y
    straight = math.hypot(dx, dy)
    path = sum(math.hypot(q.x - p.x, q.y - p.y) for p, q in zip(tracked, tracked[1:]))
    out.update({
        "measured": True,
        "straight_mm": round(straight, 1), "path_mm": round(path, 1),
        "mean_speed_mm_s": round(straight / seconds, 1) if seconds > 0 else None,      # net, start to end
        "path_speed_mm_s": round(path / seconds, 1) if seconds > 0 else None,          # fix-to-fix, jitter included
        "travel_ratio": round(straight / (leg.speed * seconds), 2) if leg.speed and seconds > 0 else None,
    })
    if a.yaw is not None and b.yaw is not None:
        out["heading_change_deg"] = round(wrap_deg(b.yaw - a.yaw), 1)
        if leg.omega:
            out["turn_ratio"] = round(out["heading_change_deg"] / out["commanded_rot_deg"], 2) if out["commanded_rot_deg"] else None
        # Travel direction relative to the body's heading at the start. The tag's
        # yaw differs from the body heading by a constant, which cancels here.
        # Robot +vy is to its right, i.e. clockwise from forward seen from above,
        # so in this z-up frame the commanded direction is atan2(-vy, vx).
        if straight > 5.0:
            travel_rel = wrap_deg(math.degrees(math.atan2(dy, dx)) - a.yaw)
            out["travel_dir_rel_start_deg"] = round(travel_rel, 1)
            if leg.speed:
                cmd_rel = math.degrees(math.atan2(-leg.vy, leg.vx))
                out["commanded_dir_rel_deg"] = round(cmd_rel, 1)
                out["drift_deg"] = round(wrap_deg(travel_rel - cmd_rel), 1)
                out["lateral_offset_mm"] = round(straight * math.sin(math.radians(travel_rel - cmd_rel)), 1)
    return out


# ----------------------------------------------------------------- run

def run_walk(settings: Settings, doc: dict, run_dir: Path, *, post: Optional[Callable] = None, get: Optional[Callable] = None,
             sleep: Optional[Callable[[float], None]] = None, clock: Optional[Callable[[], float]] = None,
             log: Callable[[str], None] = print, obstacle: Optional[str] = None) -> Dict[str, Any]:
    """Run a walk protocol. Returns {"status", "exit_code", "summary", "log_tail"}.

    ``obstacle`` is what the pre-run look saw within a body length; the legs
    are then cut to a few seconds each rather than refused."""
    run_dir.mkdir(parents=True, exist_ok=True)
    # Resolved at call time so tests can patch the module's HTTP and clock functions.
    post, get = post or _http_post, get or _http_get
    sleep, clock = sleep or time.sleep, clock or time.monotonic
    s = Session(settings, run_dir, post=post, get=get, sleep=sleep, clock=clock, log=log)
    legs = legs_of(doc)
    lines: List[str] = []

    def say(msg: str) -> None:
        lines.append(msg)
        log(msg)

    summary: Dict[str, Any] = {"walk": True, "protocol": doc.get("name"), "legs": [], "aborted": None,
                               "chassis_euler_z_deg": chassis_euler_z(settings),
                               "conventions": "vx forward, vy right, omega clockwise seen from above; heading change and "
                                              "drift are counter-clockwise-positive in the floor frame"}
    if not legs:
        say("walk protocol has no legs")
        return {"status": "failed", "exit_code": 2, "summary": summary, "log_tail": "\n".join(lines)}
    if obstacle:
        legs = [replace(l, seconds=min(l.seconds, OBSTACLE_LEG_S)) for l in legs]     # keeps the RL flag (2026-09-12: it was dropped)
        summary["obstacle"] = obstacle[:200]
        say(f"the look saw something close ({obstacle[:80]}); legs cut to {OBSTACLE_LEG_S:.0f} s each")
    started = clock()
    if not s.stand():
        say("could not stand: " + "; ".join(s.notes))
        summary["aborted"] = "stand"
        summary["notes"] = s.notes
        return {"status": "failed", "exit_code": 3, "summary": summary, "log_tail": "\n".join(lines)}
    policy = rl_policy_of(doc)
    summary["rl_policy"] = policy
    if policy and not s.rl_prepare(policy):
        say("could not get the RL policy walk-ready: " + "; ".join(s.notes[-2:]))
        summary["aborted"] = "rl_prepare"
        summary["notes"] = s.notes
        s.sit()
        return {"status": "failed", "exit_code": 3, "summary": summary, "log_tail": "\n".join(lines)}
    say(f"standing; {len(legs)} legs: " + ", ".join(
        f"{l.name} {json.dumps(l.drive_body()) if l.rl else l.command()} x{l.seconds:.0f}s" for l in legs)
        + (f"; RL policy {policy}" if policy else ""))
    status, code = "ok", 0
    with (run_dir / "walk_pose.csv").open("w", newline="") as fp, \
            (run_dir / "walk_imu.csv").open("w", newline="") as fi, \
            (run_dir / "walk_servo.csv").open("w", newline="") as fs:
        writers = {"pose": csv.writer(fp), "imu": csv.writer(fi), "servo": csv.writer(fs)}
        writers["pose"].writerow(["t", "leg", "x_mm", "y_mm", "yaw_deg", "px_frac", "py_frac"])
        writers["imu"].writerow(["t", "leg", "roll_deg", "pitch_deg"])
        writers["servo"].writerow(["t", "leg", "total_a"] + [f"q{j}" for j in range(18)] + [f"cur{j}" for j in range(18)])
        for leg in legs:
            m = run_leg(s, leg, writers)
            summary["legs"].append(m)
            say(f"{leg.name}: {m.get('stopped')}; speed {m.get('mean_speed_mm_s')} mm/s of {leg.speed:.0f} commanded, "
                f"travel ratio {m.get('travel_ratio')}, heading {m.get('heading_change_deg')} deg, drift {m.get('drift_deg')} deg, "
                f"tilt max {m.get('tilt_max_deg')}, current mean {m.get('current_total_mean_a')} A")
            if m.get("fatal"):
                status, code = "failed", 4
                summary["aborted"] = m["fatal"]
                say(f"stopping the run: {m['fatal']}")
                break
    if settings.recentre and summary["aborted"] is None:
        # Leave the robot where the next run can be measured.
        from . import recentre as _rc
        rc = _rc.recentre(s, budget_s=settings.recentre_end_budget_s, gait=legs[0].gait, label="recentre_end")
        summary["recentre"] = rc
        say(f"recentre at the end: {rc['reason']}")
    s.sit()
    summary["motion_s"] = round(clock() - started, 1)
    summary["camera_index"] = s.camera_index
    summary["notes"] = s.notes
    (run_dir / "walk_summary.json").write_text(json.dumps(summary, indent=1))
    return {"status": status, "exit_code": code, "summary": summary, "log_tail": "\n".join(lines)[-4000:]}
