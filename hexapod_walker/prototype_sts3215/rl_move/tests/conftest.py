"""Suite-wide default: pin the sim to the LEGACY primitive model family.

The behavior tests in this directory (recover rungs, catch teachers, gait
step events, spawn heights, ...) encode dynamics measured on the legacy
``mujoco_prototype`` robot (2.104 kg, hip axis on the yaw plane).  The
mesh-accurate family that ``env.model_source`` defaults to since 2026-08-24
(real CAD kinematics, as-built 3.5 kg masses) settles and loads its feet
differently, so those calibrated assertions do not transfer between the
families — running them against mesh would test nothing but the mismatch.

``HEXAPOD_MODEL_SOURCE`` overrides cfg resolution inside
``servo_model.resolve_model_source``; ``setdefault`` keeps a deliberate
outer override (e.g. a CI matrix leg) working.  Mesh-family coverage lives
in ``test_model_source.py``, which overrides per-test.

NOTE (2026-09-08, operator): the MDP_PREFLIGHT rollout bank
(``test_task_semantics.py``) is retired and this primitive pin is now a
LEGACY default for the remaining calibrated tests only. New tests set the
family they mean explicitly with ``monkeypatch.setenv("HEXAPOD_MODEL_SOURCE",
"mesh")`` and never write ``os.environ`` directly (RESEARCH_RULES "Tests").

NOTE (2026-08-25 leg-sacrifice DIG-IN): `rl_move/config.py:load_config`
grew an analogous `HEXAPOD_CONTROL_HZ` override this same cycle while
chasing a 54-test full-bank regression (was 1 known-red 08-22) that
lines up with config.yaml's `control.hz` default flip 25->100 on 08-24.
It is DELIBERATELY NOT enabled here: forcing hz=25 on a sample
(`test_walk_gait_gate_*`) made the failures WORSE, not better (e.g.
flag-leg gate return-hit dropped from 369 at the current hz=100 default
to 37 at hz=25) — the hz flip is at most a partial contributor, not the
full explanation, and blindly pinning to the old rate is unvalidated and
was reverted rather than shipped. Root cause of the 54-test regression
is still OPEN; see OPERATOR_QUESTIONS.md 2026-08-25.
"""
import os

os.environ.setdefault("HEXAPOD_MODEL_SOURCE", "primitive")


# ---------------------------------------------------------------------------
# Ledger fixture: the orchestrator's ledger is a directory of per-entry
# files, ``<state>/ledger/NNNNNN-<run>.json`` (seq prefix = identity and
# order, ``ledger_seq`` repeated inside). ``rl_move.ledger`` reads it from
# ``$HEXAPOD_STATE_DIR``; this fixture writes that layout into a temp state
# dir and points the env var at it.
# ---------------------------------------------------------------------------
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _state_dir_modules():
    """TRANSITIONAL (removed with rl_move/orchestrator): the orchestrator
    tests still in this tree read the ledger through state_dir's module
    constants; patch whichever spellings are importable."""
    mods = []
    try:
        import state_dir as bare
        mods.append(bare)
    except ImportError:
        pass
    try:
        from rl_move.orchestrator import state_dir as pkg
        if all(pkg is not m for m in mods):
            mods.append(pkg)
    except ImportError:
        pass
    return mods


@pytest.fixture
def state_ledger(tmp_path, monkeypatch):
    """Temp state dir behind ``HEXAPOD_STATE_DIR``; returns ``write(entries) -> Path``.

    ``write`` REPLACES the ledger with ``entries`` (numbered 1..N, the way
    the orchestrator's migration numbers a list) and returns the state dir.
    The caller's dicts are not mutated. Call it with ``[]`` for an empty
    ledger.
    """
    root = tmp_path / "state"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("HEXAPOD_STATE_DIR", str(root))
    for mod in _state_dir_modules():
        monkeypatch.setattr(mod, "STATE_DIR", root)
        monkeypatch.setattr(mod, "LEDGER_DIR", root / "ledger")
        monkeypatch.setattr(mod, "LEDGER", root / "ledger")

    def write(entries):
        ledger = root / "ledger"
        shutil.rmtree(ledger, ignore_errors=True)
        ledger.mkdir()
        for seq, e in enumerate(entries, 1):
            entry = {k: v for k, v in e.items() if k != "ledger_seq"}
            entry["ledger_seq"] = seq
            safe = _UNSAFE.sub("_", str(entry.get("run") or "")).strip("._") or "unnamed"
            (ledger / f"{seq:06d}-{safe[:180]}.json").write_text(
                json.dumps(entry, indent=2) + "\n")
        return root
    return write
