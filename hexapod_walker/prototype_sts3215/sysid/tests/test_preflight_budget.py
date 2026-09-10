"""The pre-run check is one health read in ten seconds. Pin it there.

Every extra pre-run verification step was added by an agent for a good local
reason; together they made a 156 s measurement take 40 minutes and $50 to
start. This test exists so the next addition fails loudly.
"""
import time

import pytest

from sysid import run_hw


class _Client:
    def __init__(self, fb, delay_s=0.0):
        self.fb, self.delay_s, self.calls = fb, delay_s, 0

    def feedback(self):
        self.calls += 1
        if self.delay_s:
            time.sleep(self.delay_s)
        return self.fb


def test_the_preflight_budget_is_ten_seconds():
    assert run_hw.PREFLIGHT_BUDGET_S == 10.0


def test_a_healthy_read_passes_with_exactly_one_call():
    client = _Client({"ok": True, "live": 18, "roll_deg": 0.1, "pitch_deg": 0.2})
    fb = run_hw._preflight_within_budget(client, run_hw.PREFLIGHT_BUDGET_S)
    assert fb["live"] == 18
    assert client.calls == 1, "preflight is one read, not a sampling campaign"


@pytest.mark.parametrize("fb", [
    {"ok": False, "live": 18},
    {"ok": True, "live": 17},
    {},
])
def test_an_unhealthy_read_fails(fb):
    with pytest.raises(SystemExit, match="preflight failed"):
        run_hw._preflight_within_budget(_Client(fb), run_hw.PREFLIGHT_BUDGET_S)


def test_a_read_that_blows_the_budget_fails_and_says_so():
    client = _Client({"ok": True, "live": 18}, delay_s=0.05)
    with pytest.raises(SystemExit, match="exceeded its 0 s budget"):
        run_hw._preflight_within_budget(client, 0.0)
