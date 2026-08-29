"""Route parity between the robot web server and the Mac sim web server.

The web UI (linux_control/webui/) is served by BOTH servers, so every
``/api/rl/*`` route the UI can hit must exist on both sides — the mirrored
route surface IS the sim/robot parity feature. This test enforces the
"add features in both servers" rule mechanically instead of by memory:

- every sim route must exist on the robot server, and
- robot-only routes must be listed in ROBOT_ONLY below (hardware-bound
  endpoints that have no sim meaning).

Routes are extracted statically from the two dispatcher sources (both are
hand-written ``elif path == "/api/rl/..."`` chains), so the test needs no
server startup and no hardware.
"""
from __future__ import annotations

import re
from pathlib import Path

_PROTO = Path(__file__).resolve().parents[2]
ROBOT_SERVER = _PROTO / "linux_control" / "web_drive.py"
SIM_SERVER = _PROTO / "rl_move" / "sim" / "web_server.py"

# Hardware-bound endpoints deliberately absent from the sim server. Adding
# a route here is a decision, not an accident: it means the web UI must
# handle its absence when driving the sim.
ROBOT_ONLY = {
    "/api/rl",                  # bare alias of /api/rl/state
    "/api/rl/state",            # live servo/estimator state
    "/api/rl/find_plant",       # physical plant acquisition
    "/api/rl/set_stance",       # physical stance jog
    "/api/rl/probe_dynamics",   # hardware dynamics probe
}


def _extract_rl_routes(source: Path) -> set[str]:
    """All quoted /api/rl route literals in a dispatcher source file.

    Trailing-slash literals are ``startswith`` prefixes for name-carrying
    routes (e.g. "/api/rl/policies/"); normalize them so both servers
    compare equal regardless of how the name capture is written.
    """
    routes: set[str] = set()
    for m in re.finditer(r'"(/api/rl(?:/[^"]*)?)"', source.read_text()):
        route = m.group(1)
        routes.add(route + "<name>" if route.endswith("/") else route)
    return routes


def test_sim_server_covers_every_ui_rl_route() -> None:
    robot = _extract_rl_routes(ROBOT_SERVER)
    sim = _extract_rl_routes(SIM_SERVER)
    missing_on_robot = sorted(sim - robot)
    assert not missing_on_robot, (
        "sim web_server.py serves /api/rl routes the robot web_drive.py "
        f"does not: {missing_on_robot} — add them to the robot server "
        "(the UI is shared; features must land on both sides)")


def test_robot_only_rl_routes_are_the_documented_hardware_set() -> None:
    robot = _extract_rl_routes(ROBOT_SERVER)
    sim = _extract_rl_routes(SIM_SERVER)
    robot_only = robot - sim
    undocumented = sorted(robot_only - ROBOT_ONLY)
    assert not undocumented, (
        f"new robot-only /api/rl routes: {undocumented} — either add them "
        "to rl_move/sim/web_server.py (preferred; the UI is shared) or, if "
        "they are hardware-bound, add them to ROBOT_ONLY in this test")
    stale = sorted(ROBOT_ONLY - robot_only)
    assert not stale, (
        f"ROBOT_ONLY entries no longer robot-only: {stale} — remove them "
        "from the allowlist")


def test_route_sets_are_nonempty_sanity() -> None:
    # Guards the regex against dispatcher refactors that would silently
    # make the parity assertions vacuous.
    assert len(_extract_rl_routes(ROBOT_SERVER)) >= 15
    assert len(_extract_rl_routes(SIM_SERVER)) >= 12
