"""Off-robot regression for composed-policy learned stance gating.

Run locally:  uv run python linux_control/test_rl_composed_policy_guard.py
No hardware: the fake API object has no bus, and the default-role refusals
return before any preflight or motion worker can start.
"""
from __future__ import annotations

import sys
import threading
import json
import tempfile
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from api.rl import RlApi
from rl_policy import (
    PolicyTiming,
    _drive_timing_trip_reason,
    _tail_tilt_summary,
    _timing_trip_reason,
)


class FakeRlApi(RlApi):
    def __init__(self, roles: dict[str, str | None] | None = None, *,
                 dry_run: bool = True, bus=None, armed: bool = False):
        self._roles_data = {
            "walk": None,
            "hold": "walk",
            "stand": None,
            "lower": None,
        }
        self._roles_data.update(roles or {})
        self.drive = types.SimpleNamespace(
            dry_run=dry_run,
            bus=bus,
            armed=armed,
            _lock=threading.RLock(),
        )
        self._demo_thread = None

    def _roles(self) -> dict:
        return dict(self._roles_data)

    def _role_weights(self, role: str) -> Path | None:
        if self._roles_data.get(role) and self._roles_data.get(role) != "walk":
            return Path("/tmp/fake_explicit_policy.json")
        return None

    def _bus_admission_error(self) -> dict | None:
        # Production BenchAPI supplies this through CoreApi.  These tests use
        # the RL mixin alone and exercise refusals before any bus transaction.
        return None


def test_default_composed_policy_refuses_learned_rise():
    out = FakeRlApi().rl_policy_move(mode="stand", learned=True)
    assert out["ok"] is False
    assert "learned RL rise is disabled" in out["error"]
    assert "explicit role" in out["error"]


def test_default_composed_policy_refuses_learned_lower():
    out = FakeRlApi().rl_policy_move(mode="lower", learned=True)
    assert out["ok"] is False
    assert "learned RL lower is disabled" in out["error"]
    assert "explicit role" in out["error"]


def test_explicit_learned_stance_role_reaches_normal_no_bus_guard():
    out = FakeRlApi({
        "stand": "stand_stancemix_tuckclock_scratch8m.json",
    }).rl_policy_move(mode="stand", learned=True)
    assert out == {"ok": False, "error": "no bus"}


def test_drive_start_refuses_limp_before_preflight_or_motion():
    out = FakeRlApi(dry_run=False, bus=object(), armed=False).rl_drive_start(
        vx=0.05)
    assert out["ok"] is False
    assert "limp/disarmed" in out["error"]


def test_drive_start_refuses_legacy_joint_hold_role_before_motion():
    out = FakeRlApi({"hold": "walk"}, dry_run=False, bus=object(),
                    armed=True).rl_drive_start(vx=0.05)
    assert out["ok"] is False
    assert "explicit learned hold role" in out["error"]
    assert "joint-hold fallback is not safe" in out["error"]


def test_policy_picker_rejects_unversioned_coordinates():
    with tempfile.TemporaryDirectory() as directory:
        api = FakeRlApi()
        api.UPLOAD_POLICIES_DIR = Path(directory)
        api.POLICIES_DIR = Path(directory) / "repo"
        path = Path(directory) / "old.json"
        path.write_text(json.dumps({
            "meta": {"obs_dim": 68, "act_dim": 18,
                     "training_hz": 25.0},
        }))
        out = api.rl_policy_select(file=path.name)
        assert out["ok"] is False
        assert "invalid v2 policy" in out["error"]


def test_walk_timing_tolerates_isolated_startup_jitter():
    assert _timing_trip_reason(
        "walk", tick=0, hz=100.0, late_s=0.007,
        consecutive_late=1,
    ) is None
    assert _timing_trip_reason(
        "walk", tick=2, hz=100.0, late_s=0.049,
        consecutive_late=3,
    ) is None


def test_walk_timing_still_trips_persistent_or_hard_stalls():
    persistent = _timing_trip_reason(
        "walk", tick=5, hz=100.0, late_s=0.007,
        consecutive_late=3,
    )
    assert persistent is not None
    assert "3 consecutive" in persistent

    hard = _timing_trip_reason(
        "walk", tick=5, hz=100.0, late_s=0.051,
        consecutive_late=1,
    )
    assert hard is not None
    assert "tick 5" in hard


def test_drive_timing_tolerates_one_hard_transport_bubble():
    timing = PolicyTiming(100.0, 0.01, 100.0, True, 100.0)
    assert _drive_timing_trip_reason(
        "walk", object(), tick=22, timing=timing, late_s=0.054,
        consecutive_late=1,
    ) is None


def test_drive_timing_trips_repeated_hard_or_critical_stall():
    timing = PolicyTiming(100.0, 0.01, 100.0, True, 100.0)
    repeated = _drive_timing_trip_reason(
        "walk", object(), tick=23, timing=timing, late_s=0.051,
        consecutive_late=2,
    )
    assert repeated is not None
    assert "2 consecutive hard misses" in repeated

    critical = _drive_timing_trip_reason(
        "walk", object(), tick=24, timing=timing, late_s=0.201,
        consecutive_late=1,
    )
    assert critical is not None
    assert "tick 24" in critical


def test_tail_fall_classifier_clears_recovered_imu_excursion():
    summary = _tail_tilt_summary([
        4.0, 7.0, 55.8, 56.1, 55.7, 10.0, 1.2, 0.4, 0.3,
    ])
    assert summary["tail_tilt_max_deg"] == 56.1
    assert summary["tail_tilt_high_samples"] == 3
    assert summary["tail_tilt_recovered"] is True
    assert summary["tail_fell"] is False


def test_tail_fall_classifier_keeps_persistent_or_late_excursion():
    persistent = _tail_tilt_summary([2.0, 38.0, 51.0, 52.0, 50.0])
    assert persistent["tail_tilt_recovered"] is False
    assert persistent["tail_fell"] is True

    late = _tail_tilt_summary([2.0, 48.0])
    assert late["tail_fell"] is True


def _main() -> int:
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    print("OK" if fails == 0 else f"{fails} FAILURES")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_main())
