"""Push linux_control to the robot between runs, when main carries code the
robot does not have. Uses the repo's own deploy_ssh.sh from the runner
checkout with the robot named explicitly: the script's default resolution
goes through a shared IP cache that hexapod2's session overwrote today."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from . import robot
from .config import Settings
from .store import Store


def deploy_if_needed(settings: Settings, store: Store, *, log=print, run=subprocess.run) -> Dict[str, Any]:
    if not settings.deploy_flag.exists():
        return {"deployed": False, "reason": "nothing pending"}
    if store.running_run():
        return {"deployed": False, "reason": "a run is in progress"}
    why = settings.deploy_flag.read_text().strip()[:200]
    script = settings.prototype_dir / "linux_control" / "deploy_ssh.sh"
    env = dict(os.environ, HEXAPOD_SSH=settings.robot_ssh, HEXAPOD_HOST=settings.robot_url)
    log(f"deploying to robot ({why})")
    try:
        proc = run([str(script)], cwd=script.parent, env=env, capture_output=True, text=True,
                   timeout=settings.deploy_timeout_s)
        ok, tail = proc.returncode == 0, (proc.stdout + proc.stderr)[-600:]
    except subprocess.TimeoutExpired:
        ok, tail = False, f"deploy exceeded {settings.deploy_timeout_s:.0f} s"
    except OSError as exc:
        ok, tail = False, str(exc)
    if ok:
        try:
            robot.health(settings.robot_url, 30.0)
        except Exception as exc:  # noqa: BLE001
            ok, tail = False, f"deployed but robot not healthy after: {exc}"
    if ok:
        settings.deploy_flag.unlink(missing_ok=True)
        store.add_event("deploy", f"deployed: {why}")
    else:
        store.add_event("deploy", f"DEPLOY FAILED ({why}): {tail[-300:]}")
        # Leave the flag so the next boundary retries once more, then give up.
        retries = settings.data_dir / "DEPLOY_RETRIES"
        n = int(retries.read_text() or 0) + 1 if retries.exists() else 1
        retries.write_text(str(n))
        if n >= 2:
            settings.deploy_flag.unlink(missing_ok=True)
            retries.unlink(missing_ok=True)
            from . import alerts
            alerts.text(store, "deploy", f"robot deploy failed twice ({why[:80]}). Main has code the robot does not; "
                                         f"run linux_control/deploy_ssh.sh by hand.")
    return {"deployed": ok, "detail": tail[-300:]}
