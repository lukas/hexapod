"""Exclusive command lease: one controller owns motion, abort stays open."""
import pytest

import command_lease


class Headers:
    def __init__(self, **values):
        self._values = {k.lower(): v for k, v in values.items()}

    def get(self, name, default=None):
        return self._values.get(name.lower(), default)


@pytest.fixture(autouse=True)
def clean():
    command_lease.reset()
    yield
    command_lease.reset()


def test_no_lease_gates_nothing():
    assert command_lease.check("POST", "/api/rl/stand") is None
    assert command_lease.check("POST", "/api/sysid/run") is None
    assert command_lease.state()["held"] is False


def test_holder_passes_and_every_other_controller_is_refused():
    got = command_lease.acquire("guarded-runner-413d5402", ttl_s=60,
                                reason="L2 belly-rest sweep")
    assert got["ok"]
    token = got["token"]

    assert command_lease.check("POST", "/api/sysid/run", token=token) is None

    refusal = command_lease.check("POST", "/api/rl/stand",
                                  controller="mac-hub")
    assert refusal is not None
    assert refusal["code"] == "command_lease_held"
    assert refusal["lease"]["owner"] == "guarded-runner-413d5402"
    assert "token" not in refusal["lease"]          # never leaked
    assert refusal["refused"]["controller"] == "mac-hub"

    wrong = command_lease.check("POST", "/api/rl/lower", token="deadbeef")
    assert wrong is not None and wrong["refused"]["had_token"] is True


def test_the_hub_stand_lower_path_is_exactly_what_gets_closed():
    """The recorded gap: :8898 commanding stand/lower during a leased window."""
    token = command_lease.acquire("guarded-runner", ttl_s=60)["token"]
    for path in ("/api/rl/stand", "/api/rl/lower", "/api/rl/walk",
                 "/api/standup", "/api/pose", "/api/demo", "/api/zero",
                 "/api/rl/drive/start", "/api/sysid/run"):
        assert command_lease.check("POST", path) is not None, path
        assert command_lease.check("POST", path, token=token) is None, path


def test_abort_path_is_never_gated():
    command_lease.acquire("guarded-runner", ttl_s=60)
    for path in ("/api/rl/stop", "/api/standup/stop", "/api/safe_zero",
                 "/api/bus/recover"):
        assert command_lease.check("POST", path) is None, path
    for word in ("X", "DISARM", "RELAX", "HOLD", "stop", " x "):
        assert command_lease.check("POST", "/cmd", command_line=word) is None
    # ...but an ordinary /cmd motion line is
    assert command_lease.check("POST", "/cmd", command_line="J 0 10") is not None


def test_reads_and_measure_notes_are_never_gated():
    command_lease.acquire("guarded-runner", ttl_s=60)
    assert command_lease.check("GET", "/api/feedback") is None
    assert command_lease.check("GET", "/api/rl/state") is None
    assert command_lease.check("POST", "/api/measure/note") is None


def test_expiry_frees_a_crashed_holder():
    ticks = [100.0]
    clock = lambda: ticks[0]
    command_lease.acquire("crashed", ttl_s=10, clock=clock)
    assert command_lease.check("POST", "/api/rl/stand", clock=clock) is not None
    ticks[0] = 111.0
    assert command_lease.check("POST", "/api/rl/stand", clock=clock) is None
    assert command_lease.state(clock=clock)["held"] is False


def test_holder_refreshes_without_a_gap_and_others_still_cannot_take_it():
    ticks = [0.0]
    clock = lambda: ticks[0]
    token = command_lease.acquire("runner", ttl_s=10, clock=clock)["token"]
    ticks[0] = 9.0
    again = command_lease.acquire("runner", ttl_s=10, token=token, clock=clock)
    assert again["ok"] and again["token"] == token
    ticks[0] = 15.0                       # would have expired without refresh
    assert command_lease.check("POST", "/api/rl/stand", clock=clock) is not None
    taken = command_lease.acquire("mac-hub", ttl_s=10, clock=clock)
    assert taken["ok"] is False and taken["code"] == "command_lease_held"


def test_release_needs_the_holders_token():
    token = command_lease.acquire("runner", ttl_s=60)["token"]
    assert command_lease.release("nope")["ok"] is False
    assert command_lease.release(token)["released"] is True
    assert command_lease.check("POST", "/api/rl/stand") is None


def test_token_is_read_from_header_or_body():
    assert command_lease.token_from_request(
        Headers(**{command_lease.TOKEN_HEADER: " abc "})) == "abc"
    assert command_lease.token_from_request(None, {"command_lease": "xyz"}) == "xyz"
    assert command_lease.token_from_request(None, {"protocol": {}}) == ""


def test_acquire_validates_owner_and_ttl():
    assert command_lease.acquire("")["code"] == "owner_required"
    assert command_lease.acquire("runner", ttl_s=0)["code"] == "bad_ttl"
    assert command_lease.acquire(
        "runner", ttl_s=command_lease.MAX_TTL_S + 1)["code"] == "bad_ttl"


def test_gated_set_tracks_the_servers_own_bus_post_set():
    """Every bus-motion POST is either gated or a named abort path."""
    import web_drive
    uncovered = (set(web_drive.BUS_REQUIRED_POST)
                 - command_lease.GATED_POST
                 - command_lease.ALWAYS_ALLOWED_POST)
    assert uncovered == set(), uncovered
