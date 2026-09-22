"""Robot-side test rules.

Every test here must finish in under half a second (Lukas, 2026-09-22): the
controller suite is the loop we run before touching a robot, and slow tests
are how it stopped being run.  A test that needs more time is testing the
wrong thing (real waits, planners, sims): fake the clock, cut the scope, or
move it under rl_move/tests with the ``slow`` marker.
"""
from __future__ import annotations

import pytest

MAX_TEST_SECONDS = 0.5


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.passed and call.duration > MAX_TEST_SECONDS:
        report.outcome = "failed"
        report.longrepr = (f"{item.nodeid} took {call.duration:.2f} s; robot-side tests must finish "
                           f"in {MAX_TEST_SECONDS:.1f} s (fake the clock or cut the scope)")
