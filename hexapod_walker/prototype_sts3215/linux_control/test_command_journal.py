"""Attribution and retention behaviour of the robot command journal."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import command_journal  # noqa: E402


class Headers:
    def __init__(self, **values):
        self._values = {k.lower(): v for k, v in values.items()}

    def get(self, name, default=None):
        return self._values.get(name.lower(), default)


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("HEXAPOD_CONTROLLER_MAP", raising=False)
    command_journal.reset()
    yield
    command_journal.reset()


def test_explicit_header_wins_and_is_recorded_as_such():
    entry = command_journal.record(
        "POST", "/api/demo", body={"name": "wave"}, peer="192.168.4.23",
        headers=Headers(**{"X-Hexapod-Controller": "robotlab"}),
    )
    assert entry["controller"] == "robotlab"
    assert entry["attributed_by"] == "header"


def test_peer_map_attributes_a_known_laptop(monkeypatch):
    monkeypatch.setenv(
        "HEXAPOD_CONTROLLER_MAP", json.dumps({"192.168.4.23": "lukas-laptop"})
    )
    entry = command_journal.record("POST", "/api/plant", peer="192.168.4.23")
    assert entry["controller"] == "lukas-laptop"
    assert entry["attributed_by"] == "peer_map"


def test_user_agent_and_bare_peer_fallbacks():
    lab = command_journal.record(
        "POST", "/api/demo", peer="10.0.0.5",
        headers=Headers(**{"User-Agent": "hexapod-lab/1.0"}),
    )
    assert lab["controller"] == "robotlab"
    assert lab["attributed_by"] == "user_agent"

    browser = command_journal.record(
        "POST", "/api/demo", peer="192.168.4.99",
        headers=Headers(**{"User-Agent": "Mozilla/5.0 (Macintosh)"}),
    )
    assert browser["controller"] == "browser@192.168.4.99"

    bare = command_journal.record("POST", "/api/demo", peer="192.168.4.7")
    assert bare["controller"] == "unknown@192.168.4.7"
    assert bare["attributed_by"] == "peer_only"


def test_a_forged_controller_label_cannot_inject_junk():
    entry = command_journal.record(
        "POST", "/api/demo", peer="1.2.3.4",
        headers=Headers(**{"X-Hexapod-Controller": "rogue\n{\"ok\":false}<script>"}),
    )
    label = entry["controller"]
    assert not any(ch in label for ch in '\n\r<>"{}:'), label
    assert label == "rogueokfalsescript"


def test_drive_heartbeats_are_counted_not_stored():
    for _ in range(40):
        assert command_journal.record(
            "POST", "/api/rl/drive/cmd", peer="192.168.4.23"
        ) is None
    command_journal.record("POST", "/api/rl/drive/start", peer="192.168.4.23")
    state = command_journal.recent()
    assert state["drive_heartbeats"]["count"] == 40
    assert [c["path"] for c in state["commands"]] == ["/api/rl/drive/start"]


def test_polling_cannot_evict_the_command_history():
    """The failure this exists to prevent: a stop record aged out by GETs."""
    command_journal.record(
        "POST", "/api/demo/stop", body={"reason": "estop"}, peer="192.168.4.23"
    )
    for _ in range(2000):
        command_journal.record("POST", "/api/rl/drive/cmd", peer="192.168.4.23")
    paths = [c["path"] for c in command_journal.recent(limit=500)["commands"]]
    assert "/api/demo/stop" in paths


def test_since_and_controller_filters_and_body_truncation():
    first = command_journal.record("POST", "/api/a", peer="1.1.1.1")
    command_journal.record(
        "POST", "/api/b", peer="2.2.2.2",
        headers=Headers(**{"X-Hexapod-Controller": "robotlab"}),
    )
    later = command_journal.recent(since=first["seq"])
    assert [c["path"] for c in later["commands"]] == ["/api/b"]
    only = command_journal.recent(controller="robotlab")
    assert [c["path"] for c in only["commands"]] == ["/api/b"]

    big = command_journal.record("POST", "/api/c", body={"x": "y" * 5000},
                                 peer="1.1.1.1")
    assert big["body"]["_truncated"] is True
    assert len(json.dumps(big["body"])) < 1200


def test_history_is_mirrored_to_disk(tmp_path):
    command_journal.record("POST", "/api/demo/stop", peer="192.168.4.23")
    lines = (tmp_path / "commands.jsonl").read_text().strip().splitlines()
    assert json.loads(lines[-1])["path"] == "/api/demo/stop"


def test_journalling_never_breaks_a_control_path(monkeypatch):
    """A logging fault must not propagate into the request handler."""
    monkeypatch.setenv("HEXAPOD_LOG_DIR", "/proc/nonexistent/denied")
    command_journal._file_failed = False
    entry = command_journal.record("POST", "/api/demo", peer="1.1.1.1")
    assert entry["path"] == "/api/demo"
    assert command_journal.recent()["returned"] == 1
