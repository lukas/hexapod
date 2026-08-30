"""Off-robot regression for composed-policy learned stance gating.

Run locally:  uv run python linux_control/test_rl_composed_policy_guard.py
No hardware: the fake API object has no bus, and the default-role refusals
return before any preflight or motion worker can start.
"""
from __future__ import annotations

import sys
import threading
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from api.rl import RlApi


class FakeRlApi(RlApi):
    def __init__(self, roles: dict[str, str | None] | None = None, *,
                 dry_run: bool = True, bus=None, armed: bool = False):
        self._roles_data = {
            "walk": None,
            "hold": RlApi.DEFAULT_HOLD_POLICY_FILE,
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
