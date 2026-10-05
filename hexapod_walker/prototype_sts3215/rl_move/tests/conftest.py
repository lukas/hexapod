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

NOTE (2026-09-30 DIG-IN, this one IS enabled): a full-suite run found 28
newly-failing tests (was ~2 known flakes as of 09-30 ~04:5x) that `git
bisect` + cross-model-family replay root-caused to commit 867835836
(2026-09-27, operator: "we should open it up for faster movement") —
config.yaml's `safety.max_delta_q_deg` default flipped 0.375 -> 1.76 to
match the real servo bus speed for the mesh/hardware family. This
PRIMITIVE-pinned suite builds fresh envs via `load_config()` with no
trained-artifact stamp to pin the legacy slew back, so it silently
inherited the wider cap; unlike the 08-25 HEXAPOD_CONTROL_HZ case above,
this one is a confirmed, complete, mechanistic explanation (a zero-
action tick snaps the PRIMITIVE model's start pose toward its commanded
target fast enough to trip the fall detector inside the opening 1s
zero-command hold — 100% reproducible, e.g.
`test_phase_contact_reward_pays_agreement` terminates at tick 28/300
with `HEXAPOD_MODEL_SOURCE=primitive`, never with mesh/default), so
pinning it here is a validated fix, not an unvalidated guess. Only
affects `HEXAPOD_MODEL_SOURCE=primitive`-pinned test envs; the new 1.76
default for real (mesh/hardware) runs is untouched.
"""
import os

os.environ.setdefault("HEXAPOD_MODEL_SOURCE", "primitive")
os.environ.setdefault("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", "0.375")


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


def pytest_collection_modifyitems(config, items):
    """Refuse accidental SERIAL full-suite runs (meta 2026-10-05).

    The full suite is ~3k tests: serial takes 12-60 min and wedges a
    decision cycle into background/wait-poll turns (measured twice on
    10-04/10-05, ~15 min + ~$2 each). ``ops.sh testfull`` (xdist -n 32)
    runs it in ~5 min and ``ops.sh testdiff`` diffs failures against
    ``known_failures.txt``. Small targeted runs are unaffected; set
    ``HEXAPOD_SERIAL_SUITE=1`` to deliberately run the suite serially.
    """
    if (len(items) > 500
            and not os.environ.get("PYTEST_XDIST_WORKER")
            and not os.environ.get("HEXAPOD_SERIAL_SUITE")
            and not getattr(config.option, "numprocesses", None)
            and not getattr(config.option, "collectonly", False)):
        raise pytest.UsageError(
            f"{len(items)} tests collected with no xdist workers: use "
            "`/workspace/hexapod-orchestrator/orchestrator/ops.sh testfull` "
            "(~5 min parallel) or `ops.sh testdiff` (suite + baseline diff). "
            "HEXAPOD_SERIAL_SUITE=1 overrides.")


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
