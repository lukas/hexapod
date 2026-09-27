"""The servo write profile a checkpoint TRAINED with.

2026-09-27: the config default moved from bus.write_speed/acc 400/20 to
2000/80 (the scripted-walk contract the robot has run since 09-01). Every
checkpoint trained before that carries no explicit bus.* cfg-set, so an
eval or export that falls back to the new default would replay the policy
under a different actuator regime than it learned (RESEARCH_RULES: "a
different, incomparable dynamics regime ... false PASSes"). The trainer's
``<checkpoint>.training_complete.json`` sidecar records the resolved motor
contract at train time (``_motor_contract`` in ``resolved_config``); this
module reads it back so eval_checkpoint pins the trained profile when the
caller did not, and export_policy_np stamps it into the artifact for the
robot (linux_control/rl_policy._policy_bus_profile).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_RX = {
    "write_speed": re.compile(r"bus\.write_speed\\?': ([0-9.]+)"),
    "write_acc": re.compile(r"bus\.write_acc\\?': ([0-9.]+)"),
}


def sidecar_path(checkpoint_path) -> Path | None:
    """``<stem>.training_complete.json`` next to the checkpoint; the
    ``_best`` checkpoint shares its run's sidecar."""
    p = Path(checkpoint_path)
    stems = [p.stem]
    if p.stem.endswith("_best"):
        stems.append(p.stem[: -len("_best")])
    for stem in stems:
        cand = p.with_name(stem + ".training_complete.json")
        if cand.is_file():
            return cand
    return None


def trained_bus_profile(checkpoint_path) -> dict | None:
    """{"bus_write_speed": int, "bus_write_acc": int, "bus_profile_origin":
    str} from the sidecar's recorded motor contract, or None when the
    checkpoint has no sidecar / the sidecar predates the contract record."""
    sc = sidecar_path(checkpoint_path)
    if sc is None:
        return None
    try:
        text = json.load(open(sc)).get("resolved_config", "")
    except Exception:  # noqa: BLE001 -- unreadable sidecar = no information
        return None
    text = str(text)
    i = text.find("_motor_contract")
    if i < 0:
        return None
    seg = text[i:]
    out = {}
    for key, rx in _RX.items():
        m = rx.search(seg)
        if m:
            out["bus_" + key] = int(round(float(m.group(1))))
    if "bus_write_speed" not in out or "bus_write_acc" not in out:
        return None
    out["bus_profile_origin"] = f"training sidecar {sc.name}"
    return out


def pin_trained_bus_profile(cfg: dict, checkpoint_path, *, caller_keys=(),
                            log=print) -> dict | None:
    """Unless the CALLER pinned bus.write_speed/write_acc itself (``caller_keys``
    = the dotted keys it passed via --cfg-set), set them (and the speed
    ceiling sentinel) to the checkpoint's trained profile -- the loaded cfg
    always carries the config.yaml default, so its presence is not a pin.
    Returns the profile applied, or None (caller pinned it, or unknown)."""
    pinned = {str(k).split("=", 1)[0] for k in caller_keys}
    if pinned & {"bus.write_speed", "bus.write_acc"}:
        return None
    prof = trained_bus_profile(checkpoint_path)
    if prof is None:
        return None
    bus = cfg.setdefault("bus", {})
    bus["write_speed"] = prof["bus_write_speed"]
    bus["write_acc"] = prof["bus_write_acc"]
    bus["servo_vel_max_counts_s"] = "write_speed"
    if log is not None:
        log(f"[motor-contract] pinned bus.write_speed={bus['write_speed']} "
            f"write_acc={bus['write_acc']} from {prof['bus_profile_origin']} "
            "(no --cfg-set bus.write_speed/acc given; the trained profile "
            "wins over the config default)")
    return prof
